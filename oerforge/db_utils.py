"""
OERForge Database Utilities
==========================

Utility functions for initializing, managing, and interacting with the SQLite database used in the OERForge project.
Supports asset tracking, page-file relationships, site metadata, and general-purpose queries and inserts.

Features:
    - Database initialization and schema setup
    - General-purpose record fetching and insertion
    - Logging of database events
    - Utility functions for linking files to pages
    - Pretty-printing tables for debugging and inspection

Usage:
    Import this module and use the provided functions to initialize the database, insert or fetch records, and link files to pages.
"""

import sqlite3
import os
import logging
import sys

# Setup logging to log/db.log
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, 'log')
os.makedirs(LOG_DIR, exist_ok=True)
DB_LOG_PATH = os.path.join(LOG_DIR, 'db.log')
db_logger = logging.getLogger('db_utils')
db_logger.setLevel(logging.INFO)
if not db_logger.handlers:
    handler = logging.FileHandler(DB_LOG_PATH)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    db_logger.addHandler(handler)

def db_log(message, level=logging.INFO):
    db_logger.log(level, message)
    print(f"[DB] {message}", file=sys.stdout)

# --- Database Initialization ---

def drop_tables(cursor):
    """Drop all tables for a clean DB initialization."""
    tables = [
        "files", "pages_files", "content", "site_info",
        "conversion_capabilities", "conversion_results", "accessibility_results"
    ]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        db_log(f"Dropped table: {table}")

def create_tables(cursor):
    """Create all required tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversion_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            source_format TEXT NOT NULL,
            target_format TEXT NOT NULL,
            output_path TEXT,
            conversion_time TEXT,
            status TEXT,
            FOREIGN KEY(content_id) REFERENCES content(id)
        )
    """)
    db_log("Created table: conversion_results")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accessibility_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            pa11y_json TEXT,
            badge_html TEXT,
            wcag_level TEXT,
            error_count INTEGER,
            warning_count INTEGER,
            notice_count INTEGER,
            checked_at TEXT,
            FOREIGN KEY(content_id) REFERENCES content(id)
        )
    """)
    db_log("Created table: accessibility_results")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            extension TEXT,
            mime_type TEXT,
            is_image BOOLEAN,
            is_remote BOOLEAN,
            url TEXT,
            referenced_page TEXT,
            relative_path TEXT,
            absolute_path TEXT,
            cell_type TEXT,
            is_code_generated BOOLEAN,
            is_embedded BOOLEAN
        )
    """)
    db_log("Created table: files")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pages_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            page_path TEXT,
            FOREIGN KEY(file_id) REFERENCES files(id)
        )
    """)
    db_log("Created table: pages_files")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            source_path TEXT,
            output_path TEXT,
            is_autobuilt BOOLEAN DEFAULT 0,
            mime_type TEXT,
            parent_output_path TEXT DEFAULT NULL,
            slug TEXT DEFAULT NULL,
            wcag_status_html TEXT DEFAULT NULL,
            can_convert_md BOOLEAN DEFAULT 0,
            can_convert_tex BOOLEAN DEFAULT 0,
            can_convert_pdf BOOLEAN DEFAULT 0,
            can_convert_docx BOOLEAN DEFAULT 0,
            can_convert_ppt BOOLEAN DEFAULT 0,
            can_convert_jupyter BOOLEAN DEFAULT 0,
            can_convert_ipynb BOOLEAN DEFAULT 0,
            relative_link TEXT DEFAULT NULL,
            menu_context TEXT DEFAULT NULL,
            level INTEGER DEFAULT 0
        )
    """)
    db_log("Created table: content")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            description TEXT,
            logo TEXT,
            favicon TEXT,
            theme_default TEXT,
            theme_light TEXT,
            theme_dark TEXT,
            language TEXT,
            github_url TEXT,
            footer_text TEXT,
            header TEXT
        );
    """)
    db_log("Created table: site_info")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversion_capabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_format TEXT NOT NULL,
            target_format TEXT NOT NULL,
            is_enabled BOOLEAN DEFAULT 1,
            UNIQUE(source_format, target_format)
        )
    """)
    db_log("Created table: conversion_capabilities")

