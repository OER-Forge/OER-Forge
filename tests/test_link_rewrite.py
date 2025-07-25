"""
Test for Markdown link rewriting in convert_markdown_to_html.
Ensures internal .md links are rewritten to correct output HTML paths using the content_lookup DB mapping.
"""
import os
import pytest
from oerforge.make import convert_markdown_to_html

def test_rewrite_internal_md_links():
    # Simulate DB mapping: content_lookup
    content_lookup = {
        ("content/sample/activities.md", "activities"): "build/sample-resources/activities/activities.html",
        ("content/sample/newton.md", "newton"): "build/sample-resources/newton/newton.html",
        ("content/sample/welcome.md", "welcome"): "build/sample-resources/welcome/welcome.html",
    }
    current_output_path = "build/sample-resources/index.html"
    md_env = {
        "content_lookup": content_lookup,
        "current_output_path": current_output_path,
        "get_asset_path": lambda typ, name, out: f"static/{typ}/{name}",
    }
    md_text = (
        "- [Activities](activities.md)\n"
        "- [Newton's Laws](newton.md)\n"
        "- [Welcome](welcome.md)\n"
    )
    import logging
    logging.basicConfig(level=logging.DEBUG)
    html = convert_markdown_to_html(md_text, md_env)
    print("[TEST-HTML]", html)
    # Check that .md links are rewritten to correct relative HTML paths
    assert "href=\"activities/activities.html\"" in html or print("[FAIL] activities.md not rewritten")
    assert "href=\"newton/newton.html\"" in html or print("[FAIL] newton.md not rewritten")
    assert "href=\"welcome/welcome.html\"" in html or print("[FAIL] welcome.md not rewritten")
    # Should not contain .md links
    assert ".md\"" not in html or print("[FAIL] .md links still present")
