"""
export_all.py

Batch export orchestrator for converting Markdown files to DOCX using Pandoc.
Logs all actions and errors to log/export.log.
"""

import os
import sys
import sqlite3
import logging
import yaml
# Ensure project root is in sys.path for module imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from oerforge.convert import convert_md_to_docx
from oerforge.copyfile import copy_build_to_docs_safe

# --- Constants ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_ROOT = os.path.join(PROJECT_ROOT, "content")
BUILD_ROOT = os.path.join(PROJECT_ROOT, "build")
BUILD_FILES_ROOT = os.path.join(BUILD_ROOT, "files")
LOG_PATH = os.path.join(PROJECT_ROOT, "log", "export.log")
DB_PATH = os.path.join(PROJECT_ROOT, "db", "sqlite.db")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
)


# --- Batch Export Orchestrator ---
def export_all(config_path=None):
    """
    Batch process all Markdown files in the TOC and convert to DOCX.
    """
    logging.info("[EXPORT] Starting batch DOCX export.")
    if config_path is None:
        config_path = os.path.join(PROJECT_ROOT, "_content.yml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    toc = config.get("toc", [])
    # Load TOC from config
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    toc = config.get("toc", [])
    conn = None
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, source_path, slug FROM content WHERE source_path LIKE '%.md'")
        records = cursor.fetchall()
        for record in records:
            record_id, source_path, slug = record
            src_path = os.path.join(PROJECT_ROOT, source_path) if not os.path.isabs(source_path) else source_path
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            # Use slug from DB for output path
            out_dir = os.path.join(BUILD_ROOT, slug) if slug else BUILD_ROOT
            out_path = os.path.join(out_dir, base_name + ".docx")
            if os.path.exists(src_path):
                logging.info(f"[EXPORT] Converting: {src_path} -> {out_path}")
                convert_md_to_docx(src_path, out_path, record_id, conn)
            else:
                logging.warning(f"[EXPORT] Missing Markdown file: {src_path}")
        conn.close()
    logging.info("[EXPORT] Batch DOCX export complete.")

def export_build_to_docs():
    """
    Copy build/ directory to docs/ using the project utility.
    """
    logging.info("[EXPORT] Copying build/ to docs/ (non-destructive)")
    copy_build_to_docs_safe()
    logging.info("[EXPORT] build/ copied to docs/ (non-destructive)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch export and copy build to docs.")
    parser.add_argument("--copy", action="store_true", help="Copy build/ to docs/")
    args = parser.parse_args()
    export_all()
    if args.copy:
        export_build_to_docs()
