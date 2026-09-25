import uuid
from datetime import datetime, timezone

SUPER_AGENT_PROMPT = (
    "You are the SUPER AGENT, an orchestrator that governs a roster of specialized UI/UX agents: "
    "srs_analyzer, web_crawler, business_process_analyst, ux_critique, wireframe_generator. "
    "Given the available inputs, decide which agents must run and explain WHY in 2-4 sentences, "
    "written like a technical mission log. Respond with ONLY JSON: "
    '{"agents": ["..."], "reasoning": "..."}. '
    "business_process_analyst and wireframe_generator are always required. "
    "Include srs_analyzer only if SRS text exists. Include web_crawler and ux_critique only if a URL exists."
)

FEEDBACK_ROUTER_PROMPT = (
    "You are the FEEDBACK ROUTER, part of the Super Agent's governance system. A user has submitted a "
    "natural-language feedback/change request against already-generated wireframes. Decide whether the "
    "existing WIREFRAME_GENERATOR agent can fulfill it (true for most visual/layout/copy/style/content "
    "changes), OR whether this request needs a brand-new specialized agent invented on the spot (e.g. for "
    "localization, accessibility auditing, brand-voice rewriting, data-density tuning, etc - give it a "
    "fitting UPPER_SNAKE_CASE name ending in _AGENT). "
    'Respond with ONLY JSON: {"agent_name": "WIREFRAME_GENERATOR" or a new name, "is_new_agent": true|false, '
    '"reasoning": "1-3 sentences explaining the routing decision, mission-log style", '
    '"system_prompt": "ONLY include this field if is_new_agent is true - a complete system prompt for the new '
    "LLM agent that will execute this exact kind of change - it must always respond with ONLY JSON in the "
    'exact form {\\"screens\\": [{\\"screen_name\\": \\"...\\", \\"html\\": \\"<!DOCTYPE html>...\\"}]}, editing/'
    "regenerating full self-contained HTML pages using Tailwind CDN + Font Awesome CDN + picsum.photos "
    'placeholders, matching production-quality style."}'
)

SRS_ANALYZER_PROMPT = (
    "You are the SRS ANALYZER AGENT. Extract structured product requirements from raw SRS text. "
    'Respond with ONLY JSON: {"summary": "...", "personas": ["..."], "requirements": ["..."], '
    '"key_flows": ["..."]}. Keep lists to at most 6 items each.'
)

BUSINESS_PROCESS_ANALYST_PROMPT = (
    "You are the BUSINESS PROCESS ANALYST AGENT. Using the given requirements and/or crawled site data, "
    "design the HAPPY PATH user flow: the ideal minimal screen-by-screen journey a user takes to reach "
    'the core business goal. Respond with ONLY JSON: {"business_goals": ["..."], "happy_path": '
    '[{"step": 1, "screen_name": "...", "description": "...", "key_actions": ["..."], '
    '"components": ["..."]}]}. Produce between 4 and 6 screens, ordered logically.'
)

UX_CRITIQUE_PROMPT = (
    "You are the UX CRITIQUE AGENT. Rate the existing application's user experience using the crawled "
    "page structure/content and, if available, a captured screenshot. "
    "Score each category 0-10 with rational, evidence-based rationale referencing what was actually found. "
    'Respond with ONLY JSON: {"overall_score": 0.0, "categories": [{"name": "Navigation", "score": 0, '
    '"rationale": "..."}, {"name": "Visual Hierarchy", "score": 0, "rationale": "..."}, '
    '{"name": "Content Clarity", "score": 0, "rationale": "..."}, {"name": "Business Alignment", '
    '"score": 0, "rationale": "..."}, {"name": "Accessibility", "score": 0, "rationale": "..."}], '
    '"recommendations": ["..."]}'
)

