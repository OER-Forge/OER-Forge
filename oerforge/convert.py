"""
convert.py
----------
Content Conversion Orchestrator

Handles conversion of content files (Markdown, Jupyter, DOCX, etc.) to various output formats
using Pandoc and other tools. Also manages asset copying and database updates for non-HTML outputs.

Usage:
    python convert.py
"""

import shutil
import re
import os
import logging
import json
import concurrent.futures
from datetime import datetime

try:
    from . import db_utils
except ImportError:
    import db_utils

# --- Constants ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')
LOG_PATH = os.path.join(PROJECT_ROOT, 'log', 'build.log')
SUMMARY_JSON = os.path.join(BUILD_DIR, 'conversion_summary.json')
DEBUG_MODE = os.environ.get("DEBUG", "0") == "1"

def get_page_files_dir(output_path):
    """
    Given an output file path (e.g., build/about.html), return the associated files directory (e.g., build/about_files/).
    Ensures the directory is always inside build/.
    """
    build_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build')
    if not os.path.isabs(output_path) and not output_path.startswith('build/'):
        output_path = os.path.join(build_dir, output_path)
    base, _ = os.path.splitext(output_path)
    return f"{base}_files"

def copy_and_update_assets_for_non_html(input_path, output_path, db_path):
    """
    For non-HTML conversions, copy all referenced assets to PAGE_files/ and update their DB paths.
    - Finds all image references in the Markdown file.
    - Copies each asset to the correct PAGE_files directory.
    - Updates the files and pages_files tables in the database.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        md = f.read()
    # Regex for Markdown and HTML image links
    img_links = re.findall(r'!\[[^\]]*\]\(([^)]+)\)|<img [^>]*src=[\"\\\']([^\"\\\']+)[\"\\\']', md)
    img_paths = [p for tup in img_links for p in tup if p]
    if not img_paths:
        return
    # Determine the correct PAGE_files dir (avoid nesting)
    if output_path.endswith('_files') or os.path.basename(os.path.dirname(output_path)).endswith('_files'):
        page_files_dir = os.path.dirname(output_path)
    else:
        page_files_dir = get_page_files_dir(output_path)
    os.makedirs(page_files_dir, exist_ok=True)
    for rel_path in img_paths:
        rel_path_clean = rel_path.split('?')[0].split('#')[0]
        src_path = os.path.join(PROJECT_ROOT, 'content', rel_path_clean)
        if os.path.exists(src_path):
            dst_path = os.path.join(page_files_dir, os.path.basename(rel_path_clean))
            shutil.copy2(src_path, dst_path)
            # Update DB: files.relative_path and pages_files.page_path
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                new_rel = os.path.join(os.path.basename(page_files_dir), os.path.basename(rel_path_clean))
                cursor.execute("UPDATE files SET relative_path=? WHERE relative_path=?", (new_rel, rel_path_clean))
                cursor.execute("UPDATE pages_files SET page_path=? WHERE page_path=?", (new_rel, rel_path_clean))
                conn.commit()
                conn.close()
            except Exception as e:
                logging.error(f"[ASSET-DB] Failed to update DB for asset {rel_path_clean}: {e}")
        else:
            logging.warning(f"[ASSET] Referenced asset not found: {src_path}")

def get_section_files_dir(content_row):
    """
    Given a content row, return the absolute path to the page-local files/ directory using PAGE_files convention.
    E.g., for build/about.html, returns build/about_files/
    """
    output_path = content_row.get("output_path")
    if not output_path:
        return None
    return get_page_files_dir(output_path)

def get_enabled_conversions(db_path):
    """
    Return list of (input_ext, output_ext) for enabled conversions.
    Uses db_utils to query conversion_capabilities for enabled conversions.
    """
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
    """
    Return list of dicts: {source_path, extension, ...} for all content files.
    Uses db_utils to query content table.
    """
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        return db_utils.get_records("content", None, conn=conn)
    finally:
        conn.close()

def should_convert(input_path, output_path, force=False):
    """
    Return True if conversion should be attempted.
    - Always convert if force is True.
    - Convert if output does not exist or is older than input.
    """
    if force:
        return True
    if not os.path.exists(output_path):
        return True
    if not os.path.exists(input_path):
        return False
    return os.path.getmtime(output_path) < os.path.getmtime(input_path)

def convert_file(input_path, output_path, input_ext, output_ext, db_path, log_queue=None):
    """
    Dispatch to the correct converter function based on input/output extensions.
    Returns a dict: {input, output, status, reason, start_time, end_time}
    """
    start = datetime.now().isoformat()
    logging.debug(f"[convert_file] Attempting: {input_path} ({input_ext}) -> {output_path} ({output_ext})")
    try:
        # Dispatch for all real Markdown converters
        if input_ext == ".md" and output_ext == ".txt":
            logging.debug(f"[convert_file] Dispatch: convert_md_to_txt")
            result = convert_md_to_txt(input_path, output_path)
            copy_and_update_assets_for_non_html(input_path, output_path, db_path)
        elif input_ext == ".md" and output_ext == ".md":
            logging.debug(f"[convert_file] Dispatch: convert_md_to_md")
            result = convert_md_to_md(input_path, output_path)
            copy_and_update_assets_for_non_html(input_path, output_path, db_path)
        elif input_ext == ".md" and output_ext == ".tex":
            logging.debug(f"[convert_file] Dispatch: convert_md_to_tex")
            result = convert_md_to_tex(input_path, output_path)
            copy_and_update_assets_for_non_html(input_path, output_path, db_path)
        elif input_ext == ".md" and output_ext == ".pdf":
            logging.debug(f"[convert_file] Dispatch: convert_md_to_pdf")
            result = convert_md_to_pdf(input_path, output_path)
            copy_and_update_assets_for_non_html(input_path, output_path, db_path)
        elif input_ext == ".md" and output_ext == ".docx":
            logging.debug(f"[convert_file] Dispatch: convert_md_to_docx")
            result = convert_md_to_docx(input_path, output_path)
            copy_and_update_assets_for_non_html(input_path, output_path, db_path)
        elif input_ext == ".docx" and output_ext == ".md":
            logging.debug(f"[convert_file] Dispatch: convert_docx_to_md")
            result = convert_docx_to_md(input_path, output_path)
            copy_and_update_assets_for_non_html(input_path, output_path, db_path)
        elif input_ext == ".ipynb" and output_ext == ".epub":
            logging.debug(f"[convert_file] Dispatch: convert_ipynb_to_epub")
            result = convert_ipynb_to_epub(input_path, output_path)
            copy_and_update_assets_for_non_html(input_path, output_path, db_path)
        elif input_ext == ".md" and output_ext == ".epub":
            logging.debug(f"[convert_file] Dispatch: convert_md_to_epub")
            result = convert_md_to_epub(input_path, output_path)
            copy_and_update_assets_for_non_html(input_path, output_path, db_path)
        else:
            msg = f"No converter for {input_ext} -> {output_ext}"
            logging.warning(msg)
            return {"input": input_path, "output": output_path, "status": "skipped", "reason": msg, "start_time": start, "end_time": datetime.now().isoformat()}
        status = "success" if result else "failed"
        logging.info(f"[convert_file] {input_path} -> {output_path}: {status}")
        return {"input": input_path, "output": output_path, "status": status, "reason": None, "start_time": start, "end_time": datetime.now().isoformat()}
    except Exception as e:
        logging.error(f"[convert_file] Conversion failed: {input_path} -> {output_path}: {e}")
        return {"input": input_path, "output": output_path, "status": "failed", "reason": str(e), "start_time": start, "end_time": datetime.now().isoformat()}

# --- Markdown Converters ---
def convert_md_to_txt(input_path, output_path):
    """
    Convert Markdown to plain text using Pandoc.
    Images will be ignored in plain text output.
    """
    import subprocess
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        subprocess.run([
            "pandoc", input_path, "-t", "plain", "-o", output_path
        ], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Pandoc failed for TXT: {e}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Pandoc failed for TXT (unexpected): {e}")
        return False

def convert_md_to_md(input_path, output_path):
    """
    Copy Markdown file to new location (identity conversion).
    Images are referenced as in the original file.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy2(input_path, output_path)
        return True
    except Exception as e:
        logging.error(f"Copy failed for MD: {e}")
        return False

