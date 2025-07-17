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
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'log', 'build.log')
# Force DEBUG logging if DEBUG_MODE is enabled
if DEBUG_MODE:
    log_level = logging.DEBUG
else:
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

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
        if DEBUG_MODE:
            logging.debug(f"[MAKE] YAML config loaded: {config}")
        return config
    except Exception as e:
        logging.error(f"Failed to load YAML config: {e}")
        if DEBUG_MODE:
            import traceback
            logging.error(traceback.format_exc())
        return {}

def ensure_output_dir(md_path):
    """Ensure the output directory for the HTML file exists, mirroring build/files structure."""
    rel_path = os.path.relpath(md_path, BUILD_FILES_DIR)
    output_dir = os.path.join(BUILD_HTML_DIR, os.path.dirname(rel_path))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        if DEBUG_MODE:
            logging.debug(f"[MAKE] Created output directory: {output_dir}")

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
    # Use toc from context or config for navigation
    toc = context.get('toc')
    if toc is None:
        config_path = os.path.join(PROJECT_ROOT, '_content.yml')
        config = load_yaml_config(config_path)
        toc = config.get('toc', [])

    rel_path = context.get('rel_path', '')

    def compute_menu_link(item, rel_path):
        """
        Compute menu link for a toc item, handling top-level and section index cases.
        """
        # Home page
        if item.get('file', '') == 'index.md':
            target = 'index.html'
        elif 'file' in item:
            md_basename = os.path.splitext(os.path.basename(item['file']))[0]
            # Section index
            if md_basename == '_index':
                parent_dir = item.get('slug', md_basename)
                target = os.path.join(parent_dir, 'index.html')
            else:
                target = f"{md_basename}.html"
        elif 'slug' in item:
            target = os.path.join(item['slug'], 'index.html')
        else:
            target = 'index.html'

        if not rel_path:
            return target
        current_dir = os.path.dirname(rel_path)
        is_section_index = rel_path.endswith('index.html') and current_dir and rel_path != 'index.html'
        if is_section_index:
            if os.path.normpath(target) == os.path.normpath(rel_path):
                return 'index.html'
            if not os.path.dirname(target):
                return f"../{target}"
            return os.path.relpath(target, current_dir)
        else:
            return os.path.relpath(target, current_dir) if not os.path.isabs(target) else target

    menu_items = []
    for item in toc:
        if not item.get('menu', False):
            continue
        title = item.get('title', 'Untitled')
        link = compute_menu_link(item, rel_path)
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

    def rewrite_md_links(tokens, target_ext='.html'):
        for token in tokens:
            if token.type == 'inline' and token.children:
                for child in token.children:
                    if child.type == 'link_open' and child.attrs:
                        href = child.attrGet('href')
                        if href and href.endswith('.md') and not href.startswith('http'):
                            child.attrSet('href', href[:-3] + target_ext)
            if token.children:
                rewrite_md_links(token.children, target_ext)
        return tokens

    tokens = md.parse(md_text)
    tokens = rewrite_md_links(tokens)
    html_body = md.renderer.render(tokens, md.options, {})
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

    def rewrite_md_links(tokens, target_ext='.html'):
        for token in tokens:
            if token.type == 'inline' and token.children:
                for child in token.children:
                    if child.type == 'link_open' and child.attrs:
                        href = child.attrGet('href')
                        if href and href.endswith('.md') and not href.startswith('http'):
                            child.attrSet('href', href[:-3] + target_ext)
            if token.children:
                rewrite_md_links(token.children, target_ext)
        return tokens

    tokens = md.parse(md_text, env=env)
    tokens = rewrite_md_links(tokens)
    html_body = md.renderer.render(tokens, md.options, env)
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
    if DEBUG_MODE:
        logging.debug(f"[MAKE] build_all_markdown_files: site={site}, toc={toc}, footer={footer_text}")
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
    def walk_toc_for_files(toc, parent_dir=None):
        """
        Yield (source_path, output_path, title, rel_path) for each file in toc tree.
        Only build files explicitly listed in toc. No auto-generated section indices or navigation.
        """
        for item in toc:
            slug = item.get('slug', parent_dir)
            if DEBUG_MODE:
                logging.debug(f"[MAKE] walk_toc_for_files: item={item}, parent_dir={parent_dir}")
            # Only yield if 'file' is present
            if item.get('file'):
                src_path = os.path.join(PROJECT_ROOT, 'content', item['file'])
                md_basename = os.path.splitext(os.path.basename(item['file']))[0]
                if not slug and md_basename == 'index':
                    out_path = os.path.join(BUILD_HTML_DIR, 'index.html')
                    rel_path = 'index.html'
                    if DEBUG_MODE:
                        logging.debug(f"[MAKE] Output path for homepage: {out_path}")
                elif md_basename == '_index' and slug:
                    out_path = os.path.join(BUILD_HTML_DIR, slug, 'index.html')
                    rel_path = os.path.join(slug, 'index.html')
                    if DEBUG_MODE:
                        logging.debug(f"[MAKE] Output path for section index: {src_path} -> {out_path}")
                elif slug:
                    out_path = os.path.join(BUILD_HTML_DIR, slug, f"{md_basename}.html")
                    rel_path = os.path.join(slug, f"{md_basename}.html")
                    if DEBUG_MODE:
                        logging.debug(f"[MAKE] Output path for file: {src_path} -> {out_path}")
                else:
                    out_path = os.path.join(BUILD_HTML_DIR, f"{md_basename}.html")
                    rel_path = f"{md_basename}.html"
                    if DEBUG_MODE:
                        logging.debug(f"[MAKE] Output path (default): {src_path} -> {out_path}")
                yield (src_path, out_path, item.get('title', md_basename), rel_path)
            # Recurse into children if present and is a list
            children = item.get('children')
            if isinstance(children, list) and children:
                if DEBUG_MODE:
                    logging.debug(f"[MAKE] Recursing into children for slug={slug}")
                yield from walk_toc_for_files(children, parent_dir=slug)

    # Build only files listed in toc, no auto-generated section indices or child navigation
    for src_path, out_path, title, rel_path in walk_toc_for_files(toc):
        if DEBUG_MODE:
            logging.debug(f"[MAKE] Building file: src={src_path}, out={out_path}, title={title}, rel_path={rel_path}")
        if not os.path.exists(src_path):
            logging.warning(f"Source markdown not found: {src_path}")
            continue
        try:
            with open(src_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
        except Exception as e:
            logging.error(f"Failed to read markdown file {src_path}: {e}")
            if DEBUG_MODE:
                import traceback
                logging.error(traceback.format_exc())
            continue
        page_title, body_text = extract_title_and_body(md_text, title or "Untitled")
        html_body = convert_markdown_to_html_text(body_text, src_path, rel_path)
        top_menu = generate_nav_menu({'rel_path': rel_path, 'toc': toc}) or []
        # Always set source_path to the relative markdown file path used for build
        md_basename = os.path.splitext(os.path.basename(src_path))[0]
        mime_type = 'section' if md_basename == '_index' else 'text/markdown'
        rel_source_path = os.path.relpath(src_path, PROJECT_ROOT)
        rel_output_path = os.path.relpath(out_path, PROJECT_ROOT)
        record = {
            'source_path': rel_source_path,
            'output_path': rel_output_path,
            'title': page_title,
            'mime_type': mime_type,
        }
        db_utils.insert_records('content', [record], db_path=db_path)
        context = {
            'Title': page_title,
            'Content': html_body,
            'toc': toc,
            'top_menu': top_menu,
            'site': site,
            'footer_text': footer_text,
            'output_file': os.path.basename(out_path),
            'rel_path': rel_path,
            'downloads': [],
        }
        context = add_asset_paths(context, rel_path)
        try:
            html_output = render_page(context, 'single.html')
        except Exception as render_err:
            logging.error(f"[ERROR] Template rendering failed for {src_path}: {render_err}")
            if DEBUG_MODE:
                import traceback
                logging.error(traceback.format_exc())
            html_output = None
        if html_output:
            # Ensure output directory exists before writing
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            try:
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(html_output)
            except Exception as e:
                logging.error(f"Failed to write HTML file {out_path}: {e}")
                if DEBUG_MODE:
                    import traceback
                    logging.error(traceback.format_exc())
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