"""Tests for Agent Inventory / Flow / LLM Settings CRUD + end-to-end prompt linkage."""
import os
import time
import requests

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"


# ------------------------ Agents CRUD ------------------------
class TestAgentsCRUD:
    def test_list_seeded_agents(self):
        r = requests.get(f"{API}/agents")
        assert r.status_code == 200
        docs = r.json()
        names = {d["name"] for d in docs}
        expected = {"SUPER_AGENT", "FEEDBACK_ROUTER", "SRS_ANALYZER", "WEB_CRAWLER",
                    "BUSINESS_PROCESS_ANALYST", "UX_CRITIQUE", "WIREFRAME_GENERATOR", "EXPORT_AGENT"}
        assert expected.issubset(names), f"missing {expected - names}"
        for d in docs:
            if d["name"] in expected:
                assert d["is_builtin"] is True
                assert isinstance(d["system_prompt"], str)

    def test_create_update_delete_custom_agent(self):
        # Create
        payload = {
            "name": "TEST_TEMP_AGENT",
            "description": "Temp desc",
            "system_prompt": "Act as a test agent.",
        }
        r = requests.post(f"{API}/agents", json=payload)
        assert r.status_code == 200, r.text
        agent = r.json()
        assert agent["name"] == "TEST_TEMP_AGENT"
        assert agent["is_builtin"] is False
        aid = agent["id"]

        # Duplicate should fail
        r = requests.post(f"{API}/agents", json=payload)
        assert r.status_code == 400

        # Update
        r = requests.put(f"{API}/agents/{aid}", json={"description": "Updated"})
        assert r.status_code == 200
        assert r.json()["description"] == "Updated"

        # Verify persisted
        docs = requests.get(f"{API}/agents").json()
        found = next(d for d in docs if d["id"] == aid)
        assert found["description"] == "Updated"

        # Delete
        r = requests.delete(f"{API}/agents/{aid}")
        assert r.status_code == 200

        # Confirm gone
        docs = requests.get(f"{API}/agents").json()
        assert not any(d["id"] == aid for d in docs)

    def test_cannot_delete_builtin(self):
        docs = requests.get(f"{API}/agents").json()
        super_agent = next(d for d in docs if d["name"] == "SUPER_AGENT")
        r = requests.delete(f"{API}/agents/{super_agent['id']}")
        assert r.status_code == 400


# ------------------------ Flow CRUD ------------------------
class TestFlow:
    def test_get_active_flow(self):
        r = requests.get(f"{API}/flows/active")
        assert r.status_code == 200
        flow = r.json()
        node_names = {n["agent_name"] for n in flow["nodes"]}
        assert {"SRS_ANALYZER", "WEB_CRAWLER", "BUSINESS_PROCESS_ANALYST", "UX_CRITIQUE"} <= node_names
        assert len(flow["edges"]) >= 3

    def test_update_active_flow_roundtrip(self):
        original = requests.get(f"{API}/flows/active").json()
        # Modify condition of one node
        modified_nodes = [dict(n) for n in original["nodes"]]
        modified_nodes[0]["condition"] = "always"
        r = requests.put(f"{API}/flows/active", json={"nodes": modified_nodes, "edges": original["edges"]})
        assert r.status_code == 200
        got = requests.get(f"{API}/flows/active").json()
        assert got["nodes"][0]["condition"] == "always"

        # Restore
        requests.put(f"{API}/flows/active", json={"nodes": original["nodes"], "edges": original["edges"]})


# ------------------------ LLM Settings ------------------------
class TestLlmSettings:
    def test_get_settings(self):
        r = requests.get(f"{API}/settings/llm")
        assert r.status_code == 200
        s = r.json()
        assert "default_provider" in s and "default_model" in s

    def test_model_choices(self):
        r = requests.get(f"{API}/model-choices")
        assert r.status_code == 200
        mc = r.json()
        assert "openai" in mc and "anthropic" in mc
        assert len(mc["openai"]) > 0 and len(mc["anthropic"]) > 0

    def test_update_settings_persists(self):
        original = requests.get(f"{API}/settings/llm").json()
        try:
            r = requests.put(f"{API}/settings/llm", json={"default_provider": "anthropic", "default_model": "claude-sonnet-4-6"})
            assert r.status_code == 200
            got = requests.get(f"{API}/settings/llm").json()
            assert got["default_provider"] == "anthropic"
            assert got["default_model"] == "claude-sonnet-4-6"
        finally:
            requests.put(f"{API}/settings/llm", json={
                "default_provider": original["default_provider"],
                "default_model": original["default_model"],
            })


# ------------------------ End-to-End Prompt Linkage (CORE PROMISE) ------------------------
class TestPromptLinkage:
    MARKER = "PERSONA_MARKER_777"

    def _get_srs_agent(self):
        docs = requests.get(f"{API}/agents").json()
        return next(d for d in docs if d["name"] == "SRS_ANALYZER")

    def test_edited_prompt_is_actually_executed(self):
        srs_agent = self._get_srs_agent()
        original_prompt = srs_agent["system_prompt"]
        marker_instr = f" IMPORTANT: Always include the exact string {self.MARKER} as one of the personas."
        new_prompt = original_prompt + marker_instr

        # Save edited prompt
        r = requests.put(f"{API}/agents/{srs_agent['id']}", json={"system_prompt": new_prompt})
        assert r.status_code == 200
        assert self.MARKER in r.json()["system_prompt"]

        try:
            # Kick off a run
            r = requests.post(f"{API}/runs", json={
                "srs_text": "Build a personal budgeting app. Users track expenses and set monthly limits.",
            })
            assert r.status_code == 200
            run_id = r.json()["run_id"]

            # Wait for awaiting_review
            deadline = time.time() + 180
            last = None
            while time.time() < deadline:
                last = requests.get(f"{API}/runs/{run_id}").json()
                if last.get("status") in ("awaiting_review", "error"):
                    break
                time.sleep(3)
            assert last and last["status"] == "awaiting_review", f"got {last.get('status')} err={last.get('error')}"

            personas = (last.get("srs_analysis") or {}).get("personas") or []
            personas_blob = " ".join(str(p) for p in personas)
            assert self.MARKER in personas_blob, f"Marker not found in personas: {personas}"
        finally:
            # Revert prompt to original
            requests.put(f"{API}/agents/{srs_agent['id']}", json={"system_prompt": original_prompt})
            verify = requests.get(f"{API}/agents").json()
            reverted = next(d for d in verify if d["id"] == srs_agent["id"])
            assert self.MARKER not in reverted["system_prompt"]
