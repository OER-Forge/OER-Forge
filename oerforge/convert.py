import sys
import os
import shutil
import sqlite3
import subprocess
import logging
import re
from nbconvert import MarkdownExporter
from nbconvert.preprocessors import ExecutePreprocessor, ExtractOutputPreprocessor
from traitlets.config import Config
from markdown_it import MarkdownIt

# --- Constants ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(PROJECT_ROOT, 'log', 'build.log')
CONTENT_ROOT = os.path.join(PROJECT_ROOT, 'content')
BUILD_FILES_ROOT = os.path.join(PROJECT_ROOT, 'build', 'files')
BUILD_IMAGES_ROOT = os.path.join(PROJECT_ROOT, 'build', 'images')
DB_PATH = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
DEBUG_MODE = os.environ.get("DEBUG", "0") == "1"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# --- Logging Setup ---
def configure_logging():
    log_level = logging.DEBUG if DEBUG_MODE else getattr(logging, LOG_LEVEL, logging.INFO)
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

configure_logging()

# --- Image Handling ---
def query_images_for_content(content_record, conn):
    from oerforge.db_utils import get_records
    images = get_records(
        "files",
        "is_image=1 AND referenced_page=?",
        (content_record['source_path'],),
        conn=conn
    )
    logging.debug(f"[IMAGES] Found {len(images)} images for {content_record['source_path']}")
    return images

def copy_images_to_build(images, images_root=BUILD_IMAGES_ROOT, conn=None):
    os.makedirs(images_root, exist_ok=True)
    copied = []
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
        if referenced_page and referenced_page in content_lookup and not os.path.isabs(src):
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

def update_markdown_image_links(md_path, images, images_root=BUILD_IMAGES_ROOT):
    if not os.path.exists(md_path):
        logging.warning(f"[IMAGES] Markdown file not found: {md_path}")
        return
    rel_path = os.path.relpath(md_path, BUILD_FILES_ROOT)
    source_path = os.path.join(CONTENT_ROOT, rel_path)
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
            rel_img_path = os.path.join('..', '..', 'images', filename)
            img_map[os.path.basename(src)] = rel_img_path
        conn.close()
    except Exception as e:
        logging.error(f"[IMAGES] DB lookup failed for {md_path}: {e}")
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.splitlines()
    new_lines = lines.copy()
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
    images = query_images_for_content(content_record, conn)
    copy_images_to_build(images, images_root=BUILD_IMAGES_ROOT, conn=conn)
    rel_path = os.path.relpath(content_record['source_path'], CONTENT_ROOT)
    md_path = os.path.join(BUILD_FILES_ROOT, rel_path)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
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

# --- Conversion Functions ---
def convert_md_to_docx(src_path, out_path, record_id=None, conn=None):
    logging.info(f"[DOCX] Starting conversion: {src_path} -> {out_path}")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        subprocess.run(["pandoc", src_path, "-o", out_path], check=True)
        logging.info(f"[DOCX] Converted {src_path} to {out_path}")
        if conn is not None:
            from oerforge import db_utils
            db_utils.insert_records(
                'files',
                [{
                    'filename': os.path.basename(out_path),
                    'extension': '.docx',
                    'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'url': out_path,
                    'referenced_page': src_path,
                    'relative_path': out_path
                }],
                conn=conn
            )
        if record_id:
            from oerforge import db_utils
            import datetime
            try:
                db_utils.insert_records(
                    'conversion_results',
                    [{
                        'content_id': record_id,
                        'source_format': '.md',
                        'target_format': '.docx',
                        'output_path': out_path,
                        'conversion_time': datetime.datetime.now().isoformat(),
                        'status': 'success'
                    }],
                    conn=conn
                )
                logging.info(f"[DOCX] conversion_results updated for id {record_id}")
            except Exception as e:
                logging.error(f"[DOCX] conversion_results insert failed for id {record_id}: {e}")
    except Exception as e:
        logging.error(f"[DOCX] Pandoc conversion failed for {src_path}: {e}")

def convert_md_to_pdf(src_path, out_path, record_id=None, conn=None):
    logging.info(f"[PDF] Starting conversion: {src_path} -> {out_path}")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        subprocess.run(["pandoc", src_path, "-o", out_path], check=True)
        logging.info(f"[PDF] Converted {src_path} to {out_path}")
        if conn is not None:
            from oerforge import db_utils
            db_utils.insert_records(
                'files',
                [{
                    'filename': os.path.basename(out_path),
                    'extension': '.pdf',
                    'mime_type': 'application/pdf',
                    'url': out_path,
                    'referenced_page': src_path,
                    'relative_path': out_path
                }],
                conn=conn
            )
        if record_id:
            from oerforge import db_utils
            import datetime
            try:
                db_utils.insert_records(
                    'conversion_results',
                    [{
                        'content_id': record_id,
                        'source_format': '.md',
                        'target_format': '.pdf',
                        'output_path': out_path,
                        'conversion_time': datetime.datetime.now().isoformat(),
                        'status': 'success'
                    }],
                    conn=conn
                )
                logging.info(f"[PDF] conversion_results updated for id {record_id}")
            except Exception as e:
                logging.error(f"[PDF] conversion_results insert failed for id {record_id}: {e}")
    except Exception as e:
        logging.error(f"[PDF] Pandoc conversion failed for {src_path}: {e}")

