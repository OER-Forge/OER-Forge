import os
import sys
import sqlite3
import subprocess
import json
from typing import Optional, Dict, Any, List
import logging

logging.basicConfig(
    filename="log/pa11y.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)

# --- Config and Logging ---
def load_pa11y_config(yml_path: str = "_content.yml") -> dict:
    """Load pa11y config and logo info from _content.yml and/or pa11y-configs/wcag.badges.json."""
    import yaml
    
    yml_path = os.path.abspath(yml_path)
    if not os.path.exists(yml_path):
        return {}
    with open(yml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    # Only return the 'pa11y' block if it exists
    return data.get('pa11y', {}) if data else {}


# --- Pa11y Integration ---
def run_pa11y_on_file(html_path: str, config_path: Optional[str] = None, wcag_level: str = "AA") -> Optional[List[Dict[str, Any]]]:
    """
    Run Pa11y on a single HTML file. Returns parsed JSON result, or None on error.
    Accepts config_path and wcag_level ("AA" or "AAA").
    """
    html_abs = os.path.abspath(html_path)
    pa11y_cmd = ["pa11y", f"file://{html_abs}", "--reporter", "json"]
    # Add WCAG level as --standard
    if wcag_level.upper() == "AAA":
        pa11y_cmd.extend(["--standard", "WCAG2AAA"])
    else:
        pa11y_cmd.extend(["--standard", "WCAG2AA"])
    if config_path:
        pa11y_cmd.extend(["--config", os.path.abspath(config_path)])
    try:
        logging.info(f"Running Pa11y on {html_path} with command: {' '.join(pa11y_cmd)}")
        result = subprocess.run(pa11y_cmd, capture_output=True, text=True, check=True)
        logging.info(f"Pa11y output for {html_path}: {result.stdout}")
        return json.loads(result.stdout)
    except FileNotFoundError:
        logging.error("Pa11y is not installed or not found in PATH.")
        return None
    except subprocess.CalledProcessError as e:
        logging.error(f"Pa11y failed for {html_path}: {e.stderr}")
        try:
            return json.loads(e.stdout)
        except Exception as parse_err:
            logging.error(f"Failed to parse Pa11y JSON output after error: {parse_err}")
            return None
    except json.JSONDecodeError:
        logging.error(f"Failed to parse Pa11y JSON output for {html_path}.")
        return None

# --- DB Operations ---
def get_content_id_for_file(html_path: str, conn) -> Optional[int]:
    """Get the content_id for a given HTML file from the DB."""
    # Normalize path for DB comparison
    html_path = os.path.abspath(html_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, output_path FROM content")
    for row in cursor.fetchall():
        db_id, db_path = row
        if os.path.abspath(db_path) == html_path:
            return db_id
    logging.warning(f"No content_id found for {html_path}")
    return None

def store_accessibility_result(content_id: int, pa11y_json: List[Dict[str, Any]], badge_html: str, wcag_level: str, error_count: int, warning_count: int, notice_count: int, conn=None):
    """Store the latest accessibility result for a page in the database."""
    if conn is None:
        raise ValueError("A valid database connection is required.")
    cursor = conn.cursor()
    # Remove old result for this content_id and wcag_level
    cursor.execute("""
        DELETE FROM accessibility_results WHERE content_id = ? AND wcag_level = ?
    """, (content_id, wcag_level))
    # Insert new result
    cursor.execute("""
        INSERT INTO accessibility_results (
            content_id, pa11y_json, badge_html, wcag_level, error_count, warning_count, notice_count, checked_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        content_id,
        json.dumps(pa11y_json),
        badge_html,
        wcag_level,
        error_count,
        warning_count,
        notice_count
    ))
    conn.commit()

# --- Badge and Report Generation ---
def generate_badge_html(wcag_level: str, error_count: int, logo_info: dict, report_link: str) -> str:
    """Generate badge HTML for a given WCAG level and error count, using logo info. Badge links to the local accessibility report."""
    # logo_info should be a dict mapping WCAG levels to badge/logo URLs
    logging.debug(f"[generate_badge_html] logo_info keys: {list(logo_info.keys())}")
    logging.debug(f"[generate_badge_html] Requested wcag_level: {wcag_level}")
    logging.debug(f"[generate_badge_html] Called with wcag_level={wcag_level}, error_count={error_count}, report_link={report_link}")
    logging.debug(f"[generate_badge_html] logo_info: {logo_info}")
    badge_url = logo_info.get(wcag_level, "")
    logging.debug(f"[generate_badge_html] badge_url resolved: {badge_url}")
    if not badge_url:
        logging.warning(f"[generate_badge_html] No badge URL found for WCAG level: {wcag_level}")
        return f'<span class="badge-missing">WCAG {wcag_level} badge not found</span>'
    img_url = f"{badge_url}"
    alt_text = f"WCAG {wcag_level} Conformance Logo"
    # Determine badge class only (no error count in badge)
    logging.debug(f"[generate_badge_html] error_count: {error_count}")
    if error_count == 0:
        badge_class = "wcag-badge wcag-badge-success"
        logging.debug(f"[generate_badge_html] No errors. badge_class={badge_class}")
    else:
        badge_class = "wcag-badge wcag-badge-error"
        logging.debug(f"[generate_badge_html] Errors present. badge_class={badge_class}")
    badge_html = (
        f'<a href="{report_link}" aria-label="View Accessibility Report" class="{badge_class}" data-accessibility-report-btn="1">'
        f'<img src="{img_url}" alt="{alt_text}" style="height:2em;vertical-align:middle;">'
        f'</a>'
    )
    logging.info(f"[generate_badge_html] Generated badge HTML for WCAG {wcag_level}: {badge_html}")
    return badge_html

def inject_badge_into_html(html_path: str, badge_html: str, report_link: str, logo_info: dict):
    """Inject the badge/button into the HTML file after <main>."""
    # Use BeautifulSoup for robust HTML manipulation
    try:
        from bs4 import BeautifulSoup
        from bs4.element import NavigableString, Tag
    except ImportError:
        raise ImportError("BeautifulSoup4 is required. Install with 'pip install beautifulsoup4'.")

    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
    except Exception as e:
        logging.error(f"[inject_badge_into_html] Failed to read {html_path}: {e}")
        return

    soup = BeautifulSoup(html, 'html.parser')

    # Remove all previous accessibility report buttons and badges (robust)
    removed = 0
    # Remove all <a> with class containing 'wcag-badge' and data-accessibility-report-btn
    for a in soup.find_all('a'):
        if (
            isinstance(a, Tag)
            and a.has_attr('class')
            and any('wcag-badge' in c for c in a['class'])
            and a.has_attr('data-accessibility-report-btn')
        ):
            a.decompose()
            removed += 1
    # Remove all <a class="download-btn" data-accessibility-report-btn>
    for a in soup.find_all('a', class_='download-btn'):
        if isinstance(a, Tag) and a.has_attr('data-accessibility-report-btn'):
            a.decompose()
            removed += 1
    # Remove all <span class="badge-missing">
    for span in soup.find_all('span', class_='badge-missing'):
        if isinstance(span, Tag):
            span.decompose()
            removed += 1
    # Remove all <img> tags whose src starts with any badge URL in logo_info, and their parent <a> if it's a badge link
    badge_urls = set(logo_info.values())
    for img in soup.find_all('img'):
        if isinstance(img, Tag) and img.has_attr('src'):
            img_src = str(img['src'])
            for badge_url in badge_urls:
                if img_src.startswith(badge_url):
                    parent = img.parent
                    if parent and parent.name == 'a' and parent.has_attr('href'):
                        parent_href = str(parent['href'])
                        if parent_href.startswith(badge_url):
                            parent.decompose()
                            removed += 1
                            break
                    img.decompose()
                    removed += 1
                    break
    if removed > 0:
        logging.info(f"[inject_badge_into_html] Removed {removed} existing accessibility report button/badge blocks in {html_path}")


    # The badge_html now includes the button and error count, so just insert badge_frag
    badge_frag = BeautifulSoup(badge_html, 'html.parser') if badge_html else None
    inserted = False
    placeholder = soup.find(id="accessibility-report-placeholder")
    if placeholder is not None and badge_frag:
        placeholder.insert_after(badge_frag)
        inserted = True
    else:
        main_tag = soup.find('main')
        if main_tag and badge_frag:
            main_tag.insert_after(badge_frag)
            inserted = True
        else:
            body_tag = soup.find('body')
            if body_tag and badge_frag:
                body_tag.insert_after(badge_frag)
                inserted = True
    if not inserted and badge_frag:
        soup.insert(0, badge_frag)
    if not inserted and badge_frag:
        # Fallback: insert at the start of the soup
        soup.insert(0, badge_frag)

    # Write back the modified HTML
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        logging.info(f"[inject_badge_into_html] Injected/replaced accessibility report button into {html_path}")
    except Exception as e:
        logging.error(f"[inject_badge_into_html] Failed to write {html_path}: {e}")


# --- Navigation Menu Generation (ported from make.py) ---
def generate_nav_menu(context: dict) -> list:
    import os
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    menu_items = []
    rel_path = context.get('rel_path', '')
    # Query for top-level menu items (menu_context='main', parent_output_path is NULL or empty)
    sql = "SELECT title, relative_link FROM content WHERE menu_context='main' AND (parent_output_path IS NULL OR parent_output_path = '') ORDER BY \"order\";"
    cursor.execute(sql)
    rows = cursor.fetchall()
    for title, relative_link in rows:
        # For Home, always use 'index.html'
        if title and title.lower() == 'home':
            target = 'index.html'
        else:
            target = relative_link
        # Compute menu links relative to the current page's directory
        if rel_path:
            current_dir = os.path.dirname(rel_path)
            is_section_index = (
                rel_path.endswith('index.html') and
                current_dir and
                rel_path != 'index.html'
            )
            if is_section_index:
                # If this menu item is the current section, use "index.html"
                if target == rel_path or os.path.normpath(target) == os.path.normpath(rel_path):
                    link = "index.html"
                else:
                    link = "../" + target
            else:
                link = os.path.relpath(target, current_dir) if not os.path.isabs(target) else target
        else:
            link = target
        menu_items.append({'title': title, 'link': link})
    conn.close()
    return menu_items

def generate_wcag_report(html_path: str, issues: List[Dict[str, Any]], badge_html: str, config: dict):
    """Generate a detailed HTML report for the file using a Jinja2 template that extends baseof.html."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    # Determine output path: wcag_report_FILENAME.html in same dir as html_path
    html_dir = os.path.dirname(html_path)
    html_filename = os.path.basename(html_path)
    if html_filename.endswith('.html'):
        report_filename = f"wcag_report_{html_filename}"
    else:
        report_filename = f"wcag_report.html"
    report_path = os.path.join(html_dir, report_filename)

    # Setup Jinja2 environment to search both reports and partials
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../layouts'))
    template_dirs = [
        os.path.join(base_dir, 'reports'),
        os.path.join(base_dir, 'partials'),
        os.path.join(base_dir, '_default'),
    ]
    env = Environment(
        loader=FileSystemLoader(template_dirs),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('wcag_report.html')

    # Load site and footer info from _content.yml
    site_config = load_pa11y_config(os.path.abspath(os.path.join(os.path.dirname(__file__), '../_content.yml')))
    site = site_config.get('site', {})
    footer_text = site_config.get('footer', {}).get('text', '')

    # Compute relative asset paths from report location
    build_dir = os.path.abspath(os.path.join(html_dir, '..'))
    css_path = os.path.relpath(os.path.join(build_dir, 'css/theme-light.css'), html_dir)
    js_path = os.path.relpath(os.path.join(build_dir, 'js/main.js'), html_dir)
    favicon = os.path.relpath(os.path.join(build_dir, 'images/favicon.ico'), html_dir)
    logo_path = os.path.relpath(os.path.join(build_dir, 'images/logo.png'), html_dir)

    # Try to extract page title from HTML file (fallback to config or filename)
    page_title = config.get('title', html_filename)
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '<title>' in line:
                    import re
                    m = re.search(r'<title>(.*?)</title>', line)
                    if m:
                        page_title = m.group(1).strip()
                        break
    except Exception:
        pass

    # Compute relative URL from build/ root
    build_root = os.path.abspath(os.path.join(html_dir, '..'))
    relative_url = os.path.relpath(html_path, build_root)

    # Compute rel_path for the report (relative to build/)
    rel_path = os.path.relpath(report_path, build_root)
    # Generate the top menu using the same logic as make.py
    top_menu = generate_nav_menu({'rel_path': rel_path})

    context = {
        'Title': page_title,  # For {% block title %} in baseof.html
        'page_title': page_title,
        'relative_url': relative_url,
        'site': site,
        'css_path': css_path,
        'js_path': js_path,
        'favicon': favicon,
        'logo_path': logo_path,
        'wcag_level': config.get('wcag_level', 'AA'),
        'error_count': sum(1 for i in issues if i.get('type') == 'error'),
        'warning_count': sum(1 for i in issues if i.get('type') == 'warning'),
        'notice_count': sum(1 for i in issues if i.get('type') == 'notice'),
        'badge_html': badge_html,
        'issues': issues,
        'footer_text': footer_text,
        'top_menu': top_menu,
        'rel_path': rel_path,
    }

    # Render and write
    rendered = template.render(**context)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(rendered)
    logging.info(f"Generated WCAG report: {report_path}")
    return report_path

def process_all_html_files(build_dir="build", wcag="WCAG2AA", config_file=None, db_path="db/sqlite.db"):
    import fnmatch
    asset_dirs = {"css", "js", "images", "files"}
    from oerforge.verify import run_pa11y_on_file, get_content_id_for_file, store_accessibility_result, generate_wcag_report, inject_badge_into_html, generate_badge_html, load_pa11y_config
    import sqlite3
    import json
    # Load config and logo info
    config_data = load_pa11y_config("_content.yml")
    # Try to load logo info from pa11y-configs/wcag.badges.json if present
    logo_info = {}
    logo_json_path = os.path.join("pa11y-config", "wcag.badges.json")
    if os.path.exists(logo_json_path):
        try:
            with open(logo_json_path, "r", encoding="utf-8") as f:
                logo_info = json.load(f)
        except Exception as e:
            logging.warning(f"[process_all_html_files] Failed to load {logo_json_path}: {e}")
    # If not, try to get from config_data
    if not logo_info:
        logo_info = config_data.get("wcag_logos", {})
    # Get default WCAG level from config
    default_wcag_level = wcag

    for root, dirs, files in os.walk(build_dir):
        # Skip asset directories
        dirs[:] = [d for d in dirs if d not in asset_dirs]
        for filename in files:
            if fnmatch.fnmatch(filename, "*.html") and not filename.startswith("wcag_report_"):
                html_path = os.path.join(root, filename)
                print(f"Processing: {html_path}")
                # Determine WCAG level (allow per-page override in config if desired)
                wcag_level = default_wcag_level
                # Optionally, you could add logic here to check for per-page config in the future
                # Run Pa11y with config and level
                result = run_pa11y_on_file(html_path, config_file, wcag_level)
                # Open DB connection
                conn = sqlite3.connect(db_path)
                content_id = get_content_id_for_file(html_path, conn)
                error_count = sum(1 for i in result if i.get("type") == "error") if result else 0
                warning_count = sum(1 for i in result if i.get("type") == "warning") if result else 0
                notice_count = sum(1 for i in result if i.get("type") == "notice") if result else 0
                safe_result = result if result is not None else []
                # Compute report link before generating badge
                report_filename = f"wcag_report_{filename}" if filename.endswith('.html') else "wcag_report.html"
                report_path = os.path.join(root, report_filename)
                report_link = os.path.basename(report_path)
                badge_html = generate_badge_html(wcag_level, error_count, logo_info, report_link)
                if content_id is not None:
                    store_accessibility_result(content_id, safe_result, badge_html, wcag_level, error_count, warning_count, notice_count, conn)
                    config = {
                        'title': os.path.splitext(filename)[0].capitalize(),
                        'wcag_level': wcag_level
                    }
                    issues = safe_result
                    # Now generate the report with badge_html
                    generate_wcag_report(html_path, issues, badge_html, config)
                    inject_badge_into_html(html_path, badge_html, report_link, logo_info)
                conn.close()
    # After processing, copy changed files to docs/
    copy_to_docs()

# --- Utility ---
def copy_to_docs():
    """Copy all changed files from build/ to docs/."""
    import filecmp
    import shutil
    build_dir = os.path.abspath("build")
    docs_dir = os.path.abspath("docs")
    for root, dirs, files in os.walk(build_dir):
        rel_root = os.path.relpath(root, build_dir)
        target_root = os.path.join(docs_dir, rel_root) if rel_root != "." else docs_dir
        if not os.path.exists(target_root):
            os.makedirs(target_root, exist_ok=True)
        for filename in files:
            src_file = os.path.join(root, filename)
            dst_file = os.path.join(target_root, filename)
            # Only copy if file does not exist or is different
            if not os.path.exists(dst_file) or not filecmp.cmp(src_file, dst_file, shallow=False):
                shutil.copy2(src_file, dst_file)
                logging.info(f"Copied {src_file} to {dst_file}")
    logging.info("All changed files copied from build/ to docs/.")

# --- CLI Entry Point ---
def main():
    """Parse CLI args, run checks, store results, and generate reports as needed."""
    pass

if __name__ == "__main__":
    main()