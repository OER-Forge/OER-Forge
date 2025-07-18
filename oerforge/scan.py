"""
scan.py
--------
Static Site Asset and Content Scanner

Scans site content, extracts assets, and populates the SQLite database
with page, section, and file records. Uses db_utils.py for all DB operations.

Usage:
    python scan.py _content.yml
"""

import os
import re
import logging
import json
from bs4 import BeautifulSoup
from oerforge.db_utils import (
    get_db_connection,
    insert_records,
    get_enabled_conversions,
    get_records,
    initialize_database,
    create_tables,
    db_log
)

# --- Constants and Logging Setup ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_LOG_PATH = os.path.join(PROJECT_ROOT, 'log', 'build.log')
DB_PATH = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
DEBUG_MODE = os.environ.get("DEBUG", "0") == "1"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

def configure_logging(overwrite=False):
    log_level = logging.DEBUG if DEBUG_MODE else getattr(logging, LOG_LEVEL, logging.INFO)
    file_mode = 'w' if overwrite else 'a'
    file_handler = logging.FileHandler(BUILD_LOG_PATH, mode=file_mode, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[file_handler, stream_handler]
    )

def initialize_db():
    """Ensure the database exists and schema is valid."""
    if not os.path.exists(DB_PATH):
        db_log("Database not found. Initializing fresh database.", level=logging.WARNING)
        initialize_database(db_path=DB_PATH)
    else:
        try:
            conn = get_db_connection(DB_PATH)
            cursor = conn.cursor()
            create_tables(cursor)
            conn.commit()
            conn.close()
        except Exception as e:
            db_log(f"Database schema mismatch or error: {e}", level=logging.ERROR)
            print("ERROR: Database schema mismatch detected. Please remove db/sqlite.db and rerun for a clean build.")
            raise SystemExit(1)

def batch_read_files(file_paths):
    """Reads multiple files and returns their contents as a dict: {path: content}."""
    contents = {}
    for path in file_paths:
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == '.md':
                contents[path] = read_markdown_file(path)
            elif ext == '.ipynb':
                contents[path] = read_notebook_file(path)
            elif ext == '.docx':
                contents[path] = read_docx_file(path)
            else:
                contents[path] = None
        except Exception as e:
            logging.error(f"Could not read {path}: {e}")
            if DEBUG_MODE:
                import traceback
                logging.error(traceback.format_exc())
            contents[path] = None
    return contents

def read_markdown_file(path):
    """Read markdown file content."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Could not read markdown file {path}: {e}")
        if DEBUG_MODE:
            import traceback
            logging.error(traceback.format_exc())
        return None

def read_notebook_file(path):
    """Read Jupyter notebook file content."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Could not read notebook file {path}: {e}")
        if DEBUG_MODE:
            import traceback
            logging.error(traceback.format_exc())
        return None

def read_docx_file(path):
    """Read docx file content."""
    try:
        from docx import Document
        doc = Document(path)
        return '\n'.join(para.text for para in doc.paragraphs)
    except ImportError:
        logging.error("python-docx is not installed. Run 'pip install python-docx' in your environment.")
        return None
    except Exception as e:
        logging.error(f"Could not read docx file {path}: {e}")
        if DEBUG_MODE:
            import traceback
            logging.error(traceback.format_exc())
        return None

def get_conversion_flags(extension):
    """Get conversion flags for a given file extension using the DB."""
    targets = get_enabled_conversions(extension)
    flag_map = {
        '.md': 'can_convert_md',
        '.tex': 'can_convert_tex',
        '.pdf': 'can_convert_pdf',
        '.docx': 'can_convert_docx',
        '.ppt': 'can_convert_ppt',
        '.jupyter': 'can_convert_jupyter',
        '.ipynb': 'can_convert_ipynb'
    }
    flags = {v: False for v in flag_map.values()}
    for t in targets:
        if t in flag_map:
            flags[flag_map[t]] = True
    return flags

