
"""
make.py
========

Hugo-style Markdown to HTML Static Site Generator
------------------------------------------------

This module provides the core logic for building a static website from Markdown and other content sources, inspired by Hugo and similar SSGs. It supports Jinja2 templating, asset management, navigation, accessibility enhancements, and integration with a SQLite database for content tracking.

Features:
    - Markdown to HTML conversion with accessibility improvements
    - Jinja2-based template rendering (blocks, inheritance, partials)
    - Asset copying and management (CSS, JS, images)
    - Navigation menu generation from database
    - Section index autogeneration
    - Download button context for multiple formats
    - Robust logging for build operations
    - Modular, extensible design for new content types

Intended Audience:
    - New users and programmers
    - Educators and open content creators
    - Developers seeking a clear, well-documented SSG foundation

Dependencies:
    - Python 3.7+
    - Jinja2
    - markdown-it-py, mdit-py-plugins
    - PyYAML
    - SQLite3

Usage:
    Import and call the main build functions from your workflow script (e.g., build.py).
    See individual function docstrings for details.
"""

import os
import logging
import yaml
import re
import sqlite3

BUILD_DIR = 'build'
FILES_DIR = 'files'
LOG_DIR = 'log'
LOG_FILENAME = 'build.log'

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_FILES_DIR = os.path.join(PROJECT_ROOT, BUILD_DIR, FILES_DIR)
BUILD_HTML_DIR = os.path.join(PROJECT_ROOT, BUILD_DIR)
LOG_PATH = os.path.join(PROJECT_ROOT, LOG_DIR, LOG_FILENAME)
LAYOUTS_DIR = os.path.join(PROJECT_ROOT, 'layouts')

# Stub for copying static assets (CSS, JS, images) to build/
def copy_static_assets_to_build():
    """
    Copy static assets (CSS, JS, images) from the project's static/ directory to build/.

    This function ensures that all required asset directories exist in the build output,
    and overwrites files on each call to guarantee up-to-date assets.

    Logging:
        - Logs info on successful copy
        - Logs warnings if source directories are missing
    """
    import logging
    import shutil
    import os
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')
    CSS_SRC = os.path.join(PROJECT_ROOT, 'static', 'css')
    CSS_DST = os.path.join(BUILD_DIR, 'css')
    JS_SRC = os.path.join(PROJECT_ROOT, 'static', 'js')
    JS_DST = os.path.join(BUILD_DIR, 'js')
    IMAGES_SRC = os.path.join(PROJECT_ROOT, 'static', 'images')
    IMAGES_DST = os.path.join(BUILD_DIR, 'images')
    def copytree_overwrite(src, dst):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        if os.path.exists(src):
            shutil.copytree(src, dst)
            logging.info(f"Copied {src} to {dst}")
        else:
            logging.warning(f"Source directory not found: {src}")
    copytree_overwrite(CSS_SRC, CSS_DST)
    copytree_overwrite(JS_SRC, JS_DST)
    copytree_overwrite(IMAGES_SRC, IMAGES_DST)
    logging.info("[ASSET] Static assets copied to build/.")

