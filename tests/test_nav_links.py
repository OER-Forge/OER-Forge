import pytest
import yaml
import os
from oerforge.make import build_all_markdown_files

def test_top_level_nav_links(tmp_path, caplog):
    """
    Test that top-level nav links in the menu point to the correct HTML file locations.
    """
    # Setup: create a minimal _content.yml and content dir
    content_yml = tmp_path / '_content.yml'
    content = {
        'toc': [
            {'title': 'Home', 'menu': True, 'file': 'index.md', 'slug': 'main'},
            {'title': 'Sample', 'menu': True, 'slug': 'sample-resources', 'file': 'sample/index.md',
             'children': [
                 {'title': "Introduction to Newton's Laws", 'file': 'sample/newton.md', 'slug': 'main', 'menu': True},
                 {'title': "Sample Activities", 'file': 'sample/activities.md', 'slug': 'activities', 'menu': True},
             ]},
            {'title': 'About', 'menu': True, 'file': 'about.md', 'slug': 'main'},
        ]
    }
    content_yml.write_text(yaml.dump(content))
    content_dir = tmp_path / 'content'
    content_dir.mkdir()
    (content_dir / 'about.md').write_text('# About')
    (content_dir / 'index.md').write_text('# Home')
    sample_dir = content_dir / 'sample'
    sample_dir.mkdir()
    (sample_dir / 'index.md').write_text('# Sample Index')
    (sample_dir / 'newton.md').write_text('# Newton')
    (sample_dir / 'activities.md').write_text('# Activities')

    with caplog.at_level('DEBUG'):
        build_all_markdown_files()

    # Collect nav log messages
    nav_logs = [r.getMessage() for r in caplog.records if '[NAV]' in r.getMessage()]

    # Home (slug: main, file: index.md) should be at './index.html'
    home_link = next((msg for msg in nav_logs if ", file='index.md'" in msg), None)
    assert home_link is not None, 'Home nav link not found in logs.'
    assert ", link='./index.html'" in home_link, f'Home nav link incorrect: {home_link}'

    # About (slug: main, file: about.md) should be at './about.html'
    about_link = next((msg for msg in nav_logs if ", file='about.md'" in msg), None)
    assert about_link is not None, 'About nav link not found in logs.'
    assert ", link='./about.html'" in about_link, f'About nav link incorrect: {about_link}'

    # Sample (slug: sample-resources, file: sample/index.md) should be at './sample-resources/index.html'
    sample_link = next((msg for msg in nav_logs if ", file='sample/index.md'" in msg), None)
    assert sample_link is not None, 'Sample nav link not found in logs.'
    assert ", link='./sample-resources/index.html'" in sample_link, f'Sample nav link incorrect: {sample_link}'

    # Child with slug: main (should not be allowed, expect error or warning in logs)
    child_main_link = next((msg for msg in nav_logs if ", file='sample/newton.md'" in msg), None)
    assert child_main_link is not None, 'Child nav link not found in logs.'
    # Should not resolve to './index.html' or './main.html' (reserved slug misused)
    assert './index.html' not in child_main_link and './main.html' not in child_main_link, \
        f"Child nav link incorrectly used reserved slug: {child_main_link}"
