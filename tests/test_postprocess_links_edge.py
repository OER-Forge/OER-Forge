"""
Test post-processing of internal Markdown links to HTML using a mapping, including edge cases.
- Ensures all <a href="*.md"> links are rewritten to their HTML equivalents if mapping exists.
- Handles anchors, query strings, subdirectories, and missing mappings.
"""
import pytest
from bs4 import BeautifulSoup, Tag
from oerforge.make import postprocess_internal_links

def test_postprocess_internal_links_edge_cases():
    html = '''<html><body>
        <a href="about.md">About</a>
        <a href="activities.md#section1">Activities Section</a>
        <a href="newton.md?ref=nav">Newton Query</a>
        <a href="sample/welcome.md">Welcome</a>
        <a href="missing.md">Missing</a>
        <a href="https://external.com/page">External</a>
    </body></html>'''
    md_to_html_map = {
        "about.md": "about.html",
        "activities.md": "activities.html",
        "newton.md": "newton.html",
        "sample/welcome.md": "sample/welcome.html"
    }
    processed = postprocess_internal_links(html, md_to_html_map)
    soup = BeautifulSoup(processed, "html.parser")
    links = {a.text: a.get('href') for a in soup.find_all("a") if isinstance(a, Tag)}
    assert links["About"] == "about.html"
    # Edge case: anchor, should not rewrite unless mapping includes anchor
    assert links["Activities Section"] == "activities.md#section1"
    # Edge case: query string, should not rewrite unless mapping includes query
    assert links["Newton Query"] == "newton.md?ref=nav"
    # Subdirectory mapping
    assert links["Welcome"] == "sample/welcome.html"
    # Missing mapping: should remain unchanged
    assert links["Missing"] == "missing.md"
    # External link
    assert links["External"] == "https://external.com/page"
