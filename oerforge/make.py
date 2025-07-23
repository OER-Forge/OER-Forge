from oerforge.scan import merge_export_config

def slugify(value):
    """
    Convert a string to a URL-friendly slug (lowercase, hyphens, alphanum only).
    """
    import re
    value = re.sub(r'[^a-zA-Z0-9]+', '-', value)
    return value.strip('-').lower()

import os
from markdown_it import MarkdownIt

from oerforge.db_utils import initialize_database

def convert_markdown_to_html(md_text):
    """
    Convert Markdown text to HTML using markdown-it-py.
    Returns the HTML string.
    """
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    return md.render(md_text)
"""
make.py
========

Database-driven Markdown to HTML Static Site Generator for OERForge.
Builds HTML pages from Markdown sources using Jinja2 templates, static assets, and the SQLite database as the source of truth.
"""

import os
import yaml
import logging
import sqlite3
from jinja2 import Environment, FileSystemLoader, select_autoescape
from oerforge.db_utils import get_db_connection, db_log
from oerforge.copyfile import ensure_dir, copy_static_assets_to_build, copy_db_images_to_build


# --- Constants ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
BUILD_HTML_DIR = os.path.join(PROJECT_ROOT, 'build')
LAYOUTS_DIR = os.path.join(PROJECT_ROOT, 'layouts')
LOG_PATH = os.path.join(PROJECT_ROOT, 'log', 'build.log')

# Ensure logging is configured and log file path is printed at import/build start


# --- Early logging setup ---
from pathlib import Path
import logging
import sys