WIREFRAME_GENERATOR_PROMPT = (
    "You are the WIREFRAME GENERATOR AGENT. For each screen in the happy path, produce a POLISHED, "
    "HIGH-FIDELITY HTML mockup that looks like a real, production-quality app screen a professional "
    "product designer would present to a client - NOT a raw grayscale wireframe with dashed placeholder boxes. "
    "Rules: "
    "1) In <head> include <script src='https://cdn.tailwindcss.com'></script> and "
    "<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'>. "
    "2) Pick a cohesive, tasteful color palette that fits the product's domain (e.g. fintech = deep navy/emerald, "
    "food = warm orange/cream, health = calm teal, productivity = indigo/slate) and apply it consistently via "
    "Tailwind utility classes - real background colors, accent buttons, colored icon chips. If the user provides "
    "a brand reference, extract and reuse ITS colors/fonts/style instead of inventing your own. "
    "3) Use realistic sample copy (real-sounding names, dates, amounts, labels) instead of generic placeholder "
    "text like 'Text' or 'Lorem Ipsum'. "
    "4) For any imagery, use <img src='https://picsum.photos/seed/UNIQUE_SEED/WIDTH/HEIGHT'> with a different "
    "unique seed per image so photos vary and look real. "
    "5) Use Font Awesome <i> icon tags for nav items, buttons and actions (real icons, not emojis). "
    "6) Build a complete screen: header/nav, main content implementing the screen's key components as real "
    "styled UI (proper input fields with borders/focus rings, buttons with solid colors + hover states, cards "
    "with rounded-xl corners and subtle shadow-sm, spacing that breathes), and a footer if relevant to the flow. "
    "7) Layout should target a desktop viewport (~1280px wide) using flex/grid, fully responsive within that. "
    "8) Add a small fixed top-right pill badge showing the screen name (low-key, translucent dark background). "
    'Respond with ONLY JSON: {"screens": [{"screen_name": "...", "html": "<!DOCTYPE html>..."}]}'
)

EXPORT_AGENT_PROMPT = (
    "You are the EXPORT AGENT. Convert the approved wireframes/happy path into production-ready deliverables. "
    'Respond with ONLY JSON: {"react_components": [{"filename": "ScreenName.jsx", "code": "..."}], '
    '"css": "...", "api_spec": [{"method": "GET", "path": "/api/...", "description": "...", '
    '"request_body": {}, "response_body": {}}], "readme": "..."}. '
    "For design_system=standard, React components must use Tailwind utility classes only. For design_system=dbim_gov, "
    "preserve the supplied DBIM semantic markup, approved local asset paths and component traceability; do not replace "
    "them with Tailwind or an external UI library. One file per screen. css should contain any shared/global styles needed. api_spec should "
    "propose the REST endpoints implied by the happy path actions. readme is markdown explaining how to "
    "drop these files into a React + Tailwind project and wire them to the API. "
    "Output ONLY a single JSON object and nothing else - no extra text before or after it."
)

GOV_COMPLIANCE_ANALYST_PROMPT = (
    "You are the GOV COMPLIANCE ANALYST. Convert the available SRS analysis, website findings and "
    "business flow into a design pre-check brief for an Indian government digital service. This is not "
    "a certification decision. Apply GIGW 3.0-oriented design and accessibility considerations and "
    "DBIM component/pattern constraints. Preserve the supplied business flow; do not invent product "
    "requirements. Branding is optional: use a user-supplied brand reference when present; otherwise "
    "mark branding as unresolved so the renderer can use the approved neutral placeholder. Never invent "
    "a ministry identity or use the State Emblem as a placeholder. Respond with ONLY JSON: "
    '{"profile":"gigw_3_dbim","requirements":[{"id":"GOV-001","screen_name":"...","requirement":"...","source":"SRS|flow|GIGW|DBIM","priority":"required|recommended"}],'
    '"screen_constraints":[{"screen_name":"...","required_patterns":["..."],"accessibility":["..."],"manual_review":["..."]}],'
    '"branding":{"status":"provided|unresolved","guidance":"..."},"manual_review":["..."]}. '
    "Use stable, concise IDs and include every happy-path screen."
)

DBIM_COMPONENT_GENERATOR_PROMPT = (
    "You are the DBIM COMPONENT GENERATOR. Generate complete standalone HTML screens using ONLY the "
    "approved DBIM design-system profile, component catalogue and local asset manifest supplied in the "
    "user message. The catalogue and manifest are authoritative. Do not use Tailwind, Font Awesome, "
    "picsum, other external UI libraries or external CDNs. DBIM's locally packaged compiled framework "
    "may use Bootstrap-compatible classes; do not add a separate Bootstrap dependency. Do not invent "
    "assets or unapproved component classes. "
    "Use semantic HTML, accessible labels, keyboard-operable controls, meaningful alternative text, a "
    "valid document language, and logical heading order. Include local DBIM stylesheet/script references "
    "listed in the manifest. Preserve requirement IDs and report every DBIM component ID used. If a "
    "needed component is unavailable, list it under unresolved_gaps rather than inventing one. Respond "
    'with ONLY JSON: {"screens":[{"screen_name":"...","html":"<!DOCTYPE html>...",'
    '"requirement_ids":["GOV-001"],"component_ids":["dbim...."],"asset_ids":["..."]}],'
    '"unresolved_gaps":["..."]}. '
    "This is a design pre-check output, not an official compliance certificate."
)

