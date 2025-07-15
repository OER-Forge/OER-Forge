import os
import logging
from oerforge.logging_utils import setup_logging
from oerforge.db_utils import initialize_database
from oerforge.copyfile import copy_build_to_docs_safe
from oerforge.scan import scan_toc_and_populate_db
from oerforge.export_all import export_all
from oerforge.convert import batch_convert_all_content
from oerforge.make import build_all_markdown_files, create_section_index_html, load_yaml_config

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
print("Project root:", PROJECT_ROOT)
BUILD_FILES_DIR = os.path.join(PROJECT_ROOT, 'build', 'files')
BUILD_HTML_DIR = os.path.join(PROJECT_ROOT, 'build')

def log_directory_contents(directory: str) -> None:
    """Logs all files in the specified directory for debugging purposes."""
    logging.info(f"[DEBUG] Contents of {directory}:")
    for root, _, files in os.walk(directory):
        for name in files:
            logging.info(f"  {os.path.join(root, name)}")

def run_full_workflow() -> None:
    """Runs the complete OERForge build workflow."""
    setup_logging()
    logging.info("Step 1: Initializing database...")
    initialize_database()

    # logging.info("Step 2: Copying project files and static assets...")
    # copy_project_files()
    # log_directory_contents(BUILD_FILES_DIR)

    logging.info("Step 3: Scanning TOC and populating database...")
    scan_toc_and_populate_db('_content.yml')

    logging.info("Step 4: Batch converting all content...")
    batch_convert_all_content()
    
    logging.info("Step 4.5: Exporting all content to DOCX...")
    export_all()

    logging.info("Step 5: Building HTML and section indexes...")
    build_all_markdown_files()
    
    # Autogenerate index.html for top-level sections from the database
    def get_top_level_sections(db_path=None):
        import sqlite3
        print("Path to database:", db_path)
        if db_path is None:
            db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
            print("Using default database path:", db_path)
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

    config_path = os.path.join(PROJECT_ROOT, '_content.yml')
    config = load_yaml_config(config_path)
    print("Config path:", config_path)
    print("File exists:", os.path.exists(config_path))
    print("File size:", os.path.getsize(config_path) if os.path.exists(config_path) else "N/A")
    toc = config.get('toc', [])
    print("Full TOC:", toc)
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

    # Final copy: ensure build/ is copied to docs/ after all build steps
    copy_build_to_docs_safe()

    logging.info("Workflow complete. Please check the build/, docs/, and logs directories for results.")

if __name__ == "__main__":
    run_full_workflow()