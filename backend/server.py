import asyncio
import io
import json
import logging
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import orchestration
import seed_data
from crawler import crawl_site, capture_screenshot, summarize_pages

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class RunCreate(BaseModel):
    srs_text: str | None = None
    url: str | None = None
    crawl_depth: str = "single"
    brand_reference: str | None = None


async def get_settings() -> dict:
    s = await db.settings.find_one({"id": "global"}, {"_id": 0})
    return s or seed_data.DEFAULT_SETTINGS


async def get_agent_map() -> dict:
    docs = {}
    async for a in db.agents.find({}, {"_id": 0}):
        docs[a["name"]] = a
    return docs


async def push_log(run_id: str, stage: str, label: str, status: str, detail: str = ""):
    await db.runs.update_one(
        {"id": run_id},
        {
            "$set": {"current_stage": stage, "status": "error" if status == "error" else "running"},
            "$push": {"stage_log": {
                "stage": stage, "label": label, "status": status, "detail": detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }},
        },
    )


async def run_pipeline(run_id: str, srs_text: str | None, url: str | None, crawl_depth: str):
    try:
        settings = await get_settings()
        agent_map = await get_agent_map()

        await push_log(run_id, "orchestrating", "SUPER_AGENT", "running", "Deciding which agents to invoke...")
        plan = await orchestration.run_orchestrator_plan(agent_map["SUPER_AGENT"], settings, run_id, bool(srs_text), bool(url), crawl_depth)
        await db.runs.update_one({"id": run_id}, {"$set": {"orchestrator_plan": plan}})
        await push_log(run_id, "orchestrating", "SUPER_AGENT", "completed", plan.get("reasoning", ""))

        flow = await db.flows.find_one({"is_active": True}, {"_id": 0})
        levels = orchestration.topo_levels(flow["nodes"], flow["edges"])
        context = {"srs_text": srs_text, "url": url, "crawl_depth": crawl_depth}

        for level in levels:
            for node in level:
                agent_name = node["agent_name"]
                if not orchestration.node_condition_met(node, bool(srs_text), bool(url)):
                    continue
                agent_doc = agent_map.get(agent_name)
                if not agent_doc:
                    continue
                await push_log(run_id, agent_name.lower(), agent_name, "running", f"Executing {agent_name}...")
                try:
                    result = await orchestration.execute_node(agent_name, agent_doc, settings, run_id, context)
                    kind, value = result["kind"], result["value"]
                    if kind != "custom":
                        context[kind] = value
                        await db.runs.update_one({"id": run_id}, {"$set": {kind: value}})
                    detail = orchestration.summarize_result(kind, value)
                    await push_log(run_id, agent_name.lower(), agent_name, "completed", detail)
                except Exception as ne:
                    logger.exception(f"Node {agent_name} failed")
                    await push_log(run_id, agent_name.lower(), agent_name, "error", str(ne))

        await push_log(run_id, "happy_path_ready", "SUPER_AGENT", "completed",
                        "Happy path ready for your review. Edit steps or generate wireframes when ready.")
        await db.runs.update_one({"id": run_id}, {"$set": {"status": "awaiting_review", "current_stage": "happy_path_ready"}})
    except Exception as e:
        logger.exception("Pipeline failed")
        await db.runs.update_one({"id": run_id}, {"$set": {"status": "error", "error": str(e)}})


async def run_wireframe_stage(run_id: str, happy_path: list, brand_reference: str | None):
    try:
        settings = await get_settings()
        agent_doc = await db.agents.find_one({"name": "WIREFRAME_GENERATOR"}, {"_id": 0})
        await push_log(run_id, "generating_wireframes", "WIREFRAME_GENERATOR", "running", "Rendering live HTML/CSS wireframes...")
        wireframes = await orchestration.run_wireframe_generation(agent_doc, settings, run_id, happy_path, brand_reference)
        await db.runs.update_one({"id": run_id}, {"$set": {"wireframes": wireframes}})
        await push_log(run_id, "generating_wireframes", "WIREFRAME_GENERATOR", "completed", f"{len(wireframes)} screens rendered.")
        await db.runs.update_one({"id": run_id}, {"$set": {"status": "completed", "current_stage": "completed"}})
    except Exception as e:
        logger.exception("Wireframe generation failed")
        await db.runs.update_one({"id": run_id}, {"$set": {"status": "error", "error": str(e)}})