# =========================
# Utility Functions
# =========================
def get_available_downloads_for_page(rel_path, page_dir=None):
    """
    Scan the published output directory for this page and return a list of available download formats.
    Returns: [{'label': 'PDF', 'filename': 'index.pdf', 'theme': 'light', ...}, ...]
    """
    # Determine the directory containing downloadable files
    if page_dir is None:
        # rel_path like 'about/index.html' -> build/files/about/
        if rel_path == 'index.html':
            page_dir = os.path.join(PROJECT_ROOT, 'build', 'files')
        else:
            page_dir = os.path.join(PROJECT_ROOT, 'build', 'files', os.path.dirname(rel_path))
    logging.debug(f"[DOWNLOAD][DEBUG] get_available_downloads_for_page called with rel_path={rel_path}, page_dir={page_dir}")
    # List of supported formats and labels
    formats = [
        ('.pdf', 'PDF', 'download-pdf'),
        ('.docx', 'Word', 'download-docx'),
        ('.tex', 'LaTeX', 'download-tex'),
        ('.md', 'Markdown', 'download-md'),
        ('.txt', 'Plain Text', 'download-txt'),
    ]
    # Look for files matching the page's base name (e.g., db_utils.pdf for db_utils.html)
    downloads = []
    try:
        files = os.listdir(page_dir)
        logging.debug(f"[DOWNLOAD][DEBUG] Listing files in {page_dir}: {files}")
    except Exception as e:
        logging.warning(f"[DOWNLOAD] Could not list files in {page_dir}: {e}")
        files = []
    logging.debug(f"[DOWNLOAD][DEBUG] Supported formats: {[f[0] for f in formats]}")
    # Determine base name for this page (e.g., db_utils for db_utils.html)
    base_name = os.path.splitext(os.path.basename(rel_path))[0]
    section = os.path.dirname(rel_path)
    # If rel_path is a section index page (endswith index.html and not at root), skip buttons
    is_section_index = rel_path.endswith('index.html') and section and rel_path != 'index.html'
    if is_section_index:
        logging.debug(f"[DOWNLOAD][DEBUG] Skipping download buttons for section index page: {rel_path}")
        return []
    # Get relative_link from DB for this rel_path
    db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Find the DB row for this HTML file
    cursor.execute("SELECT relative_link FROM content WHERE output_path LIKE ?", (f"%{rel_path}",))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        rel_link_base = row[0]
        if rel_link_base.endswith('.html'):
            rel_link_base = rel_link_base[:-5]
        # Compute download links for children and grandchildren
        # Compute the relative path from the HTML file's directory to the file in build/files/
        html_dir = os.path.dirname(os.path.join(PROJECT_ROOT, 'build', rel_path))
        file_path_base = os.path.join(PROJECT_ROOT, 'build', 'files', rel_link_base)
        for ext, label, theme in formats:
            fname = base_name + ext
            logging.debug(f"[DOWNLOAD][DEBUG] Checking for file: {fname} in files: {files}")
            file_path = f"{file_path_base}{ext}"
            # Only add button if file exists in files list
            if fname in files:
                # Compute relative href from HTML file's directory to the file
                href = os.path.relpath(file_path, html_dir)
                logging.debug(f"[DOWNLOAD][DEBUG] Found downloadable file for button: {fname} in {page_dir}, href={href}")
                downloads.append({
                    'label': label,
                    'filename': fname,
                    'href': href,
                    'theme': theme,
                    'aria_label': f"Download as {label}",
                })
    else:
        # No DB mapping, do not show download buttons
        logging.debug(f"[DOWNLOAD][DEBUG] No DB mapping for rel_path={rel_path}, skipping download buttons.")
        downloads = []
    logging.debug(f"[DOWNLOAD][DEBUG] Final downloads list for rel_path={rel_path}, page_dir={page_dir}: {downloads}")
    return downloads

def build_download_buttons_context(rel_path, page_dir=None):
    """
    Build the download_buttons context for a page.
    - rel_path: relative path to the HTML file (e.g., 'about/index.html')
    - page_dir: directory containing downloadable files (default: docs/about/)
    Returns: list of button dicts for the template.
    """
    logging.debug(f"[BUTTONS][DEBUG] build_download_buttons_context called for rel_path={rel_path}, page_dir={page_dir}")
    downloads = get_available_downloads_for_page(rel_path, page_dir)
    logging.debug(f"[BUTTONS][DEBUG] Downloads found for rel_path={rel_path}: {downloads}")
    buttons = []
    for d in downloads:
        button = {
            'label': d['label'],
            'href': d['href'],
            'theme': d['theme'],
            'aria_label': d['aria_label'],
        }
        logging.debug(f"[BUTTONS][DEBUG] Adding button for rel_path={rel_path}: {button}")
        buttons.append(button)
    logging.debug(f"[BUTTONS][DEBUG] Final buttons list for rel_path={rel_path}: {buttons}")
    return buttons

def slugify(title: str) -> str:
    """Convert a title to a slug suitable for folder names."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def load_yaml_config(config_path: str) -> dict:
    """Load and parse the YAML config file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logging.info(f"Loaded YAML config from {config_path}")
        return config
    except Exception as e:
        logging.error(f"Failed to load YAML config: {e}")
        return {}

def ensure_output_dir(md_path):
    """Ensure the output directory for the HTML file exists, mirroring build/files structure."""
    rel_path = os.path.relpath(md_path, BUILD_FILES_DIR)
    output_dir = os.path.join(BUILD_HTML_DIR, os.path.dirname(rel_path))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

# =========================
# Template Engine Setup
# =========================

