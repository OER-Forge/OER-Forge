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
from oerforge import db_utils

BUILD_DIR = 'build'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_HTML_DIR = os.path.join(PROJECT_ROOT, BUILD_DIR)

__all__ = [
    "copy_to_build",
    "copy_build_to_docs_safe",
    "ensure_dir",
    "create_nojekyll",
    "copy_build_to_docs"
]

def get_project_root():
    """
    Get the project root directory, compatible with both import and direct execution.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = get_project_root()
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
def copy_to_build(src_path, dst_dir=None):
    """
    Copy any source file to the build/files directory (or specified dst_dir).
    Returns the destination path.
    """
    if dst_dir is None:
        dst_dir = CONTENT_DST
    ensure_dir(dst_dir)
    filename = os.path.basename(src_path)
    dst_path = os.path.join(dst_dir, filename)
    shutil.copy2(src_path, dst_path)
    logging.info(f"Copied {src_path} to {dst_path}")
    return dst_path
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

def copy_static_assets_to_build(asset_types=None):
    """
    Copy static assets (CSS, JS, images) from static/ to build/.
    Extensible for new asset types.
    """
    if asset_types is None:
        asset_types = ['css', 'js', 'images']
    for asset in asset_types:
        src = os.path.join(PROJECT_ROOT, 'static', asset)
        dst = os.path.join(BUILD_HTML_DIR, asset)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        if os.path.exists(src):
            shutil.copytree(src, dst)
            logging.info(f"Copied {src} to {dst}")
        else:
            logging.warning(f"Source directory not found: {src}")
    logging.info("[ASSET] Static assets copied to build/.")

def copy_db_images_to_build():
    """
    Copy all images referenced in the DB from their source location to build/images/.
    Only copies images where is_image=1 and is_remote=0.
    """
    db_path = os.path.join(PROJECT_ROOT, 'db', 'sqlite.db')
    image_records = db_utils.get_records(
        'files',
        where_clause="is_image=1 AND is_remote=0",
        db_path=db_path
    )
    images_dir = os.path.join(BUILD_HTML_DIR, 'images')
    os.makedirs(images_dir, exist_ok=True)
    for rec in image_records:
        src = rec.get('absolute_path') or rec.get('relative_path')
        if src and os.path.exists(src):
            dst = os.path.join(images_dir, os.path.basename(src))
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                logging.info(f"[DB-IMG] Copied image {src} to {dst}")
        else:
            logging.warning(f"[DB-IMG] Image not found for copying: {src}")
           
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Copy project files and assets for deployment.")
    parser.add_argument("--copy-to-build", metavar="SRC_PATH", help="Copy a file to build/files/")
    parser.add_argument("--copy-build-to-docs", action="store_true", help="Copy build/ to docs/ (destructive)")
    parser.add_argument("--copy-build-to-docs-safe", action="store_true", help="Copy build/ to docs/ (non-destructive)")
    parser.add_argument("--create-nojekyll", action="store_true", help="Create .nojekyll in build/")
    args = parser.parse_args()

    if args.copy_to_build:
        result = copy_to_build(args.copy_to_build)
        print(f"Copied to: {result}")
    if args.copy_build_to_docs:
        copy_build_to_docs()
        print("Copied build/ to docs/ (destructive)")
    if args.copy_build_to_docs_safe:
        copy_build_to_docs_safe()
        print("Copied build/ to docs/ (non-destructive)")
    if args.create_nojekyll:
        create_nojekyll(NOJEKYLL_PATH)
        print(f"Created .nojekyll at {NOJEKYLL_PATH}")