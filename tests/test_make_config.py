import pytest
import copy
from oerforge import make

def test_merge_export_config():
    global_export = {"types": ["html"], "force": False, "custom_label": "Download"}
    local_export = {"types": ["html", "pdf"], "force": True}
    merged = make.merge_export_config(global_export, local_export)
    assert merged["types"] == ["html", "pdf"]
    assert merged["force"] is True
    assert merged["custom_label"] == "Download"

def test_validate_export_config_valid():
    config = {"types": ["html", "pdf"], "force": True}
    is_valid, errors = make.validate_export_config(config)
    assert is_valid
    assert not errors

def test_validate_export_config_invalid():
    config = {"types": "html", "force": True}
    is_valid, errors = make.validate_export_config(config)
    assert not is_valid
    assert "types must be a list" in errors

def test_walk_toc_with_exports_merging():
    toc = [
        {"title": "Home", "file": "index.md", "export": {"types": ["html"]}},
        {"title": "About", "file": "about.md"}
    ]
    global_export = {"types": ["html", "pdf"], "force": False}
    results = make.walk_toc_with_exports(toc, global_export)
    assert results[0]["export_config"]["types"] == ["html"]
    assert results[1]["export_config"]["types"] == ["html", "pdf"]

def test_get_all_exports_integration():
    content = {
        "export": {"types": ["html", "pdf"], "force": False},
        "toc": [
            {"title": "Home", "file": "index.md", "export": {"types": ["html"]}},
            {"title": "About", "file": "about.md"}
        ]
    }
    results = make.get_all_exports(content)
    assert len(results) == 2
    assert results[0]["is_valid"]
    assert results[1]["is_valid"]