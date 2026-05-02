"""Tests for Workflow Orchestration API (v2.0).

Covers: DAG validation, CRUD, run creation, state transitions, retry, timeout, approval.

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
Each test runs in a rolled-back transaction so tests are isolated.
"""

from __future__ import annotations

import uuid

import pytest

from models import Runtime, WorkflowDefinition, WorkflowNode, WorkflowEdge, Run, Task, Approval


def _seed_runtime(session, name: str | None = None) -> Runtime:
    """Create a runtime and return it."""
    rt = Runtime(
        id=uuid.uuid4(),
        name=name or f"rt-{uuid.uuid4().hex[:6]}",
        type="test",
        status="active",
    )
    session.add(rt)
    session.flush()
    return rt


# ---------------------------------------------------------------------------
# DAG Validation Tests
# ---------------------------------------------------------------------------


class TestDAGValidation:
    def test_create_linear_workflow(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "linear-wf",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "Step A"},
                {"node_id": "b", "title": "Step B"},
                {"node_id": "c", "title": "Step C"},
            ],
            "edges": [
                {"from_node": "a", "to_node": "b"},
                {"from_node": "b", "to_node": "c"},
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "linear-wf"
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2

    def test_create_diamond_workflow(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "diamond-wf",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "start", "title": "Start"},
                {"node_id": "left", "title": "Left"},
                {"node_id": "right", "title": "Right"},
                {"node_id": "end", "title": "End"},
            ],
            "edges": [
                {"from_node": "start", "to_node": "left"},
                {"from_node": "start", "to_node": "right"},
                {"from_node": "left", "to_node": "end"},
                {"from_node": "right", "to_node": "end"},
            ],
        })
        assert resp.status_code == 201
        assert len(resp.json()["edges"]) == 4

    def test_reject_cycle(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "cycle-wf",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A"},
                {"node_id": "b", "title": "B"},
            ],
            "edges": [
                {"from_node": "a", "to_node": "b"},
                {"from_node": "b", "to_node": "a"},
            ],
        })
        assert resp.status_code == 400
        assert "cycle" in resp.json()["detail"].lower()

    def test_reject_self_loop(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "self-loop",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
            "edges": [{"from_node": "a", "to_node": "a"}],
        })
        assert resp.status_code == 400

    def test_reject_duplicate_node_id(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "dup-nodes",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A1"},
                {"node_id": "a", "title": "A2"},
            ],
        })
        assert resp.status_code == 400
        assert "duplicate" in resp.json()["detail"].lower()

    def test_reject_unknown_edge_source(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "bad-edge",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
            "edges": [{"from_node": "x", "to_node": "a"}],
        })
        assert resp.status_code == 400
        assert "unknown" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# CRUD Tests
# ---------------------------------------------------------------------------


