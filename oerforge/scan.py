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
from oerforge.db_utils import (
    get_db_connection,
    insert_records,
    link_files_to_pages,
    set_relative_link,
    set_menu_context,
    get_enabled_conversions,
    get_records,
    pretty_print_table,
    get_descendants_for_parent
)

# --- Configurable Environment ---
DEBUG_MODE = os.environ.get("DEBUG", "0") == "1"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
build_log_path = os.path.join(project_root, 'log', 'build.log')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(build_log_path, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

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
    try:
        from docx import Document
        doc = Document(path)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        return '\n'.join(text)
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

def scan_toc_and_populate_db(config_path):
    """
    Walk the TOC from the config YAML, read each file, extract assets/images, and populate the DB with content and asset records.
    Maintains TOC hierarchy and section relationships.
    Args:
        config_path (str): Path to the config YAML file.
    """
    import yaml
    full_config_path = os.path.join(project_root, config_path)
    with open(full_config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    toc = config.get('toc', [])

    conn = get_db_connection()
    cursor = conn.cursor()
    # Use db_utils to delete all content records
    content_records = get_records('content', db_path=os.path.join(project_root, 'db', 'sqlite.db'), conn=conn, cursor=cursor)
    if content_records:
        cursor.execute("DELETE FROM content")
        conn.commit()

    file_paths = []

    def walk_toc(items, parent_output_path=None, parent_slug=None, parent_menu_context=None, level=0):
        content_records = []
        for idx, item in enumerate(items):
            file_path = item.get('file')
            title = item.get('title', None)
            order = int(idx)
            item_slug = item.get('slug', re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')) if title else f'section_{idx}'
            menu_context = item.get('menu_context', parent_menu_context if parent_menu_context else 'main')
            children = item.get('children', [])
            is_section_index = 1 if children else 0
            # Always set parent_slug for children
            record_parent_slug = parent_slug if parent_slug else None
            if file_path:
                source_path = file_path if file_path.startswith('content/') else f'content/{file_path}'
                ext = os.path.splitext(source_path)[1].lower()
                rel_path = source_path[8:] if source_path.startswith('content/') else source_path
                base_name = os.path.splitext(os.path.basename(rel_path))[0]
                parent_dir = os.path.basename(os.path.dirname(source_path))
                if source_path == f'content/{base_name}.md' and base_name != 'index':
                    output_path = os.path.join('build', base_name, 'index.html')
                elif base_name == parent_dir:
                    output_path = os.path.join('build', item_slug, 'index.html')
                else:
                    output_path = os.path.join('build', item_slug, base_name + '.html')
                relative_link = output_path[6:] if output_path.startswith('build/') else output_path
                flags = get_conversion_flags(ext)
                content_record = {
                    'title': title,
                    'source_path': source_path,
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
                content_records.append(content_record)
                abs_path = os.path.join(project_root, source_path)
                file_paths.append(abs_path)
                if children:
                    child_records = walk_toc(children, parent_output_path=output_path, parent_slug=item_slug, parent_menu_context=menu_context, level=int(level)+1)
                    content_records.extend(child_records)
            elif children:
                output_path = os.path.join('build', item_slug, 'index.html')
                relative_link = output_path[6:] if output_path.startswith('build/') else output_path
                content_record = {
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
                content_records.append(content_record)
                child_records = walk_toc(children, parent_output_path=output_path, parent_slug=item_slug, parent_menu_context=menu_context, level=int(level)+1)
                content_records.extend(child_records)
        return content_records

    all_content_records = walk_toc(toc)
    unique_records = {}
    for rec in all_content_records:
        key = (rec.get('source_path'), rec.get('output_path'), rec.get('title'))
        if key not in unique_records:
            unique_records[key] = rec
    deduped_records = list(unique_records.values())
    insert_records('content', deduped_records, db_path=os.path.join(project_root, 'db', 'sqlite.db'), conn=conn, cursor=cursor)
    try:
        conn.commit()
    except Exception as e:
        import traceback
        logging.error(f"Commit failed in scan_toc_and_populate_db: {e}\n{traceback.format_exc()}")
        if not DEBUG_MODE:
            raise
    rel_file_paths = [os.path.relpath(p, project_root) for p in file_paths if os.path.exists(p)]
    contents = batch_read_files(rel_file_paths)
    # Asset extraction would also use db_utils for inserts/links
    # ...existing asset extraction logic...
    conn.close()

if __name__ == "__main__":
    import sys
    config_file = "_content.yml"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    logging.info(f"[MAIN] Running scan_toc_and_populate_db with config: {config_file}")
    scan_toc_and_populate_db(config_file)
    
def main():
    import sys
    config_file = "_content.yml"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    logging.info(f"[MAIN] Running scan_toc_and_populate_db with config: {config_file}")
    scan_toc_and_populate_db(config_file)

if __name__ == "__main__":
    main()