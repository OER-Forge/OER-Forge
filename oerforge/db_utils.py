"""
OERForge Database Utilities
==========================

This module provides utility functions for initializing, managing, and interacting with the SQLite database used in the OERForge project. It supports asset tracking, page-file relationships, site metadata, and general-purpose queries and inserts.

Features:
    - Database initialization and schema setup
    - General-purpose record fetching and insertion
    - Logging of database events
    - Utility functions for linking files to pages
    - Pretty-printing tables for debugging and inspection

Note:
    Conversion status is NOT tracked in the content table. If conversion results need to be tracked, use a separate table (e.g., conversion_results) or check for file existence.

Intended Audience:
    - Contributors to OERForge
    - Anyone needing to interact with or extend the database layer

Usage:
    Import this module and use the provided functions to initialize the database, insert or fetch records, and link files to pages. All functions are documented with clear arguments and return values.
"""

import sqlite3
import os
import logging
import threading
import time
import sys
import logging

# Setup logging to log/db.log
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(project_root, 'log')
os.makedirs(log_dir, exist_ok=True)
db_log_path = os.path.join(log_dir, 'db.log')
db_logger = logging.getLogger('db_utils')
db_logger.setLevel(logging.INFO)
if not db_logger.handlers:
    handler = logging.FileHandler(db_log_path)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    db_logger.addHandler(handler)

def db_log(message, level=logging.INFO):
    db_logger.log(level, message)
    print(f"[DB] {message}", file=sys.stdout)


# ------------------------------------------------------------------------------
# Database Initialization and Utility Functions for OERForge Asset Tracking
# ------------------------------------------------------------------------------

def initialize_database():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(project_root, 'db')
    db_path = os.path.join(db_dir, 'sqlite.db')
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop tables
    cursor.execute("DROP TABLE IF EXISTS files")
    db_log("Dropped table: files")
    cursor.execute("DROP TABLE IF EXISTS pages_files")
    db_log("Dropped table: pages_files")
    cursor.execute("DROP TABLE IF EXISTS content")
    db_log("Dropped table: content")
    cursor.execute("DROP TABLE IF EXISTS site_info")
    db_log("Dropped table: site_info")
    cursor.execute("DROP TABLE IF EXISTS conversion_capabilities")
    db_log("Dropped table: conversion_capabilities")
    cursor.execute("DROP TABLE IF EXISTS conversion_results")
    db_log("Dropped table: conversion_results")
    # Create conversion_results table for tracking conversion outputs
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

    # Create tables
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
            "level" INTEGER DEFAULT 0
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

    # Default conversion rules: source_format -> [target_formats]
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
    # Check if conversion_capabilities is empty, then insert defaults
    cursor.execute("SELECT COUNT(*) FROM conversion_capabilities")
    if cursor.fetchone()[0] == 0:
        records = []
        for source, targets in default_conversion_matrix.items():
            for target in targets:
                records.append({
                    'source_format': source,
                    'target_format': target,
                    'is_enabled': True
                })
        for record in records:
            cursor.execute(
                "INSERT OR IGNORE INTO conversion_capabilities (source_format, target_format, is_enabled) VALUES (?, ?, ?)",
                (record['source_format'], record['target_format'], int(record['is_enabled']))
            )
            db_log(f"Inserted conversion capability: {record['source_format']} -> {record['target_format']}")
        conn.commit()
        db_log("Committed all default conversion capabilities.")

    conn.close()
    db_log("Closed DB connection after initialization.")
    
    