def insert_default_conversion_capabilities(cursor):
    """Insert default conversion capabilities if table is empty."""
    default_conversion_matrix = {
        '.md':     ['.txt','.md', '.marp', '.tex', '.pdf', '.docx', '.ppt', '.jupyter'],
        '.marp':   ['.txt','.md', '.marp', '.pdf', '.docx', '.ppt'],
        '.tex':    ['.txt','.md', '.tex', '.pdf', '.docx'],
        '.ipynb':  ['.txt','.md', '.tex', '.pdf', '.docx', '.jupyter', '.ipynb'],
        '.jupyter':['.md', '.tex', '.pdf', '.docx', '.jupyter', '.ipynb'],
        '.docx':   ['.txt','.md', '.tex', '.pdf', '.docx'],
        '.ppt':    ['.txt','.ppt'],
        '.txt':    ['.txt','.md','.tex','.docx','.pdf']
    }
    cursor.execute("SELECT COUNT(*) FROM conversion_capabilities")
    if cursor.fetchone()[0] == 0:
        for source, targets in default_conversion_matrix.items():
            for target in targets:
                cursor.execute(
                    "INSERT OR IGNORE INTO conversion_capabilities (source_format, target_format, is_enabled) VALUES (?, ?, ?)",
                    (source, target, 1)
                )
                db_log(f"Inserted conversion capability: {source} -> {target}")

def initialize_database():
    """Initialize the OERForge database schema and defaults."""
    db_dir = os.path.join(PROJECT_ROOT, 'db')
    db_path = os.path.join(db_dir, 'sqlite.db')
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    drop_tables(cursor)
    create_tables(cursor)
    insert_default_conversion_capabilities(cursor)
    conn.commit()
    conn.close()
    db_log("Closed DB connection after initialization.")

# --- General Purpose DB Functions ---

def get_db_connection(db_path=None):
    """
    Returns a sqlite3 connection to the database.
    If db_path is None, defaults to <project_root>/db/sqlite.db.
    """
    if db_path is None:
        db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
    db_log(f"Opening DB connection to {db_path}.")
    return sqlite3.connect(db_path)

def get_descendants_for_parent(parent_output_path, db_path):
    """
    Query all children, grandchildren, and deeper descendants for a given parent_output_path using a recursive CTE.
    Args:
        parent_output_path (str): Output path of the parent section.
        db_path (str): Path to the SQLite database.
    Returns:
        list: Dicts for each descendant (id, title, output_path, parent_output_path, slug, level).
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = '''
    WITH RECURSIVE content_hierarchy(id, title, output_path, parent_output_path, slug, level) AS (
      SELECT id, title, output_path, parent_output_path, slug, 0 as level
      FROM content
      WHERE output_path = ?
      UNION ALL
      SELECT c.id, c.title, c.output_path, c.parent_output_path, c.slug, ch.level + 1
      FROM content c
      JOIN content_hierarchy ch ON c.parent_output_path = ch.output_path
    )
    SELECT id, title, output_path, parent_output_path, slug, level FROM content_hierarchy WHERE level > 0 ORDER BY level, output_path;
    '''
    cursor.execute(query, (parent_output_path,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            'id': row[0],
            'title': row[1],
            'output_path': row[2],
            'parent_output_path': row[3],
            'slug': row[4],
            'level': row[5]
        }
        for row in rows
    ]
    
def get_records(table_name, where_clause=None, params=None, db_path=None, conn=None, cursor=None):
    """
    Fetch records from a table with optional WHERE clause and parameters.
    Returns: list of dicts.
    """
    db_log(f"Fetching records from table: {table_name}")
    close_conn = False
    if conn is None or cursor is None:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        close_conn = True
    sql = f"SELECT * FROM {table_name}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    if params is None:
        params = ()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    records = [dict(zip(col_names, row)) for row in rows]
    if close_conn:
        conn.close()
    return records

def insert_records(table_name, records, db_path=None, conn=None, cursor=None):
    """
    Batch insert for any table. Returns list of inserted row ids.
    """
    db_log(f"Inserting records into table: {table_name}")
    close_conn = False
    if conn is None or cursor is None:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        close_conn = True
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if cursor.fetchone() is None:
        db_log(f"Table '{table_name}' does not exist in the database.", level=logging.ERROR)
        if close_conn:
            conn.close()
        raise ValueError(f"Table '{table_name}' does not exist.")
    row_ids = []
    for record in records:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall() if row[1] != 'id']
        col_names = []
        values = []
        for col in columns:
            col_names.append(col)
            val = record.get(col, None)
            if col in ('level', 'order') and val is not None:
                try:
                    val = int(val)
                except Exception:
                    val = 0
            values.append(val)
        sql = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({', '.join(['?' for _ in col_names])})"
        cursor.execute(sql, values)
        row_ids.append(cursor.lastrowid)
    try:
        conn.commit()
    except Exception as e:
        db_log(f"Commit failed in insert_records: {e}", level=logging.ERROR)
        raise
    if close_conn:
        conn.close()
    return row_ids

def set_relative_link(content_id, relative_link, db_path=None):
    """Update the relative_link for a content item."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE content SET relative_link=? WHERE id=?", (relative_link, content_id))
    conn.commit()
    conn.close()

