import os
import sqlite3
import pytest
from oerforge import scan
from oerforge.db_utils import initialize_database

def test_real_content_files_table(tmp_path):
    # Copy the real content directory to the temp path
    import shutil
    content_src = os.path.join(os.getcwd(), "content")
    content_dst = tmp_path / "content"
    shutil.copytree(content_src, content_dst)
    # Copy the real _content.yml to the temp path if it exists
    config_src = os.path.join(os.getcwd(), "_content.yml")
    config_dst = tmp_path / "_content.yml"
    if os.path.exists(config_src):
        shutil.copy(config_src, config_dst)
    else:
        pytest.skip("_content.yml not found in project root.")
    db_path = tmp_path / "sqlite.db"
    initialize_database(db_path=str(db_path))
    scan.scan_toc_and_populate_db(config_path=str(config_dst), db_path=str(db_path))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM files")
    filenames = [row[0] for row in cursor.fetchall()]
    conn.close()
    # Check that sample.png is registered
    assert "sample.png" in filenames, "sample.png should be registered in files table from about.md reference."
    # Optionally, check other expected files
    assert "about.md" in filenames, "about.md should be registered in files table."