# =============================================
# General Purpose Functions for DB Interactions
# =============================================
def set_relative_link(content_id, relative_link, db_path=None):
    """
    Update the relative_link for a content item.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE content SET relative_link=? WHERE id=?", (relative_link, content_id))
    conn.commit()
    conn.close()

def set_menu_context(content_id, menu_context, db_path=None):
    """
    Update the menu_context for a content item.
    """
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

def get_db_connection(db_path=None):
    """
    Returns a sqlite3 connection to the database.

    Args:
        db_path (str, optional): Path to the SQLite database file.
    db_log("Created table: conversion_capabilities")
    db_log(f"Opening DB connection to {db_path if db_path else 'default path'}.")
            If None, defaults to <project_root>/db/sqlite.db.

        sqlite3.Connection: A connection object to the SQLite database.
    """
    if db_path is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, 'db', 'sqlite.db')
    return sqlite3.connect(db_path)

def get_records(table_name, where_clause=None, params=None, db_path=None, conn=None, cursor=None):
    db_log(f"Fetching records from table: {table_name}")
    """
    Fetch records from a table with optional WHERE clause and parameters.
    Args:
        table_name (str): Name of the table to query.
        where_clause (str, optional): SQL WHERE clause (without 'WHERE').
        params (tuple or list, optional): Parameters for the WHERE clause.
        db_path (str, optional): Path to the SQLite database file.
        conn, cursor: Optional existing connection/cursor.
    Returns:
        list of dict: List of records as dictionaries.
    """
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
    db_log(f"Inserting records into table: {table_name}")
    """
    General-purpose batch insert for any table.
    Checks if table exists, inserts records, returns list of inserted row ids.
    Args:
        table_name (str): Name of the table to insert into.
        records (list of dict): Each dict contains column-value pairs.
        db_path (str, optional): Path to the SQLite database file.
        conn, cursor: Optional existing connection/cursor.
    Returns:
        list of int: List of inserted row ids.
    """
    close_conn = False
    if conn is None or cursor is None:
        conn = get_db_connection(db_path)
        log_event(f"[DEBUG][{os.getpid()}][{threading.get_ident()}] Opened DB connection in insert_records for table '{table_name}' at {time.time()}", level="DEBUG")
        cursor = conn.cursor()
        close_conn = True
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if cursor.fetchone() is None:
        log_event(f"[ERROR] Table '{table_name}' does not exist in the database.", level="ERROR")
        if close_conn:
            conn.close()
        return []
    row_ids = []
    for record in records:
        # Get columns for this table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall() if row[1] != 'id']
        # Build insert statement
        col_names = []
        values = []
        for col in columns:
            col_names.append(col)
            val = record.get(col, None)
            # Ensure 'level' and 'order' are always int if present
            if col in ('level', 'order') and val is not None:
                try:
                    val = int(val)
                except Exception:
                    val = 0
            values.append(val)
        sql = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({', '.join(['?' for _ in col_names])})"
        cursor.execute(sql, values)
        row_ids.append(cursor.lastrowid)
    log_event(f"[DEBUG][{os.getpid()}][{threading.get_ident()}] Committing DB in insert_records for table '{table_name}' at {time.time()}", level="DEBUG")
    try:
        conn.commit()
    except Exception as e:
        import traceback
        log_event(f"[ERROR][{os.getpid()}][{threading.get_ident()}] Commit failed in insert_records: {e}\n{traceback.format_exc()}", level="ERROR")
        raise
    if close_conn:
        log_event(f"[DEBUG][{os.getpid()}][{threading.get_ident()}] Closing DB connection in insert_records for table '{table_name}' at {time.time()}", level="DEBUG")
        conn.close()
    return row_ids

def get_enabled_conversions(source_format, db_path=None):
    """
    Returns a list of enabled target formats for a given source format.

    Args:
        source_format (str): The source file extension (e.g., '.md').
        db_path (str, optional): Path to the SQLite database file.

    Returns:
        List[str]: List of enabled target formats (e.g., ['.pdf', '.docx']).
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
    db_log(f"Pretty printing table: {table_name}")
    """
    Pretty-print all rows of a table to the log and terminal for inspection/debugging.

    Args:
        table_name (str): Name of the table to print.
        db_path (str, optional): Path to the SQLite database file.
        conn, cursor: Optional existing connection/cursor.

    Returns:
        None

    Output:
        Logs a formatted table to the scan.log file and prints to stdout.
    """
    close_conn = False
    if conn is None or cursor is None:
        # If db_path is None, default to project_root/db/sqlite.db
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, 'db', 'sqlite.db')
        logging.info(f"[DB-OPEN] Attempting to open database: {db_path}")
        conn = sqlite3.connect(db_path)
        logging.info(f"[DB-OPEN] Database connection established: {db_path}")
        log_event(f"[DEBUG][{os.getpid()}][{threading.get_ident()}] Opened DB connection in pretty_print_table at {time.time()}", level="DEBUG")
        cursor = conn.cursor()
        close_conn = True
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    col_names = [description[0] for description in cursor.description]
    # Calculate column widths for pretty printing
    col_widths = [max(len(str(col)), max((len(str(row[i])) for row in rows), default=0)) for i, col in enumerate(col_names)]
    # Print header row
    header = " | ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(col_names))
    log_event(header, level="INFO")
    log_event("-" * len(header), level="INFO")
    print(header)
    print("-" * len(header))
    # Print each row
    for row in rows:
        row_str = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
        log_event(row_str, level="INFO")
        print(row_str)
    if close_conn:
        log_event(f"[DEBUG][{os.getpid()}][{threading.get_ident()}] Closing DB connection in pretty_print_table at {time.time()}", level="DEBUG")
    logging.info(f"[DB-CLOSE] Database connection closed: {db_path}")
    conn.close()

