"""
make.py
========

Hugo-style Markdown to HTML Static Site Generator

Core logic for building a static website from Markdown and other content sources.
Supports Jinja2 templating, asset management, navigation, accessibility, and SQLite integration.

Debug mode and logging level are controlled via environment variables:
    DEBUG=1 enables debug logging and extra error details.
    LOG_LEVEL sets the logging level (default: INFO).
"""

import os
import logging
import yaml
import re
import sqlite3
import shutil
import base64
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.texmath import texmath_plugin
import html
from oerforge import db_utils
from oerforge.copyfile import copy_db_images_to_build, copy_static_assets_to_build

# --- Configurable Environment ---
DEBUG_MODE = os.environ.get("DEBUG", "0") == "1"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

BUILD_DIR = 'build'
FILES_DIR = 'files'
LOG_DIR = 'log'
LOG_FILENAME = 'build.log'

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_FILES_DIR = os.path.join(PROJECT_ROOT, BUILD_DIR, FILES_DIR)
BUILD_HTML_DIR = os.path.join(PROJECT_ROOT, BUILD_DIR)
LOG_PATH = os.path.join(PROJECT_ROOT, LOG_DIR, LOG_FILENAME)
LAYOUTS_DIR = os.path.join(PROJECT_ROOT, 'layouts')

def extract_title_and_body(md_text, default_title="Untitled"):
    """
    Extract the first # header as title and the rest as body.
    """
    lines = md_text.splitlines()
    title = default_title
    body_lines = []
    found_title = False
    for line in lines:
        if not found_title and line.strip().startswith('# '):
            title = line.strip()[2:].strip()
            found_title = True
            continue
        body_lines.append(line)
    body_text = '\n'.join(body_lines)
    return title, body_text

def slugify(title: str) -> str:
    """Convert a title to a slug suitable for folder names."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def load_yaml_config(config_path: str) -> dict:
    """Load and parse the YAML config file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logging.info(f"Loaded YAML config from {config_path}")
        return config
    except Exception as e:
        logging.error(f"Failed to load YAML config: {e}")
        return {}

def ensure_output_dir(md_path):
    """Ensure the output directory for the HTML file exists, mirroring build/files structure."""
    rel_path = os.path.relpath(md_path, BUILD_FILES_DIR)
    output_dir = os.path.join(BUILD_HTML_DIR, os.path.dirname(rel_path))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

def setup_template_env():
    """Set up Jinja2 template environment."""
    layouts_default = os.path.join(LAYOUTS_DIR, '_default')
    layouts_partials = os.path.join(LAYOUTS_DIR, 'partials')
    env = Environment(
        loader=FileSystemLoader([LAYOUTS_DIR, layouts_default, layouts_partials]),
        autoescape=select_autoescape(['html', 'xml'])
    )
    return env

def render_page(context: dict, template_name: str) -> str:
    """
    Render a page using Hugo-style templates (baseof.html, single.html, partials).
    """
    env = setup_template_env()
    template = env.get_template(f'_default/{template_name}')
    return template.render(**context)

def generate_nav_menu(context: dict) -> list:
    """
    Generate top-level navigation menu items from content table using relative_link and menu_context.
    Returns a list of menu item dicts: [{"title": ..., "link": ...}, ...]
    """
    db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Use parent_slug IS NULL for top-level navigation items
        sql = "SELECT title, relative_link FROM content WHERE menu_context='main' AND parent_slug IS NULL ORDER BY \"order\";"
        cursor.execute(sql)
        rows = cursor.fetchall()
    rel_path = context.get('rel_path', '')
    menu_items = []
    for title, relative_link in rows:
        target = 'index.html' if title and title.lower() == 'home' else relative_link
        current_dir = os.path.dirname(rel_path) if rel_path else ''
        is_section_index = rel_path.endswith('index.html') and current_dir and rel_path != 'index.html'
        if rel_path:
            if is_section_index:
                link = "index.html" if target == rel_path or os.path.normpath(target) == os.path.normpath(rel_path) else "../" + target
            else:
                link = os.path.relpath(target, current_dir) if not os.path.isabs(target) else target
        else:
            link = target
        menu_items.append({'title': title, 'link': link})
    return menu_items

