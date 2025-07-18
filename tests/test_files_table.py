import os
import sqlite3
import tempfile
import shutil
import pytest
from oerforge import scan
from oerforge.db_utils import initialize_database

def run_scan_and_get_files(tmp_path, config_file):
    db_path = tmp_path / "sqlite.db"
    initialize_database(db_path=str(db_path))
    scan.scan_toc_and_populate_db(config_path=config_file, db_path=str(db_path))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, extension, mime_type, is_image, is_remote, has_local_copy FROM files")
    rows = cursor.fetchall()
    conn.close()
    return rows

def test_files_table_registration(tmp_path):
    # Copy a minimal _content.yml and a sample .md file into tmp_path/content
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    sample_md = content_dir / "index.md"
    sample_md.write_text("""# Sample\n![img](sample.png)\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ\n""")
    sample_img = content_dir / "sample.png"
    sample_img.write_bytes(b"\x89PNG\r\n\x1a\n")
    config_file = tmp_path / "_content.yml"
    config_file.write_text("""
toc:
  - title: Home
    file: content/index.md
""")
    # Run scan and get files table
    rows = run_scan_and_get_files(tmp_path, str(config_file))
    filenames = [r[0] for r in rows]
    assert "index.md" in filenames
    assert "sample.png" in filenames
    # Check fields for sample.png
    img_row = next(r for r in rows if r[0] == "sample.png")
    assert img_row[1] == ".png"
    assert img_row[3] == 1  # is_image
    assert img_row[4] == 0  # is_remote
    assert img_row[5] == 1  # has_local_copy
    # Check fields for index.md
    md_row = next(r for r in rows if r[0] == "index.md")
    assert md_row[1] == ".md"
    assert md_row[3] == 0  # is_image
    assert md_row[4] == 0  # is_remote
    assert md_row[5] == 1  # has_local_copy
