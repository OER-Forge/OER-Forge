"""Unit tests for the oerforge.make module."""

import pytest
from oerforge import make

def test_slugify():
    """
    Test the slugify function to ensure it converts strings to URL-friendly slugs.
    """
    assert make.slugify("Hello World!") == "hello-world"
    assert make.slugify("A  B  C") == "a-b-c"

def test_merge_export_config():
    """
    Test the merge_export_config function to verify correct merging of export configurations.
    """
    global_export = {"types": ["html"], "foo": 1}
    local_export = {"foo": 2}
    merged = make.merge_export_config(global_export, local_export)
    assert merged["foo"] == 2
    assert merged["types"] == ["html"]

# Integration tests can use tmp_path and mock file/DB access as needed.