def log_event(message, level="INFO"):
    """
    Logs an event to both stdout and a log file in the project root.

    Args:
        message (str): The log message to record.
        level (str): The severity level (e.g., "INFO", "ERROR", "WARNING").

    The log file is named 'scan.log' and is located at <project_root>/scan.log.
    Each log entry is timestamped.
    """
    logging.log(getattr(logging, level.upper(), logging.INFO), f"[DB] {message}")


def link_files_to_pages(file_page_pairs, db_path=None, conn=None, cursor=None):
    db_log(f"Linking files to pages in table: pages_files")
    """
    Link files to pages in the pages_files table.

    Args:
        file_page_pairs (list of tuple): Each tuple is (file_id, page_path).
        db_path (str, optional): Path to the SQLite database file.
        conn, cursor: Optional existing connection/cursor.

    Returns:
        None

    Example:
        link_files_to_pages([(1, 'index.html'), (2, 'about.html')])
    """
    close_conn = False
    if conn is None or cursor is None:
        conn = get_db_connection(db_path)
        log_event(f"[DEBUG][{os.getpid()}][{threading.get_ident()}] Opened DB connection in link_files_to_pages at {time.time()}", level="DEBUG")
        cursor = conn.cursor()
        close_conn = True
    for file_id, page_path in file_page_pairs:
        cursor.execute(
            """
            INSERT INTO pages_files (file_id, page_path)
            VALUES (?, ?)
            """,
            (file_id, page_path)
        )
    log_event(f"[DEBUG][{os.getpid()}][{threading.get_ident()}] Committing DB in link_files_to_pages at {time.time()}", level="DEBUG")
    try:
        conn.commit()
    except Exception as e:
        import traceback
        log_event(f"[ERROR][{os.getpid()}][{threading.get_ident()}] Commit failed in link_files_to_pages: {e}\n{traceback.format_exc()}", level="ERROR")
        raise
    if close_conn:
        log_event(f"[DEBUG][{os.getpid()}][{threading.get_ident()}] Closing DB connection in link_files_to_pages at {time.time()}", level="DEBUG")
        conn.close()

def get_available_conversions_for_page(output_path, db_path=None):
    """
    Given a page output_path, return all successful conversions for that page.
    Returns a list of dicts: {target_format, output_path, status}
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    # Find content.id for this output_path
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
    test_output_path = None
    import sys
    if len(sys.argv) > 1:
        test_output_path = sys.argv[1]
    if test_output_path:
        print(f"Available conversions for {test_output_path}:")
        for conv in get_available_conversions_for_page(test_output_path):
            print(conv)