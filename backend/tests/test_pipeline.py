"""Backend API tests for UX Orchestrator - covers pipeline, polling, finalize/export."""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ux-orchestrator-ai.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

SRS_TEXT = """
Product: TaskFlow - A simple task management app for small teams.
Users: Team members and team leads.
Core Features:
1. Users can sign up and log in with email/password
2. Users can create, edit, and delete tasks with title, description, due date, priority
3. Users can assign tasks to team members
4. Users can view a Kanban board (To Do, In Progress, Done)
5. Team leads can view team dashboard with progress metrics
Happy path: user signs up -> logs in -> creates a task -> assigns to teammate -> moves to done
"""


class TestHealth:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        assert "message" in r.json()


class TestRunValidation:
    def test_reject_empty(self):
        r = requests.post(f"{API}/runs", json={})
        assert r.status_code == 400

    def test_get_missing_run(self):
        r = requests.get(f"{API}/runs/nonexistent-id-xyz")
        assert r.status_code == 404


class TestUploadSrs:
    def test_upload_txt(self):
        files = {"file": ("srs.txt", b"Hello SRS content", "text/plain")}
        r = requests.post(f"{API}/upload-srs", files=files)
        assert r.status_code == 200
        assert r.json()["text"].startswith("Hello SRS")


class TestFullPipelineSrsOnly:
    """End-to-end pipeline with SRS text only (no URL). ~30-90s."""

    @pytest.fixture(scope="class")
    def run_id(self):
        r = requests.post(f"{API}/runs", json={"srs_text": SRS_TEXT})
        assert r.status_code == 200
        rid = r.json()["run_id"]
        assert rid
        return rid

    def test_run_created(self, run_id):
        r = requests.get(f"{API}/runs/{run_id}")
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == run_id
        assert d["status"] in ("running", "completed")

    def test_pipeline_completes(self, run_id):
        deadline = time.time() + 180
        last = None
        while time.time() < deadline:
            r = requests.get(f"{API}/runs/{run_id}")
            assert r.status_code == 200
            d = r.json()
            last = d
            if d["status"] in ("completed", "error"):
                break
            time.sleep(3)
        assert last is not None
        assert last["status"] == "completed", f"Pipeline did not complete. status={last.get('status')}, error={last.get('error')}, stage={last.get('current_stage')}"
        assert last.get("orchestrator_plan") is not None
        assert last.get("srs_analysis") is not None
        assert last.get("business_flow") is not None
        assert last.get("wireframes"), "wireframes missing"
        assert len(last["wireframes"]) >= 1
        # UX rating should NOT be present since no URL
        assert last.get("ux_rating") in (None, {}), "ux_rating should be empty when no URL"
        # Wireframe should have html content
        wf = last["wireframes"][0]
        assert "html" in wf or "code" in wf or "content" in wf, f"wireframe keys: {list(wf.keys())}"

    def test_finalize_starts_async(self, run_id):
        r = requests.post(f"{API}/runs/{run_id}/finalize")
        assert r.status_code == 200
        assert r.json().get("status") == "started"

    def test_export_completes(self, run_id):
        deadline = time.time() + 180
        last_status = None
        while time.time() < deadline:
            r = requests.get(f"{API}/runs/{run_id}")
            d = r.json()
            last_status = d.get("export_status")
            if last_status in ("completed", "error"):
                break
            time.sleep(3)
        assert last_status == "completed", f"Export status: {last_status}"
        d = requests.get(f"{API}/runs/{run_id}").json()
        exp = d.get("export")
        assert exp is not None
        assert exp.get("react_components")
        assert isinstance(exp["react_components"], list)
        assert len(exp["react_components"]) >= 1
        assert "code" in exp["react_components"][0]

    def test_download_zip(self, run_id):
        r = requests.get(f"{API}/runs/{run_id}/download")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")
        assert len(r.content) > 500
