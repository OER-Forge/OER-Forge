"""
Test: Minimal MarkdownIt link rewriting for internal .md links
"""
import os
import logging
import pytest
from oerforge.make import convert_markdown_to_html

def test_internal_md_link_rewriting(tmp_path):
    # Minimal markdown with only internal links
    md_text = """
[Activities](activities.md)
[Welcome](welcome.md)
"""
    # Fake content_lookup for .md -> .html mapping
    content_lookup = {
        ("content/activities.md", "activities"): str(tmp_path / "activities.html"),
        ("content/welcome.md", "welcome"): str(tmp_path / "welcome.html"),
    }
    env = {
        'content_lookup': content_lookup,
        'current_output_path': str(tmp_path / "index.html"),
        'get_asset_path': lambda typ, name, out: name,
        'current_source_path': str(tmp_path / "index.md"),
    }
    html = convert_markdown_to_html(md_text, env)
    # Should rewrite .md links to .html
    assert 'href="activities.html"' in html
    assert 'href="welcome.html"' in html
    # Should not contain .md links
    assert '.md"' not in html