async def run_export(run_id: str, happy_path: list, wireframes: list):
    try:
        settings = await get_settings()
        agent_doc = await db.agents.find_one({"name": "EXPORT_AGENT"}, {"_id": 0})
        export = await orchestration.run_export(agent_doc, settings, run_id, happy_path, wireframes)
        await db.runs.update_one({"id": run_id}, {"$set": {"export": export, "export_status": "completed"}})
    except Exception as e:
        logger.exception("Export failed")
        await db.runs.update_one({"id": run_id}, {"$set": {"export_status": "error", "export_error": str(e)}})


async def run_feedback(run_id: str, feedback_id: str, instruction: str, scope: str, screen_name: str | None, reference_text: str | None, element_context: str | None):
    try:
        settings = await get_settings()
        doc = await db.runs.find_one({"id": run_id}, {"_id": 0})
        wireframes = doc.get("wireframes") or []
        brand_reference = (doc.get("input") or {}).get("brand_reference")
        target = [w for w in wireframes if w["screen_name"] == screen_name] if scope == "screen" and screen_name else wireframes

        router_doc = await db.agents.find_one({"name": "FEEDBACK_ROUTER"}, {"_id": 0})
        route = await orchestration.run_feedback_routing(router_doc, settings, run_id, feedback_id, instruction, scope, bool(reference_text))
        agent_name = route.get("agent_name", "WIREFRAME_GENERATOR")
        is_new = bool(route.get("is_new_agent"))

        existing = await db.agents.find_one({"name": agent_name}, {"_id": 0})
        if is_new and not existing:
            now = datetime.now(timezone.utc).isoformat()
            target_agent_doc = {
                "id": str(uuid.uuid4()), "name": agent_name,
                "description": f"Auto-created by Super Agent: {route.get('reasoning', '')[:200]}",
                "agent_type": "llm", "system_prompt": route.get("system_prompt", ""),
                "model_provider": None, "model_name": None,
                "is_builtin": False, "is_dynamic": True, "created_at": now, "updated_at": now,
            }
            await db.agents.insert_one(target_agent_doc)
        else:
            target_agent_doc = existing or {"system_prompt": route.get("system_prompt", "")}

        await db.runs.update_one(
            {"id": run_id, "feedback_log.id": feedback_id},
            {"$set": {
                "feedback_log.$.agent_name": agent_name,
                "feedback_log.$.is_new_agent": is_new,
                "feedback_log.$.reasoning": route.get("reasoning", ""),
            }},
        )

        updated = await orchestration.run_apply_feedback(target_agent_doc, settings, run_id, feedback_id, instruction, target, reference_text, element_context, brand_reference)
        updated_map = {u["screen_name"]: u["html"] for u in updated if u.get("screen_name")}
        new_wireframes = [{**w, "html": updated_map.get(w["screen_name"], w["html"])} for w in wireframes]

        await db.runs.update_one({"id": run_id}, {"$set": {"wireframes": new_wireframes}})
        await db.runs.update_one(
            {"id": run_id, "feedback_log.id": feedback_id},
            {"$set": {"feedback_log.$.status": "completed"}},
        )
    except Exception as e:
        logger.exception("Feedback processing failed")
        await db.runs.update_one(
            {"id": run_id, "feedback_log.id": feedback_id},
            {"$set": {"feedback_log.$.status": "error", "feedback_log.$.error": str(e)}},
        )


@api_router.get("/")
async def root():
    return {"message": "UX Orchestrator API"}


@api_router.post("/upload-srs")
async def upload_srs(file: UploadFile = File(...)):
    content = await file.read()
    if file.filename.lower().endswith(".pdf"):
        import pdfplumber
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    else:
        text = content.decode("utf-8", errors="ignore")
    return {"text": text[:20000]}


