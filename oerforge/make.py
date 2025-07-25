"""
make.py
========

Database-driven Markdown to HTML Static Site Generator for OERForge.
Builds HTML pages from Markdown sources using Jinja2 templates, static assets, and the SQLite database as the source of truth.
"""

import os
import re
import sys
import yaml
import logging
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from markdown_it import MarkdownIt
from jinja2 import Environment, FileSystemLoader, select_autoescape
from oerforge.db_utils import get_db_connection, db_log, initialize_database
from oerforge.copyfile import ensure_dir, copy_static_assets_to_build, copy_db_images_to_build
from oerforge.scan import merge_export_config

# --- Constants ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
BUILD_HTML_DIR = os.path.join(PROJECT_ROOT, 'build')
LAYOUTS_DIR = os.path.join(PROJECT_ROOT, 'layouts')
LOG_PATH = os.path.join(PROJECT_ROOT, 'log', 'build.log')

def configure_logging(overwrite=False):
    """
    Configure logging to file and console. If overwrite is True, the log file is truncated.
    """
    log_mode = 'w' if overwrite else 'a'
    handlers = [
        logging.FileHandler(LOG_PATH, mode=log_mode, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=handlers
    )

def slugify(value):
    """
    Convert a string to a URL-friendly slug (lowercase, hyphens, alphanum only).
    """
    value = re.sub(r'[^a-zA-Z0-9]+', '-', value)
    return value.strip('-').lower()

def convert_markdown_to_html(md_text):
    """
    Convert Markdown text to HTML using markdown-it-py.
    Returns the HTML string.
    """
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    return md.render(md_text)

def postprocess_internal_links(html, md_to_html_map, current_output_path=None):
    """
    Replace all internal .md links in <a> tags with their HTML equivalents using the mapping.
    Tries multiple variants of the href to maximize match chances.
    Logs any links that could not be rewritten.
    """
    import os
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        if not isinstance(a, Tag):
            continue
        href = a.get("href", None)
        if not (isinstance(href, str) and href.endswith('.md')):
            continue
        # Normalize to DB lookup: try direct DB key and basename
        target_html = md_to_html_map.get(href) or md_to_html_map.get(os.path.basename(href))
        if target_html:
            a['href'] = target_html
        else:
            # Add '(Page not in sqlite.db)' message next to the link in HTML
            not_found_msg = soup.new_string(' (OER-Forge: Page not found in sqlite.db)')
            if a.next_sibling:
                a.insert_after(not_found_msg)
            elif a.parent:
                a.parent.append(not_found_msg)
            else:
                a.insert_after(not_found_msg)
    return str(soup)

def setup_template_env():
    """
    Set up and return a Jinja2 Environment for rendering HTML templates.
    Loads templates from the layouts directory and its subfolders.
    Enables autoescaping for HTML and XML files.
    """
    env = Environment(
        loader=FileSystemLoader([
            LAYOUTS_DIR,
            os.path.join(LAYOUTS_DIR, '_default'),
            os.path.join(LAYOUTS_DIR, 'partials')
        ]),
        autoescape=select_autoescape(['html', 'xml'])
    )
    return env

def get_asset_path(asset_type, filename, output_path):
    """
    Compute the relative path from the output HTML file to the asset.
    Keeps asset linking robust for static deployment.
    """
    # Use root-relative paths without 'static/' prefix
    asset_dir = asset_type if asset_type else ''
    asset_path = os.path.join(asset_dir, filename) if asset_dir else filename
    root_path = '/' + asset_path.replace('\\', '/').lstrip('/')
    return root_path

def fetch_site_info_from_db(cursor):
    """
    Fetch site info from the database as a dictionary.
    """
    cursor.execute('SELECT * FROM site_info LIMIT 1')
    row = cursor.fetchone()
    if not row:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))