def build_content_record(title, file_path, item_slug, menu_context, children, parent_output_path, parent_slug, order, level, export_config=None):
    """Build a content record for the database."""
    md_is_section_index = bool(file_path and os.path.basename(file_path) == '_index.md')
    is_section_index = 1 if children or md_is_section_index else 0
    record_parent_slug = parent_slug if parent_slug else None
    if DEBUG_MODE:
        logging.debug(f"[RECORD-START] title={title}, file_path={file_path}, item_slug={item_slug}, parent_slug={parent_slug}, is_section_index={is_section_index}, order={order}, level={level}")
    if file_path:
        source_path = file_path if file_path.startswith('content/') else f'content/{file_path}'
        rel_source_path = os.path.relpath(os.path.join(PROJECT_ROOT, source_path), PROJECT_ROOT)
        ext = os.path.splitext(source_path)[1].lower()
        rel_path = source_path[8:] if source_path.startswith('content/') else source_path
        base_name = os.path.splitext(os.path.basename(rel_path))[0]
        parent_dir = os.path.basename(os.path.dirname(source_path))
        if DEBUG_MODE:
            logging.debug(f"[DEBUG] Checking output path logic for file_path={file_path}, source_path={source_path}, base_name={base_name}, parent_dir={parent_dir}")
        # Output path logic
        if os.path.basename(source_path) == '_index.md':
            output_path = os.path.join('build', item_slug, 'index.html')
            if DEBUG_MODE:
                logging.info(f"[SECTION-INDEX] Processing _index.md for section '{item_slug}' -> {output_path}")
        elif source_path == f'content/{base_name}.md' and base_name != 'index':
            output_path = os.path.join('build', base_name, 'index.html')
        elif base_name == parent_dir:
            output_path = os.path.join('build', item_slug, 'index.html')
        else:
            output_path = os.path.join('build', item_slug, base_name + '.html')
        relative_link = output_path[6:] if output_path.startswith('build/') else output_path
        flags = get_conversion_flags(ext)
        if DEBUG_MODE:
            logging.debug(f"[RECORD-BUILD] title={title}, source_path={rel_source_path}, output_path={output_path}, relative_link={relative_link}, flags={flags}")
        record = {
            'title': title,
            'source_path': rel_source_path,
            'output_path': output_path,
            'is_autobuilt': 0,
            'mime_type': ext,
            'can_convert_md': flags['can_convert_md'],
            'can_convert_tex': flags['can_convert_tex'],
            'can_convert_pdf': flags['can_convert_pdf'],
            'can_convert_docx': flags['can_convert_docx'],
            'can_convert_ppt': flags['can_convert_ppt'],
            'can_convert_jupyter': flags['can_convert_jupyter'],
            'can_convert_ipynb': flags['can_convert_ipynb'],
            'parent_output_path': parent_output_path,
            'slug': item_slug,
            'parent_slug': record_parent_slug,
            'is_section_index': is_section_index,
            'order': int(order),
            'relative_link': relative_link,
            'menu_context': menu_context,
            'level': int(level)
        }
        if export_config:
            record['export_types'] = ','.join(export_config.get('types', []))
            record['export_force'] = export_config.get('force', False)
            record['export_custom_label'] = export_config.get('custom_label', None)
            record['export_output_path'] = export_config.get('output_path', None)
        return record, rel_source_path
    else:
        output_path = os.path.join('build', item_slug, 'index.html')
        relative_link = output_path[6:] if output_path.startswith('build/') else output_path
        if DEBUG_MODE:
            logging.debug(f"[RECORD-BUILD] (section) title={title}, output_path={output_path}, relative_link={relative_link}")
        record = {
            'title': title,
            'source_path': None,
            'output_path': output_path,
            'is_autobuilt': 1,
            'mime_type': 'section',
            'can_convert_md': False,
            'can_convert_tex': False,
            'can_convert_pdf': False,
            'can_convert_docx': False,
            'can_convert_ppt': False,
            'can_convert_jupyter': False,
            'can_convert_ipynb': False,
            'parent_output_path': parent_output_path,
            'slug': item_slug,
            'parent_slug': record_parent_slug,
            'is_section_index': is_section_index,
            'order': int(order),
            'relative_link': relative_link,
            'menu_context': menu_context,
            'level': int(level)
        }
        if export_config:
            record['export_types'] = ','.join(export_config.get('types', []))
            record['export_force'] = export_config.get('force', False)
            record['export_custom_label'] = export_config.get('custom_label', None)
            record['export_output_path'] = export_config.get('output_path', None)
        return record, None

