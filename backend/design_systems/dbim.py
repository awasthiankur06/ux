"""DBIM package loading and deterministic pre-check validation.

The package intentionally starts unavailable. It may only be enabled after an
approved DBIM distribution, source details and reuse review are recorded.
"""
import json
import re
from pathlib import Path

DBIM_DIR = Path(__file__).with_name("dbim")


def _load(name: str) -> dict:
    with (DBIM_DIR / name).open(encoding="utf-8") as file:
        return json.load(file)


def get_profile() -> dict:
    manifest = _load("manifest.json")
    catalogue = _load("components.json")
    return {
        "manifest": manifest,
        "components": catalogue.get("components", []),
        "patterns": _load("patterns.json").get("patterns", []),
        "validation_rules": _load("validation_rules.json"),
    }


def is_ready() -> bool:
    """Whether an approved DBIM package is present for live Gov generation."""
    profile = get_profile()
    return bool(profile["manifest"].get("approved_for_generation") and profile["components"])


def validate_screens(screens: list[dict]) -> dict:
    """Return deterministic findings. This is a pre-check, never a certificate."""
    profile = get_profile()
    manifest = profile["manifest"]
    rules = profile["validation_rules"]
    approved_ids = {component.get("id") for component in profile["components"]}
    findings = []
    rule_catalogue = {rule["id"]: rule for rule in rules.get("rules", [])}

    if not manifest.get("approved_for_generation"):
        findings.append({
            "severity": "error",
            "rule": "dbim-package-approved",
            "message": "The approved DBIM distribution has not yet been installed and verified.",
        })

    for screen in screens:
        name = screen.get("screen_name", "Unnamed screen")
        html = screen.get("html", "")
        lower_html = html.lower()
        for marker in rules["prohibited_markers"]:
            if marker in lower_html:
                findings.append({"severity": "error", "screen_name": name, "rule": "prohibited-dependency", "message": f"Prohibited dependency: {marker}"})
        if not re.search(r"<!doctype\s+html", html, re.I):
            findings.append({"severity": "warning", "screen_name": name, "rule": "html5-doctype", "message": "HTML5 doctype is missing."})
        if not re.search(r"<html[^>]*\blang=[\"'][^\"']+[\"']", html, re.I):
            findings.append({"severity": "warning", "screen_name": name, "rule": "document-language", "message": "Document language is missing."})
        if not re.search(r"<title>[^<]+</title>", html, re.I):
            findings.append({"severity": "warning", "screen_name": name, "rule": "document-title", "message": "Document title is missing."})
        if not re.search(r"<meta[^>]+name=[\"']viewport[\"']", html, re.I):
            findings.append({"severity": "warning", "screen_name": name, "rule": "responsive-viewport", "message": "Responsive viewport meta tag is missing."})
        for asset in manifest["assets"]["stylesheets"]:
            if asset not in html:
                findings.append({"severity": "error", "screen_name": name, "rule": "dbim-stylesheet", "message": f"Required local DBIM stylesheet is not included: {asset}"})
        for asset in manifest["assets"]["scripts"]:
            if asset not in html:
                findings.append({"severity": "warning", "screen_name": name, "rule": "dbim-script", "message": f"Required local DBIM script is not included: {asset}"})
        heading_levels = [int(level) for level in re.findall(r"<h([1-6])\b", html, re.I)]
        if heading_levels and any(next_level > level + 1 for level, next_level in zip(heading_levels, heading_levels[1:])):
            findings.append({"severity": "warning", "screen_name": name, "rule": "heading-order", "message": "Heading levels skip a hierarchy level."})
        for image in re.findall(r"<img\b[^>]*>", html, re.I):
            if not re.search(r"\balt=[\"'][^\"']*[\"']", image, re.I):
                findings.append({"severity": "warning", "screen_name": name, "rule": "image-alt", "message": "An image lacks alternative text."})
        for source in re.findall(r"(?:src|href)=[\"']([^\"']+)[\"']", html, re.I):
            if source.startswith("http://"):
                findings.append({"severity": "warning", "screen_name": name, "rule": "secure-link", "message": f"Insecure HTTP reference: {source}"})
        for control in re.findall(r"<(?:input|select|textarea)\b[^>]*>", html, re.I):
            control_id = re.search(r"\bid=[\"']([^\"']+)[\"']", control, re.I)
            aria_label = re.search(r"\baria-label=[\"'][^\"']+[\"']", control, re.I)
            if control_id and not aria_label and not re.search(rf"<label[^>]+for=[\"']{re.escape(control_id.group(1))}[\"']", html, re.I):
                findings.append({"severity": "warning", "screen_name": name, "rule": "form-label", "message": f"Control '{control_id.group(1)}' has no associated label."})
        for button in re.findall(r"<button\b[^>]*>(.*?)</button>", html, re.I | re.S):
            if not re.sub(r"<[^>]+>", "", button).strip():
                findings.append({"severity": "warning", "screen_name": name, "rule": "button-name", "message": "A button has no accessible text label."})
        for component_id in screen.get("component_ids", []):
            if component_id not in approved_ids:
                findings.append({"severity": "error", "screen_name": name, "rule": "approved-component", "message": f"Unknown or unapproved DBIM component: {component_id}"})
            elif f'data-dbim-component-id="{component_id}"' not in html and f"data-dbim-component-id='{component_id}'" not in html:
                findings.append({"severity": "warning", "screen_name": name, "rule": "component-traceability", "message": f"Component ID is declared but not marked in HTML: {component_id}"})

    for finding in findings:
        rule = rule_catalogue.get(finding["rule"])
        if rule:
            finding["rule_title"] = rule["title"]
            finding["source"] = rule["source"]

    counts = {severity: sum(f["severity"] == severity for f in findings) for severity in ("error", "warning", "info")}
    manual_review = [
        {"rule": rule["id"], "title": rule["title"], "requirement": rule["requirement"], "source": rule["source"]}
        for rule in rules.get("rules", []) if rule.get("automation") == "manual_review"
    ]
    return {
        "profile": "gigw_3_dbim",
        "profile_label": rules.get("profile_label", "Gov Compliance - Design Pre-check"),
        "pre_check_only": True,
        "disclaimer": rules.get("disclaimer"),
        "passed": counts["error"] == 0,
        "summary": counts,
        "findings": findings,
        "manual_review": manual_review,
    }