def upsert_site_info(cursor, site, footer):
    """
    Insert site info into the database if not present.
    """
    cursor.execute('SELECT COUNT(*) FROM site_info')
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute('''INSERT INTO site_info
            (title, author, description, logo, favicon, theme_default, theme_light, theme_dark, language, github_url, footer_text, header)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            site.get('title', ''),
            site.get('author', ''),
            site.get('description', ''),
            site.get('logo', ''),
            site.get('favicon', ''),
            site.get('theme', {}).get('default', ''),
            site.get('theme', {}).get('light', ''),
            site.get('theme', {}).get('dark', ''),
            site.get('language', ''),
            site.get('github_url', ''),
            footer.get('text', ''),
            site.get('header', ''),
        ))
        logging.info("Populated site_info table from _content.yml.")

def build_nav(items, content_lookup, current_output_dir, parent_slugs=None):
    """
    Recursively build nav structure from TOC, using full slug path.
    Adds debug logging for each menu item.
    """
    nav = []
    parent_slugs = parent_slugs or []
    for item in items:
        if not item.get('menu', True):
            continue
        file_path = item.get('file', '')
        slug = item.get('slug', None)
        output_path = (
            content_lookup.get((file_path, slug)) or
            content_lookup.get(('content/' + file_path, slug)) if not file_path.startswith('content/') else None or
            content_lookup.get((f"content/{'/'.join(parent_slugs)}/{file_path}", slug)) if parent_slugs else None
        )
        debug_msg = f"[NAV-DEBUG] file_path='{file_path}', slug='{slug}', "
        if output_path:
            rel_link = os.path.relpath(output_path, current_output_dir).replace('\\', '/')
            debug_msg += f"db_output_path='{output_path}', rel_link='{rel_link}' (DB match)"
            nav_item = {'title': item.get('title', ''), 'link': rel_link, 'file': file_path, 'slug': slug}
            if item.get('children'):
                nav_item['children'] = build_nav(item['children'], content_lookup, current_output_dir, parent_slugs + ([slug] if slug else []))
            nav.append(nav_item)
        else:
            logging.warning(f"[NAV-OMIT] No DB output path for nav item '{item.get('title', '')}' (file: '{file_path}', slug: '{slug}'). Skipping.")
            debug_msg += "NO DB output path, item skipped."
        logging.debug(debug_msg)
    return nav

def build_all_markdown_files():
    """
    Main build routine for the static site generator.
    - Auto-populates the DB with Markdown files if the content table is empty.
    - Loads site context from _content.yml.
    - Syncs site_info table with YAML.
    - Converts Markdown to HTML and renders with Jinja2.
    - Copies static assets and images.
    """
    if not os.path.exists(DB_PATH):
        logging.warning(f"Database not found at {DB_PATH}. Initializing new database.")
        initialize_database(DB_PATH)

    content_yml_path = os.path.join(PROJECT_ROOT, '_content.yml')
    if not os.path.exists(content_yml_path):
        logging.error(f"_content.yml not found at {content_yml_path}. Aborting build.")
        return

    with open(content_yml_path, 'r', encoding='utf-8') as f:
        content_config = yaml.safe_load(f)
    site = content_config.get('site', {})
    footer = content_config.get('footer', {})
    toc = content_config.get('toc', [])

    content_lookup = {}
    conn = get_db_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT source_path, slug, output_path FROM content WHERE mime_type = '.md'")
    db_md_files = set()
    for source_path, slug, output_path in cursor.fetchall():
        content_lookup[(source_path, slug)] = output_path
        db_md_files.add(source_path)

    # --- Check: Every TOC Markdown file must be present in DB ---
    def extract_toc_md_files(items):
        files = set()
        for item in items:
            file_path = item.get('file', '')
            if isinstance(file_path, str) and file_path.endswith('.md'):
                files.add(file_path)
            if item.get('children'):
                files.update(extract_toc_md_files(item['children']))
        return files
    toc_md_files = extract_toc_md_files(toc)
    missing_in_db = toc_md_files - db_md_files
    if missing_in_db:
        for missing in missing_in_db:
            abs_missing_path = os.path.join(PROJECT_ROOT, 'content', missing) if not missing.startswith('content/') else os.path.join(PROJECT_ROOT, missing)
            if os.path.exists(abs_missing_path):
                logging.error(f"[DB-CHECK] TOC file '{missing}' exists on disk but is missing from DB after scan. Add file to _content.yml toc:  - title: <your title>\n    file: {missing}\n    slug: <your-slug>")
            else:
                logging.error(f"[DB-CHECK] TOC file '{missing}' missing from DB and not found on disk. This may be a DB population bug or a missing file.")

    upsert_site_info(cursor, site, footer)
    conn.commit()
    db_site_info = fetch_site_info_from_db(cursor)
    if db_site_info:
        mismatch = []
        def check(key, yaml_val, db_val):
            if (yaml_val or '') != (db_val or ''):
                mismatch.append(f"{key}: YAML='{yaml_val}' DB='{db_val}'")
        check('title', site.get('title', ''), db_site_info.get('title', ''))
        check('author', site.get('author', ''), db_site_info.get('author', ''))
        check('description', site.get('description', ''), db_site_info.get('description', ''))
        check('logo', site.get('logo', ''), db_site_info.get('logo', ''))
        check('favicon', site.get('favicon', ''), db_site_info.get('favicon', ''))
        check('theme_default', site.get('theme', {}).get('default', ''), db_site_info.get('theme_default', ''))
        check('theme_light', site.get('theme', {}).get('light', ''), db_site_info.get('theme_light', ''))
        check('theme_dark', site.get('theme', {}).get('dark', ''), db_site_info.get('theme_dark', ''))
        check('language', site.get('language', ''), db_site_info.get('language', ''))
        check('github_url', site.get('github_url', ''), db_site_info.get('github_url', ''))
        check('footer_text', footer.get('text', ''), db_site_info.get('footer_text', ''))
        check('header', site.get('header', ''), db_site_info.get('header', ''))
        if mismatch:
            logging.warning("Site info mismatch between _content.yml and site_info table:\n" + "\n".join(mismatch))

    cursor.execute("SELECT source_path, output_path, title, slug, export_types FROM content WHERE mime_type = '.md'")
    records = cursor.fetchall()
    if not records:
        logging.warning("No Markdown files found in database. Nothing to build.")
        conn.close()
        return

    env = setup_template_env()
    logging.debug(f"[BUILD] Total markdown records: {len(records)}")
    files_written = []
    files_skipped = []
    for i, (source_path, output_path, title, slug, export_types) in enumerate(records):
        logging.debug(f"[BUILD] Record {i}: source_path={source_path}, output_path={output_path}, title={title}, slug={slug}, export_types={export_types}")
        abs_source_path = os.path.join(PROJECT_ROOT, source_path) if not os.path.isabs(source_path) else source_path
        abs_output_path = os.path.join(BUILD_HTML_DIR, output_path) if not os.path.isabs(output_path) else output_path
        logging.debug(f"[BUILD] abs_source_path={abs_source_path}, abs_output_path={abs_output_path}")
        if not os.path.exists(abs_source_path):
            logging.error(f"[BUILD] Source file not found: {abs_source_path}. Skipping.")
            files_skipped.append((source_path, abs_output_path, 'source missing'))
            continue
        try:
            with open(abs_source_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
            logging.debug(f"[BUILD] Read markdown from {abs_source_path} (length={len(md_text)})")
        except Exception as e:
            logging.error(f"[BUILD] Failed to read {abs_source_path}: {e}")
            files_skipped.append((source_path, abs_output_path, f'read error: {e}'))
            continue
        html_body = convert_markdown_to_html(md_text)
        try:
            def asset(name, typ=''):
                return get_asset_path(typ, name, abs_output_path)
            logo_file = site.get('logo', 'logo.png')
            favicon_file = site.get('favicon', 'favicon.ico')
            current_output_dir = os.path.dirname(output_path)
            nav_menu = build_nav(toc, content_lookup, current_output_dir)
            context = {
                'title': title,
                'body': html_body,
                'slug': slug,
                'site': site,
                'footer': footer,
                'css_path': asset('theme-dark.css', 'css'),
                'js_path': asset('main.js', 'js'),
                'logo_path': asset(os.path.basename(logo_file), 'images'),
                'favicon_path': asset(os.path.basename(favicon_file), 'images'),
                'favicon16_path': asset('favicon-16x16.png', 'images'),
                'favicon32_path': asset('favicon-32x32.png', 'images'),
                'apple_touch_icon_path': asset('apple-touch-icon.png', 'images'),
                'android192_path': asset('android-chrome-192x192.png', 'images'),
                'android512_path': asset('android-chrome-512x192x192.png', 'images'),
                'manifest_path': asset('site.webmanifest'),
                'top_menu': nav_menu,
            }
            page_html = env.get_template('base.html').render(**context)
            # --- Post-process internal links in final HTML ---
            md_to_html_map = {}
            for (src_path, slug_key), out_path in content_lookup.items():
                if src_path.endswith('.md'):
                    root_out = '/' + out_path.replace('\\', '/').lstrip('/')
                    basename = os.path.basename(src_path)
                    md_to_html_map[basename] = root_out
                    md_to_html_map[src_path] = root_out
                    md_to_html_map[out_path] = root_out
                    norm_path = os.path.normpath(src_path).replace('\\', '/')
                    md_to_html_map[norm_path] = root_out
                    if src_path.startswith('content/'):
                        md_to_html_map[src_path[len('content/'):]] = root_out
            logging.debug(f"[POSTPROCESS] md_to_html_map for {abs_output_path}: {md_to_html_map}")

            page_html_post = postprocess_internal_links(page_html, md_to_html_map, abs_output_path)
            soup = BeautifulSoup(page_html_post, "html.parser")
            for a in soup.find_all("a"):
                if isinstance(a, Tag):
                    href = a.get("href", None)
                    if isinstance(href, str) and href.endswith('.html'):
                        logging.debug(f"[POSTPROCESS] Link rewritten: {a.text} -> {href}")
            page_html = page_html_post
        except Exception as e:
            logging.error(f"[BUILD] Template rendering or post-processing failed for {source_path}: {e}")
            files_skipped.append((source_path, abs_output_path, f'template error: {e}'))
            continue
        ensure_dir(os.path.dirname(abs_output_path))
        try:
            with open(abs_output_path, 'w', encoding='utf-8') as outf:
                outf.write(page_html)
            logging.info(f"[BUILD] Wrote HTML: {abs_output_path}")
            files_written.append((source_path, abs_output_path))
        except Exception as e:
            logging.error(f"[BUILD] Failed to write output for {source_path}: {e}")
            files_skipped.append((source_path, abs_output_path, f'write error: {e}'))
    logging.info(f"[SUMMARY] Files written: {len(files_written)}")
    for src, out in files_written:
        logging.info(f"[SUMMARY] WROTE: {src} -> {out}")
    logging.info(f"[SUMMARY] Files skipped: {len(files_skipped)}")
    for src, out, reason in files_skipped:
        logging.info(f"[SUMMARY] SKIPPED: {src} -> {out} ({reason})")
    conn.close()
    copy_static_assets_to_build()
    copy_db_images_to_build()
    logging.info("[AUTO] All markdown files built.")

def main():
    """
    Entrypoint for the script.
    Configures logging and runs the build process.
    """
    log_dir = Path(LOG_PATH).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"[LOGGING] Build log will be written to: {LOG_PATH}")
    try:
        configure_logging(overwrite=True)
    except Exception as e:
        print(f"[LOGGING] Failed to configure logging: {e}")
    build_all_markdown_files()

if __name__ == "__main__":
    main()