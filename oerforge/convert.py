"""
convert.py
----------
Generic, SQL-driven, parallelized content conversion pipeline for OER-Forge.

- Only enabled conversions (from conversion_capabilities) attempted.
- Caching: skip if up-to-date, unless --force.
- Parallelization with concurrent.futures (default max_workers).
- CLI: simple, with --force and summary JSON output.
- Logging to file and screen; no need to store skip reasons in the DB.
- Best-effort: continue on errors.

Add new converter functions as needed for (input_ext, output_ext) pairs.
"""

import os
import sys
import logging
import json
import concurrent.futures
from datetime import datetime
from oerforge import db_utils

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')
LOG_PATH = os.path.join(PROJECT_ROOT, 'log', 'build.log')
SUMMARY_JSON = os.path.join(BUILD_DIR, 'convert_summary.json')
DEBUG_MODE = os.environ.get("DEBUG", "0") == "1"

# --- Logging Setup ---
def configure_logging():
    log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    handlers = [
        logging.FileHandler(LOG_PATH, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=handlers
    )

# --- DB Queries ---
def get_enabled_conversions(db_path):
    """Return list of (input_ext, output_ext) for enabled conversions."""
    # Uses db_utils to query conversion_capabilities for enabled conversions
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        rows = db_utils.get_records(
            "conversion_capabilities",
            "is_enabled=1",
            conn=conn
        )
        return [(row["source_format"], row["target_format"]) for row in rows]
    finally:
        conn.close()

def get_content_files_to_convert(db_path):
    """Return list of dicts: {source_path, extension, ...} for all content files."""
    # Uses db_utils to query content table
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        return db_utils.get_records("content", None, conn=conn)
    finally:
        conn.close()

# --- Caching ---
def should_convert(input_path, output_path, force=False):
    """Return True if conversion should be attempted."""
    if force:
        return True
    if not os.path.exists(output_path):
        return True
    if not os.path.exists(input_path):
        return False
    return os.path.getmtime(output_path) < os.path.getmtime(input_path)

# --- Converter Dispatch ---
def convert_file(input_path, output_path, input_ext, output_ext, db_path, log_queue=None):
    """
    Dispatch to the correct converter function based on input/output extensions.
    Returns a dict: {input, output, status, reason, start_time, end_time}
    """
    start = datetime.now().isoformat()
    try:
        # Example dispatch pattern
        if input_ext == ".md" and output_ext == ".pdf":
            result = convert_md_to_pdf(input_path, output_path)
        elif input_ext == ".docx" and output_ext == ".md":
            result = convert_docx_to_md(input_path, output_path)
        elif input_ext == ".ipynb" and output_ext == ".epub":
            result = convert_ipynb_to_epub(input_path, output_path)
        # ... add more converters ...
        else:
            msg = f"No converter for {input_ext} -> {output_ext}"
            logging.warning(msg)
            return {"input": input_path, "output": output_path, "status": "skipped", "reason": msg, "start_time": start, "end_time": datetime.now().isoformat()}
        status = "success" if result else "failed"
        return {"input": input_path, "output": output_path, "status": status, "reason": None, "start_time": start, "end_time": datetime.now().isoformat()}
    except Exception as e:
        logging.error(f"Conversion failed: {input_path} -> {output_path}: {e}")
        return {"input": input_path, "output": output_path, "status": "failed", "reason": str(e), "start_time": start, "end_time": datetime.now().isoformat()}

# --- Converters ---
def convert_md_to_txt(input_path, output_path):
    """
    Convert Markdown to plain text using Pandoc.
    Images will be ignored in plain text output.
    """
    import subprocess
    try:
        subprocess.run([
            "pandoc", input_path, "-t", "plain", "-o", output_path
        ], check=True)
        return True
    except Exception as e:
        logging.error(f"Pandoc failed for TXT: {e}")
        return False

def convert_md_to_md(input_path, output_path):
    """
    Copy Markdown file to new location (identity conversion).
    Images are referenced as in the original file.
    """
    import shutil
    try:
        shutil.copy2(input_path, output_path)
        return True
    except Exception as e:
        logging.error(f"Copy failed for MD: {e}")
        return False

def convert_md_to_marp(input_path, output_path):
    """
    Convert Markdown to Marp Markdown (for slides). Assumes Marp-compatible input.
    This is a simple copy; for real conversion, use Marp CLI.
    """
    import shutil
    try:
        shutil.copy2(input_path, output_path)
        return True
    except Exception as e:
        logging.error(f"Copy failed for MARP: {e}")
        return False

def convert_md_to_tex(input_path, output_path):
    """
    Convert Markdown to LaTeX using Pandoc.
    Images are converted to LaTeX includegraphics commands.
    """
    import subprocess
    try:
        subprocess.run([
            "pandoc", input_path, "-o", output_path
        ], check=True)
        return True
    except Exception as e:
        logging.error(f"Pandoc failed for LaTeX: {e}")
        return False

def convert_md_to_pdf(input_path, output_path):
    """
    Convert Markdown to PDF using Pandoc.
    Images are embedded in the PDF if accessible.
    """
    import subprocess
    try:
        subprocess.run([
            "pandoc", input_path, "-o", output_path
        ], check=True)
        return True
    except Exception as e:
        logging.error(f"Pandoc failed for PDF: {e}")
        return False

def convert_md_to_docx(input_path, output_path):
    """
    Convert Markdown to DOCX using Pandoc, extracting media to embed images.
    """
    import subprocess
    import os
    try:
        media_dir = os.path.splitext(output_path)[0] + "_media"
        subprocess.run([
            "pandoc", input_path, "-o", output_path,
            "--extract-media", media_dir
        ], check=True)
        return True
    except Exception as e:
        logging.error(f"Pandoc failed for DOCX: {e}")
        return False

def convert_md_to_ppt(input_path, output_path):
    """
    Convert Markdown to PowerPoint (PPTX) using Pandoc.
    Images are embedded if accessible.
    """
    import subprocess
    try:
        subprocess.run([
            "pandoc", input_path, "-o", output_path
        ], check=True)
        return True
    except Exception as e:
        logging.error(f"Pandoc failed for PPTX: {e}")
        return False

def convert_md_to_jupyter(input_path, output_path):
    """
    Convert Markdown to Jupyter Notebook (.ipynb) using Pandoc.
    Images are included as notebook attachments if possible.
    """
    import subprocess
    try:
        subprocess.run([
            "pandoc", input_path, "-o", output_path
        ], check=True)
        return True
    except Exception as e:
        logging.error(f"Pandoc failed for Jupyter: {e}")
        return False

def convert_ipynb_to_epub(input_path, output_path):
    """
    Convert a Jupyter Notebook (.ipynb) file to EPUB (.epub).

    Args:
        input_path (str): Path to the input notebook file.
        output_path (str): Path to the output EPUB file.

    Returns:
        bool: True if conversion succeeds, False otherwise.
    """
    # TODO: Implement with nbconvert or other tool
    return False

def convert_md_to_txt(input_path, output_path):
    """Convert .md to .txt (stub)."""
    logging.info(f"[STUB] convert_md_to_txt called: {input_path} -> {output_path}")
    return False

def convert_md_to_md(input_path, output_path):
    """Convert .md to .md (stub)."""
    logging.info(f"[STUB] convert_md_to_md called: {input_path} -> {output_path}")
    return False

def convert_md_to_marp(input_path, output_path):
    """Convert .md to .marp (stub)."""
    logging.info(f"[STUB] convert_md_to_marp called: {input_path} -> {output_path}")
    return False

def convert_md_to_tex(input_path, output_path):
    """Convert .md to .tex (stub)."""
    logging.info(f"[STUB] convert_md_to_tex called: {input_path} -> {output_path}")
    return False

def convert_md_to_pdf(input_path, output_path):
    """Convert .md to .pdf (already implemented)."""
    import subprocess
    try:
        subprocess.run(["pandoc", input_path, "-o", output_path], check=True)
        return True
    except Exception as e:
        logging.error(f"Pandoc failed: {e}")
        return False

def convert_md_to_ppt(input_path, output_path):
    """Convert .md to .ppt (stub)."""
    logging.info(f"[STUB] convert_md_to_ppt called: {input_path} -> {output_path}")
    return False

def convert_md_to_jupyter(input_path, output_path):
    """Convert .md to .jupyter (stub)."""
    logging.info(f"[STUB] convert_md_to_jupyter called: {input_path} -> {output_path}")
    return False

def convert_marp_to_txt(input_path, output_path):
    """Convert .marp to .txt (stub)."""
    logging.info(f"[STUB] convert_marp_to_txt called: {input_path} -> {output_path}")
    return False

def convert_marp_to_md(input_path, output_path):
    """Convert .marp to .md (stub)."""
    logging.info(f"[STUB] convert_marp_to_md called: {input_path} -> {output_path}")
    return False

def convert_marp_to_marp(input_path, output_path):
    """Convert .marp to .marp (stub)."""
    logging.info(f"[STUB] convert_marp_to_marp called: {input_path} -> {output_path}")
    return False

def convert_marp_to_pdf(input_path, output_path):
    """Convert .marp to .pdf (stub)."""
    logging.info(f"[STUB] convert_marp_to_pdf called: {input_path} -> {output_path}")
    return False

def convert_marp_to_docx(input_path, output_path):
    """Convert .marp to .docx (stub)."""
    logging.info(f"[STUB] convert_marp_to_docx called: {input_path} -> {output_path}")
    return False

def convert_marp_to_ppt(input_path, output_path):
    """Convert .marp to .ppt (stub)."""
    logging.info(f"[STUB] convert_marp_to_ppt called: {input_path} -> {output_path}")
    return False

def convert_tex_to_txt(input_path, output_path):
    """Convert .tex to .txt (stub)."""
    logging.info(f"[STUB] convert_tex_to_txt called: {input_path} -> {output_path}")
    return False
def convert_tex_to_md(input_path, output_path):
    """Convert .tex to .md (stub)."""
    logging.info(f"[STUB] convert_tex_to_md called: {input_path} -> {output_path}")
    return False
def convert_tex_to_tex(input_path, output_path):
    """Convert .tex to .tex (stub)."""
    logging.info(f"[STUB] convert_tex_to_tex called: {input_path} -> {output_path}")
    return False
def convert_tex_to_pdf(input_path, output_path):
    """Convert .tex to .pdf (stub)."""
    logging.info(f"[STUB] convert_tex_to_pdf called: {input_path} -> {output_path}")
    return False
def convert_tex_to_docx(input_path, output_path):
    """Convert .tex to .docx (stub)."""
    logging.info(f"[STUB] convert_tex_to_docx called: {input_path} -> {output_path}")
    return False
def convert_ipynb_to_txt(input_path, output_path):
    """Convert .ipynb to .txt (stub)."""
    logging.info(f"[STUB] convert_ipynb_to_txt called: {input_path} -> {output_path}")
    return False
def convert_ipynb_to_md(input_path, output_path):
    """Convert .ipynb to .md (stub)."""
    logging.info(f"[STUB] convert_ipynb_to_md called: {input_path} -> {output_path}")
    return False
def convert_ipynb_to_tex(input_path, output_path):
    """Convert .ipynb to .tex (stub)."""
    logging.info(f"[STUB] convert_ipynb_to_tex called: {input_path} -> {output_path}")
    return False
def convert_ipynb_to_pdf(input_path, output_path):
    """Convert .ipynb to .pdf (stub)."""
    logging.info(f"[STUB] convert_ipynb_to_pdf called: {input_path} -> {output_path}")
    return False
def convert_ipynb_to_docx(input_path, output_path):
    """Convert .ipynb to .docx (stub)."""
    logging.info(f"[STUB] convert_ipynb_to_docx called: {input_path} -> {output_path}")
    return False
def convert_ipynb_to_jupyter(input_path, output_path):
    """Convert .ipynb to .jupyter (stub)."""
    logging.info(f"[STUB] convert_ipynb_to_jupyter called: {input_path} -> {output_path}")
    return False
def convert_ipynb_to_ipynb(input_path, output_path):
    """Convert .ipynb to .ipynb (stub)."""
    logging.info(f"[STUB] convert_ipynb_to_ipynb called: {input_path} -> {output_path}")
    return False
def convert_jupyter_to_md(input_path, output_path):
    """Convert .jupyter to .md (stub)."""
    logging.info(f"[STUB] convert_jupyter_to_md called: {input_path} -> {output_path}")
    return False
def convert_jupyter_to_tex(input_path, output_path):
    """Convert .jupyter to .tex (stub)."""
    logging.info(f"[STUB] convert_jupyter_to_tex called: {input_path} -> {output_path}")
    return False
def convert_jupyter_to_pdf(input_path, output_path):
    """Convert .jupyter to .pdf (stub)."""
    logging.info(f"[STUB] convert_jupyter_to_pdf called: {input_path} -> {output_path}")
    return False
def convert_jupyter_to_docx(input_path, output_path):
    """Convert .jupyter to .docx (stub)."""
    logging.info(f"[STUB] convert_jupyter_to_docx called: {input_path} -> {output_path}")
    return False
def convert_jupyter_to_jupyter(input_path, output_path):
    """Convert .jupyter to .jupyter (stub)."""
    logging.info(f"[STUB] convert_jupyter_to_jupyter called: {input_path} -> {output_path}")
    return False
def convert_jupyter_to_ipynb(input_path, output_path):
    """Convert .jupyter to .ipynb (stub)."""
    logging.info(f"[STUB] convert_jupyter_to_ipynb called: {input_path} -> {output_path}")
    return False
def convert_docx_to_txt(input_path, output_path):
    """Convert .docx to .txt (stub)."""
    logging.info(f"[STUB] convert_docx_to_txt called: {input_path} -> {output_path}")
    return False
def convert_docx_to_md(input_path, output_path):
    """Convert .docx to .md (already implemented as stub)."""
    # TODO: Implement with Pandoc or other tool
    return False
def convert_docx_to_tex(input_path, output_path):
    """Convert .docx to .tex (stub)."""
    logging.info(f"[STUB] convert_docx_to_tex called: {input_path} -> {output_path}")
    return False
def convert_docx_to_pdf(input_path, output_path):
    """Convert .docx to .pdf (stub)."""
    logging.info(f"[STUB] convert_docx_to_pdf called: {input_path} -> {output_path}")
    return False
def convert_docx_to_docx(input_path, output_path):
    """Convert .docx to .docx (stub)."""
    logging.info(f"[STUB] convert_docx_to_docx called: {input_path} -> {output_path}")
    return False
def convert_ppt_to_txt(input_path, output_path):
    """Convert .ppt to .txt (stub)."""
    logging.info(f"[STUB] convert_ppt_to_txt called: {input_path} -> {output_path}")
    return False
def convert_ppt_to_ppt(input_path, output_path):
    """Convert .ppt to .ppt (stub)."""
    logging.info(f"[STUB] convert_ppt_to_ppt called: {input_path} -> {output_path}")
    return False
def convert_txt_to_txt(input_path, output_path):
    """Convert .txt to .txt (stub)."""
    logging.info(f"[STUB] convert_txt_to_txt called: {input_path} -> {output_path}")
    return False
def convert_txt_to_md(input_path, output_path):
    """Convert .txt to .md (stub)."""
    logging.info(f"[STUB] convert_txt_to_md called: {input_path} -> {output_path}")
    return False
def convert_txt_to_tex(input_path, output_path):
    """Convert .txt to .tex (stub)."""
    logging.info(f"[STUB] convert_txt_to_tex called: {input_path} -> {output_path}")
    return False
def convert_txt_to_docx(input_path, output_path):
    """Convert .txt to .docx (stub)."""
    logging.info(f"[STUB] convert_txt_to_docx called: {input_path} -> {output_path}")
    return False
def convert_txt_to_pdf(input_path, output_path):
    """Convert .txt to .pdf (stub)."""
    logging.info(f"[STUB] convert_txt_to_pdf called: {input_path} -> {output_path}")
    return False
print("Total converter stubs defined: 44")

# --- Orchestrator ---
def batch_convert_all_content(db_path=DB_PATH, force=False, summary_json_path=SUMMARY_JSON):
    configure_logging()
    conversions = get_enabled_conversions(db_path)
    files = get_content_files_to_convert(db_path)
    jobs = []
    # Debug: print keys of first few file dicts
    for i, file in enumerate(files):
        if i < 5:
            print(f"DEBUG file dict {i}: keys={list(file.keys())}, file={file}")
    for file in files:
        input_path = file["source_path"]
        input_ext = file.get("mime_type")
        if not input_ext:
            _, input_ext = os.path.splitext(input_path)
        for (src_ext, tgt_ext) in conversions:
            if input_ext != src_ext:
                continue
            output_path = os.path.join(BUILD_DIR, os.path.splitext(os.path.basename(input_path))[0] + tgt_ext)
            if not should_convert(input_path, output_path, force=force):
                logging.info(f"Skipping up-to-date: {input_path} -> {output_path}")
                continue
            jobs.append((input_path, output_path, input_ext, tgt_ext, db_path))
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_job = {executor.submit(convert_file, *job): job for job in jobs}
        for future in concurrent.futures.as_completed(future_to_job):
            result = future.result()
            results.append(result)
    # Write summary JSON
    os.makedirs(BUILD_DIR, exist_ok=True)
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    # Print plain text summary
    print("\nConversion Summary:")
    for r in results:
        print(f"{r['input']} -> {r['output']}: {r['status']} ({r.get('reason', '')})")

# --- CLI ---
def cli():
    import argparse
    parser = argparse.ArgumentParser(description="OERForge Batch Conversion Pipeline")
    parser.add_argument("--force", action="store_true", help="Force all conversions (ignore cache)")
    parser.add_argument("--summary-json", type=str, default=SUMMARY_JSON, help="Path to summary JSON output")