log_dir = Path(LOG_PATH).parent
log_dir.mkdir(parents=True, exist_ok=True)
print(f"[LOGGING] Build log will be written to: {LOG_PATH}")
def configure_logging(overwrite=False):
    """
    Configure logging to file and console. If overwrite is True, the log file is truncated.
    """
    log_mode = 'w' if overwrite else 'a'
    handlers = [
        logging.FileHandler(LOG_PATH, mode=log_mode, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=handlers
    )

log_dir = Path(LOG_PATH).parent
log_dir.mkdir(parents=True, exist_ok=True)
print(f"[LOGGING] Build log will be written to: {LOG_PATH}")
try:
    configure_logging(overwrite=True)
except Exception as e:
    print(f"[LOGGING] Failed to configure logging: {e}")
def setup_template_env():
    """
    Set up and return a Jinja2 Environment for rendering HTML templates.
    Loads templates from the layouts directory and its subfolders.
    Enables autoescaping for HTML and XML files.
    """
    env = Environment(
        loader=FileSystemLoader([LAYOUTS_DIR, os.path.join(LAYOUTS_DIR, '_default'), os.path.join(LAYOUTS_DIR, 'partials')]),
        autoescape=select_autoescape(['html', 'xml'])
    )
    return env

def build_all_markdown_files():
    """
    Main build routine for the static site generator.
    - Auto-populates the DB with Markdown files if the content table is empty.
    - Loads site context from _content.yml.
    - Syncs site_info table with YAML.
    - Converts Markdown to HTML and renders with Jinja2.
    - Copies static assets and images.
    """


    def get_asset_path(asset_type, filename, output_path):
        """
        Compute the relative path from the output HTML file to the asset.
        Keeps asset linking robust for static deployment (SRP, DRY).
        """
        asset_dir = os.path.join('static', asset_type) if asset_type else 'static'
        asset_path = os.path.join(asset_dir, filename)
        rel_path = os.path.relpath(asset_path, os.path.dirname(output_path))
        return rel_path.replace('\\', '/')

    # Ensure DB exists, or initialize it
    if not os.path.exists(DB_PATH):
        logging.warning(f"Database not found at {DB_PATH}. Initializing new database.")
        initialize_database(DB_PATH)


    # Load global site context from _content.yml
    content_yml_path = os.path.join(PROJECT_ROOT, '_content.yml')
    if not os.path.exists(content_yml_path):
        logging.error(f"_content.yml not found at {content_yml_path}. Aborting build.")
        return

    with open(content_yml_path, 'r', encoding='utf-8') as f:
        content_config = yaml.safe_load(f)
    site = content_config.get('site', {})
    footer = content_config.get('footer', {})
    toc = content_config.get('toc', [])
    top_menu = []
    # --- Build nav recursively, respecting slugs and children ---
    content_lookup = {}
    conn = get_db_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT source_path, slug, output_path FROM content WHERE mime_type = '.md'")
    for row in cursor.fetchall():
        source_path, slug, output_path = row
        content_lookup[(source_path, slug)] = output_path

    def build_nav(items, parent_slugs=None):
        """Recursively build nav structure from TOC, using full slug path. Adds debug logging for each menu item."""
        nav = []
        parent_slugs = parent_slugs or []
        for item in items:
            if not item.get('menu', True):
                continue
            file_path = item.get('file', '')
            slug = item.get('slug', None)
            # Always use the DB output_path if available
            output_path = content_lookup.get((file_path, slug))
            debug_msg = f"[NAV-DEBUG] file_path='{file_path}', slug='{slug}', "
            if output_path:
                link = './' + output_path.replace('build/', '').lstrip('/')
                debug_msg += f"db_output_path='{output_path}', link='{link}' (DB match)"
            else:
                # Fallbacks for legacy/edge cases
                if (file_path in ("index.md", "content/index.md") and slug == "main"):
                    link = './index.html'
                    debug_msg += f"fallback=index.html, link='{link}'"
                elif slug == "main" and file_path.endswith(".md"):
                    link = './' + os.path.splitext(os.path.basename(file_path))[0] + '.html'
                    debug_msg += f"fallback=basename.html, link='{link}'"
                else:
                    full_slugs = parent_slugs + [slug] if slug else parent_slugs
                    if full_slugs:
                        link = './' + '/'.join(full_slugs) + '.html'
                        debug_msg += f"fallback=slug.html, link='{link}'"
                    else:
                        link = './' + file_path.replace('.md', '.html').replace('content/', '').lstrip('/')
                        debug_msg += f"fallback=file.html, link='{link}'"
            logging.debug(debug_msg)
            nav_item = {'title': item.get('title', ''), 'link': link}
            if 'children' in item and item['children']:
                nav_item['children'] = build_nav(item['children'], parent_slugs + ([slug] if slug else []))
            nav.append(nav_item)
        return nav

    top_menu = build_nav(toc)

    # --- Sync site_info table with _content.yml ---
    def fetch_site_info_from_db(cursor):
        cursor.execute('SELECT * FROM site_info LIMIT 1')
        row = cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def upsert_site_info(cursor, site, footer):
        cursor.execute('SELECT COUNT(*) FROM site_info')
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute('''INSERT INTO site_info
                (title, author, description, logo, favicon, theme_default, theme_light, theme_dark, language, github_url, footer_text, header)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                site.get('title', ''),
                site.get('author', ''),
                site.get('description', ''),
                site.get('logo', ''),
                site.get('favicon', ''),
                site.get('theme', {}).get('default', ''),
                site.get('theme', {}).get('light', ''),
                site.get('theme', {}).get('dark', ''),
                site.get('language', ''),
                site.get('github_url', ''),
                footer.get('text', ''),
                site.get('header', ''),
            ))
            logging.info("Populated site_info table from _content.yml.")

    db_site_info = fetch_site_info_from_db(cursor)
    upsert_site_info(cursor, site, footer)
    conn.commit()
    db_site_info = fetch_site_info_from_db(cursor)
    if db_site_info:
        mismatch = []
        def check(key, yaml_val, db_val):
            if (yaml_val or '') != (db_val or ''):
                mismatch.append(f"{key}: YAML='{yaml_val}' DB='{db_val}'")
        check('title', site.get('title', ''), db_site_info.get('title', ''))
        check('author', site.get('author', ''), db_site_info.get('author', ''))
        check('description', site.get('description', ''), db_site_info.get('description', ''))
        check('logo', site.get('logo', ''), db_site_info.get('logo', ''))
        check('favicon', site.get('favicon', ''), db_site_info.get('favicon', ''))
        check('theme_default', site.get('theme', {}).get('default', ''), db_site_info.get('theme_default', ''))
        check('theme_light', site.get('theme', {}).get('light', ''), db_site_info.get('theme_light', ''))
        check('theme_dark', site.get('theme', {}).get('dark', ''), db_site_info.get('theme_dark', ''))
        check('language', site.get('language', ''), db_site_info.get('language', ''))
        check('github_url', site.get('github_url', ''), db_site_info.get('github_url', ''))
        check('footer_text', footer.get('text', ''), db_site_info.get('footer_text', ''))
        check('header', site.get('header', ''), db_site_info.get('header', ''))
        if mismatch:
            logging.warning("Site info mismatch between _content.yml and site_info table:\n" + "\n".join(mismatch))

    cursor.execute("SELECT source_path, output_path, title, slug, export_types FROM content WHERE mime_type = '.md'")
    records = cursor.fetchall()
    if not records:
        logging.warning("No Markdown files found in database. Nothing to build.")
        conn.close()
        return

    env = setup_template_env()
    for row in records:
        source_path, output_path, title, slug, export_types = row
        abs_source_path = os.path.join(PROJECT_ROOT, source_path) if not os.path.isabs(source_path) else source_path
        is_main_index = os.path.normpath(source_path) in ["content/index.md", "index.md"] or slug == "home"
        abs_output_path = os.path.join(BUILD_HTML_DIR, "index.html") if is_main_index else (
            os.path.join(PROJECT_ROOT, output_path) if not os.path.isabs(output_path) else output_path
        )
        logging.info(f"[BUILD] {source_path} -> {abs_output_path} (title: {title}, exports: {export_types})")
        if not os.path.exists(abs_source_path):
            logging.warning(f"Source file not found: {abs_source_path}. Skipping.")
            continue
        try:
            with open(abs_source_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
        except Exception as e:
            logging.error(f"Failed to read {abs_source_path}: {e}")
            continue
        html_body = convert_markdown_to_html(md_text)
        try:
            # DRY: asset path computation
            def asset(name, typ=''):
                return get_asset_path(typ, name, abs_output_path)
            logo_file = site.get('logo', 'logo.png')
            favicon_file = site.get('favicon', 'favicon.ico')
            context = {
                'title': title,
                'body': html_body,
                'slug': slug,
                'site': site,
                'footer': footer,
                'css_path': asset('theme-dark.css', 'css'),
                'js_path': asset('main.js', 'js'),
                'logo_path': asset(os.path.basename(logo_file), 'images'),
                'favicon_path': asset(os.path.basename(favicon_file), 'images'),
                'favicon16_path': asset('favicon-16x16.png', 'images'),
                'favicon32_path': asset('favicon-32x32.png', 'images'),
                'apple_touch_icon_path': asset('apple-touch-icon.png', 'images'),
                'android192_path': asset('android-chrome-192x192.png', 'images'),
                'android512_path': asset('android-chrome-512x192.png', 'images'),
                'manifest_path': asset('site.webmanifest'),
                'top_menu': top_menu,
            }
            page_html = env.get_template('base.html').render(**context)
        except Exception as e:
            logging.error(f"Template rendering failed for {source_path}: {e}")
            continue
        ensure_dir(os.path.dirname(abs_output_path))
        try:
            with open(abs_output_path, 'w', encoding='utf-8') as outf:
                outf.write(page_html)
            logging.info(f"Wrote HTML: {abs_output_path}")
        except Exception as e:
            logging.error(f"Failed to write output for {source_path}: {e}")
    conn.close()

    copy_static_assets_to_build()
    copy_db_images_to_build()
    logging.info("[AUTO] All markdown files built.")

def main():
    """
    Entrypoint for the script.
    Configures logging and runs the build process.
    """
    configure_logging(overwrite=True)
    build_all_markdown_files()

if __name__ == "__main__":
    main()
