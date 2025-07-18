"""
make.py
========

Database-driven Markdown to HTML Static Site Generator for OERForge.
Builds HTML pages from Markdown sources using Jinja2 templates, static assets, and the SQLite database as the source of truth.
"""

import os
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
    """Configure logging for the build process."""
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
    """Set up the Jinja2 environment for HTML rendering."""
    env = Environment(
        loader=FileSystemLoader([LAYOUTS_DIR, os.path.join(LAYOUTS_DIR, '_default'), os.path.join(LAYOUTS_DIR, 'partials')]),
        autoescape=select_autoescape(['html', 'xml'])
    )
    return env

def build_all_markdown_files():
    """Main build function: queries DB for Markdown files and builds HTML pages."""
    if not os.path.exists(DB_PATH):
        logging.error(f"Database not found at {DB_PATH}. Aborting build.")
        return
    try:
        conn = get_db_connection(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT source_path, output_path, title, slug, export_types FROM content WHERE mime_type = '.md'")
        records = cursor.fetchall()
        if not records:
            logging.warning("No Markdown files found in database. Nothing to build.")
            return
        # TODO: For each record, read Markdown, convert to HTML, render template, write output
        for row in records:
            source_path, output_path, title, slug, export_types = row
            logging.info(f"[BUILD] {source_path} -> {output_path} (title: {title}, exports: {export_types})")
            # TODO: Implement file existence check, HTML conversion, asset linking, and output writing
        conn.close()
    except Exception as e:
        logging.error(f"Error during build: {e}")

    # Copy static assets and images
    copy_static_assets_to_build()
    copy_db_images_to_build()
    logging.info("[AUTO] All markdown files built.")

def main():
    configure_logging(overwrite=True)
    build_all_markdown_files()

if __name__ == "__main__":
    main()
