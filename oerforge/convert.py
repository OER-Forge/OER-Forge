import sys
import os
# Ensure project root is in sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""
convert.py

Module for converting Jupyter notebooks (.ipynb) and Markdown files to various formats,
managing associated images, and updating a SQLite database with conversion status.

Main features:
- Executes notebooks and exports to Markdown.
- Handles image extraction, copying, and reference updates.
- Logs conversion actions and updates database flags.
- Provides stub functions for other conversions (docx, tex, pdf).

Author: [Your Name]
"""


import logging
def setup_logging():
    import logging
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log", "export.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler()]
    )

import sys
import os
import shutil
import sqlite3
import subprocess
from nbconvert import MarkdownExporter
from nbconvert.preprocessors import ExecutePreprocessor, ExtractOutputPreprocessor
from traitlets.config import Config
import re
from markdown_it import MarkdownIt

# --- Constants ---
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "sqlite.db")
CONTENT_ROOT = "content"
BUILD_ROOT = "build"
BUILD_FILES_ROOT = os.path.join(BUILD_ROOT, "files")
BUILD_IMAGES_ROOT = os.path.join(BUILD_ROOT, "images")
IMAGES_ROOT = BUILD_IMAGES_ROOT  # For compatibility in image functions
LOG_DIR = "log"

# --- Modular Image Handling for Markdown ---
def query_images_for_content(content_record, conn):
    """
    Query sqlite.db for all images associated with this content file.
    Returns a list of image records (dicts).
    """
    from oerforge.db_utils import get_records
    images = get_records(
        "files",
        "is_image=1 AND referenced_page=?",
        (content_record['source_path'],),
        conn=conn
    )
    logging.debug(f"[IMAGES] Found {len(images)} images for {content_record['source_path']}")
    return images

def copy_images_to_build(images, images_root=IMAGES_ROOT, conn=None):
    """
    Copy each image to the top-level images directory. All images go in images/ with their filename only.
    Uses the content table to resolve the correct source path for each image.
    Returns a list of new build paths (absolute paths).
    """
    os.makedirs(images_root, exist_ok=True)
    copied = []
    # Build a lookup for content source paths
    content_lookup = {}
    if conn is not None:
        cursor = conn.cursor()
        cursor.execute("SELECT source_path FROM content")
        for row in cursor.fetchall():
            content_lookup[row[0]] = row[0]
    for img in images:
        src = img.get('relative_path') or img.get('absolute_path')
        referenced_page = img.get('referenced_page')
        logging.debug(f"[IMAGES][DEBUG] src={src} img={img}")
        if not src or img.get('is_remote'):
            logging.warning(f"[IMAGES] Skipping remote or missing image: {img.get('filename')}")
            continue
        # Compute the actual source path
        if referenced_page and referenced_page in content_lookup and not os.path.isabs(src):
            # If src is relative, resolve it against the referenced_page's directory
            src_path = os.path.normpath(os.path.join(os.path.dirname(referenced_page), src))
        else:
            src_path = src
        filename = os.path.basename(src)
        dest = os.path.join(images_root, filename)
        logging.debug(f"[IMAGES][DEBUG] Copying {src_path} to {dest}")
        try:
            shutil.copy2(src_path, dest)
            logging.info(f"[IMAGES] Copied image {src_path} to {dest}")
            copied.append(dest)
        except Exception as e:
            logging.error(f"[IMAGES] Failed to copy {src_path} to {dest}: {e}")
    return copied

def update_markdown_image_links(md_path, images, images_root=IMAGES_ROOT):
    """
    Update image links in the Markdown file to point to the copied images in the top-level images directory.
    Uses sqlite.db to look up image records for this markdown file.
    """
    if not os.path.exists(md_path):
        logging.warning(f"[IMAGES] Markdown file not found: {md_path}")
        return
    # Compute the source_path for this markdown file
    rel_path = os.path.relpath(md_path, BUILD_FILES_ROOT)
    source_path = os.path.join(CONTENT_ROOT, rel_path)
    # Query DB for images for this markdown file
    img_map = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT relative_path, absolute_path, filename FROM files WHERE is_image=1 AND referenced_page=?", (source_path,))
        for row in cursor.fetchall():
            rel, abs_path, filename = row
            src = rel or abs_path
            if not src:
                continue
            # Always use ../../images/<filename> for image references
            rel_img_path = os.path.join('..', '..', 'images', filename)
            img_map[os.path.basename(src)] = rel_img_path
        conn.close()
    except Exception as e:
        logging.error(f"[IMAGES] DB lookup failed for {md_path}: {e}")
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.splitlines()
    new_lines = lines.copy()
    # For each line, replace any image markdown src with correct relative path
    for idx, line in enumerate(lines):
        matches = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', line)
        for old_src in matches:
            filename = os.path.basename(old_src)
            if filename in img_map:
                new_src = img_map[filename]
                new_lines[idx] = new_lines[idx].replace(old_src, new_src)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))
    logging.info(f"[IMAGES] Updated image links in {md_path} to use correct relative paths (DB-driven)")

def handle_images_for_markdown(content_record, conn):
    """
    Orchestrate image handling for a Markdown file: query, copy, update links.
    """
    images = query_images_for_content(content_record, conn)
    copied = copy_images_to_build(images, images_root=BUILD_IMAGES_ROOT)
    rel_path = os.path.relpath(content_record['source_path'], CONTENT_ROOT)
    md_path = os.path.join(BUILD_FILES_ROOT, rel_path)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    # Copy original markdown to build/files if not already there
    abs_src_path = os.path.join(CONTENT_ROOT, rel_path)
    if not os.path.exists(md_path):
        try:
            shutil.copy2(abs_src_path, md_path)
            logging.info(f"Copied original md to {md_path}")
        except Exception as e:
            logging.error(f"Failed to copy md: {e}")
            return
    update_markdown_image_links(md_path, images, images_root=BUILD_IMAGES_ROOT)
    logging.info(f"[IMAGES] Finished handling images for {md_path}")
    
def convert_md_to_docx(src_path, out_path, record_id=None, conn=None):
    """
    Convert a Markdown file to DOCX using Pandoc.
    Copy converted file to build/files. Update DB conversion status if record_id and conn provided.
    """
    import logging
    logging.info(f"[DOCX] Starting conversion: {src_path} -> {out_path}")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        import subprocess
        subprocess.run(["pandoc", src_path, "-o", out_path], check=True)
        logging.info(f"[DOCX] Converted {src_path} to {out_path}")
        # DB update logic remains, but use logging for status
        if record_id:
            from oerforge.db_utils import get_db_connection
            import datetime
            try:
                db_conn = conn if conn is not None else get_db_connection()
                db_cursor = db_conn.cursor()
                db_cursor.execute(
                    "INSERT INTO conversion_results (content_id, source_format, target_format, output_path, conversion_time, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        record_id,
                        '.md',
                        '.docx',
                        out_path,
                        datetime.datetime.now().isoformat(),
                        'success'
                    )
                )
                db_conn.commit()
                logging.info(f"[DOCX] conversion_results updated for id {record_id}")
                if conn is None:
                    db_conn.close()
            except Exception as e:
                logging.error(f"[DOCX] conversion_results insert failed for id {record_id}: {e}")
    except Exception as e:
        logging.error(f"[DOCX] Pandoc conversion failed for {src_path}: {e}")

def convert_md_to_pdf(src_path, out_path, record_id=None, conn=None):
    """
    Convert a Markdown file to PDF using Pandoc.
    Update DB conversion status if record_id and conn provided.
    """
    import logging
    logging.info(f"[PDF] Starting conversion: {src_path} -> {out_path}")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        import subprocess
        subprocess.run(["pandoc", src_path, "-o", out_path], check=True)
        logging.info(f"[PDF] Converted {src_path} to {out_path}")
        if record_id:
            from oerforge.db_utils import get_db_connection
            import datetime
            try:
                db_conn = conn if conn is not None else get_db_connection()
                db_cursor = db_conn.cursor()
                db_cursor.execute(
                    "INSERT INTO conversion_results (content_id, source_format, target_format, output_path, conversion_time, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        record_id,
                        '.md',
                        '.pdf',
                        out_path,
                        datetime.datetime.now().isoformat(),
                        'success'
                    )
                )
                db_conn.commit()
                logging.info(f"[PDF] conversion_results updated for id {record_id}")
                if conn is None:
                    db_conn.close()
            except Exception as e:
                logging.error(f"[PDF] conversion_results insert failed for id {record_id}: {e}")
    except Exception as e:
        logging.error(f"[PDF] Pandoc conversion failed for {src_path}: {e}")

def convert_md_to_tex(src_path, out_path, record_id=None, conn=None):
    """
    Convert a Markdown file to LaTeX using Pandoc.
    Update DB conversion status if record_id and conn provided.
    """
    import logging
    logging.info(f"[TEX] Starting conversion: {src_path} -> {out_path}")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        import subprocess
        subprocess.run(["pandoc", src_path, "-o", out_path], check=True)
        logging.info(f"[TEX] Converted {src_path} to {out_path}")
        if record_id:
            from oerforge.db_utils import get_db_connection
            import datetime
            try:
                db_conn = conn if conn is not None else get_db_connection()
                db_cursor = db_conn.cursor()
                db_cursor.execute(
                    "INSERT INTO conversion_results (content_id, source_format, target_format, output_path, conversion_time, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        record_id,
                        '.md',
                        '.tex',
                        out_path,
                        datetime.datetime.now().isoformat(),
                        'success'
                    )
                )
                db_conn.commit()
                logging.info(f"[TEX] conversion_results updated for id {record_id}")
                if conn is None:
                    db_conn.close()
            except Exception as e:
                logging.error(f"[TEX] conversion_results insert failed for id {record_id}: {e}")
    except Exception as e:
        logging.error(f"[TEX] Pandoc conversion failed for {src_path}: {e}")

# --- Batch Conversion Orchestrator ---
def batch_convert_all_content(config_path=None):
    """
    Main entry point: batch process all files in the content table.
    For each file, check conversion flags and call appropriate conversion stubs.
    Copy original files to build/files. Organize output to mirror TOC hierarchy.
    Log all errors and warnings to log/convert.log.
    config_path: Optional path to _config.yml. If None, uses default location.
    """
    print("[DEBUG] Starting batch conversion for all content records.")
    logging.info("Starting batch conversion for all content records.")
    import yaml
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if config_path is None:
        config_path = os.path.join(project_root, "_content.yml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    toc = config.get('toc', [])

    # --- Generic Conversion Logic ---
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Get all enabled conversions
    cursor.execute("SELECT source_format, target_format FROM conversion_capabilities WHERE is_enabled=1")
    conversions = cursor.fetchall()
    # Get all content files with output_path
    cursor.execute("SELECT id, source_path, output_path, slug FROM content")
    content_files = cursor.fetchall()
    for record_id, source_path, output_path, slug in content_files:
        if not source_path or not output_path:
            logging.warning(f"Skipping content record id={record_id} with None source_path or output_path")
            logging.info(f"SKIP: id={record_id} source_path={source_path} output_path={output_path}")
            continue
        src_ext = os.path.splitext(source_path)[1]
        rel_path = os.path.relpath(source_path, CONTENT_ROOT)
        src_path = os.path.join(CONTENT_ROOT, rel_path)
        # --- Per-page folder logic ---
        if slug:
            out_dir = os.path.join(BUILD_FILES_ROOT, slug)
        else:
            out_dir = os.path.dirname(output_path)
        os.makedirs(out_dir, exist_ok=True)
        for conv_src, conv_target in conversions:
            if src_ext == conv_src:
                out_name = os.path.splitext(os.path.basename(output_path))[0] + conv_target
                out_path = os.path.join(out_dir, out_name)
                # Dispatch conversion
                if conv_src == ".md" and conv_target == ".md":
                    try:
                        shutil.copy2(src_path, out_path)
                        logging.info(f"COPY: {src_path} -> {out_path}")
                    except Exception as e:
                        logging.error(f"ERROR: Failed to copy {src_path} -> {out_path}: {e}")
                elif conv_src == ".md" and conv_target == ".docx":
                    convert_md_to_docx(src_path, out_path, record_id, conn)
                    logging.info(f"CONVERT: {src_path} -> {out_path} (docx)")
                elif conv_src == ".md" and conv_target == ".pdf":
                    convert_md_to_pdf(src_path, out_path, record_id, conn)
                    logging.info(f"CONVERT: {src_path} -> {out_path} (pdf)")
                elif conv_src == ".md" and conv_target == ".tex":
                    convert_md_to_tex(src_path, out_path, record_id, conn)
                    logging.info(f"CONVERT: {src_path} -> {out_path} (tex)")
                elif conv_src == ".ipynb" and conv_target == ".jupyter":
                    logging.info(f"JUPYTER: {src_path} -> {out_path}")
                # Add more elifs for other conversions as needed
    conn.close()
    logging.info("Batch conversion complete.")

# --- Main Entry Point ---
if __name__ == "__main__":
    import argparse
    setup_logging()
    parser = argparse.ArgumentParser(description="OERForge Conversion CLI")
    parser.add_argument("mode", choices=["batch", "single"], help="Conversion mode: batch or single file")
    parser.add_argument("--src", type=str, help="Source file path (for single mode)")
    parser.add_argument("--out", type=str, help="Output file path (for single mode)")
    parser.add_argument("--fmt", choices=["docx", "pdf", "tex"], help="Target format (for single mode)")
    parser.add_argument("--record_id", type=int, default=None, help="Content record ID (optional)")
    args = parser.parse_args()

    if args.mode == "batch":
        logging.info("[convert] __main__ entry: running batch_convert_all_content()")
        batch_convert_all_content()
    elif args.mode == "single":
        if not args.src or not args.out or not args.fmt:
            print("Error: --src, --out, and --fmt are required for single mode.")
            exit(1)
        if args.fmt == "docx":
            convert_md_to_docx(args.src, args.out, args.record_id)
        elif args.fmt == "pdf":
            convert_md_to_pdf(args.src, args.out, args.record_id)
        elif args.fmt == "tex":
            convert_md_to_tex(args.src, args.out, args.record_id)
        else:
            print(f"Unknown format: {args.fmt}")
            exit(1)

