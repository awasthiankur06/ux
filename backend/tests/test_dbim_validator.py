import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from design_systems.dbim import get_profile, is_ready, validate_screens


def test_incomplete_dbim_package_and_generic_dependencies_validation():
    profile = get_profile()
    assert profile["manifest"]["approved_for_generation"] is False
    assert is_ready() is False
    for path in profile["manifest"]["assets"]["stylesheets"] + profile["manifest"]["assets"]["scripts"]:
        assert (Path(__file__).resolve().parents[2] / "frontend" / "public" / path.lstrip("/")).exists()
    result = validate_screens([{
        "screen_name": "Test",
        "html": '<html><head><script src="https://cdn.tailwindcss.com"></script></head><body><img src="x"></body></html>',
        "component_ids": ["dbim.missing"],
    }])
    assert result["passed"] is False
    rules = {finding["rule"] for finding in result["findings"]}
    assert {"dbim-package-approved", "prohibited-dependency", "approved-component"} <= rules