@api_router.post("/runs")
async def create_run(payload: RunCreate):
    if not payload.srs_text and not payload.url:
        raise HTTPException(status_code=400, detail="Provide SRS text and/or a website URL.")
    run_id = str(uuid.uuid4())
    doc = {
        "id": run_id,
        "status": "running",
        "current_stage": "orchestrating",
        "stage_log": [],
        "input": {"srs_text": payload.srs_text, "url": payload.url, "crawl_depth": payload.crawl_depth, "brand_reference": payload.brand_reference},
        "orchestrator_plan": None,
        "srs_analysis": None,
        "crawl_data": None,
        "business_flow": None,
        "ux_rating": None,
        "wireframes": None,
        "feedback_log": [],
        "export": None,
        "export_status": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.runs.insert_one(doc)
    asyncio.create_task(run_pipeline(run_id, payload.srs_text, payload.url, payload.crawl_depth))
    return {"run_id": run_id}


@api_router.get("/runs/{run_id}")
async def get_run(run_id: str):
    doc = await db.runs.find_one({"id": run_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    return doc


class HappyPathUpdate(BaseModel):
    happy_path: list[dict]


@api_router.put("/runs/{run_id}/happy-path")
async def update_happy_path(run_id: str, payload: HappyPathUpdate):
    doc = await db.runs.find_one({"id": run_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    if not doc.get("business_flow"):
        raise HTTPException(status_code=400, detail="Happy path not ready yet")
    steps = [{**step, "step": i + 1} for i, step in enumerate(payload.happy_path)]
    await db.runs.update_one({"id": run_id}, {"$set": {"business_flow.happy_path": steps}})
    return {"happy_path": steps}


@api_router.post("/runs/{run_id}/generate-wireframes")
async def generate_wireframes(run_id: str):
    doc = await db.runs.find_one({"id": run_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    happy_path = (doc.get("business_flow") or {}).get("happy_path")
    if not happy_path:
        raise HTTPException(status_code=400, detail="Happy path not ready yet")
    await db.runs.update_one({"id": run_id}, {"$set": {"status": "running", "wireframes": None}})
    asyncio.create_task(run_wireframe_stage(run_id, happy_path, (doc.get("input") or {}).get("brand_reference")))
    return {"status": "started"}


@api_router.post("/runs/{run_id}/finalize")
async def finalize_run(run_id: str):
    doc = await db.runs.find_one({"id": run_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    if not doc.get("wireframes"):
        raise HTTPException(status_code=400, detail="Run has no wireframes yet")
    await db.runs.update_one({"id": run_id}, {"$set": {"export_status": "generating"}})
    asyncio.create_task(run_export(run_id, doc["business_flow"].get("happy_path", []), doc["wireframes"]))
    return {"status": "started"}


@api_router.get("/runs/{run_id}/download")
async def download_run(run_id: str):
    doc = await db.runs.find_one({"id": run_id}, {"_id": 0})
    if not doc or not doc.get("export"):
        raise HTTPException(status_code=404, detail="No export available. Finalize the run first.")
    export = doc["export"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for comp in export.get("react_components", []):
            zf.writestr(f"components/{comp['filename']}", comp["code"])
        zf.writestr("styles.css", export.get("css", ""))
        zf.writestr("api_spec.json", json.dumps(export.get("api_spec", []), indent=2))
        zf.writestr("README.md", export.get("readme", ""))
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=ux-orchestrator-export-{run_id[:8]}.zip"},
    )


@api_router.post("/runs/{run_id}/feedback")
async def submit_feedback(
    run_id: str,
    instruction: str = Form(...),
    scope: str = Form("all"),
    screen_name: str | None = Form(None),
    element_context: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    doc = await db.runs.find_one({"id": run_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    if not doc.get("wireframes"):
        raise HTTPException(status_code=400, detail="Generate wireframes before sending feedback.")

    reference_text = None
    if file:
        content = await file.read()
        if file.filename.lower().endswith((".html", ".css", ".txt")):
            reference_text = content.decode("utf-8", errors="ignore")[:8000]
        else:
            reference_text = f"[User attached a reference image: {file.filename} - visual content is not analyzed in this version, treat it only as a named hint.]"

    feedback_id = str(uuid.uuid4())
    entry = {
        "id": feedback_id,
        "instruction": instruction,
        "scope": scope,
        "screen_name": screen_name,
        "element_context": element_context,
        "has_reference": bool(reference_text),
        "agent_name": None,
        "is_new_agent": False,
        "reasoning": None,
        "status": "running",
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await db.runs.update_one({"id": run_id}, {"$push": {"feedback_log": entry}})
    asyncio.create_task(run_feedback(run_id, feedback_id, instruction, scope, screen_name, reference_text, element_context))
    return {"status": "started", "feedback_id": feedback_id}


@api_router.get("/agents")
async def list_agents():
    return await db.agents.find({}, {"_id": 0}).to_list(1000)


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    system_prompt: str
    model_provider: str | None = None
    model_name: str | None = None


@api_router.post("/agents")
async def create_agent(payload: AgentCreate):
    name = payload.name.upper().replace(" ", "_")
    if await db.agents.find_one({"name": name}):
        raise HTTPException(status_code=400, detail="Agent name already exists")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()), "name": name, "description": payload.description,
        "agent_type": "llm", "system_prompt": payload.system_prompt,
        "model_provider": payload.model_provider, "model_name": payload.model_name,
        "is_builtin": False, "is_dynamic": False, "created_at": now, "updated_at": now,
    }
    await db.agents.insert_one(doc)
    doc.pop("_id", None)
    return doc


class AgentUpdate(BaseModel):
    description: str | None = None
    system_prompt: str | None = None
    model_provider: str | None = None
    model_name: str | None = None


@api_router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, payload: AgentUpdate):
    doc = await db.agents.find_one({"id": agent_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if payload.description is not None:
        updates["description"] = payload.description
    if payload.system_prompt is not None:
        updates["system_prompt"] = payload.system_prompt
    if payload.model_provider is not None:
        updates["model_provider"] = payload.model_provider or None
    if payload.model_name is not None:
        updates["model_name"] = payload.model_name or None
    await db.agents.update_one({"id": agent_id}, {"$set": updates})
    return await db.agents.find_one({"id": agent_id}, {"_id": 0})


@api_router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    doc = await db.agents.find_one({"id": agent_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    if doc.get("is_builtin"):
        raise HTTPException(status_code=400, detail="Cannot delete a built-in agent")
    await db.agents.delete_one({"id": agent_id})
    return {"status": "deleted"}


@api_router.get("/flows/active")
async def get_active_flow():
    flow = await db.flows.find_one({"is_active": True}, {"_id": 0})
    if not flow:
        raise HTTPException(status_code=404, detail="No active flow")
    return flow


class FlowUpdate(BaseModel):
    nodes: list[dict]
    edges: list[dict]


@api_router.put("/flows/active")
async def update_active_flow(payload: FlowUpdate):
    flow = await db.flows.find_one({"is_active": True}, {"_id": 0})
    if not flow:
        raise HTTPException(status_code=404, detail="No active flow")
    await db.flows.update_one(
        {"id": flow["id"]},
        {"$set": {"nodes": payload.nodes, "edges": payload.edges, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return await db.flows.find_one({"id": flow["id"]}, {"_id": 0})


def _mask_key(key: str) -> str:
    return f"****{key[-4:]}" if key and len(key) > 4 else ("****" if key else "")


@api_router.get("/settings/llm")
async def get_llm_settings():
    s = await get_settings()
    raw_keys = s.get("api_keys") or {}
    return {
        **s,
        "api_keys": {p: _mask_key(k) for p, k in raw_keys.items() if k},
        "has_platform_key": bool(os.environ.get("EMERGENT_LLM_KEY")),
        "has_ey_incubator_config": bool(
            ((s.get("provider_configs") or {}).get("ey_incubator") or {}).get("base_url")
            and raw_keys.get("ey_incubator")
        ) or bool(
            os.environ.get("EY_INCUBATOR_BASE_URL") and os.environ.get("EY_INCUBATOR_API_KEY")
        ),
    }


class SettingsUpdate(BaseModel):
    default_provider: str
    default_model: str


@api_router.put("/settings/llm")
async def update_llm_settings(payload: SettingsUpdate):
    await db.settings.update_one({"id": "global"}, {"$set": payload.dict()}, upsert=True)
    return await get_llm_settings()


class ApiKeyUpdate(BaseModel):
    provider: str
    api_key: str


class EyIncubatorConfigUpdate(BaseModel):
    base_url: str
    models: list[str]


@api_router.put("/settings/llm/ey-incubator")
async def update_ey_incubator_config(payload: EyIncubatorConfigUpdate):
    base_url = payload.base_url.strip().rstrip("/")
    models = list(dict.fromkeys(model.strip() for model in payload.models if model.strip()))
    if not base_url.startswith(("https://", "http://")):
        raise HTTPException(status_code=400, detail="Endpoint must start with http:// or https://")
    if not models:
        raise HTTPException(status_code=400, detail="Add at least one EY Incubator model")
    await db.settings.update_one(
        {"id": "global"},
        {"$set": {"provider_configs.ey_incubator": {"base_url": base_url, "models": models}}},
        upsert=True,
    )
    return await get_llm_settings()


@api_router.put("/settings/llm/keys")
async def update_llm_api_key(payload: ApiKeyUpdate):
    if payload.provider not in orchestration.MODEL_CHOICES:
        raise HTTPException(status_code=400, detail="Unknown provider")
    if not payload.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    await db.settings.update_one(
        {"id": "global"}, {"$set": {f"api_keys.{payload.provider}": payload.api_key.strip()}}, upsert=True
    )
    return await get_llm_settings()


@api_router.delete("/settings/llm/keys/{provider}")
async def delete_llm_api_key(provider: str):
    await db.settings.update_one({"id": "global"}, {"$unset": {f"api_keys.{provider}": ""}})
    return await get_llm_settings()


@api_router.get("/model-choices")
async def model_choices():
    return orchestration.get_model_choices(await get_settings())


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_seed():
    await seed_data.seed_if_empty(db)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
