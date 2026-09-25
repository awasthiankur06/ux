import json
import os
from agents import run_llm_agent, _parse_json
from crawler import crawl_site, capture_screenshot, summarize_pages
from design_systems.dbim import get_profile

MODEL_CHOICES = {
    "openai": ["gpt-5.4", "gpt-5.4-mini", "gpt-5.6-terra"],
    "anthropic": ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
    "ey_incubator": ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
}


def get_model_choices(settings: dict | None = None) -> dict:
    choices = {provider: list(models) for provider, models in MODEL_CHOICES.items()}
    configured_models = (((settings or {}).get("provider_configs") or {}).get("ey_incubator") or {}).get("models")
    if configured_models:
        choices["ey_incubator"] = configured_models
    return choices


def resolve_model(agent_doc: dict, settings: dict):
    provider = agent_doc.get("model_provider") or settings.get("default_provider", "openai")
    model = agent_doc.get("model_name") or settings.get("default_model", "gpt-5.4")
    return provider, model


def topo_levels(nodes: list, edges: list) -> list:
    node_ids = [n["id"] for n in nodes]
    incoming = {nid: set() for nid in node_ids}
    for e in edges:
        if e.get("target") in incoming and e.get("source") in incoming:
            incoming[e["target"]].add(e["source"])
    levels, done, remaining = [], set(), set(node_ids)
    while remaining:
        ready = [nid for nid in remaining if incoming[nid] <= done]
        if not ready:
            ready = list(remaining)
        levels.append([n for n in nodes if n["id"] in ready])
        done |= set(ready)
        remaining -= set(ready)
    return levels


def node_condition_met(node: dict, has_srs: bool, has_url: bool) -> bool:
    cond = node.get("condition", "always")
    if cond == "requires_srs":
        return has_srs
    if cond == "requires_url":
        return has_url
    return True


async def run_orchestrator_plan(agent_doc: dict, settings: dict, run_id: str, has_srs: bool, has_url: bool, crawl_depth: str) -> dict:
    provider, model = resolve_model(agent_doc, settings)
    user = f"SRS provided: {has_srs}. Website URL provided: {has_url}. Crawl depth requested: {crawl_depth}."
    raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, user, f"{run_id}-orchestrator", settings)
    return _parse_json(raw)


async def execute_node(agent_name: str, agent_doc: dict, settings: dict, run_id: str, context: dict) -> dict:
    if agent_name == "WEB_CRAWLER":
        pages = await crawl_site(context["url"], multi_page=(context["crawl_depth"] == "multi"))
        screenshot = await capture_screenshot(context["url"])
        return {"kind": "crawl_data", "value": {"pages": pages, "screenshot_b64": screenshot}}

    provider, model = resolve_model(agent_doc, settings)

    if agent_name == "SRS_ANALYZER":
        raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, context["srs_text"][:12000], f"{run_id}-srs", settings)
        return {"kind": "srs_analysis", "value": _parse_json(raw)}

    if agent_name == "BUSINESS_PROCESS_ANALYST":
        crawl = context.get("crawl_data")
        crawl_summary = summarize_pages(crawl["pages"]) if crawl else None
        srs_analysis = context.get("srs_analysis")
        user = f"SRS analysis: {json.dumps(srs_analysis) if srs_analysis else 'None provided.'}\n\nCrawled site summary: {crawl_summary or 'None provided.'}"
        raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, user, f"{run_id}-bpa", settings)
        return {"kind": "business_flow", "value": _parse_json(raw)}

    if agent_name == "UX_CRITIQUE":
        crawl = context.get("crawl_data")
        crawl_summary = summarize_pages(crawl["pages"]) if crawl else ""
        has_screenshot = bool(crawl and crawl.get("screenshot_b64"))
        user = f"Screenshot captured: {has_screenshot}\n\n{crawl_summary[:10000]}"
        raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, user, f"{run_id}-uxcritique", settings)
        return {"kind": "ux_rating", "value": _parse_json(raw)}

    # generic custom agent node
    user = (
        f"SRS analysis: {json.dumps(context.get('srs_analysis')) if context.get('srs_analysis') else 'None.'}\n\n"
        f"Crawl data available: {bool(context.get('crawl_data'))}\n\n"
        f"Business flow so far: {json.dumps(context.get('business_flow')) if context.get('business_flow') else 'None.'}"
    )
    raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, user, f"{run_id}-{agent_name}", settings)
    return {"kind": "custom", "value": raw}


