"""
make.py
========

Hugo-style Markdown to HTML Static Site Generator

Builds a static website from Markdown and other content sources using Jinja2 templates,
asset management, navigation, accessibility, and SQLite integration.

Debug mode and logging level are controlled via environment variables:
    DEBUG=1 enables debug logging and extra error details.
    LOG_LEVEL sets the logging level (default: INFO).
"""

import os
import logging
import yaml
import copy
import re
import sqlite3
from typing import Any, Dict, List, Tuple, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.texmath import texmath_plugin
import html
from oerforge import db_utils
from oerforge.copyfile import copy_db_images_to_build, copy_static_assets_to_build

# --- Constants and Logging Setup ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(PROJECT_ROOT, 'log', 'build.log')
BUILD_HTML_DIR = os.path.join(PROJECT_ROOT, 'build')
LAYOUTS_DIR = os.path.join(PROJECT_ROOT, 'layouts')
DEBUG_MODE = os.environ.get("DEBUG", "0") == "1"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

def configure_logging(overwrite=False):
    log_level = logging.DEBUG if DEBUG_MODE else getattr(logging, LOG_LEVEL, logging.INFO)
    file_mode = 'w' if overwrite else 'a'
    file_handler = logging.FileHandler(LOG_PATH, mode=file_mode, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[file_handler, stream_handler]
    )

def load_content_yaml(path: str = "_content.yml") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def merge_export_config(global_export: Dict[str, Any], local_export: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = copy.deepcopy(global_export)
    if local_export:
        merged.update(local_export)
    return merged

def validate_export_config(export_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []
    if not isinstance(export_config.get("types"), list):
        errors.append("types must be a list")
    return (len(errors) == 0, errors)

def walk_toc_with_exports(
    toc: List[Dict[str, Any]],
    global_export: Dict[str, Any],
    parent_export: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    results = []
    for entry in toc:
        local_export = entry.get("export")
        parent = parent_export or global_export
        effective_export = merge_export_config(parent, local_export)
        if "slug" not in entry and "file" in entry:
            entry["slug"] = os.path.splitext(entry["file"])[0]
        is_valid, errors = validate_export_config(effective_export)
        results.append({
            "title": entry.get("title"),
            "file": entry.get("file"),
            "slug": entry.get("slug"),
            "export_config": effective_export,
            "is_valid": is_valid,
            "errors": errors,
        })
        if "children" in entry:
            results.extend(
                walk_toc_with_exports(entry["children"], global_export, effective_export)
            )
    return results

def get_all_exports(content_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    global_export = content_dict.get("export", {})
    toc = content_dict.get("toc", [])
    return walk_toc_with_exports(toc, global_export)

def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def setup_template_env():
    layouts_default = os.path.join(LAYOUTS_DIR, '_default')
    layouts_partials = os.path.join(LAYOUTS_DIR, 'partials')
    env = Environment(
        loader=FileSystemLoader([LAYOUTS_DIR, layouts_default, layouts_partials]),
        autoescape=select_autoescape(['html', 'xml'])
    )
    return env

def render_page(context: dict, template_name: str) -> str:
    env = setup_template_env()
    template = env.get_template(f'_default/{template_name}')
    return template.render(**context)

def convert_markdown_to_html_text(md_text: str, referenced_page: str, rel_path: str) -> str:
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
    # Accessibility roles
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
    depth = rel_path.count(os.sep)
    prefix = '../' * depth if depth > 0 else ''
    return f"{prefix}{asset_type}/{asset_name}"

def add_asset_paths(context, rel_path):
    context['css_path'] = get_asset_path('css', 'theme-dark.css', rel_path)
    context['js_path'] = get_asset_path('js', 'main.js', rel_path)
    logo_file = context.get('site', {}).get('logo', 'static/images/logo.png')
    logo_name = os.path.basename(logo_file)
    context['logo_path'] = get_asset_path('images', logo_name, rel_path)
    return context

def build_all_markdown_files():

    # Load global site context once
    config_path = os.path.join(PROJECT_ROOT, '_content.yml')
    content = load_content_yaml(config_path)
    site = content.get('site', {})
    footer = content.get('footer', {})

    db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
    all_exports = get_all_exports(content)

    for item in all_exports:
        if not item["is_valid"]:
            logging.warning(f"Skipping {item['file']}: invalid export config: {item['errors']}")
            continue
        file = item["file"]
        if not file:
            continue
        src_path = os.path.join(PROJECT_ROOT, 'content', file)
        slug = item.get("slug")
        export_config = item["export_config"]
        output_path_template = export_config.get("output_path", "build/{slug}/{file}")
        file_stem = os.path.splitext(os.path.basename(file))[0]
        out_path = output_path_template.format(slug=slug or "", file=file_stem)
        out_path = os.path.join(PROJECT_ROOT, out_path)
        rel_path = os.path.relpath(out_path, BUILD_HTML_DIR)
        # Read markdown, convert to HTML, render template, write output
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                md_text = f.read()
            html_body = convert_markdown_to_html_text(md_text, referenced_page=file, rel_path=rel_path)
            context = {
                "site": site,
                "footer": footer,
                "title": item.get("title") or file_stem,
                "body": html_body,
                "rel_path": rel_path,
                "slug": slug,
            }
            context = add_asset_paths(context, rel_path)
            if DEBUG_MODE:
                logging.debug(f"Context keys for {file}: {list(context.keys())}")
                logging.debug(f"Context['site']: {context.get('site')}")
            page_html = render_page(context, "base.html")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as outf:
                outf.write(page_html)
            logging.info(f"Built {out_path}")
        except Exception as e:
            logging.error(f"Failed to build {file}: {e}")
            if DEBUG_MODE:
                import traceback
                logging.error(traceback.format_exc())

    copy_static_assets_to_build()
    copy_db_images_to_build()
    logging.info("[AUTO] All markdown files built.")

def main():
    configure_logging(overwrite=True)
    build_all_markdown_files()

if __name__ == "__main__":
    main()