def setup_template_env():
    """Set up Jinja2 template environment."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    layouts_default = os.path.join(LAYOUTS_DIR, '_default')
    layouts_partials = os.path.join(LAYOUTS_DIR, 'partials')
    env = Environment(
        loader=FileSystemLoader([LAYOUTS_DIR, layouts_default, layouts_partials]),
        autoescape=select_autoescape(['html', 'xml'])
    )
    return env

# =========================
# Rendering Functions
# =========================

def render_page(context: dict, template_name: str) -> str:
    """
    Render a page using Hugo-style templates (baseof.html, single.html, partials).
    """
    env = setup_template_env()
    template = env.get_template(f'_default/{template_name}')
    return template.render(**context)

# =========================
# Navigation and Partials
# =========================

def generate_nav_menu(context: dict) -> list:
    import os
    """Generate top-level navigation menu items from content table using relative_link and menu_context.
    Returns a list of menu item dicts: [{"title": ..., "link": ...}, ...]
    """
    db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    menu_items = []
    rel_path = context.get('rel_path', '')
    logging.info(f"[TEST1] generate_nav_menu called with rel_path: {rel_path}")
    # Query for top-level menu items (menu_context='main', parent_output_path is NULL or empty)
    sql = "SELECT title, relative_link FROM content WHERE menu_context='main' AND (parent_output_path IS NULL OR parent_output_path = '') ORDER BY \"order\";"
    cursor.execute(sql)
    rows = cursor.fetchall()
    logging.info(f"[TEST3] SQL query for nav menu: {sql}")
    logging.info(f"[TEST3] SQL query results: {rows}")
    # Detect if this is a section index page (e.g., 'sample-resources/index.html', not 'index.html' at root)
    is_section_index = False
    if rel_path:
        parts = rel_path.split(os.sep)
        if rel_path != 'index.html' and rel_path.endswith('index.html') and len(parts) == 2:
            is_section_index = True
    logging.info(f"[MENU] rel_path={rel_path}, is_section_index={is_section_index}")
    for title, relative_link in rows:
        # For Home, always use 'index.html'
        if title and title.lower() == 'home':
            target = 'index.html'
        else:
            target = relative_link
        # Compute menu links relative to the current page's directory
    for title, relative_link in rows:
        # For Home, always use 'index.html'
        if title and title.lower() == 'home':
            target = 'index.html'
        else:
            target = relative_link
        # Special-case for section index pages (autogen)
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
        logging.info(f"[MENU] Menu item: title={title}, target={target}, computed_link={link}, rel_path={rel_path}, dirname={os.path.dirname(rel_path)}, is_section_index={is_section_index}")
        menu_items.append({'title': title, 'link': link})
    logging.info(f"[MENU] Final menu_items: {menu_items}")
    conn.close()
    return menu_items

def get_header_partial(context: dict) -> str:
    """Render header partial using Jinja2."""
    env = setup_template_env()
    template = env.get_template('partials/header.html')
    return template.render(**context)

def get_footer_partial(context: dict) -> str:
    """Render footer partial using Jinja2."""
    env = setup_template_env()
    template = env.get_template('partials/footer.html')
    return template.render(**context)

# =========================
# Markdown Conversion
# =========================

def convert_markdown_to_html(md_path: str) -> str:
    """Convert markdown to HTML using markdown-it-py, rewriting local image paths to images/filename.ext without regex."""
    from markdown_it import MarkdownIt
    from mdit_py_plugins.footnote import footnote_plugin
    from mdit_py_plugins.texmath import texmath_plugin
    import os
    import html
    def custom_image_renderer(self, tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrs.get('src', '')
        # Only rewrite if not external or already in images/
        if not (src.startswith('http') or src.startswith('/') or src.startswith('images/')):
            filename = os.path.basename(src)
            src = f'images/{filename}'
        alt = html.escape(token.content)
        return f'<img src="{src}" alt="{alt}">'  # basic fallback
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    md.use(footnote_plugin)
    md.use(texmath_plugin)
    md.add_render_rule('image', custom_image_renderer)
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    html_body = md.render(md_text)
    # Accessibility: Add ARIA roles to elements
    html_body = html_body.replace('<table>', '<table role="table">')
    html_body = html_body.replace('<th>', '<th role="columnheader">')
    html_body = html_body.replace('<td>', '<td role="cell">')
    html_body = html_body.replace('<ul>', '<ul role="list">')
    html_body = html_body.replace('<ol>', '<ol role="list">')
    html_body = html_body.replace('<li>', '<li role="listitem">')
    html_body = html_body.replace('<nav>', '<nav role="navigation">')
    html_body = html_body.replace('<header>', '<header role="banner">')
    html_body = html_body.replace('<footer>', '<footer role="contentinfo">')
    mathjax_script = '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
    html_body += mathjax_script
    return html_body

def convert_markdown_to_html_text(md_text: str) -> str:
    """Convert markdown text to HTML using markdown-it-py, rewriting local image paths to images/filename.ext without regex."""
    from markdown_it import MarkdownIt
    from mdit_py_plugins.footnote import footnote_plugin
    from mdit_py_plugins.texmath import texmath_plugin
    import os
    import html
    def custom_image_renderer(self, tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrs.get('src', '')
        if not (src.startswith('http') or src.startswith('/') or src.startswith('images/')):
            filename = os.path.basename(src)
            src = f'images/{filename}'
        alt = html.escape(token.content)
        return f'<img src="{src}" alt="{alt}">'  # basic fallback
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    md.use(footnote_plugin)
    md.use(texmath_plugin)
    md.add_render_rule('image', custom_image_renderer)
    html_body = md.render(md_text)
    html_body = html_body.replace('<table>', '<table role="table">')
    html_body = html_body.replace('<th>', '<th role="columnheader">')
    html_body = html_body.replace('<td>', '<td role="cell">')
    html_body = html_body.replace('<ul>', '<ul role="list">')
    html_body = html_body.replace('<ol>', '<ol role="list">')
    html_body = html_body.replace('<li>', '<li role="listitem">')
    html_body = html_body.replace('<nav>', '<nav role="navigation">')
    html_body = html_body.replace('<header>', '<header role="banner">')
    html_body = html_body.replace('<footer>', '<footer role="contentinfo">')
    mathjax_script = '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
    html_body += mathjax_script
    return html_body

# =========================
# Page Build Workflow
# =========================

def get_asset_path(asset_type, asset_name, rel_path):
    depth = rel_path.count(os.sep)
    prefix = '../' * depth if depth > 0 else ''
    return f"{prefix}{asset_type}/{asset_name}"

def add_asset_paths(context, rel_path):
    context['css_path'] = get_asset_path('css', 'theme-dark.css', rel_path)
    context['js_path'] = get_asset_path('js', 'main.js', rel_path)
    # Add logo_path for correct logo asset referencing
    logo_file = context.get('site', {}).get('logo', 'static/images/logo.png')
    # Remove 'static/' prefix if present, since assets are in build/images/
    logo_name = os.path.basename(logo_file)
    context['logo_path'] = get_asset_path('images', logo_name, rel_path)
    return context

# Autogenerate index.html for top-level sections from the database
def get_top_level_sections(db_path=None):
    import sqlite3
    logging.info(f"Path to database: {db_path}")
    if db_path is None:
        db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
        logging.info(f"Using default database path: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = "SELECT title, output_path FROM content WHERE is_autobuilt=1 AND output_path LIKE '%/index.html'"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        result = [(row[0], os.path.dirname(row[1])) for row in rows]
        logging.info(f"get_top_level_sections result: {result}")
        return result
    except Exception as e:
        logging.error(f"[ERROR] get_top_level_sections failed: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return []
        
def build_section_indexes():
    config_path = os.path.join(PROJECT_ROOT, '_content.yml')
    config = load_yaml_config(config_path)
    logging.info(f"Config path: {config_path}")
    logging.info(f"File exists: {os.path.exists(config_path)}")
    logging.info(f"File size: {os.path.getsize(config_path) if os.path.exists(config_path) else 'N/A'}")
    toc = config.get('toc', [])
    logging.info(f"Full TOC: {toc}")
    sections = get_top_level_sections()
    debug_path = os.path.join(PROJECT_ROOT, 'debug_sections.txt')
    with open(debug_path, 'w', encoding='utf-8') as dbg:
        dbg.write(f"get_top_level_sections() returned: {sections}\n")
        found_news = False
        for section_title, output_dir in sections:
            dbg.write(f"Processing section: {section_title} at {output_dir}\n")
            if section_title.lower() == 'news':
                found_news = True
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            logging.info(f"[AUTO] Generating section index for: {section_title} at {output_dir}")
            create_section_index_html(section_title, output_dir, {"toc": toc})
        if not found_news:
            dbg.write("[WARNING] News section NOT found in get_top_level_sections()!\n")

def build_all_markdown_files():
    """Build all markdown files using Hugo-style rendering, using first # header as title."""
    config_path = os.path.join(PROJECT_ROOT, '_content.yml')
    config = load_yaml_config(config_path)
    site = config.get('site', {})
    toc = config.get('toc', [])
    footer_text = config.get('footer', {}).get('text', '')
    db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT source_path, output_path, title, mime_type FROM content")
    records = cursor.fetchall()
    # Build homepage from content/index.md to build/index.html
    homepage_md = os.path.join(PROJECT_ROOT, 'content', 'index.md')
    homepage_html = os.path.join(BUILD_HTML_DIR, 'index.html')
    if os.path.exists(homepage_md):
        try:
            with open(homepage_md, 'r', encoding='utf-8') as f:
                md_text = f.read()
            # Use first # header as title
            title = "Home"
            lines = md_text.splitlines()
            body_lines = []
            found_title = False
            for line in lines:
                if not found_title and line.strip().startswith('# '):
                    title = line.strip()[2:].strip()
                    found_title = True
                    continue
                body_lines.append(line)
            body_text = '\n'.join(body_lines)
            html_body = convert_markdown_to_html_text(body_text)
            rel_path_home = 'index.html'
            top_menu = generate_nav_menu({'rel_path': rel_path_home, 'toc': toc})
            if top_menu is None:
                top_menu = []
            rel_path = 'index.html'
            context = {
                'Title': title,
                'Content': html_body,
                'toc': toc,
                'top_menu': top_menu,
                'site': site,
                'footer_text': footer_text,
                'output_file': 'index.html',
            }
            context = add_asset_paths(context, rel_path)
            html_output = render_page(context, 'single.html')
            with open(homepage_html, 'w', encoding='utf-8') as f:
                f.write(html_output)
            logging.info(f"[AUTO] Built homepage: {homepage_html}")
        except Exception as e:
            logging.error(f"Failed to build homepage from {homepage_md}: {e}")
    # Filter for markdown files robustly by extension or mime_type
    for source_path, output_path, db_title, mime_type in records:
        # Skip records with missing source_path or output_path
        if not source_path or not output_path:
            logging.info(f"Skipping record with missing source_path or output_path: title={db_title}, source_path={source_path}, output_path={output_path}")
            continue
        ext = os.path.splitext(source_path)[1].lower()
        # You can extend this list for other MIME types as needed
        if ext == '.md' or (mime_type and 'markdown' in mime_type.lower()):
            # Read markdown from source_path
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    md_text = f.read()
            except Exception as e:
                logging.error(f"Failed to read markdown file {source_path}: {e}")
                continue
            # Extract first # header as title if not present in DB
            title = db_title or "Untitled"
            lines = md_text.splitlines()
            body_lines = []
            found_title = False
            for line in lines:
                if not found_title and line.strip().startswith('# '):
                    if not db_title:
                        title = line.strip()[2:].strip()
                    found_title = True
                    continue  # skip this line
                body_lines.append(line)
            body_text = '\n'.join(body_lines)
            html_body = convert_markdown_to_html(source_path) if not found_title else convert_markdown_to_html_text(body_text)
            # Patch: output single files as folder/index.html
            md_basename = os.path.splitext(os.path.basename(source_path))[0]
            parent_dir = os.path.basename(os.path.dirname(source_path))
            # Only patch if file is in a subfolder and matches parent folder name (e.g. about.md in about/)
            if md_basename == parent_dir:
                output_dir = os.path.join(BUILD_HTML_DIR, parent_dir)
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as dir_err:
                    logging.error(f"[ERROR] Failed to create output directory {output_dir}: {dir_err}")
                output_path_final = os.path.join(output_dir, 'index.html')
                rel_path = os.path.relpath(output_path_final, BUILD_HTML_DIR)
                output_file = 'index.html'
            else:
                output_path_final = output_path
                out_dir = os.path.dirname(output_path_final)
                try:
                    os.makedirs(out_dir, exist_ok=True)
                except Exception as dir_err:
                    logging.error(f"[ERROR] Failed to create output directory {out_dir}: {dir_err}")
                rel_path = os.path.relpath(output_path_final, BUILD_HTML_DIR)
                output_file = os.path.basename(output_path_final)
            logging.info(f"[TEST1] Building page: source_path={source_path}, output_path={output_path_final}, rel_path={rel_path}, title={title}")
            top_menu = generate_nav_menu({'rel_path': rel_path, 'toc': toc})
            if top_menu is None:
                top_menu = []
            logging.info(f"[TEST2] Rendered top_menu for output_file {output_file}: {top_menu}")
            context = {
                'Title': title,
                'Content': html_body,
                'toc': toc,
                'top_menu': top_menu,
                'site': site,
                'footer_text': footer_text,
                'output_file': output_file,
            }
            context = add_asset_paths(context, rel_path)
            # Add download_buttons context for template
            if rel_path == 'index.html':
                page_dir = os.path.join(PROJECT_ROOT, 'build', 'files')
            else:
                page_dir = os.path.join(PROJECT_ROOT, 'build', 'files', os.path.dirname(rel_path))
            context['download_buttons'] = build_download_buttons_context(rel_path, page_dir)
            try:
                html_output = render_page(context, 'single.html')
            except Exception as render_err:
                logging.error(f"[ERROR] Template rendering failed for {source_path}: {render_err}")
                import traceback
                logging.error(traceback.format_exc())
                html_output = None
            if html_output:
                try:
                    with open(output_path_final, 'w', encoding='utf-8') as f:
                        f.write(html_output)
                except Exception as e:
                    logging.error(f"Failed to write HTML file {output_path_final}: {e}")
    conn.close()
    
    copy_static_assets_to_build()
    logging.info("[AUTO] All markdown files built.")

