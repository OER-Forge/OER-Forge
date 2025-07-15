"""
view_db.py: CLI/utility for viewing asset database contents (files/pages_files only).
Intended for future web admin interface.
"""
import os
import sqlite3
from tabulate import tabulate

# --- Site info DB access ---
def get_site_info():
    """
    Returns a dict of site and footer info from the site_info table.
    """
    import sqlite3
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT title, author, description, logo, favicon, theme_default, theme_light, theme_dark, language, github_url, footer_text, header FROM site_info LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        keys = ["title", "author", "description", "logo", "favicon", "theme_default", "theme_light", "theme_dark", "language", "github_url", "footer_text", "header"]
        return dict(zip(keys, row))
    return {}

def get_db_path():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, 'db', 'sqlite.db')

def get_table_names():
    """
    Return asset DB tables: files, pages_files, and pages.
    """
    return ['files', 'pages_files', 'pages', 'content']

def get_table_columns(table_name):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    return columns

def fetch_table(table_name, columns=None, where=None, limit=None):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cols = ', '.join(columns) if columns else '*'
    query = f"SELECT {cols} FROM {table_name}"
    if where:
        query += f" WHERE {where}"
    if limit:
        query += f" LIMIT {limit}"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows

def display_table(table_name, columns=None, where=None, limit=None):
    cols = columns if columns else get_table_columns(table_name)
    rows = fetch_table(table_name, columns=columns, where=where, limit=limit)
    print(f"\nTable: {table_name}")
    print(tabulate(rows, headers=cols, tablefmt="grid"))

def display_all_tables():
    for table in get_table_names():
        display_table(table)


# --- Stubs for static HTML export and template integration ---
def insert_autobuilt_page(output_path, source_path=None):
    """
    Insert a record for an auto-generated page (e.g., admin page) into the pages table.
    output_path: location of the generated HTML file (e.g., build/admin/files_table.html)
    source_path: original source (if any), else None
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO pages (source_path, output_path, is_autobuilt)
        VALUES (?, ?, 1)
        """,
        (source_path, output_path)
    )
    conn.commit()
    conn.close()

def export_table_to_html(table_name, output_path, template_path=None, columns=None, where=None, limit=None):
    """
    Stub: Export a table to static HTML using a site template.
    - table_name: DB table to export
    - output_path: Path to write HTML file
    - template_path: Optional path to HTML template (from static/templates)
    - columns, where, limit: Optional query params
    """
    # Query table
    rows = fetch_table(table_name, columns=columns, where=where, limit=limit)
    cols = columns if columns else get_table_columns(table_name)
    table_html = tabulate(rows, headers=cols, tablefmt="html")

    # Load template
    if not template_path:
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "templates", "admin_page.html")
    with open(template_path, "r") as tpl:
        template = tpl.read()

    # Get site info for title and footer
    site_info = get_site_info()
    page_title = site_info.get("title", "Admin Table")
    footer_text = site_info.get("footer_text", "")

    # Inject table HTML, title, and footer
    html = template.replace("{{ content }}", table_html)
    html = html.replace("{{ title }}", page_title)
    html = html.replace("{{ footer }}", footer_text)
    # Optionally inject header/nav (stubbed as empty)
    html = html.replace("{{ header }}", "")
    html = html.replace("{{ nav_menu }}", "")

    with open(output_path, "w") as f:
        f.write(html)

def export_all_tables_to_html(output_dir, template_path=None):
    """
    Stub: Export all tables to static HTML files in output_dir using a site template.
    """
    os.makedirs(output_dir, exist_ok=True)
    for table in get_table_names():
        output_path = os.path.join(output_dir, f"{table}_table.html")
        export_table_to_html(table, output_path, template_path)

def integrate_with_make():
    """
    Stub: Integrate admin HTML export into build/make process.
    """
    # TODO: Hook export functions into make.py/build.py workflow
    pass

def main():
    import argparse
    parser = argparse.ArgumentParser(description="View asset database contents (files/pages_files/pages).")
    parser.add_argument('--table', type=str, choices=get_table_names(), help='Table name to display (files, pages_files, or pages)')
    parser.add_argument('--columns', type=str, nargs='+', help='Columns to display')
    parser.add_argument('--where', type=str, help='SQL WHERE clause')
    parser.add_argument('--limit', type=int, help='Limit number of rows')
    parser.add_argument('--all', action='store_true', help='Display all tables')
    args = parser.parse_args()

    if args.all:
        display_all_tables()
    elif args.table:
        display_table(args.table, columns=args.columns, where=args.where, limit=args.limit)
    else:
        print("Specify --table files, --table pages_files, --table pages, or --all to display asset database contents.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    def main():
        import argparse
        parser = argparse.ArgumentParser(description="View asset database contents (files/pages_files only).")
        parser.add_argument('--table', type=str, choices=get_table_names(), help='Table name to display (files or pages_files)')
        parser.add_argument('--columns', type=str, nargs='+', help='Columns to display')
        parser.add_argument('--where', type=str, help='SQL WHERE clause')
        parser.add_argument('--limit', type=int, help='Limit number of rows')
        parser.add_argument('--all', action='store_true', help='Display both files and pages_files tables')
        # Future: parser.add_argument('--export-html', action='store_true', help='Export table(s) to static HTML')
        args = parser.parse_args()

        if args.all:
            display_all_tables()
        elif args.table:
            display_table(args.table, columns=args.columns, where=args.where, limit=args.limit)
        else:
            print("Specify --table files, --table pages_files, or --all to display asset database contents.")

    # Test: Insert a sample admin page record
    insert_autobuilt_page("build/admin/files_table.html")
    main()

"""
Recommendations for future web admin interface:
- Use this module's logic as backend for a Flask/FastAPI app.
- Provide endpoints for table listing, selective queries, and pagination.
- Use tabulate or pandas for pretty HTML tables.
- Add authentication and role-based access for admin features.
- Support export to CSV/JSON for data analysis.
- Add search/filter UI for large tables.
- Only expose files and pages_files tables for asset management.
"""