def set_menu_context(content_id, menu_context, db_path=None):
    """Update the menu_context for a content item."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE content SET menu_context=? WHERE id=?", (menu_context, content_id))
    conn.commit()
    conn.close()

def get_menu_items(db_path=None):
    """
    Fetch all menu items with their links and context.
    Returns: list of dicts with id, title, relative_link, menu_context
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, relative_link, menu_context FROM content")
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    items = [dict(zip(col_names, row)) for row in rows]
    conn.close()
    return items

def get_enabled_conversions(source_format, db_path=None):
    """
    Returns a list of enabled target formats for a given source format.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT target_format FROM conversion_capabilities WHERE source_format=? AND is_enabled=1",
        (source_format,)
    )
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results

def pretty_print_table(table_name, db_path=None, conn=None, cursor=None):
    """
    Pretty-print all rows of a table to the log and terminal for inspection/debugging.
    """
    db_log(f"Pretty printing table: {table_name}")
    close_conn = False
    if conn is None or cursor is None:
        if db_path is None:
            db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        close_conn = True
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    col_names = [description[0] for description in cursor.description]
    col_widths = [max(len(str(col)), max((len(str(row[i])) for row in rows), default=0)) for i, col in enumerate(col_names)]
    header = " | ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(col_names))
    print(header)
    print("-" * len(header))
    for row in rows:
        row_str = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
        print(row_str)
    if close_conn:
        conn.close()

def link_files_to_pages(file_page_pairs, db_path=None, conn=None, cursor=None):
    """
    Link files to pages in the pages_files table.
    file_page_pairs: list of (file_id, page_path)
    """
    db_log("Linking files to pages in table: pages_files")
    close_conn = False
    if conn is None or cursor is None:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        close_conn = True
    for file_id, page_path in file_page_pairs:
        cursor.execute(
            "INSERT INTO pages_files (file_id, page_path) VALUES (?, ?)",
            (file_id, page_path)
        )
    try:
        conn.commit()
    except Exception as e:
        db_log(f"Commit failed in link_files_to_pages: {e}", level=logging.ERROR)
        raise
    if close_conn:
        conn.close()

def get_available_conversions_for_page(output_path, db_path=None):
    """
    Given a page output_path, return all successful conversions for that page.
    Returns a list of dicts: {target_format, output_path, status}
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM content WHERE output_path=?", (output_path,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return []
    content_id = row[0]
    cursor.execute("SELECT target_format, output_path, status FROM conversion_results WHERE content_id=? AND status='success'", (content_id,))
    results = [
        {
            'target_format': r[0],
            'output_path': r[1],
            'status': r[2]
        }
        for r in cursor.fetchall()
    ]
    conn.close()
    return results

if __name__ == "__main__":
    # Example test: print available conversions for a given output_path
    import sys
    test_output_path = sys.argv[1] if len(sys.argv) > 1 else None
    if test_output_path:
        print(f"Available conversions for {test_output_path}:")
        for conv in get_available_conversions_for_page(test_output_path):
            print(conv)