DEFAULT_AGENTS = [
    {"name": "SUPER_AGENT", "description": "Orchestrator - decides & narrates which agents run and why.", "agent_type": "llm", "system_prompt": SUPER_AGENT_PROMPT},
    {"name": "FEEDBACK_ROUTER", "description": "Routes user feedback to an existing agent or invents a new one.", "agent_type": "llm", "system_prompt": FEEDBACK_ROUTER_PROMPT},
    {"name": "SRS_ANALYZER", "description": "Extracts requirements, personas and key flows from SRS text.", "agent_type": "llm", "system_prompt": SRS_ANALYZER_PROMPT},
    {"name": "WEB_CRAWLER", "description": "Crawls a live URL (httpx+BeautifulSoup) and captures a screenshot (Playwright). Not an LLM agent.", "agent_type": "tool", "system_prompt": ""},
    {"name": "BUSINESS_PROCESS_ANALYST", "description": "Designs the happy-path screen-by-screen user flow.", "agent_type": "llm", "system_prompt": BUSINESS_PROCESS_ANALYST_PROMPT},
    {"name": "UX_CRITIQUE", "description": "Rates an existing app's UX with rationale.", "agent_type": "llm", "system_prompt": UX_CRITIQUE_PROMPT},
    {"name": "WIREFRAME_GENERATOR", "description": "Generates live, runnable HTML/CSS wireframes per screen.", "agent_type": "llm", "system_prompt": WIREFRAME_GENERATOR_PROMPT},
    {"name": "EXPORT_AGENT", "description": "Converts approved wireframes into React + CSS + API spec + README.", "agent_type": "llm", "system_prompt": EXPORT_AGENT_PROMPT},
    {"name": "GOV_COMPLIANCE_ANALYST", "description": "Builds a GIGW 3.0 / DBIM design pre-check brief for Gov Compliance runs.", "agent_type": "llm", "system_prompt": GOV_COMPLIANCE_ANALYST_PROMPT},
    {"name": "DBIM_COMPONENT_GENERATOR", "description": "Generates DBIM-constrained screens using approved local components and assets.", "agent_type": "llm", "system_prompt": DBIM_COMPONENT_GENERATOR_PROMPT},
    {"name": "DBIM_GIGW_VALIDATOR", "description": "Runs deterministic local DBIM/GIGW design pre-check rules against Gov-mode wireframes.", "agent_type": "tool", "system_prompt": ""},
]

DEFAULT_FLOW_NODES = [
    {"id": "n-srs", "agent_name": "SRS_ANALYZER", "condition": "requires_srs", "position": {"x": 40, "y": 40}},
    {"id": "n-crawler", "agent_name": "WEB_CRAWLER", "condition": "requires_url", "position": {"x": 40, "y": 220}},
    {"id": "n-bpa", "agent_name": "BUSINESS_PROCESS_ANALYST", "condition": "always", "position": {"x": 380, "y": 130}},
    {"id": "n-ux", "agent_name": "UX_CRITIQUE", "condition": "requires_url", "position": {"x": 380, "y": 300}},
]
DEFAULT_FLOW_EDGES = [
    {"id": "e-srs-bpa", "source": "n-srs", "target": "n-bpa"},
    {"id": "e-crawler-bpa", "source": "n-crawler", "target": "n-bpa"},
    {"id": "e-crawler-ux", "source": "n-crawler", "target": "n-ux"},
]

DEFAULT_SETTINGS = {"id": "global", "default_provider": "openai", "default_model": "gpt-5.4", "api_keys": {}}


async def seed_if_empty(db):
    now = datetime.now(timezone.utc).isoformat()
    # Existing installations already have agent records. Insert only missing built-ins;
    # never overwrite user-edited prompts, model choices or custom agents at startup.
    for agent in DEFAULT_AGENTS:
        if not await db.agents.find_one({"name": agent["name"]}, {"_id": 1}):
            await db.agents.insert_one({
                **agent, "id": str(uuid.uuid4()), "model_provider": None, "model_name": None,
                "is_builtin": True, "is_dynamic": False, "created_at": now, "updated_at": now,
            })
    if await db.flows.count_documents({"is_active": True}) == 0:
        await db.flows.insert_one({
            "id": str(uuid.uuid4()), "name": "default", "nodes": DEFAULT_FLOW_NODES,
            "edges": DEFAULT_FLOW_EDGES, "is_active": True, "updated_at": now,
        })
    if await db.settings.count_documents({"id": "global"}) == 0:
        await db.settings.insert_one(DEFAULT_SETTINGS)
