import unittest
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.texmath import texmath_plugin

# Import the function to test from make.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../oerforge')))
from make import convert_markdown_to_html_text

def minimal_rewrite_md_links(md_text, target_ext='.html'):
    """Minimal version of the rewrite_md_links logic for isolated testing."""
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    md.use(footnote_plugin)
    md.use(texmath_plugin)
    tokens = md.parse(md_text)
    # Try to rewrite links as in the main code
    for token in tokens:
        if token.type == 'inline' and token.children:
            for child in token.children:
                if child.type == 'link_open':
                    for i, attr in enumerate(child.attrs):
                        name, value = attr
                        if name == 'href' and value.endswith('.md') and not value.startswith('http'):
                            child.attrs[i] = [name, value[:-3] + target_ext]
    html = md.renderer.render(tokens, md.options, {})
    return html


class TestMarkdownLinkRewrite(unittest.TestCase):
    def test_md_links_to_html(self):
        from oerforge.make import convert_markdown_to_html_text
        md = """
[Internal](foo.md)
[External](http://example.com)
[Image](bar.png)
"""
        html = convert_markdown_to_html_text(md, referenced_page="test.md", rel_path="index.html")
        self.assertIn('href="foo.html"', html)
        self.assertIn('href="http://example.com"', html)
        self.assertIn('href="bar.png"', html)

    def test_no_unpack_error(self):
        from oerforge.make import convert_markdown_to_html_text
        md = "[Test](foo.md)"
        try:
            html = convert_markdown_to_html_text(md, referenced_page="test.md", rel_path="index.html")
        except ValueError as e:
            self.fail(f"Unpacking error occurred: {e}")

if __name__ == '__main__':
    unittest.main()
