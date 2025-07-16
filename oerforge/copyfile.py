def copy_build_to_docs_safe():
    """
    Non-destructively copy everything from build/ to docs/.
    Creates docs/ if missing, copies files over themselves, does not remove docs/.
    """
    DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')
    BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
    for root, dirs, files in os.walk(BUILD_DIR):
        rel_path = os.path.relpath(root, BUILD_DIR)
        target_dir = os.path.join(DOCS_DIR, rel_path) if rel_path != '.' else DOCS_DIR
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(target_dir, file)
            shutil.copy2(src_file, dst_file)
"""
Module to copy project content and static assets into build directories for deployment.

Features:
- Copies all contents of 'content/' to 'build/files/'
- Copies 'static/css/' to 'build/css/' and 'static/js/' to 'build/js/'
- Creates target directories if they do not exist
- Overwrites files each time it is called
- Creates 'build/.nojekyll' to prevent GitHub Pages from running Jekyll

Usage:
    from oerforge.copyfile import copy_project_files
    copy_project_files()
"""

import os
import shutil
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')
CONTENT_SRC = os.path.join(PROJECT_ROOT, 'content')
CONTENT_DST = os.path.join(BUILD_DIR, 'files')
CSS_SRC = os.path.join(PROJECT_ROOT, 'static', 'css')
CSS_DST = os.path.join(BUILD_DIR, 'css')
JS_SRC = os.path.join(PROJECT_ROOT, 'static', 'js')
JS_DST = os.path.join(BUILD_DIR, 'js')
NOJEKYLL_PATH = os.path.join(BUILD_DIR, '.nojekyll')
LOG_PATH = os.path.join(PROJECT_ROOT, 'log/build.log')

def ensure_dir(path):
    """
    Ensure that a directory exists.
    """
    if not os.path.exists(path):
        logging.debug(f"Creating directory: {path}")
    os.makedirs(path, exist_ok=True)


def create_nojekyll(path):
    """
    Create an empty .nojekyll file at the given path.
    """
    with open(path, 'w') as f:
        f.write('')
    logging.info(f"Created .nojekyll at {path}")
    
def copy_build_to_docs():
    """
    Copy everything from build/ to docs/, including .nojekyll
    """
    DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')
    logging.info(f"Copying all build/ contents to docs/: {BUILD_DIR} -> {DOCS_DIR}")
    if os.path.exists(DOCS_DIR):
        logging.debug(f"Removing existing docs directory: {DOCS_DIR}")
        shutil.rmtree(DOCS_DIR)
    shutil.copytree(BUILD_DIR, DOCS_DIR)
    logging.info(f"Copied build/ to docs/")