def merge_export_config(parent, override):
    """Merge two export config dicts, with override taking precedence."""
    if not parent:
        return dict(override) if override else {}
    if not override:
        return dict(parent)
    merged = dict(parent)
    for k, v in override.items():
        merged[k] = v
    return merged

def walk_toc(items, file_paths, parent_output_path=None, parent_slug=None, parent_menu_context=None, level=0, parent_export_config=None):
    """Recursively walk the TOC and build content records, merging export configs."""
    content_records = []
    for idx, item in enumerate(items):
        title = item.get('title', None)
        file_path = item.get('file')
        order = int(idx)
        item_slug = item.get('slug', re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')) if title else f'section_{idx}'
        menu_context = item.get('menu_context', parent_menu_context if parent_menu_context else 'main')
        children = item.get('children', [])

        # --- Auto-detect _index.md for section landing pages if not explicitly set ---
        if not file_path and children:
            section_dir = os.path.join('content', item_slug)
            index_md_path = os.path.join(section_dir, '_index.md')
            abs_index_md_path = os.path.join(PROJECT_ROOT, index_md_path)
            if os.path.exists(abs_index_md_path):
                file_path = os.path.relpath(index_md_path, 'content')
                if DEBUG_MODE:
                    logging.info(f"[AUTO-INDEX] Using _index.md for section '{item_slug}': {file_path}")

        # Merge export config: parent_export_config (from parent) and item.get('export')
        item_export = item.get('export', None)
        merged_export = merge_export_config(parent_export_config, item_export)

        if DEBUG_MODE:
            logging.debug(f"[TOC] Entering item: title={title}, slug={item_slug}, file={file_path}, children={len(children)}, level={level}, export={merged_export}")
        record, source_path = build_content_record(
            title, file_path, item_slug, menu_context, children,
            parent_output_path, parent_slug, order, level, export_config=merged_export
        )
        content_records.append(record)
        if source_path:
            abs_path = os.path.join(PROJECT_ROOT, source_path)
            file_paths.append(abs_path)
            if DEBUG_MODE:
                logging.debug(f"[FILE-PATH] Added file for scan: {abs_path}")
        if children:
            child_records = walk_toc(
                children,
                file_paths,
                parent_output_path=record['output_path'],
                parent_slug=record['slug'],
                parent_menu_context=menu_context,
                level=int(level)+1,
                parent_export_config=merged_export
            )
            content_records.extend(child_records)
    return content_records

def extract_and_register_images(content_path, content_text, db_path):
    """Extract image paths from content and register in DB."""
    md_image_paths = re.findall(r'!\[.*?\]\((.*?)\)', content_text)
    soup = BeautifulSoup(content_text, "html.parser")
    from bs4 import Tag
    html_image_paths = [img.get('src') for img in soup.find_all('img') if isinstance(img, Tag) and img.get('src')]
    image_paths = md_image_paths + html_image_paths
    for img in image_paths:
        filename = os.path.basename(img)
        is_remote = img.startswith('http://') or img.startswith('https://')
        abs_img_path = img if is_remote else os.path.abspath(os.path.join(os.path.dirname(os.path.join(PROJECT_ROOT, content_path)), img))
        rel_content_path = os.path.relpath(content_path, PROJECT_ROOT)
        logging.info(f"[ASSET] Checking image: {img} (resolved as {abs_img_path}) in {rel_content_path}")
        if not is_remote and not os.path.exists(abs_img_path):
            logging.warning(f"[ASSET] Local image not found: {img} (resolved as {abs_img_path}) in {rel_content_path}")
        records = get_records('files', where_clause="filename=? AND is_image=1", params=(filename,), db_path=db_path)
        if not records:
            insert_records('files', [{
                'filename': filename,
                'extension': os.path.splitext(filename)[1],
                'mime_type': 'image/png',  # TODO: detect type
                'is_image': 1,
                'is_remote': int(is_remote),
                'url': img if is_remote else None,
                'referenced_page': rel_content_path,
                'relative_path': img,
                'absolute_path': abs_img_path
            }], db_path=db_path)
            logging.info(f"[ASSET] Registered {'remote' if is_remote else 'local'} image: {filename} for {rel_content_path}")
        else:
            if is_remote and records[0].get('url') != img:
                conn = get_db_connection(db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE files SET url=?, referenced_page=? WHERE id=?", (img, rel_content_path, records[0]['id']))
                conn.commit()
                conn.close()
                logging.info(f"[ASSET] Updated remote image URL: {filename} for {rel_content_path}")
            else:
                logging.info(f"[ASSET] Image already registered: {filename}")

def scan_toc_and_populate_db(config_path, db_path=DB_PATH):
    """
    Walk the TOC from the config YAML, read each file, extract assets/images, and populate the DB with content and asset records.
    Maintains TOC hierarchy and section relationships.
    Args:
        config_path (str): Path to the config YAML file.
        db_path (str): Path to the SQLite database file.
    """
    import yaml
    full_config_path = os.path.join(PROJECT_ROOT, config_path)
    with open(full_config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    toc = config.get('toc', [])
    global_export = config.get('export', {})

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    # Clear content records for fresh scan
    content_records = get_records('content', db_path=db_path, conn=conn, cursor=cursor)
    if content_records:
        cursor.execute("DELETE FROM content")
        conn.commit()

    file_paths = []
    all_content_records = walk_toc(toc, file_paths, parent_export_config=global_export)
    # Deduplicate records
    unique_records = {}
    for rec in all_content_records:
        key = (rec.get('source_path'), rec.get('output_path'), rec.get('title'))
        if key not in unique_records:
            unique_records[key] = rec
    deduped_records = list(unique_records.values())
    insert_records('content', deduped_records, db_path=db_path, conn=conn, cursor=cursor)
    try:
        conn.commit()
    except Exception as e:
        import traceback
        logging.error(f"Commit failed in scan_toc_and_populate_db: {e}\n{traceback.format_exc()}")
        if not DEBUG_MODE:
            raise
    import mimetypes
    rel_file_paths = [os.path.relpath(p, PROJECT_ROOT) for p in file_paths if os.path.exists(p)]
    contents = batch_read_files(rel_file_paths)

    # Register all files (not just images) in files table
    for abs_path in file_paths:
        if not os.path.exists(abs_path):
            continue
        filename = os.path.basename(abs_path)
        extension = os.path.splitext(filename)[1].lower()
        mime_type, _ = mimetypes.guess_type(abs_path)
        is_image = int(extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])
        is_remote = 0
        # For now, referenced_page is None for content files
        insert_records('files', [{
            'filename': filename,
            'extension': extension,
            'mime_type': mime_type or 'application/octet-stream',
            'is_image': is_image,
            'is_remote': is_remote,
            'url': None,
            'referenced_page': None,
            'relative_path': os.path.relpath(abs_path, PROJECT_ROOT),
            'absolute_path': abs_path,
            'has_local_copy': 1  # New field for tracking local copy
        }], db_path=db_path, conn=conn, cursor=cursor)

    # Asset extraction (images)
    for content_path, content_text in contents.items():
        if content_text:
            extract_and_register_images(content_path, content_text, db_path=db_path)

    # Stub: extract and register videos (e.g., YouTube)
    for content_path, content_text in contents.items():
        if content_text:
            extract_and_register_videos(content_path, content_text, db_path=db_path)

    conn.close()

def extract_and_register_videos(content_path, content_text, db_path):
    """Extract YouTube/video links and register in a future videos table. Stub for now."""
    # Example: Find YouTube links
    youtube_links = re.findall(r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)', content_text)
    for url in youtube_links:
        # TODO: insert into videos table with has_local_copy=0
        logging.info(f"[VIDEO] Found YouTube link: {url} in {content_path}")
    # Extend for other video platforms as needed

def main():
    """Main entry point for scan.py."""
    import sys
    configure_logging()
    initialize_db()
    config_file = "_content.yml"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    logging.info(f"[MAIN] Running scan_toc_and_populate_db with config: {config_file}")
    scan_toc_and_populate_db(config_file)

if __name__ == "__main__":
    main()