import os
import logging
from oerforge.db_utils import initialize_database
from oerforge.scan import scan_toc_and_populate_db
from oerforge.convert import batch_convert_all_content
from oerforge.make import build_all_markdown_files
from oerforge.export_all import export_all
from oerforge.copyfile import copy_build_to_docs

#================================================================
# Directories for builds and file storage
# Not checked for changes, leave alone for now
#================================================================

BUILD_DIR = 'build'
FILES_DIR = 'files'
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_FILES_DIR = os.path.join(PROJECT_ROOT, BUILD_DIR, FILES_DIR)
BUILD_HTML_DIR = os.path.join(PROJECT_ROOT, BUILD_DIR)

#================================================================
# Workflow for scanning, converting, and building the basic site
# No Automatic WCAG Validation
#================================================================

def run() -> None:
    """Runs the complete OERForge build workflow."""
    
    logging.info("Step 1: Initializing database...")
    initialize_database()

    logging.info("Step 2: Scanning TOC and populating database...")
    scan_toc_and_populate_db('_content.yml')

    logging.info("Step 3: Batch converting all content...")
    batch_convert_all_content()
    
    logging.info("Step 4: Exporting all content to build/...")
    export_all()

    logging.info("Step 5: Building HTML and section indexes...")
    build_all_markdown_files()

    print("Step 6: Copying build/ to docs/ for publishing...")
    copy_build_to_docs()

    logging.info("Workflow complete. Please check the build/, docs/, and logs directories for results.")

if __name__ == "__main__":
    run()