import os
import shutil
import tempfile
import yaml
import pytest
from oerforge import make

def setup_test_content(tmpdir):
    content_dir = os.path.join(tmpdir, 'content')
    os.makedirs(content_dir, exist_ok=True)
    # Create markdown files
    with open(os.path.join(content_dir, 'index.md'), 'w') as f:
        f.write('# Home\nWelcome to the homepage.')
    with open(os.path.join(content_dir, 'about.md'), 'w') as f:
        f.write('# About\nAbout page content.')
    sample_dir = os.path.join(content_dir, 'sample')
    os.makedirs(sample_dir, exist_ok=True)
    # Use the real content for _index.md
    real_index_md = os.path.join(os.path.dirname(__file__), '../content/sample/_index.md')
    with open(os.path.join(sample_dir, '_index.md'), 'w') as f:
        if os.path.exists(real_index_md):
            with open(real_index_md, 'r', encoding='utf-8') as rf:
                f.write(rf.read())
        else:
            f.write('# Sample Resources\n\nExplore sample resources for modern classical mechanics and physics education. Below are some featured pages:\n\n- [Activities](activities.html)\n- [Newton\'s Laws](newton.html)\n- [Welcome](welcome.html)\n\n---\n\nReturn to [Home](../home/index.html)')
    with open(os.path.join(sample_dir, 'newton.md'), 'w') as f:
        f.write('# Newton\nNewton content.')
    with open(os.path.join(sample_dir, 'activities.md'), 'w') as f:
        f.write('# Activities\nActivities content.')
    # Create _content.yml
    toc = [
        {'title': 'Home', 'menu': True, 'file': 'index.md'},
        {'title': 'Sample', 'menu': True, 'slug': 'sample-resources', 'file': 'sample/_index.md', 'children': [
            {'title': "Introduction to Newton's Laws", 'file': 'sample/newton.md', 'menu': False},
            {'title': 'Activities', 'file': 'sample/activities.md', 'menu': False}
        ]},
        {'title': 'About', 'menu': True, 'file': 'about.md'}
    ]
    config = {
        'site': {'title': 'Test Site'},
        'footer': {'text': 'Footer text'},
        'toc': toc
    }
    with open(os.path.join(tmpdir, '_content.yml'), 'w') as f:
        yaml.dump(config, f)
    # Create db/sqlite.db and minimal content table
    db_dir = os.path.join(tmpdir, 'db')
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, 'sqlite.db')
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE IF NOT EXISTS content (source_path TEXT, output_path TEXT, title TEXT, mime_type TEXT)')
    conn.commit()
    conn.close()
    return content_dir

def test_build_output_structure(tmpdir):
    # Setup test content and config
    setup_test_content(tmpdir)
    # Patch PROJECT_ROOT and BUILD_HTML_DIR
    make.PROJECT_ROOT = tmpdir
    make.BUILD_HTML_DIR = os.path.join(tmpdir, 'build')
    # Run build
    make.build_all_markdown_files()
    # Check output files
    assert os.path.exists(os.path.join(tmpdir, 'build', 'index.html'))
    assert os.path.exists(os.path.join(tmpdir, 'build', 'about.html'))
    assert os.path.exists(os.path.join(tmpdir, 'build', 'sample-resources', 'index.html'))
    assert os.path.exists(os.path.join(tmpdir, 'build', 'sample-resources', 'newton.html'))
    assert os.path.exists(os.path.join(tmpdir, 'build', 'sample-resources', 'activities.html'))
    # No auto-generated pages
    # Only files listed in toc should exist
    output_files = []
    for root, dirs, files in os.walk(os.path.join(tmpdir, 'build')):
        for file in files:
            output_files.append(os.path.relpath(os.path.join(root, file), os.path.join(tmpdir, 'build')))
    expected = [
        'index.html',
        'about.html',
        os.path.join('sample-resources', 'index.html'),
        os.path.join('sample-resources', 'newton.html'),
        os.path.join('sample-resources', 'activities.html')
    ]
    assert sorted(output_files) == sorted(expected)

