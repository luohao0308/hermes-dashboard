"""Integration tests for the generic Run and Runtime APIs.

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
Example: TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_workflow_test

Each test runs in a rolled-back transaction so tests are isolated.
"""

from __future__ import annotations

import uuid

import pytest


# ---------------------------------------------------------------------------
# Runtime API
# ---------------------------------------------------------------------------

class TestRuntimesAPI:
    def test_create_runtime(self, client):
        resp = client.post("/api/runtimes", json={
            "name": "test-runtime",
            "type": "agent",
            "status": "active",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-runtime"
        assert data["type"] == "agent"
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data

    def test_list_runtimes(self, client):
        client.post("/api/runtimes", json={"name": "rt-a", "type": "agent"})
        client.post("/api/runtimes", json={"name": "rt-b", "type": "connector"})
        resp = client.get("/api/runtimes")
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()]
        assert "rt-a" in names
        assert "rt-b" in names

    def test_list_runtimes_filter_status(self, client):
        client.post("/api/runtimes", json={"name": "rt-active", "status": "active"})
        client.post("/api/runtimes", json={"name": "rt-paused", "status": "paused"})
        resp = client.get("/api/runtimes", params={"status": "paused"})
        assert resp.status_code == 200
        assert all(r["status"] == "paused" for r in resp.json())

    def test_create_runtime_validation_error(self, client):
        resp = client.post("/api/runtimes", json={"name": "", "type": "agent"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Run CRUD API
# ---------------------------------------------------------------------------

class TestRunsAPI:
    def _create_runtime(self, client) -> str:
        resp = client.post("/api/runtimes", json={"name": f"rt-{uuid.uuid4().hex[:8]}", "type": "agent"})
        return resp.json()["id"]

    def test_create_run(self, client):
        rt_id = self._create_runtime(client)
        resp = client.post("/api/runs", json={
            "runtime_id": rt_id,
            "title": "test run",
            "input_summary": "do something",
            "status": "running",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "test run"
        assert data["runtime_id"] == rt_id
        assert data["status"] == "running"
        assert data["started_at"] is not None

    def test_create_run_invalid_runtime(self, client):
        resp = client.post("/api/runs", json={
            "runtime_id": str(uuid.uuid4()),
            "title": "bad run",
        })
        assert resp.status_code == 400
        assert "Runtime" in resp.json()["detail"]

    def test_get_run(self, client):
        rt_id = self._create_runtime(client)
        create_resp = client.post("/api/runs", json={"runtime_id": rt_id, "title": "get me"})
        run_id = create_resp.json()["id"]

        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == run_id
        assert resp.json()["title"] == "get me"

    def test_get_run_not_found(self, client):
        resp = client.get(f"/api/runs/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_list_runs(self, client):
        rt_id = self._create_runtime(client)
        client.post("/api/runs", json={"runtime_id": rt_id, "title": "run-1"})
        client.post("/api/runs", json={"runtime_id": rt_id, "title": "run-2"})
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    def test_list_runs_filter_status(self, client):
        rt_id = self._create_runtime(client)
        client.post("/api/runs", json={"runtime_id": rt_id, "title": "queued-run", "status": "queued"})
        client.post("/api/runs", json={"runtime_id": rt_id, "title": "done-run", "status": "completed"})
        resp = client.get("/api/runs", params={"status": "queued"})
        assert resp.status_code == 200
        assert all(r["status"] == "queued" for r in resp.json()["items"])

    def test_list_runs_filter_runtime(self, client):
        rt1 = self._create_runtime(client)
        rt2 = self._create_runtime(client)
        client.post("/api/runs", json={"runtime_id": rt1, "title": "rt1-run"})
        client.post("/api/runs", json={"runtime_id": rt2, "title": "rt2-run"})
        resp = client.get("/api/runs", params={"runtime_id": rt1})
        assert resp.status_code == 200
        assert all(r["runtime_id"] == rt1 for r in resp.json()["items"])

    def test_list_runs_pagination(self, client):
        rt_id = self._create_runtime(client)
        for i in range(5):
            client.post("/api/runs", json={"runtime_id": rt_id, "title": f"page-run-{i}"})
        resp = client.get("/api/runs", params={"limit": 2, "offset": 0})
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_update_run(self, client):
        rt_id = self._create_runtime(client)
        create_resp = client.post("/api/runs", json={"runtime_id": rt_id, "title": "update me"})
        run_id = create_resp.json()["id"]

        resp = client.patch(f"/api/runs/{run_id}", json={
            "title": "updated title",
            "status": "completed",
            "output_summary": "all done",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "updated title"
        assert data["status"] == "completed"
        assert data["output_summary"] == "all done"
        assert data["ended_at"] is not None
        assert data["duration_ms"] is not None

    def test_update_run_not_found(self, client):
        resp = client.patch(f"/api/runs/{uuid.uuid4()}", json={"status": "completed"})
        assert resp.status_code == 404

    def test_update_run_partial(self, client):
        rt_id = self._create_runtime(client)
        run_id = client.post("/api/runs", json={"runtime_id": rt_id, "title": "partial"}).json()["id"]

        resp = client.patch(f"/api/runs/{run_id}", json={"total_tokens": 1500})
        assert resp.status_code == 200
        assert resp.json()["title"] == "partial"  # unchanged
        assert resp.json()["total_tokens"] == 1500


# ---------------------------------------------------------------------------
# Span API
# ---------------------------------------------------------------------------

class TestSpansAPI:
    def _create_run(self, client) -> str:
        rt_resp = client.post("/api/runtimes", json={"name": f"rt-{uuid.uuid4().hex[:8]}", "type": "agent"})
        run_resp = client.post("/api/runs", json={"runtime_id": rt_resp.json()["id"], "title": "span test"})
        return run_resp.json()["id"]

    def test_create_span(self, client):
        run_id = self._create_run(client)
        resp = client.post(f"/api/runs/{run_id}/spans", json={
            "span_type": "llm",
            "title": "GPT-4 call",
            "status": "completed",
            "model_name": "gpt-4",
            "input_tokens": 500,
            "output_tokens": 200,
            "cost": 0.021,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["span_type"] == "llm"
        assert data["title"] == "GPT-4 call"
        assert data["model_name"] == "gpt-4"
        assert data["input_tokens"] == 500
        assert data["run_id"] == run_id

    def test_create_span_run_not_found(self, client):
        resp = client.post(f"/api/runs/{uuid.uuid4()}/spans", json={
            "span_type": "tool", "title": "bad",
        })
        assert resp.status_code == 404

    def test_create_multiple_spans(self, client):
        run_id = self._create_run(client)
        client.post(f"/api/runs/{run_id}/spans", json={"span_type": "llm", "title": "call-1"})
        client.post(f"/api/runs/{run_id}/spans", json={"span_type": "tool", "title": "call-2"})
        client.post(f"/api/runs/{run_id}/spans", json={"span_type": "guardrail", "title": "check-1"})

        resp = client.get(f"/api/runs/{run_id}/trace")
        assert resp.status_code == 200
        assert len(resp.json()["spans"]) == 3


# ---------------------------------------------------------------------------
# Trace API
# ---------------------------------------------------------------------------

class TestTraceAPI:
    def test_get_trace(self, client):
        rt_resp = client.post("/api/runtimes", json={"name": f"rt-{uuid.uuid4().hex[:8]}", "type": "agent"})
        rt_id = rt_resp.json()["id"]
        run_resp = client.post("/api/runs", json={"runtime_id": rt_id, "title": "trace test"})
        run_id = run_resp.json()["id"]

        client.post(f"/api/runs/{run_id}/spans", json={"span_type": "llm", "title": "step-1"})
        client.post(f"/api/runs/{run_id}/spans", json={"span_type": "tool", "title": "step-2"})

        resp = client.get(f"/api/runs/{run_id}/trace")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run"]["id"] == run_id
        assert data["run"]["title"] == "trace test"
        assert len(data["spans"]) == 2
        assert data["spans"][0]["title"] == "step-1"
        assert data["spans"][1]["title"] == "step-2"

    def test_get_trace_not_found(self, client):
        resp = client.get(f"/api/runs/{uuid.uuid4()}/trace")
        assert resp.status_code == 404

    def test_get_trace_empty(self, client):
        rt_resp = client.post("/api/runtimes", json={"name": f"rt-{uuid.uuid4().hex[:8]}", "type": "agent"})
        run_resp = client.post("/api/runs", json={"runtime_id": rt_resp.json()["id"], "title": "empty trace"})
        run_id = run_resp.json()["id"]

        resp = client.get(f"/api/runs/{run_id}/trace")
        assert resp.status_code == 200
        assert resp.json()["spans"] == []


# ---------------------------------------------------------------------------
# End-to-end: write through API, read back through API
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_full_workflow(self, client):
        """Create runtime -> create run -> add spans -> update run -> read trace."""
        # 1. Create runtime
        rt = client.post("/api/runtimes", json={
            "name": "e2e-runtime",
            "type": "agent",
            "config_json": {"model": "gpt-4"},
        })
        assert rt.status_code == 201
        rt_id = rt.json()["id"]

        # 2. Create run
        run = client.post("/api/runs", json={
            "runtime_id": rt_id,
            "title": "e2e test run",
            "input_summary": "review PR #42",
        })
        assert run.status_code == 201
        run_id = run.json()["id"]

        # 3. Add spans
        s1 = client.post(f"/api/runs/{run_id}/spans", json={
            "span_type": "llm",
            "title": "analyze code",
            "model_name": "gpt-4",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost": 0.045,
        })
        assert s1.status_code == 201

        s2 = client.post(f"/api/runs/{run_id}/spans", json={
            "span_type": "tool",
            "title": "post comment",
            "tool_name": "github_comment",
        })
        assert s2.status_code == 201

        # 4. Update run to completed
        patch = client.patch(f"/api/runs/{run_id}", json={
            "status": "completed",
            "output_summary": "Found 2 issues",
            "total_tokens": 1500,
            "total_cost": 0.045,
        })
        assert patch.status_code == 200
        assert patch.json()["status"] == "completed"
        assert patch.json()["ended_at"] is not None
        assert patch.json()["duration_ms"] is not None

        # 5. Read back full trace
        trace = client.get(f"/api/runs/{run_id}/trace")
        assert trace.status_code == 200
        data = trace.json()
        assert data["run"]["status"] == "completed"
        assert data["run"]["total_tokens"] == 1500
        assert len(data["spans"]) == 2
        assert data["spans"][0]["cost"] == 0.045

        # 6. Verify list filters work
        listed = client.get("/api/runs", params={"runtime_id": rt_id, "status": "completed"})
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1
        assert any(r["id"] == run_id for r in listed.json()["items"])
