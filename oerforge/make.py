from markdown_it import MarkdownIt

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

def configure_logging(overwrite=False):
    """
    Configure logging to both file and console for the build process.
    If overwrite is True, the log file is truncated; otherwise, logs are appended.
    Sets log level to INFO for console and DEBUG for file.
    """
    log_level = logging.INFO
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
    def get_asset_path(asset_type, asset_name, abs_output_path):
        # Compute the relative path from the HTML file to the asset in build/
        asset_path = os.path.join(BUILD_HTML_DIR, asset_type, asset_name)
        rel_path = os.path.relpath(asset_path, os.path.dirname(abs_output_path))
        return rel_path.replace(os.sep, '/')
    """
    Main build routine for the static site generator.
    Queries the database for Markdown files to build, logs each build action,
    and (in future steps) will convert and render each file to HTML using Jinja2 templates.
    Copies static assets and images after building.
    Handles all error logging and database connection management.
    """

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
    # Only include items with menu: true (default true)
    top_menu = [
        {'title': item.get('title', ''), 'link': '/' if item.get('file', '') == 'index.md' else ('/' + item.get('slug', item.get('file', '').replace('.md', '').replace('content/', '').replace('sample/', 'sample-resources/')) + '/')}
        for item in toc if item.get('menu', True)
    ]

    # --- Sync site_info table with _content.yml ---
    def fetch_site_info_from_db(cursor):
        cursor.execute('SELECT * FROM site_info LIMIT 1')
        row = cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def upsert_site_info(cursor, site, footer):
        # Only insert if table is empty
        cursor.execute('SELECT COUNT(*) FROM site_info')
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute('''INSERT INTO site_info \
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

    # --- End sync helpers ---

    if not os.path.exists(DB_PATH):
        logging.error(f"Database not found at {DB_PATH}. Aborting build.")
        return
    try:
        conn = get_db_connection(DB_PATH)
        cursor = conn.cursor()

        # Sync site_info table with _content.yml
        db_site_info = fetch_site_info_from_db(cursor)
        upsert_site_info(cursor, site, footer)
        conn.commit()
        db_site_info = fetch_site_info_from_db(cursor)
        # Compare YAML and DB, warn if mismatch
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
            return
        env = setup_template_env()
        for row in records:
            source_path, output_path, title, slug, export_types = row
            abs_source_path = os.path.join(PROJECT_ROOT, source_path) if not os.path.isabs(source_path) else source_path
            # Special case: if this is the main index page, write to build/index.html
            is_main_index = False
            if os.path.normpath(source_path) in ["content/index.md", "index.md"] or slug == "home":
                abs_output_path = os.path.join(BUILD_HTML_DIR, "index.html")
                is_main_index = True
            else:
                abs_output_path = os.path.join(PROJECT_ROOT, output_path) if not os.path.isabs(output_path) else output_path
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
            # --- Markdown to HTML conversion ---
            html_body = convert_markdown_to_html(md_text)
            # --- Render with Jinja2 template ---
            try:
                # Compute asset paths relative to this page
                css_path = get_asset_path('css', 'theme-dark.css', abs_output_path)
                js_path = get_asset_path('js', 'main.js', abs_output_path)
                logo_file = site.get('logo', 'logo.png')
                logo_name = os.path.basename(logo_file)
                logo_path = get_asset_path('images', logo_name, abs_output_path)
                favicon_file = site.get('favicon', 'favicon.ico')
                favicon_name = os.path.basename(favicon_file)
                favicon_path = get_asset_path('images', favicon_name, abs_output_path)
                # Additional icons and manifest paths
                favicon16_file = 'favicon-16x16.png'
                favicon32_file = 'favicon-32x32.png'
                apple_touch_icon_file = 'apple-touch-icon.png'
                android192_file = 'android-chrome-192x192.png'
                android512_file = 'android-chrome-512x512.png'
                manifest_file = 'site.webmanifest'

                favicon16_path = get_asset_path('images', favicon16_file, abs_output_path)
                favicon32_path = get_asset_path('images', favicon32_file, abs_output_path)
                apple_touch_icon_path = get_asset_path('images', apple_touch_icon_file, abs_output_path)
                android192_path = get_asset_path('images', android192_file, abs_output_path)
                android512_path = get_asset_path('images', android512_file, abs_output_path)
                manifest_path = get_asset_path('', manifest_file, abs_output_path)

                context = {
                    'title': title,
                    'body': html_body,
                    'slug': slug,
                    'site': site,
                    'footer': footer,
                    'css_path': css_path,
                    'js_path': js_path,
                    'logo_path': logo_path,
                    'favicon_path': favicon_path,
                    'favicon16_path': favicon16_path,
                    'favicon32_path': favicon32_path,
                    'apple_touch_icon_path': apple_touch_icon_path,
                    'android192_path': android192_path,
                    'android512_path': android512_path,
                    'manifest_path': manifest_path,
                    'top_menu': top_menu,
                    # Add more context as needed (navigation, etc.)
                }
                page_html = env.get_template('base.html').render(**context)
            except Exception as e:
                logging.error(f"Template rendering failed for {source_path}: {e}")
                continue
            # --- Ensure output directory exists ---
            ensure_dir(os.path.dirname(abs_output_path))
            # --- Write output ---
            try:
                with open(abs_output_path, 'w', encoding='utf-8') as outf:
                    outf.write(page_html)
                logging.info(f"Wrote HTML: {abs_output_path}")
            except Exception as e:
                logging.error(f"Failed to write output for {source_path}: {e}")
        conn.close()
    except Exception as e:
        logging.error(f"Error during build: {e}")

    # Copy static assets and images
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