def convert_markdown_to_html(md_path: str) -> str:
    """
    Convert markdown file to HTML using markdown-it-py, rewriting local image paths.
    """
    def custom_image_renderer(self, tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrs.get('src', '')
        alt = html.escape(token.content) or "Image"
        db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
        referenced_page = env.get('referenced_page', '')
        filename = os.path.basename(src)
        image_record = db_utils.get_image_record(referenced_page, filename, db_path=db_path)
        if image_record:
            # Always use build/images/<filename>
            image_build_path = os.path.join('images', filename)
            # Compute relative path from current HTML file
            rel_path = env.get('rel_path', 'index.html')
            image_src = os.path.relpath(image_build_path, os.path.dirname(rel_path))
            
            return f'<img src="{image_src}" alt="{alt}">'
        else:
            logging.warning(f"Missing image in DB: {src} (referenced from {referenced_page})")
            return f'<span class="missing-image">{alt} [Image not found]</span>'
    
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    md.use(footnote_plugin)
    md.use(texmath_plugin)
    md.add_render_rule('image', custom_image_renderer)
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    html_body = md.render(md_text)
    html_body = html_body.replace('<table>', '<table role="table">')
    html_body = html_body.replace('<th>', '<th role="columnheader">')
    html_body = html_body.replace('<td>', '<td role="cell">')
    html_body = html_body.replace('<ul>', '<ul role="list">')
    html_body = html_body.replace('<ol>', '<ol role="list">')
    html_body = html_body.replace('<li>', '<li role="listitem">')
    html_body = html_body.replace('<nav>', '<nav role="navigation">')
    html_body = html_body.replace('<header>', '<header role="banner">')
    html_body = html_body.replace('<footer>', '<footer role="contentinfo">')
    mathjax_script = '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
    html_body += mathjax_script
    return html_body

def convert_markdown_to_html_text(md_text: str, referenced_page: str, rel_path: str) -> str:
    """
    Convert markdown text to HTML using markdown-it-py, rewriting image paths using DB records.
    Args:
        md_text: Markdown content as a string.
        referenced_page: Source markdown file path (for DB lookup).
        rel_path: Relative path of output HTML file (for correct image linking).
    Returns:
        HTML string with images embedded using DB-driven paths.
    """
    def custom_image_renderer(self, tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrs.get('src', '')
        alt = html.escape(token.content) or "Image"
        db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
        filename = os.path.basename(src)
        referenced_page_val = env.get('referenced_page', '')
        rel_path_val = env.get('rel_path', 'index.html')
        image_record = db_utils.get_image_record(referenced_page_val, filename, db_path=db_path)
        if image_record:
            image_build_path = os.path.join('images', filename)
            image_src = os.path.relpath(image_build_path, os.path.dirname(rel_path_val))
            return f'<img src="{image_src}" alt="{alt}">'
        else:
            logging.warning(f"Missing image in DB: {src} (referenced from {referenced_page_val})")
            return f'<span class="missing-image">{alt} [Image not found]</span>'
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    md.use(footnote_plugin)
    md.use(texmath_plugin)
    md.add_render_rule('image', custom_image_renderer)
    env = {'referenced_page': referenced_page, 'rel_path': rel_path}
    html_body = md.render(md_text, env=env)
    html_body = html_body.replace('<table>', '<table role="table">')
    html_body = html_body.replace('<th>', '<th role="columnheader">')
    html_body = html_body.replace('<td>', '<td role="cell">')
    html_body = html_body.replace('<ul>', '<ul role="list">')
    html_body = html_body.replace('<ol>', '<ol role="list">')
    html_body = html_body.replace('<li>', '<li role="listitem">')
    html_body = html_body.replace('<nav>', '<nav role="navigation">')
    html_body = html_body.replace('<header>', '<header role="banner">')
    html_body = html_body.replace('<footer>', '<footer role="contentinfo">')
    mathjax_script = '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
    html_body += mathjax_script
    return html_body

def get_asset_path(asset_type, asset_name, rel_path):
    """
    Compute the relative asset path for a given file.
    """
    depth = rel_path.count(os.sep)
    prefix = '../' * depth if depth > 0 else ''
    return f"{prefix}{asset_type}/{asset_name}"

def add_asset_paths(context, rel_path):
    """
    Add asset paths to the template context.
    """
    context['css_path'] = get_asset_path('css', 'theme-dark.css', rel_path)
    context['js_path'] = get_asset_path('js', 'main.js', rel_path)
    logo_file = context.get('site', {}).get('logo', 'static/images/logo.png')
    logo_name = os.path.basename(logo_file)
    context['logo_path'] = get_asset_path('images', logo_name, rel_path)
    return context

def build_all_markdown_files():
    """
    Build all markdown files using Hugo-style rendering, using first # header as title.
    """
    config_path = os.path.join(PROJECT_ROOT, '_content.yml')
    config = load_yaml_config(config_path)
    site = config.get('site', {})
    toc = config.get('toc', [])
    footer_text = config.get('footer', {}).get('text', '')
    db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_path, output_path, title, mime_type FROM content")
        records = cursor.fetchall()
    homepage_md = os.path.join(PROJECT_ROOT, 'content', 'index.md')
    homepage_html = os.path.join(BUILD_HTML_DIR, 'index.html')
    if os.path.exists(homepage_md):
        try:
            with open(homepage_md, 'r', encoding='utf-8') as f:
                md_text = f.read()
            title, body_text = extract_title_and_body(md_text, "Home")
            rel_path = 'index.html'
            html_body = convert_markdown_to_html_text(body_text, homepage_md, rel_path)
            top_menu = generate_nav_menu({'rel_path': rel_path, 'toc': toc}) or []
            context = {
                'Title': title,
                'Content': html_body,
                'toc': toc,
                'top_menu': top_menu,
                'site': site,
                'footer_text': footer_text,
                'output_file': 'index.html',
                'rel_path': 'index.html',
            }
            context = add_asset_paths(context, rel_path)
            html_output = render_page(context, 'single.html')
            with open(homepage_html, 'w', encoding='utf-8') as f:
                f.write(html_output)
            logging.info(f"[AUTO] Built homepage: {homepage_html}")
        except Exception as e:
            logging.error(f"Failed to build homepage from {homepage_md}: {e}")
            if DEBUG_MODE:
                import traceback
                logging.error(traceback.format_exc())
    for source_path, output_path, db_title, mime_type in records:
        if not source_path or not output_path:
            logging.info(f"Skipping record with missing source_path or output_path: title={db_title}, source_path={source_path}, output_path={output_path}")
            continue
        ext = os.path.splitext(source_path)[1].lower()
        if ext == '.md' or (mime_type and 'markdown' in mime_type.lower()):
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    md_text = f.read()
            except Exception as e:
                logging.error(f"Failed to read markdown file {source_path}: {e}")
                if DEBUG_MODE:
                    import traceback
                    logging.error(traceback.format_exc())
                continue
            title, body_text = extract_title_and_body(md_text, db_title or "Untitled")
            # Always set output_path_final and rel_path before rendering
            md_basename = os.path.splitext(os.path.basename(source_path))[0]
            parent_dir = os.path.basename(os.path.dirname(source_path))
            # --- Section index logic ---
            if md_basename == '_index':
                # Section index: output to section/index.html
                output_dir = os.path.join(BUILD_HTML_DIR, parent_dir)
                os.makedirs(output_dir, exist_ok=True)
                output_path_final = os.path.join(output_dir, 'index.html')
                rel_path = os.path.relpath(output_path_final, BUILD_HTML_DIR)
                output_file = 'index.html'
            else:
                # Top-level page: output to about.html (or filename.html) at root
                output_path_final = os.path.join(BUILD_HTML_DIR, f"{md_basename}.html")
                os.makedirs(BUILD_HTML_DIR, exist_ok=True)
                rel_path = os.path.relpath(output_path_final, BUILD_HTML_DIR)
                output_file = f"{md_basename}.html"
            html_body = convert_markdown_to_html_text(body_text, source_path, rel_path)
            top_menu = generate_nav_menu({'rel_path': rel_path, 'toc': toc}) or []
            # --- Copy source file to build/files/ and insert DB record for download ---
            try:
                from oerforge.copyfile import copy_to_build
                copied_md_path = copy_to_build(source_path)
                # Insert record for markdown file if not already present
                files_exist = db_utils.get_records(
                    'files',
                    where_clause="referenced_page=? AND extension='.md'",
                    params=(source_path,),
                    db_path=db_path
                )
                if not files_exist:
                    db_utils.insert_records(
                        'files',
                        [{
                            'filename': os.path.basename(copied_md_path),
                            'extension': '.md',
                            'mime_type': 'text/markdown',
                            'url': copied_md_path,
                            'referenced_page': source_path,
                            'relative_path': copied_md_path
                        }],
                        db_path=db_path
                    )
            except Exception as e:
                logging.error(f"Failed to copy markdown or insert DB record for {source_path}: {e}")
            # --- Query converted files for download buttons ---
            downloads = []
            try:
                file_records = db_utils.get_records(
                    'files',
                    where_clause="referenced_page=?",
                    params=(source_path,),
                    db_path=db_path
                )
                for file_rec in file_records:
                    file_rel_path = os.path.relpath(file_rec['url'], os.path.dirname(output_path_final))
                    downloads.append({
                        'filename': file_rec['filename'],
                        'extension': file_rec['extension'],
                        'mime_type': file_rec['mime_type'],
                        'url': file_rel_path
                    })
            except Exception as e:
                logging.error(f"Failed to query downloads for {source_path}: {e}")
            context = {
                'Title': title,
                'Content': html_body,
                'toc': toc,
                'top_menu': top_menu,
                'site': site,
                'footer_text': footer_text,
                'output_file': output_file,
                'rel_path': rel_path,
                'downloads': downloads,
            }
            context = add_asset_paths(context, rel_path)
            try:
                html_output = render_page(context, 'single.html')
            except Exception as render_err:
                logging.error(f"[ERROR] Template rendering failed for {source_path}: {render_err}")
                if DEBUG_MODE:
                    import traceback
                    logging.error(traceback.format_exc())
                html_output = None
            if html_output:
                try:
                    with open(output_path_final, 'w', encoding='utf-8') as f:
                        f.write(html_output)
                except Exception as e:
                    logging.error(f"Failed to write HTML file {output_path_final}: {e}")
                    if DEBUG_MODE:
                        import traceback
                        logging.error(traceback.format_exc())
    # --- Section Index Generation (DB-driven) ---
    from oerforge.db_utils import get_top_level_sections, get_children_for_section, get_section_by_slug

    def build_section_index_db(section_slug, parent_dir):
        """
        Build index.html for a section using DB-driven hierarchy.
        Uses new db_utils utilities for clarity and extensibility.
        """
        section_dir = os.path.join(BUILD_HTML_DIR, parent_dir)
        index_html_path = os.path.join(section_dir, 'index.html')
        if os.path.exists(index_html_path):
            return
        os.makedirs(section_dir, exist_ok=True)
        # Query children from DB
        children = get_children_for_section(section_slug, db_path=db_path)
        children_list = []
        for child in children:
            child_slug = child.get('slug')
            child_title = child.get('title', child_slug)
            child_output = child.get('output_path')
            is_section_index = child.get('is_section_index', 0)
            if child_slug:
                if is_section_index:
                    child_index = os.path.join(child_slug, 'index.html')
                    children_list.append({
                        'link': child_index,
                        'title': child_title,
                        'description': child.get('description', ''),
                        'level': child.get('level', 0)
                    })
                    next_parent_dir = os.path.join(parent_dir, child_slug) if parent_dir else child_slug
                    build_section_index_db(child_slug, next_parent_dir)
                elif child_output:
                    child_rel = os.path.relpath(child_output, section_dir)
                    children_list.append({
                        'link': child_rel,
                        'title': child_title,
                        'description': child.get('description', ''),
                        'level': child.get('level', 0)
                    })
        # Query section record for title
        section_record = get_section_by_slug(section_slug, db_path=db_path)
        section_title = section_record.get('title', section_slug) if section_record else section_slug
        # Always populate top_menu and site context for navigation and completeness
        rel_path = os.path.relpath(index_html_path, BUILD_HTML_DIR)
        config_path = os.path.join(PROJECT_ROOT, '_content.yml')
        config = load_yaml_config(config_path)
        site = config.get('site', {})
        toc = config.get('toc', [])
        footer_text = config.get('footer', {}).get('text', '')
        top_menu = generate_nav_menu({'rel_path': rel_path, 'toc': toc}) or []
        context = {
            'Title': section_title,
            'Children': children_list,
            'top_menu': top_menu,
            'site': site,
            'footer_text': footer_text,
            'output_file': 'index.html',
            'rel_path': rel_path,
            'downloads': [],
        }
        context = add_asset_paths(context, rel_path)
        try:
            html_output = render_page(context, 'section.html')
        except Exception:
            html_output = None
        if html_output:
            with open(index_html_path, 'w', encoding='utf-8') as f:
                f.write(html_output)
        else:
            with open(index_html_path, 'w', encoding='utf-8') as f:
                f.write(f'<h1>{section_title}</h1><p>No content found in this section.</p>')
        logging.info(f"[AUTO] Generated section index: {index_html_path}")

    # Build section indices for all top-level sections in DB
    top_sections = get_top_level_sections(db_path=db_path)
    for section in top_sections:
        section_slug = section.get('slug')
        if section_slug:
            build_section_index_db(section_slug, section_slug)
    copy_static_assets_to_build()
    copy_db_images_to_build()
    logging.info("[AUTO] All markdown files built.")

#=================


 
if __name__ == "__main__":
    import sys
    config_file = "_content.yml"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    build_all_markdown_files()