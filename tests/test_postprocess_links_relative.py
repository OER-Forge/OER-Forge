"""
Test post-processing of internal Markdown links to HTML using a mapping, with correct relative path computation.
- Ensures links like [Home](../index.md) are rewritten to ../index.html, respecting author intent.
- Other links should remain correct.
"""
import pytest
from bs4 import BeautifulSoup, Tag
from oerforge.make import postprocess_internal_links
import os

def test_postprocess_internal_links_relative():
    html = '''<html><body>
        <a href="activities.md">Activities</a>
        <a href="../index.md">Home</a>
        <a href="welcome.md">Welcome</a>
    </body></html>'''
    md_to_html_map = {
        "activities.md": "build/activities/activities.html",
        "../index.md": "build/index.html",
        "welcome.md": "build/welcome.html",
        "index.md": "build/index.html"
    }
    # Simulate current output file in 'build/sample-resources/index.html'
    current_output_path = os.path.join("build", "sample-resources", "index.html")
    processed = postprocess_internal_links(html, md_to_html_map, current_output_path)
    soup = BeautifulSoup(processed, "html.parser")
    links = {a.text: a.get('href') for a in soup.find_all("a") if isinstance(a, Tag)}
    assert links["Activities"] == "../activities/activities.html"
    assert links["Home"] == "../index.html"
    assert links["Welcome"] == "../welcome.html"