def summarize_result(kind: str, value) -> str:
    if kind == "srs_analysis":
        return value.get("summary", "") if isinstance(value, dict) else ""
    if kind == "crawl_data":
        return f"Fetched {len(value.get('pages', []))} page(s)."
    if kind == "business_flow":
        return f"{len(value.get('happy_path', []))} screens mapped."
    if kind == "ux_rating":
        return f"Overall score: {value.get('overall_score', 'N/A')}"
    return str(value)[:200]


async def run_wireframe_generation(agent_doc: dict, settings: dict, run_id: str, happy_path: list, brand_reference: str | None) -> list:
    provider, model = resolve_model(agent_doc, settings)
    brand_clause = f"\n\nBrand reference provided by the user - reuse its colors/fonts/style consistently:\n{brand_reference}" if brand_reference else ""
    user = (
        "Generate exactly one complete screen for EVERY approved happy-path item below. "
        "Return the same number of screens, retain each screen_name exactly, and keep their order. "
        "Never merge, omit or replace a happy-path screen.\n\n"
        + json.dumps(happy_path)
        + brand_clause
    )
    raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, user, f"{run_id}-wireframe", settings)
    return await _complete_screen_set(
        agent_doc, settings, run_id, happy_path, _parse_json(raw).get("screens", []), brand_reference
    )


async def run_gov_compliance_analysis(agent_doc: dict, settings: dict, run_id: str, context: dict, brand_reference: str | None) -> dict:
    provider, model = resolve_model(agent_doc, settings)
    user = (
        f"SRS analysis: {json.dumps(context.get('srs_analysis')) if context.get('srs_analysis') else 'None.'}\n\n"
        f"Business flow: {json.dumps(context.get('business_flow') or {})}\n\n"
        f"Crawl data available: {bool(context.get('crawl_data'))}\n\n"
        f"Brand reference supplied: {bool(brand_reference)}"
    )
    raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, user, f"{run_id}-gov-compliance", settings)
    return _parse_json(raw)


async def run_dbim_generation(agent_doc: dict, settings: dict, run_id: str, happy_path: list, brand_reference: str | None, gov_compliance: dict | None) -> list:
    provider, model = resolve_model(agent_doc, settings)
    profile = get_profile()
    user = json.dumps({
        "happy_path": happy_path,
        "gov_compliance": gov_compliance or {},
        "brand_reference": brand_reference,
        "dbim_manifest": profile["manifest"],
        "dbim_components": profile["components"],
        "dbim_patterns": profile["patterns"],
        "controlled_fallback_patterns": profile["fallback_patterns"],
    })
    runtime_policy = (
        "\n\nRuntime policy: The supplied controlled_fallback_patterns are internal semantic fallbacks, not DBIM "
        "components. Use one only when no approved DBIM component fits. Use local-only implementation, add its "
        "data-gov-fallback-id to HTML, return its ID in fallback_ids, and list the required manual review. Never "
        "invent a fallback or represent it as an official DBIM component."
        " If an official ministry/department logo, icon or image is needed but not supplied in the local asset "
        "manifest, render a visible text placeholder marked data-gov-asset-placeholder with a descriptive value "
        "such as department-logo or official-image-required. Do not invent an asset or use an external URL."
        " Use the local compiled DBIM Bootstrap 5.3 utility classes for visible layout and styling (for example "
        "container, row, col-*, navbar, card, btn, form-control, table, alert, breadcrumb, pagination, "
        "d-flex, gap-*, p-*, m-*, text-*); do not output unstyled semantic-only markup."
    )
    user["generation_contract"] = (
        "Generate exactly one complete standalone HTML document for every happy_path item. Keep each screen_name "
        "exactly as supplied and in the same order. Never merge or omit screens."
    )
    raw = await run_llm_agent(agent_doc["system_prompt"] + runtime_policy, provider, model, user, f"{run_id}-dbim-wireframe", settings)
    return await _complete_screen_set(
        agent_doc, settings, run_id, happy_path, _parse_json(raw).get("screens", []), brand_reference,
        gov_compliance=gov_compliance, dbim_profile=profile, runtime_policy=runtime_policy,
    )


