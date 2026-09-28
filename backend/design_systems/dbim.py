"""DBIM package loading and deterministic pre-check validation.

The package intentionally starts unavailable. It may only be enabled after an
approved DBIM distribution, source details and reuse review are recorded.
"""
import json
import re
from pathlib import Path

DBIM_DIR = Path(__file__).with_name("dbim")

FINDING_ACTIONS = {
    "dbim-page-shell": ("header, nav, footer", "Restore the DBIM global header, primary navigation, skip-to-main link, main landmark, and standard footer. Preserve the approved content."),
    "heading-order": ("h1, h2, h3", "Correct the heading hierarchy: use one page h1 and do not skip heading levels."),
    "image-alt": ("img", "Add concise, meaningful alternative text to every informative image; keep decorative images appropriately marked."),
    "form-label": ("input, select, textarea", "Add a visible label or programmatic aria-label for every form control, preserving the existing DBIM form styling."),
    "button-name": ("button", "Give each button a clear accessible name while preserving the approved DBIM/Bootstrap button classes."),
    "dbim-colour-token": ("body", "Replace custom colours with approved local DBIM/Bootstrap semantic classes such as bg-primary, text-primary, btn-primary, alert-* or border-*."),
    "citizen-copy": ("main", "Replace implementation or approval language with natural citizen-facing service content. Keep review details only in metadata."),
    "remote-preview-image": ("img", "Replace the remote preview image with a user-provided approved asset, or retain it only as a clearly reviewed preview image with accurate alt text."),
    "dbim-stylesheet": ("head", "Include the required local DBIM stylesheet links and retain local-only DBIM styling."),
    "dbim-script": ("head", "Include the required local DBIM behaviour bundle for interactive DBIM components."),
}


def _decorate_finding(finding: dict) -> None:
    selector, suggestion = FINDING_ACTIONS.get(finding["rule"], ("main", "Resolve this finding while preserving the approved DBIM page shell and local semantic styles."))
    control = re.search(r"Control '([^']+)'", finding.get("message", ""))
    if control:
        selector = f"#{control.group(1)}"
    finding["selector"] = selector
    finding["suggested_feedback"] = suggestion


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
        "fallback_patterns": _load("fallback_patterns.json").get("patterns", []),
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
    approved_fallback_ids = {pattern.get("id") for pattern in profile["fallback_patterns"]}
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
        inline_colour = re.search(r"\bstyle\s*=\s*([\"'])[^\"']*(?:color\s*:|background(?:-color)?\s*:|border-color\s*:)", html, re.I)
        style_block_colour = re.search(r"<style\b[^>]*>.*?(?:color\s*:|background(?:-color)?\s*:|border-color\s*:)", html, re.I | re.S)
        if inline_colour or style_block_colour:
            findings.append({"severity": "error", "screen_name": name, "rule": "dbim-colour-token", "message": "Use local DBIM/Bootstrap semantic colour classes instead of custom inline or embedded colour styling."})
        if re.search(r"awaiting\s+(?:branding|approval|confirmation)|official\s+image\s+required|manual\s+review|\bplaceholder\b", re.sub(r"<[^>]+>", " ", html), re.I):
            findings.append({"severity": "error", "screen_name": name, "rule": "citizen-copy", "message": "Implementation, approval or placeholder instructions must not appear in citizen-facing screen copy."})
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
        for image_source in re.findall(r"<img\b[^>]*\bsrc=[\"'](https://[^\"']+)[\"'][^>]*>", html, re.I):
            if not image_source.startswith("https://images.unsplash.com/"):
                findings.append({"severity": "error", "screen_name": name, "rule": "remote-preview-image", "message": f"Unapproved remote image source: {image_source}"})
            else:
                findings.append({"severity": "warning", "screen_name": name, "rule": "remote-preview-image", "message": "Remote preview image requires rights and production-replacement review."})
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
        required_shell = ("dbim.header.global", "dbim.navigation.primary", "dbim.footer.standard")
        missing_shell = [component_id for component_id in required_shell if f'data-dbim-component-id="{component_id}"' not in html and f"data-dbim-component-id='{component_id}'" not in html]
        if missing_shell:
            findings.append({"severity": "error", "screen_name": name, "rule": "dbim-page-shell", "message": f"Required DBIM page shell is incomplete: {', '.join(missing_shell)}"})
        for fallback_id in screen.get("fallback_ids", []):
            if fallback_id not in approved_fallback_ids:
                findings.append({"severity": "error", "screen_name": name, "rule": "controlled-fallback", "message": f"Unknown controlled fallback: {fallback_id}"})
            elif f'data-gov-fallback-id="{fallback_id}"' not in html and f"data-gov-fallback-id='{fallback_id}'" not in html:
                findings.append({"severity": "warning", "screen_name": name, "rule": "fallback-traceability", "message": f"Fallback ID is declared but not marked in HTML: {fallback_id}"})

    for finding in findings:
        _decorate_finding(finding)
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
