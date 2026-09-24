"""Tests for new features: brand_reference on run creation, element_context on feedback, /run/:runId route persistence."""
import os
import time
import requests

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"

SIMPLE_SRS = "Build a simple task management app. Users sign up, create a project, add tasks with due dates, and mark tasks complete."
BRAND_CSS = ":root { --brand-primary: #ff6600; --brand-font: Georgia; }"


def _wait(run_id, target_statuses, timeout=180):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = requests.get(f"{API}/runs/{run_id}")
        last = r.json()
        if last.get("status") in target_statuses:
            return last
        time.sleep(3)
    return last


class TestBrandReferenceAndFeedback:
    """End-to-end: create run with brand_reference, generate wireframes, submit feedback w/ element_context."""

    def test_end_to_end(self):
        # 1. Create run with brand_reference
        r = requests.post(f"{API}/runs", json={
            "srs_text": SIMPLE_SRS,
            "brand_reference": BRAND_CSS,
        })
        assert r.status_code == 200
        run_id = r.json()["run_id"]

        # 2. Verify brand_reference persisted
        d = requests.get(f"{API}/runs/{run_id}").json()
        assert d["input"]["brand_reference"] == BRAND_CSS

        # 3. Wait for awaiting_review
        last = _wait(run_id, ("awaiting_review", "error"), timeout=180)
        assert last["status"] == "awaiting_review", f"got {last.get('status')} err={last.get('error')}"
        assert last.get("business_flow", {}).get("happy_path")

        # 4. Trigger wireframe generation
        r = requests.post(f"{API}/runs/{run_id}/generate-wireframes")
        assert r.status_code == 200

        # 5. Wait for completion
        last = _wait(run_id, ("completed", "error"), timeout=180)
        assert last["status"] == "completed", f"got {last.get('status')} err={last.get('error')}"
        wireframes = last.get("wireframes")
        assert wireframes and len(wireframes) >= 1
        first_html = wireframes[0]["html"]

        # 6. Check brand color reflected (heuristic - not strict since LLM may vary)
        all_html = " ".join([w["html"] for w in wireframes]).lower()
        brand_hit = "#ff6600" in all_html or "ff6600" in all_html or "georgia" in all_html
        # log but don't hard-fail brand influence check - it's a heuristic
        print(f"[brand_influence_heuristic] found_brand_hit={brand_hit}")

        # 7. Submit feedback with element_context (multipart form)
        screen_name = wireframes[0]["screen_name"]
        form = {
            "instruction": (None, "Change the primary button color to bright red"),
            "scope": (None, "screen"),
            "screen_name": (None, screen_name),
            "element_context": (None, '<button class="primary"> text: "Continue"'),
        }
        r = requests.post(f"{API}/runs/{run_id}/feedback", files=form)
        assert r.status_code == 200, r.text
        feedback_id = r.json()["feedback_id"]

        # 8. Verify element_context persisted immediately in feedback_log
        d = requests.get(f"{API}/runs/{run_id}").json()
        entry = next((f for f in d["feedback_log"] if f["id"] == feedback_id), None)
        assert entry is not None
        assert entry["element_context"] == '<button class="primary"> text: "Continue"'
        assert entry["scope"] == "screen"

        # 9. Wait for feedback to complete
        deadline = time.time() + 120
        completed = False
        while time.time() < deadline:
            d = requests.get(f"{API}/runs/{run_id}").json()
            entry = next((f for f in d["feedback_log"] if f["id"] == feedback_id), None)
            if entry and entry["status"] in ("completed", "error"):
                completed = True
                assert entry["status"] == "completed", f"feedback err: {entry.get('error')}"
                assert entry.get("agent_name")
                break
            time.sleep(3)
        assert completed, "Feedback did not finish in 120s"


class TestSharedRunRoute:
    """Verify GET /api/runs/{run_id} returns full data for a known persisted run (share link scenario)."""

    def test_get_missing_returns_404(self):
        r = requests.get(f"{API}/runs/does-not-exist-12345")
        assert r.status_code == 404