def test_slug_inheritance(tmpdir):
    setup_test_content(tmpdir)
    make.PROJECT_ROOT = tmpdir
    make.BUILD_HTML_DIR = os.path.join(tmpdir, 'build')
    make.build_all_markdown_files()
    # Children should be in parent slug folder
    assert os.path.exists(os.path.join(tmpdir, 'build', 'sample-resources', 'newton.html'))
    assert os.path.exists(os.path.join(tmpdir, 'build', 'sample-resources', 'activities.html'))

def test_no_autogen_navigation(tmpdir):
    setup_test_content(tmpdir)
    make.PROJECT_ROOT = tmpdir
    make.BUILD_HTML_DIR = os.path.join(tmpdir, 'build')
    make.build_all_markdown_files()
    # Navigation is manual, so check that only toc items are present
    output_files = []
    for root, dirs, files in os.walk(os.path.join(tmpdir, 'build')):
        for file in files:
            output_files.append(os.path.relpath(os.path.join(root, file), os.path.join(tmpdir, 'build')))
    # No extra files
    expected = [
        'index.html',
        'about.html',
        os.path.join('sample-resources', 'index.html'),
        os.path.join('sample-resources', 'newton.html'),
        os.path.join('sample-resources', 'activities.html')
    ]
    assert sorted(output_files) == sorted(expected)
    
def test_section_index_content_matches_source(tmpdir):
    # Setup test content and config
    setup_test_content(tmpdir)
    make.PROJECT_ROOT = tmpdir
    make.BUILD_HTML_DIR = os.path.join(tmpdir, 'build')
    make.build_all_markdown_files()
    # Compare content/sample/_index.md and build/sample-resources/index.html
    src_md = os.path.join(tmpdir, 'content', 'sample', '_index.md')
    out_html = os.path.join(tmpdir, 'build', 'sample-resources', 'index.html')
    assert os.path.exists(src_md)
    assert os.path.exists(out_html)
    with open(src_md, 'r', encoding='utf-8') as f:
        src_text = f.read()
    with open(out_html, 'r', encoding='utf-8') as f:
        html_text = f.read()
    # Parse markdown to extract expected headings, paragraphs, and links
    import markdown_it
    md = markdown_it.MarkdownIt()
    tokens = md.parse(src_text)
    found_headings = set()
    found_links = set()
    found_paragraphs = set()
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            heading = tokens[i+1].content.strip()
            found_headings.add(heading)
        if token.type == 'inline' and token.children:
            # Collect link texts and paragraph texts
            for idx, child in enumerate(token.children):
                if child.type == 'link_open':
                    if idx+1 < len(token.children):
                        link_text = token.children[idx+1].content.strip()
                        found_links.add(link_text)
                if child.type == 'text':
                    para_text = child.content.strip()
                    if para_text:
                        found_paragraphs.add(para_text)
    # Assert all headings, links, and paragraphs are present in HTML
    for heading in found_headings:
        assert heading in html_text
    for link_text in found_links:
        assert link_text in html_text
    for para_text in found_paragraphs:
        assert para_text in html_text

def test_sample_resources_index_build_and_log(tmpdir):
    """
    Build the site and check if sample-resources/index.html is created. If not, inspect build.log for missing source file warnings.
    """
    import logging
    setup_test_content(tmpdir)
    # Patch PROJECT_ROOT and BUILD_HTML_DIR
    from oerforge import make
    make.PROJECT_ROOT = tmpdir
    make.BUILD_HTML_DIR = os.path.join(tmpdir, 'build')
    # Set log path and level
    log_dir = os.path.join(tmpdir, 'log')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'build.log')
    make.LOG_PATH = log_path
    logging.basicConfig(filename=log_path, level=logging.DEBUG, force=True)
    # Build
    make.build_all_markdown_files()
    # Check for sample-resources/index.html
    out_html = os.path.join(tmpdir, 'build', 'sample-resources', 'index.html')
    exists = os.path.exists(out_html)
    # Read log
    with open(log_path, 'r', encoding='utf-8') as f:
        log_text = f.read()
    # If file missing, assert log contains warning
    if not exists:
        assert ('Source markdown not found' in log_text) or ('Failed to read markdown file' in log_text), "Missing file should be logged as a warning or error."
    else:
        # If file exists, log should not contain missing file warning for this path
        assert ('sample/_index.md' not in log_text) and ('Source markdown not found' not in log_text), "File built, should not log missing file."