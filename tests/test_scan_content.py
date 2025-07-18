import os
import sqlite3
import tempfile
import pytest
import shutil
from oerforge import scan
from oerforge import db_utils

def test_scan_populates_content_and_files(tmp_path):
    # Setup: copy a minimal _content.yml and content dir to tmp_path
    test_root = tmp_path / "project"
    test_root.mkdir()
    db_path = test_root / "db" / "sqlite.db"
    (test_root / "db").mkdir()
    (test_root / "content").mkdir()
    # Minimal content
    with open(test_root / "_content.yml", "w") as f:
        f.write("""
toc:
  - title: Home
    file: index.md
  - title: About
    file: about.md
""")
    with open(test_root / "content" / "index.md", "w") as f:
        f.write("# Home\nWelcome to the site.")
    with open(test_root / "content" / "about.md", "w") as f:
        f.write("# About\nAbout this site.")
    # Patch PROJECT_ROOT and DB_PATH in scan
    orig_project_root = scan.PROJECT_ROOT
    orig_db_path = scan.DB_PATH
    scan.PROJECT_ROOT = str(test_root)
    scan.DB_PATH = str(db_path)
    # Run scan
    scan.initialize_db()
    scan.scan_toc_and_populate_db("_content.yml", db_path=str(db_path))
    # Check DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT title, source_path, output_path FROM content ORDER BY title")
    rows = cursor.fetchall()
    titles = [row[0] for row in rows]
    assert "Home" in titles
    assert "About" in titles
    # Check files table (should have at least the two markdown files)
    cursor.execute("SELECT filename FROM files")
    file_rows = [row[0] for row in cursor.fetchall()]
    assert "index.md" in file_rows
    assert "about.md" in file_rows
    # Cleanup
    scan.PROJECT_ROOT = orig_project_root
    scan.DB_PATH = orig_db_path
    conn.close()