class TestWorkflowCRUD:
    def test_list_workflows(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        c.post("/api/workflows", json={
            "name": "list-test",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        resp = c.get("/api/workflows")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(w["name"] == "list-test" for w in data["items"])

    def test_get_workflow(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        create = c.post("/api/workflows", json={
            "name": "get-test",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        wf_id = create.json()["id"]
        resp = c.get(f"/api/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "get-test"

    def test_get_workflow_not_found(self, client):
        c = client
        resp = c.get(f"/api/workflows/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_update_workflow(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        create = c.post("/api/workflows", json={
            "name": "update-test",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        wf_id = create.json()["id"]
        resp = c.put(f"/api/workflows/{wf_id}", json={
            "name": "updated-name",
            "description": "new desc",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated-name"
        assert resp.json()["description"] == "new desc"
        assert resp.json()["version"] == 2

    def test_delete_workflow(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        create = c.post("/api/workflows", json={
            "name": "delete-test",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        wf_id = create.json()["id"]
        resp = c.delete(f"/api/workflows/{wf_id}")
        assert resp.status_code == 204
        resp = c.get(f"/api/workflows/{wf_id}")
        assert resp.status_code == 404

    def test_filter_by_runtime(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        c.post("/api/workflows", json={
            "name": "filter-test",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        resp = c.get(f"/api/workflows?runtime_id={rt.id}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# Run Creation & State Transition Tests
# ---------------------------------------------------------------------------


class TestWorkflowRuns:
    def _create_workflow(self, c, rt) -> str:
        resp = c.post("/api/workflows", json={
            "name": "run-test",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "Step A"},
                {"node_id": "b", "title": "Step B"},
            ],
            "edges": [{"from_node": "a", "to_node": "b"}],
        })
        return resp.json()["id"]

    def test_start_run(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf_id = self._create_workflow(c, rt)
        resp = c.post(f"/api/workflows/{wf_id}/runs", json={
            "input_summary": "test run",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "running"
        assert data["workflow_id"] == wf_id
        assert len(data["tasks"]) == 2
        root_task = next(t for t in data["tasks"] if t["node_id"] == "a")
        assert root_task["status"] == "running"
        dep_task = next(t for t in data["tasks"] if t["node_id"] == "b")
        assert dep_task["status"] == "pending"

    def test_complete_task_advances(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf_id = self._create_workflow(c, rt)
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        run_id = run["id"]
        task_a = next(t for t in run["tasks"] if t["node_id"] == "a")

        resp = c.post(
            f"/api/workflows/{wf_id}/runs/{run_id}/tasks/{task_a['id']}/complete",
            json={"output_summary": "done"},
        )
        assert resp.status_code == 200
        data = resp.json()
        updated_a = next(t for t in data["tasks"] if t["node_id"] == "a")
        assert updated_a["status"] == "completed"
        updated_b = next(t for t in data["tasks"] if t["node_id"] == "b")
        assert updated_b["status"] == "running"

    def test_run_completes_when_all_tasks_done(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf_id = self._create_workflow(c, rt)
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        run_id = run["id"]
        task_a = next(t for t in run["tasks"] if t["node_id"] == "a")

        resp1 = c.post(
            f"/api/workflows/{wf_id}/runs/{run_id}/tasks/{task_a['id']}/complete",
            json={},
        )
        task_b = next(t for t in resp1.json()["tasks"] if t["node_id"] == "b")
        resp2 = c.post(
            f"/api/workflows/{wf_id}/runs/{run_id}/tasks/{task_b['id']}/complete",
            json={},
        )
        assert resp2.json()["status"] == "completed"

    def test_fail_task(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf_id = self._create_workflow(c, rt)
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        run_id = run["id"]
        task_a = next(t for t in run["tasks"] if t["node_id"] == "a")

        resp = c.post(
            f"/api/workflows/{wf_id}/runs/{run_id}/tasks/{task_a['id']}/fail",
            json={"error_summary": "something broke"},
        )
        assert resp.status_code == 200
        updated_a = next(t for t in resp.json()["tasks"] if t["node_id"] == "a")
        assert updated_a["status"] in ("pending", "failed")

    def test_list_runs(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf_id = self._create_workflow(c, rt)
        c.post(f"/api/workflows/{wf_id}/runs", json={})
        resp = c.get(f"/api/workflows/{wf_id}/runs")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_get_run_detail(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf_id = self._create_workflow(c, rt)
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run_id = run_resp.json()["id"]
        resp = c.get(f"/api/workflows/{wf_id}/runs/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == run_id


# ---------------------------------------------------------------------------
# Retry Policy Tests
# ---------------------------------------------------------------------------


class TestRetryPolicy:
    def test_retry_on_failure(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "retry-test",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A", "retry_policy": {"max_retries": 2, "backoff_seconds": 0}},
            ],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        run_id = run["id"]
        task_a = run["tasks"][0]

        resp1 = c.post(
            f"/api/workflows/{wf_id}/runs/{run_id}/tasks/{task_a['id']}/fail",
            json={"error_summary": "fail 1"},
        )
        updated = resp1.json()["tasks"][0]
        assert updated["status"] == "pending"
        assert updated["retry_count"] == 1

        resp2 = c.get(f"/api/workflows/{wf_id}/runs/{run_id}")
        task_a2 = resp2.json()["tasks"][0]
        assert task_a2["status"] == "running"

        resp3 = c.post(
            f"/api/workflows/{wf_id}/runs/{run_id}/tasks/{task_a2['id']}/fail",
            json={"error_summary": "fail 2"},
        )
        updated2 = resp3.json()["tasks"][0]
        assert updated2["retry_count"] == 2

    def test_retry_exhausted(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "retry-exhaust",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A", "retry_policy": {"max_retries": 0, "backoff_seconds": 0}},
            ],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        run_id = run["id"]
        task_a = run["tasks"][0]

        resp1 = c.post(
            f"/api/workflows/{wf_id}/runs/{run_id}/tasks/{task_a['id']}/fail",
            json={"error_summary": "permanent fail"},
        )
        run_data = resp1.json()
        assert run_data["status"] == "failed"
        assert run_data["tasks"][0]["status"] == "failed"


# ---------------------------------------------------------------------------
# Timeout Tests
# ---------------------------------------------------------------------------


class TestTimeoutPolicy:
    def test_timeout_config_stored(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "timeout-test",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A", "timeout_seconds": 30},
            ],
        })
        assert resp.status_code == 201
        node = resp.json()["nodes"][0]
        assert node["timeout_seconds"] == 30


# ---------------------------------------------------------------------------
# Approval Node Tests
# ---------------------------------------------------------------------------


class TestApprovalNode:
    def test_approval_node_blocks(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "approval-test",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "Do work"},
                {"node_id": "approve", "title": "Approve", "task_type": "approval"},
            ],
            "edges": [{"from_node": "a", "to_node": "approve"}],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        run_id = run["id"]

        task_a = next(t for t in run["tasks"] if t["node_id"] == "a")
        resp1 = c.post(
            f"/api/workflows/{wf_id}/runs/{run_id}/tasks/{task_a['id']}/complete",
            json={},
        )
        approve_task = next(t for t in resp1.json()["tasks"] if t["node_id"] == "approve")
        assert approve_task["status"] == "waiting_approval"

    def test_approval_resolved_advances(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "approval-resolve",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "approve", "title": "Approve", "task_type": "approval"},
                {"node_id": "after", "title": "After approval"},
            ],
            "edges": [{"from_node": "approve", "to_node": "after"}],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        run_id = run["id"]
        approve_task = next(t for t in run["tasks"] if t["node_id"] == "approve")

        approval = session.query(Approval).filter(Approval.task_id == uuid.UUID(approve_task["id"])).first()
        assert approval is not None
        assert approval.status == "pending"
        approval.status = "approved"
        session.commit()

        resp1 = c.post(f"/api/workflows/{wf_id}/runs/{run_id}/advance", json={})
        data = resp1.json()
        updated_approve = next(t for t in data["tasks"] if t["node_id"] == "approve")
        assert updated_approve["status"] == "completed"
        after_task = next(t for t in data["tasks"] if t["node_id"] == "after")
        assert after_task["status"] == "running"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_workflow_with_no_edges(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "no-edges",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A"},
                {"node_id": "b", "title": "B"},
            ],
            "edges": [],
        })
        assert resp.status_code == 201
        run_resp = c.post(f"/api/workflows/{resp.json()['id']}/runs", json={})
        statuses = {t["status"] for t in run_resp.json()["tasks"]}
        assert statuses == {"running"}

    def test_advance_completed_run_fails(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "advance-done",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        run_id = run["id"]

        c.post(
            f"/api/workflows/{wf_id}/runs/{run_id}/tasks/{run['tasks'][0]['id']}/complete",
            json={},
        )
        resp2 = c.post(f"/api/workflows/{wf_id}/runs/{run_id}/advance", json={})
        assert resp2.status_code == 400

    def test_complete_non_running_task_fails(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "complete-pending",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A"},
                {"node_id": "b", "title": "B"},
            ],
            "edges": [{"from_node": "a", "to_node": "b"}],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        task_b = next(t for t in run["tasks"] if t["node_id"] == "b")

        resp2 = c.post(
            f"/api/workflows/{wf_id}/runs/{run['id']}/tasks/{task_b['id']}/complete",
            json={},
        )
        assert resp2.status_code == 400