def convert_md_to_tex(input_path, output_path):
    """
    Convert Markdown to LaTeX using Pandoc.
    Images are converted to LaTeX includegraphics commands.
    """
    import subprocess
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        subprocess.run([
            "pandoc", input_path, "-o", output_path
        ], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Pandoc failed for LaTeX: {e}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Pandoc failed for LaTeX (unexpected): {e}")
        return False

def convert_md_to_pdf(input_path, output_path):
    """
    Convert Markdown to PDF using Pandoc, removing emoji characters before conversion.
    """
    import subprocess
    import tempfile
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        import emoji
    except ImportError:
        logging.error("The 'emoji' package is required for emoji removal in PDF export. Please install it.")
        return False
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        md_text_clean = emoji.replace_emoji(md_text, replace="")
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md", encoding="utf-8") as tmp:
            tmp.write(md_text_clean)
            tmp_path = tmp.name
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_path = os.path.join(project_root, "templates", "tex", "oerforge-pdf-template.tex")
        pandoc_cmd = ["pandoc", tmp_path, "-o", output_path]
        if os.path.exists(template_path):
            pandoc_cmd += ["--template", template_path]
        subprocess.run(pandoc_cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Pandoc failed for PDF (emoji removed): {e}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Pandoc failed for PDF (unexpected): {e}")
        return False

def convert_md_to_docx(input_path, output_path):
    """
    Convert Markdown to DOCX using Pandoc, extracting media to embed images.
    """
    import subprocess
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        from .convert import get_page_files_dir
        media_dir = get_page_files_dir(output_path)
        subprocess.run([
            "pandoc", input_path, "-o", output_path,
            "--extract-media", media_dir
        ], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Pandoc failed for DOCX: {e}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Pandoc failed for DOCX (unexpected): {e}")
        return False

def convert_md_to_epub(input_path, output_path):
    """
    Convert Markdown to EPUB using Pandoc.
    """
    import subprocess
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        subprocess.run([
            "pandoc", input_path, "-o", output_path
        ], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Pandoc failed for EPUB: {e}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Pandoc failed for EPUB (unexpected): {e}")
        return False

# --- Stub converters for other formats (ipynb, docx, marp, tex, jupyter, ppt, txt) ---
# ...existing code for stub converters...

print("Total converter stubs defined: 44")

def batch_convert_all_content(db_path=DB_PATH, force=False, summary_json_path=SUMMARY_JSON):
    """
    Orchestrate batch conversion of all content files.
    - Gathers enabled conversions and content files.
    - Schedules and runs conversion jobs in parallel.
    - Writes a summary JSON and prints a plain text summary.
    """
    logging.info("[batch_convert_all_content] Starting batch conversion...")
    conversions = get_enabled_conversions(db_path)
    logging.debug(f"[batch_convert_all_content] Enabled conversions: {conversions}")
    files = get_content_files_to_convert(db_path)
    logging.debug(f"[batch_convert_all_content] Content files to convert: {len(files)}")
    jobs = []
    for i, file in enumerate(files):
        if i < 5:
            logging.debug(f"[batch_convert_all_content] file dict {i}: keys={list(file.keys())}, file={file}")
    for file in files:
        input_path = file["source_path"]
        if input_path and os.path.basename(input_path) == "_index.md":
            logging.info(f"[batch_convert_all_content] Skipping conversion for section index: {input_path}")
            continue
        input_ext = file.get("mime_type")
        if not input_ext:
            _, input_ext = os.path.splitext(input_path)
        export_types = file.get("export_types")
        export_types_list = [t.strip() for t in export_types.split(",") if t.strip()] if export_types else []
        export_force = file.get("export_force")
        force_this = bool(export_force) if export_force is not None else force
        base_output_path = file.get("output_path")
        if not base_output_path:
            continue
        base_dir = os.path.dirname(base_output_path)
        base_name = os.path.splitext(os.path.basename(base_output_path))[0]
        did_identity = False
        for (src_ext, tgt_ext) in conversions:
            if input_ext != src_ext:
                continue
            tgt_fmt = tgt_ext.lstrip(".")
            if tgt_ext == ".html":
                output_path = os.path.join(base_dir, base_name + tgt_ext)
            else:
                page_files_dir = get_page_files_dir(os.path.join(base_dir, base_name + ".html"))
                os.makedirs(page_files_dir, exist_ok=True)
                output_path = os.path.join(page_files_dir, base_name + tgt_ext)
            if input_ext == tgt_ext:
                if export_types_list and tgt_fmt not in export_types_list:
                    logging.debug(f"[batch_convert_all_content] SKIP: identity conversion {input_ext}->{tgt_ext} excluded by export_types_list {export_types_list}")
                    continue
                did_identity = True
            else:
                if export_types_list and tgt_fmt not in export_types_list:
                    continue
            if os.path.abspath(input_path) == os.path.abspath(output_path):
                logging.info(f"[batch_convert_all_content] Skipping identity conversion to avoid overwriting source: {input_path} -> {output_path}")
                continue
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if not should_convert(input_path, output_path, force=force_this):
                logging.info(f"[batch_convert_all_content] Skipping up-to-date: {input_path} -> {output_path}")
                continue
            logging.debug(f"[batch_convert_all_content] Adding job: {input_path} ({input_ext}) -> {output_path} ({tgt_ext})")
            jobs.append((input_path, output_path, input_ext, tgt_ext, db_path))
    logging.info(f"[batch_convert_all_content] Total jobs queued: {len(jobs)}")
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_job = {executor.submit(convert_file, *job): job for job in jobs}
        for future in concurrent.futures.as_completed(future_to_job):
            result = future.result()
            logging.debug(f"[batch_convert_all_content] Job result: {result}")
            results.append(result)
    os.makedirs(BUILD_DIR, exist_ok=True)
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nConversion Summary:")