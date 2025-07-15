"""
export_db_html.py: Export asset DB tables to static HTML using site templates (e.g., page.html).
"""
import os
import logging
from oerforge.logging_utils import setup_logging

def log_admin(msg):
    logging.info(f"[ADMIN] {msg}")
from tabulate import tabulate
from oerforge_admin.view_db import get_db_path, get_table_names, get_table_columns, fetch_table

def render_table_html(table_name, columns=None, where=None, limit=None):
    log_admin(f"Rendering HTML for table: {table_name}, columns: {columns}, where: {where}, limit: {limit}")
    cols = columns if columns else get_table_columns(table_name)
    rows = fetch_table(table_name, columns=columns, where=where, limit=limit)
    log_admin(f"Fetched {len(rows)} rows for table: {table_name}")
    return tabulate(rows, headers=cols, tablefmt="html")

def inject_table_into_template(table_html, template_path, output_path):
    """
    Read template, inject table_html at <!-- ASSET_TABLE -->, write to output_path.
    Also inject header/footer and update CSS/JS references to /build.
    """
    log_admin(f"Injecting table HTML into template: {template_path}, output: {output_path}")
    with open(template_path, "r") as f:
        template = f.read()
    log_admin(f"Template contents (first 500 chars): {template[:500]}")
    # Inject site info from DB
    from oerforge_admin.view_db import get_site_info
    site_info = get_site_info()
    header_html = site_info.get("header", "")
    # Replace {{ site_title }} and {{ nav_menu }} in header HTML
    header_html = header_html.replace("{{ site_title }}", site_info.get("title", "Admin Table"))
    # For now, nav_menu is empty or can be set to a default value
    header_html = header_html.replace("{{ nav_menu }}", "")
    log_admin(f"Header from DB (first 500 chars): {repr(header_html)[:500]}")
    # Replace title, header, and footer placeholders
    template = template.replace("{{ title }}", site_info.get("title", "Admin Table"))
    template = template.replace("{{ header }}", header_html)
    # Inject full footer HTML from static/templates/footer.html
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    footer_path = os.path.join(project_root, "static", "templates", "footer.html")
    with open(footer_path, "r") as f:
        footer_html = f.read()
    # Replace {{ footer_text }} in footer.html with site_info value
    footer_html = footer_html.replace("{{ footer_text }}", site_info.get("footer_text", ""))
    template = template.replace("{{ footer }}", footer_html)
    log_admin(f"Template after header injection (first 500 chars): {template[:500]}")
    # Replace CSS/JS references to point to local admin assets
    template = template.replace("/build/css/", "css/")
    template = template.replace("/build/js/", "js/")
    # Inject table HTML
    if "<!-- ASSET_TABLE -->" in template:
        html = template.replace("<!-- ASSET_TABLE -->", table_html)
    elif "{{ content }}" in template:
        html = template.replace("{{ content }}", table_html)
    elif "</main>" in template:
        html = template.replace("</main>", f"{table_html}\n</main>")
    elif "</body>" in template:
        html = template.replace("</body>", f"{table_html}\n</body>")
    else:
        html = template + table_html
    with open(output_path, "w") as f:
        f.write(html)
    log_admin(f"Wrote injected HTML to: {output_path}")

def export_table_to_html(table_name, output_path, template_path=None, columns=None, where=None, limit=None):
    """
    Export a table to static HTML using a site template.
    """
    log_admin(f"Exporting table {table_name} to HTML: {output_path}, template: {template_path}")
    if not template_path:
        # Default to admin_page.html in static/templates
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_path = os.path.join(project_root, "static", "templates", "page.html")
    table_html = render_table_html(table_name, columns, where, limit)
    inject_table_into_template(table_html, template_path, output_path)

def export_all_tables_to_html(output_dir, template_path=None):
    """
    Export all tables to static HTML files in output_dir using a site template.
    """
    log_admin(f"Exporting all tables to HTML in: {output_dir}, template: {template_path}")
    os.makedirs(output_dir, exist_ok=True)
    tables = get_table_names()
    log_admin(f"get_table_names() returned: {tables}")
    if 'content' not in tables:
        log_admin("WARNING: 'content' table not found in get_table_names() output!")
    else:
        log_admin("'content' table found in get_table_names() output.")
    for table in tables:
        output_path = os.path.join(output_dir, f"{table}_table.html")
        log_admin(f"Exporting table: {table} to {output_path}")
        export_table_to_html(table, output_path, template_path)
    log_admin("All tables exported.")

def copy_static_assets_to_admin(output_dir):
    """
    Copy only required CSS and JS files to build/admin for standalone admin pages.
    """
    import shutil
    log_admin(f"Copying static assets to admin output dir: {output_dir}")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_css = os.path.join(project_root, "static", "css")
    static_js = os.path.join(project_root, "static", "js")
    build_css = os.path.join(project_root, "build", "css")
    build_js = os.path.join(project_root, "build", "js")
    os.makedirs(build_css, exist_ok=True)
    os.makedirs(build_js, exist_ok=True)
    # Copy only theme-dark.css and theme-light.css
    for css_file in ["theme-dark.css", "theme-light.css"]:
        src = os.path.join(static_css, css_file)
        dst = os.path.join(build_css, css_file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            log_admin(f"Copied CSS: {src} -> {dst}")
        else:
            log_admin(f"CSS file missing: {src}")
    # Copy main.js
    js_src = os.path.join(static_js, "main.js")
    js_dst = os.path.join(build_js, "main.js")
    if os.path.exists(js_src):
        shutil.copy2(js_src, js_dst)
        log_admin(f"Copied JS: {js_src} -> {js_dst}")
    else:
        log_admin(f"JS file missing: {js_src}")
if __name__ == "__main__":
    # Example usage stub
    # export_all_tables_to_html("build/admin/")
    # copy_static_assets_to_admin("build/admin/")
    setup_logging()
    log_admin("Run as a module or import for use in build/make workflow. Output: build/admin/")
