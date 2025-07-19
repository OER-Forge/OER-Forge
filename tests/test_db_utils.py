import os
import sqlite3
import tempfile
import pytest
from oerforge import db_utils

def test_create_tables_and_migration():
    """
    Test that create_tables creates all required columns for both conversion_results and accessibility_results.
    """
    # Use a temporary DB file
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Create tables (fresh)
        db_utils.create_tables(cursor)
        conn.commit()
        # Check columns in conversion_results
        cursor.execute("PRAGMA table_info(conversion_results)")
        columns = [row[1] for row in cursor.fetchall()]
        for col in ['reason', 'forced', 'custom_label', 'created_at']:
            assert col in columns
        # Check columns in accessibility_results
        cursor.execute("PRAGMA table_info(accessibility_results)")
        columns = [row[1] for row in cursor.fetchall()]
        for col in ['status', 'reason', 'custom_label', 'forced', 'created_at']:
            assert col in columns
        # Migration logic removed; only test create_tables
        conn.close()

def test_insert_and_fetch_records():
    """
    Test that records can be inserted and fetched from conversion_results with all new fields present.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        db_utils.create_tables(cursor)
        conn.commit()
        # Insert a record into conversion_results
        record = {
            'content_id': 1,
            'source_format': 'md',
            'target_format': 'pdf',
            'output_path': 'foo.pdf',
            'conversion_time': '2025-07-17T12:00:00',
            'status': 'success',
            'reason': 'ok',
            'forced': 0,
            'custom_label': 'PDF',
            'created_at': '2025-07-17T12:00:00'
        }
        db_utils.insert_records('conversion_results', [record], db_path=db_path)
        results = db_utils.get_records('conversion_results', db_path=db_path)
        assert len(results) == 1
        assert results[0]['status'] == 'success'
        assert results[0]['reason'] == 'ok'
        assert results[0]['custom_label'] == 'PDF'
        conn.close()

def test_migrate_database_entrypoint():
    """
    Test that the migrate_database entrypoint function adds all new columns to existing tables.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE conversion_results (id INTEGER PRIMARY KEY, content_id INTEGER)")
        cursor.execute("CREATE TABLE accessibility_results (id INTEGER PRIMARY KEY, content_id INTEGER)")
        conn.commit()
        conn.close()
        db_utils.migrate_database(db_path=db_path)
        # Check columns after migration
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(conversion_results)")
        columns = [row[1] for row in cursor.fetchall()]
        for col in ['reason', 'forced', 'custom_label', 'created_at']:
            assert col in columns
        cursor.execute("PRAGMA table_info(accessibility_results)")
        columns = [row[1] for row in cursor.fetchall()]
        for col in ['status', 'reason', 'custom_label', 'forced', 'created_at']:
            assert col in columns
        conn.close()