def create_section_index_html(section_title: str, output_dir: str, context: dict):
    """Generate section index.html using section.html template."""
    import logging
    logging.info(f"[DEBUG] create_section_index_html called for: {section_title} -> {output_dir}")
    try:
        section = next((entry for entry in context.get('toc', []) if entry.get('title') == section_title), None)
        children = []
        if section and 'children' in section:
            logging.info(f"[DEBUG] Section found in TOC: {section_title}")
            for entry in section['children']:
                if entry.get('file'):
                    file_path = entry.get('file')
                    base_name = os.path.splitext(os.path.basename(file_path))[0] + '.html'
                    link = base_name
                else:
                    link = slugify(entry.get('title', '')) + '/index.html'
                children.append({
                    'title': entry.get('title', ''),
                    'slug': slugify(entry.get('title', '')),
                    'link': link
                })
            logging.info(f"[DEBUG] Children for {section_title}: {children}")
        else:
            logging.warning(f"[DEBUG] No children found for section: {section_title}")
            children = []
        rel_path = os.path.relpath(os.path.join(output_dir, 'index.html'), BUILD_HTML_DIR)
        # Ensure site.title and site.subtitle are always present
        config_path = os.path.join(PROJECT_ROOT, '_content.yml')
        config = load_yaml_config(config_path)
        site = config.get('site', {})
        footer_text = config.get('footer', {}).get('text', '')
        # Add top_menu to page_context for navigation
        nav_context = {'rel_path': rel_path}
        top_menu = generate_nav_menu(nav_context)
        if top_menu is None:
            top_menu = []
        page_context = {
            'Title': section_title,
            'Children': children,
            'toc': context.get('toc', []),
            'top_menu': top_menu,
            'site': site,
            'footer_text': footer_text,
        }
        # Add download_buttons context for section index page
        if rel_path == 'index.html':
            page_dir = os.path.join(PROJECT_ROOT, 'build', 'files')
        else:
            page_dir = os.path.join(PROJECT_ROOT, 'build', 'files', os.path.dirname(rel_path))
        page_context['download_buttons'] = build_download_buttons_context(rel_path, page_dir)
        page_context = add_asset_paths(page_context, rel_path)
        try:
            env = setup_template_env()
            template = env.get_template('section.html')
            html_output = template.render(**page_context)
        except Exception as render_err:
            logging.error(f"[ERROR] Template rendering failed for {section_title}: {render_err}")
            import traceback
            logging.error(traceback.format_exc())
            html_output = None
        # Ensure output directory exists
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as dir_err:
            logging.error(f"[ERROR] Failed to create output directory {output_dir}: {dir_err}")
        # Write index.html with error logging
        if html_output:
            try:
                with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(html_output)
            except Exception as file_err:
                logging.error(f"[ERROR] Failed to write index.html for {section_title} in {output_dir}: {file_err}")
                import traceback
                logging.error(traceback.format_exc())
    except Exception as e:
        logging.error(f"[ERROR] Failed to create section index for {section_title}: {e}")
        import traceback
        logging.error(traceback.format_exc())