def convert_md_to_tex(src_path, out_path, record_id=None, conn=None):
    logging.info(f"[TEX] Starting conversion: {src_path} -> {out_path}")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        subprocess.run(["pandoc", src_path, "-o", out_path], check=True)
        logging.info(f"[TEX] Converted {src_path} to {out_path}")
        if conn is not None:
            from oerforge import db_utils
            db_utils.insert_records(
                'files',
                [{
                    'filename': os.path.basename(out_path),
                    'extension': '.tex',
                    'mime_type': 'application/x-tex',
                    'url': out_path,
                    'referenced_page': src_path,
                    'relative_path': out_path
                }],
                conn=conn
            )
        if record_id:
            from oerforge import db_utils
            import datetime
            try:
                db_utils.insert_records(
                    'conversion_results',
                    [{
                        'content_id': record_id,
                        'source_format': '.md',
                        'target_format': '.tex',
                        'output_path': out_path,
                        'conversion_time': datetime.datetime.now().isoformat(),
                        'status': 'success'
                    }],
                    conn=conn
                )
                logging.info(f"[TEX] conversion_results updated for id {record_id}")
            except Exception as e:
                logging.error(f"[TEX] conversion_results insert failed for id {record_id}: {e}")
    except Exception as e:
        logging.error(f"[TEX] Pandoc conversion failed for {src_path}: {e}")

