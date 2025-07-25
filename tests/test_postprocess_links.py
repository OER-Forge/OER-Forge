"""
Test post-processing of internal Markdown links to HTML using a mapping.
- Ensures all <a href="*.md"> links are rewritten to their HTML equivalents.
- Uses BeautifulSoup for HTML parsing.
- Simulates the mapping as would be retrieved from the database.
"""
import pytest
from bs4 import BeautifulSoup, Tag
from oerforge.make import postprocess_internal_links

def test_postprocess_internal_links():
    html = '''<html><body>
        <a href="about.md">About</a>
        <a href="activities.md">Activities</a>
        <a href="https://external.com/page">External</a>
    </body></html>'''
    md_to_html_map = {
        "about.md": "about.html",
        "activities.md": "activities.html"
    }
    processed = postprocess_internal_links(html, md_to_html_map)
    soup = BeautifulSoup(processed, "html.parser")
    links = {a.text: a.get('href') for a in soup.find_all("a") if isinstance(a, Tag)}
    assert links["About"] == "about.html"
    assert links["Activities"] == "activities.html"
    assert links["External"] == "https://external.com/page"
