import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from design_systems.dbim import get_profile, is_ready, validate_screens


def test_controlled_text_first_package_and_generic_dependencies_validation():
    profile = get_profile()
    assert profile["manifest"]["approved_for_generation"] is True
    assert profile["manifest"]["generation_scope"] == "controlled_text_first"
    assert is_ready() is True
    for path in profile["manifest"]["assets"]["stylesheets"] + profile["manifest"]["assets"]["scripts"]:
        assert (Path(__file__).resolve().parents[2] / "frontend" / "public" / path.lstrip("/")).exists()
    result = validate_screens([{
        "screen_name": "Test",
        "html": '<html><head><script src="https://cdn.tailwindcss.com"></script></head><body><img src="x"></body></html>',
        "component_ids": ["dbim.missing"],
    }])
    assert result["passed"] is False
    rules = {finding["rule"] for finding in result["findings"]}
    assert {"prohibited-dependency", "approved-component"} <= rules


def test_controlled_fallbacks_must_be_known_and_traceable():
    profile = get_profile()
    assert any(pattern["id"] == "gov.fallback.form" for pattern in profile["fallback_patterns"])
    result = validate_screens([{
        "screen_name": "Application form",
        "html": "<!doctype html><html lang='en'><head><title>Form</title><meta name='viewport' content='width=device-width'></head><body></body></html>",
        "fallback_ids": ["gov.fallback.form", "gov.fallback.unknown"],
    }])
    rules = {finding["rule"] for finding in result["findings"]}
    assert {"controlled-fallback", "fallback-traceability"} <= rules