def convert_md_to_txt(src_path, out_path, record_id=None, conn=None):
    logging.info(f"[TXT] Starting conversion: {src_path} -> {out_path}")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        with open(src_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        md = MarkdownIt()
        tokens = md.parse(md_text)

        def extract_text_with_newlines(tokens, depth=0):
            indent = '  ' * depth
            if tokens is None:
                logging.warning(f"[TXT][extract_text] tokens is None at depth {depth}")
                return ""
            if not tokens:
                logging.debug(f"[TXT][extract_text] tokens is empty at depth {depth}")
                return ""
            text = []
            for t in tokens:
                logging.debug(f"{indent}[TXT][extract_text] token type: {getattr(t, 'type', None)}, content: {getattr(t, 'content', None)}")
                if getattr(t, 'type', None) == "link_open":
                    text.append("")
                elif getattr(t, 'type', None) == "link_close":
                    text.append("")
                elif getattr(t, 'type', None) == "inline" and hasattr(t, "children"):
                    i = 0
                    children = t.children or []
                    while i < len(children):
                        child = children[i]
                        if getattr(child, 'type', None) == 'link_open':
                            href = None
                            for attr in getattr(child, 'attrs', []) or []:
                                if attr[0] == 'href':
                                    href = attr[1]
                                    break
                            link_text = ""
                            j = i + 1
                            while j < len(children) and getattr(children[j], 'type', None) != 'link_close':
                                if getattr(children[j], 'type', None) == 'text':
                                    link_text += children[j].content
                                elif hasattr(children[j], 'children'):
                                    link_text += extract_text_with_newlines(children[j].children, depth+2)
                                j += 1
                            if link_text:
                                text.append(link_text)
                            if href:
                                text.append(f" ({href})")
                            i = j
                        elif getattr(child, 'type', None) == 'text':
                            text.append(child.content)
                        elif hasattr(child, 'children'):
                            text.append(extract_text_with_newlines(child.children, depth+2))
                        i += 1
                elif getattr(t, 'type', None) == "text":
                    text.append(t.content)
                elif t.type in ("paragraph_close", "heading_close"):
                    text.append("\n\n")
                elif t.type in ("list_item_close"):
                    text.append("\n")
                elif hasattr(t, "children"):
                    text.append(extract_text_with_newlines(t.children, depth+1))
            try:
                joined = "".join(text)
            except Exception as e:
                logging.error(f"[TXT][extract_text] join failed at depth {depth}: {e}, text={text}")
                raise
            return joined

        plain_text = extract_text_with_newlines(tokens).strip()
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(plain_text)
        logging.info(f"[TXT] Converted {src_path} to {out_path}")
        if conn is not None:
            from oerforge import db_utils
            db_utils.insert_records(
                'files',
                [{
                    'filename': os.path.basename(out_path),
                    'extension': '.txt',
                    'mime_type': 'text/plain',
                    'url': out_path,
                    'referenced_page': src_path,
                    'relative_path': out_path
                }],
                conn=conn
            )
        if record_id:
            from oerforge import db_utils
            import datetime
            try:
                db_utils.insert_records(
                    'conversion_results',
                    [{
                        'content_id': record_id,
                        'source_format': '.md',
                        'target_format': '.txt',
                        'output_path': out_path,
                        'conversion_time': datetime.datetime.now().isoformat(),
                        'status': 'success'
                    }],
                    conn=conn
                )
                logging.info(f"[TXT] conversion_results updated for id {record_id}")
            except Exception as e:
                logging.error(f"[TXT] conversion_results insert failed for id {record_id}: {e}")
    except Exception as e:
        logging.error(f"[TXT] Conversion failed for {src_path}: {e}")

# --- Batch Conversion Orchestrator ---
def batch_convert_all_content(config_path=None):
    logging.info("Starting batch conversion for all content records.")
    import yaml
    project_root = PROJECT_ROOT
    if config_path is None:
        config_path = os.path.join(project_root, "_content.yml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    toc = config.get('toc', [])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT source_format, target_format FROM conversion_capabilities WHERE is_enabled=1")
    conversions = cursor.fetchall()
    cursor.execute("SELECT id, source_path, output_path, slug FROM content")
    content_files = cursor.fetchall()
    for record_id, source_path, output_path, slug in content_files:
        if not source_path or not output_path:
            logging.warning(f"Skipping content record id={record_id} with None source_path or output_path")
            continue
        src_ext = os.path.splitext(source_path)[1]
        rel_path = os.path.relpath(source_path, CONTENT_ROOT)
        src_path = os.path.join(CONTENT_ROOT, rel_path)
        out_dir = os.path.join(BUILD_FILES_ROOT, slug) if slug else os.path.dirname(output_path)
        os.makedirs(out_dir, exist_ok=True)
        for conv_src, conv_target in conversions:
            if src_ext == conv_src:
                out_name = os.path.splitext(os.path.basename(output_path))[0] + conv_target
                out_path = os.path.join(out_dir, out_name)
                if conv_src == ".md" and conv_target == ".md":
                    try:
                        shutil.copy2(src_path, out_path)
                        logging.info(f"COPY: {src_path} -> {out_path}")
                    except Exception as e:
                        logging.error(f"ERROR: Failed to copy {src_path} -> {out_path}: {e}")
                elif conv_src == ".md" and conv_target == ".docx":
                    convert_md_to_docx(src_path, out_path, record_id, conn)
                elif conv_src == ".md" and conv_target == ".pdf":
                    convert_md_to_pdf(src_path, out_path, record_id, conn)
                elif conv_src == ".md" and conv_target == ".tex":
                    convert_md_to_tex(src_path, out_path, record_id, conn)
                elif conv_src == ".md" and conv_target == ".txt":
                    convert_md_to_txt(src_path, out_path, record_id, conn)
                elif conv_src == ".ipynb" and conv_target == ".jupyter":
                    logging.info(f"JUPYTER: {src_path} -> {out_path}")
    conn.close()
    logging.info("Batch conversion complete.")

# --- Main Entry Point ---
def main():
    import argparse
    parser = argparse.ArgumentParser(description="OERForge Conversion CLI")
    parser.add_argument("mode", choices=["batch", "single"], help="Conversion mode: batch or single file")
    parser.add_argument("--src", type=str, help="Source file path (for single mode)")
    parser.add_argument("--out", type=str, help="Output file path (for single mode)")
    parser.add_argument("--fmt", choices=["docx", "pdf", "tex", "txt"], help="Target format (for single mode)")
    parser.add_argument("--record_id", type=int, default=None, help="Content record ID (optional)")
    args = parser.parse_args()

    if args.mode == "batch":
        logging.info("[convert] main() entry: running batch_convert_all_content()")
        batch_convert_all_content()
    elif args.mode == "single":
        if not args.src or not args.out or not args.fmt:
            print("Error: --src, --out, and --fmt are required for single mode.")
            exit(1)
        conn = sqlite3.connect(DB_PATH)
        try:
            if args.fmt == "docx":
                convert_md_to_docx(args.src, args.out, args.record_id, conn)
            elif args.fmt == "pdf":
                convert_md_to_pdf(args.src, args.out, args.record_id, conn)
            elif args.fmt == "tex":
                convert_md_to_tex(args.src, args.out, args.record_id, conn)
            elif args.fmt == "txt":
                convert_md_to_txt(args.src, args.out, args.record_id, conn)
            else:
                print(f"Unknown format: {args.fmt}")
                exit(1)
        finally:
            conn.close()

if __name__ == "__main__":
    main()