def _screen_key(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _align_screens_to_happy_path(happy_path: list, screens: list) -> tuple[list, list]:
    """Keep valid first responses in the user-approved happy-path order."""
    by_name = {}
    for screen in screens if isinstance(screens, list) else []:
        if isinstance(screen, dict) and screen.get("screen_name") and screen.get("html"):
            by_name.setdefault(_screen_key(screen["screen_name"]), screen)
    aligned, missing = [], []
    for step in happy_path:
        name = step.get("screen_name") or "Untitled screen"
        screen = by_name.get(_screen_key(name))
        if screen:
            aligned.append({**screen, "screen_name": name})
        else:
            missing.append(step)
    return aligned, missing


async def _complete_screen_set(agent_doc: dict, settings: dict, run_id: str, happy_path: list, initial_screens: list,
                               brand_reference: str | None, gov_compliance: dict | None = None,
                               dbim_profile: dict | None = None, runtime_policy: str = "") -> list:
    """Repair partial LLM output without ever silently showing fewer screens than the approved flow."""
    aligned, missing = _align_screens_to_happy_path(happy_path, initial_screens)
    if not missing:
        return aligned

    provider, model = resolve_model(agent_doc, settings)
    generated = {_screen_key(screen["screen_name"]): screen for screen in aligned}
    for index, step in enumerate(missing, start=1):
        name = step.get("screen_name") or "Untitled screen"
        repair_payload = {
            "required_screen": step,
            "instruction": "Generate ONLY this one missing screen. Its screen_name must exactly match required_screen.screen_name. Return one element in screens.",
            "brand_reference": brand_reference,
        }
        if gov_compliance is not None:
            repair_payload.update({"gov_compliance": gov_compliance, "dbim_manifest": dbim_profile["manifest"],
                                   "dbim_components": dbim_profile["components"], "dbim_patterns": dbim_profile["patterns"],
                                   "controlled_fallback_patterns": dbim_profile["fallback_patterns"]})
        raw = await run_llm_agent(
            agent_doc["system_prompt"] + runtime_policy, provider, model, json.dumps(repair_payload),
            f"{run_id}-screen-repair-{index}", settings,
        )
        repaired, still_missing = _align_screens_to_happy_path([step], _parse_json(raw).get("screens", []))
        if not repaired or still_missing:
            raise RuntimeError(f"The generator did not return the required screen '{name}'.")
        generated[_screen_key(name)] = repaired[0]

    return [generated[_screen_key(step.get("screen_name") or "Untitled screen")] for step in happy_path]


async def run_export(agent_doc: dict, settings: dict, run_id: str, happy_path: list, wireframes: list, design_system: str = "standard", compliance_report: dict | None = None) -> dict:
    provider, model = resolve_model(agent_doc, settings)
    user = json.dumps({
        "design_system": design_system,
        "happy_path": happy_path,
        "wireframes": wireframes,
        "compliance_report": compliance_report,
    })
    raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, user, f"{run_id}-export", settings)
    return _parse_json(raw)


async def run_feedback_routing(agent_doc: dict, settings: dict, run_id: str, feedback_id: str, instruction: str, scope: str, has_reference: bool) -> dict:
    provider, model = resolve_model(agent_doc, settings)
    user = f"User instruction: {instruction}\nScope: {scope} (screen = one screen only, all = every screen)\nReference material attached: {has_reference}"
    raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, user, f"{run_id}-route-{feedback_id}", settings)
    return _parse_json(raw)


async def run_apply_feedback(agent_doc: dict, settings: dict, run_id: str, feedback_id: str, instruction: str, target_screens: list, reference_text: str | None, element_context: str | None, brand_reference: str | None, design_system_context: dict | None = None) -> list:
    provider, model = resolve_model(agent_doc, settings)
    element_clause = f"\n\nTarget element the user clicked on (modify ONLY this element, leave the rest of the screen intact):\n{element_context}" if element_context else ""
    brand_clause = f"\n\nBrand reference to stay consistent with:\n{brand_reference}" if brand_reference else ""
    design_system_clause = f"\n\nApproved design-system context (authoritative):\n{json.dumps(design_system_context)}" if design_system_context else ""
    user = (
        f"User instruction: {instruction}\n\n"
        f"Reference material provided by the user (if any):\n{reference_text or 'None provided.'}"
        f"{element_clause}{brand_clause}{design_system_clause}\n\n"
        f"Current screens to modify (apply the instruction to each, keep everything else about them intact "
        f"unless the instruction implies otherwise):\n{json.dumps(target_screens)}"
    )
    raw = await run_llm_agent(agent_doc["system_prompt"], provider, model, user, f"{run_id}-apply-{feedback_id}", settings)
    data = _parse_json(raw)
    return data.get("screens", [])
