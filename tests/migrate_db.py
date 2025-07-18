"""
Script to run the database schema migration for OERForge.
This will add new columns to conversion_results and accessibility_results tables if needed.

Usage:
    python tests/migrate_db.py [<db_path>]
If no db_path is given, uses the default project db.
"""
import sys
from oerforge import db_utils

def main():
    db_path = None
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    print(f"Running migration on DB: {db_path or 'default project db'}")
    db_utils.migrate_database(db_path=db_path)
    print("Migration complete.")

if __name__ == "__main__":
    main()
