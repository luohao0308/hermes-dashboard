"""Tests for Workflow Nesting functionality (v2.0).

Covers: child workflow launching, parent_run_id tracking, cascade controls,
is_reusable filtering, nesting validation, and child run polling.

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
Each test runs in a rolled-back transaction so tests are isolated.
"""

from __future__ import annotations

import uuid

import pytest

from models import Runtime, WorkflowDefinition, WorkflowNode, WorkflowEdge, Run, Task


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


def _create_reusable_workflow(c, session, rt, name: str) -> str:
    """Create a reusable workflow and return its ID."""
    resp = c.post("/api/workflows", json={
        "name": name,
        "runtime_id": str(rt.id),
        "is_reusable": True,
        "nodes": [
            {"node_id": "child_start", "title": "Child Start"},
            {"node_id": "child_end", "title": "Child End"},
        ],
        "edges": [{"from_node": "child_start", "to_node": "child_end"}],
    })
    assert resp.status_code == 201
    return resp.json()["id"]


class TestWorkflowNestingValidation:
    """Tests for validating nested workflow definitions."""

    def test_create_workflow_with_subworkflow_node(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        child_id = _create_reusable_workflow(c, session, rt, "child-workflow")

        resp = c.post("/api/workflows", json={
            "name": "parent-workflow",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "start", "title": "Start"},
                {
                    "node_id": "subworkflow",
                    "title": "Call Child",
                    "task_type": "subworkflow",
                    "child_workflow_id": child_id,
                },
                {"node_id": "end", "title": "End"},
            ],
            "edges": [
                {"from_node": "start", "to_node": "subworkflow"},
                {"from_node": "subworkflow", "to_node": "end"},
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["nodes"]) == 3
        sub_node = next(n for n in data["nodes"] if n["node_id"] == "subworkflow")
        assert sub_node["task_type"] == "subworkflow"
        assert sub_node["child_workflow_id"] == child_id

    def test_reject_subworkflow_node_without_child_id(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        resp = c.post("/api/workflows", json={
            "name": "invalid-subworkflow",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "sub", "title": "Sub", "task_type": "subworkflow"},
            ],
        })
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any("child_workflow_id" in str(e) for e in detail)

    def test_reject_circular_workflow_reference(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        wf1_resp = c.post("/api/workflows", json={
            "name": "wf1",
            "runtime_id": str(rt.id),
            "is_reusable": True,
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        wf1_id = wf1_resp.json()["id"]

        wf2_resp = c.post("/api/workflows", json={
            "name": "wf2",
            "runtime_id": str(rt.id),
            "is_reusable": True,
            "nodes": [
                {"node_id": "b", "title": "B"},
                {
                    "node_id": "call_wf1",
                    "title": "Call WF1",
                    "task_type": "subworkflow",
                    "child_workflow_id": wf1_id,
                },
            ],
            "edges": [{"from_node": "b", "to_node": "call_wf1"}],
        })
        wf2_id = wf2_resp.json()["id"]

        update_resp = c.put(f"/api/workflows/{wf1_id}", json={
            "nodes": [
                {
                    "node_id": "a",
                    "title": "A",
                    "task_type": "subworkflow",
                    "child_workflow_id": wf2_id,
                },
            ],
        })
        assert update_resp.status_code == 400
        assert "circular" in update_resp.json()["detail"].lower()

    def test_reject_self_reference(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        wf_resp = c.post("/api/workflows", json={
            "name": "self-ref",
            "runtime_id": str(rt.id),
            "is_reusable": True,
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        wf_id = wf_resp.json()["id"]

        update_resp = c.put(f"/api/workflows/{wf_id}", json={
            "nodes": [
                {
                    "node_id": "a",
                    "title": "A",
                    "task_type": "subworkflow",
                    "child_workflow_id": wf_id,
                },
            ],
        })
        assert update_resp.status_code == 400
        assert "circular" in update_resp.json()["detail"].lower()

    def test_reject_missing_child_workflow(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        fake_id = str(uuid.uuid4())
        resp = c.post("/api/workflows", json={
            "name": "missing-child",
            "runtime_id": str(rt.id),
            "nodes": [
                {
                    "node_id": "sub",
                    "title": "Sub",
                    "task_type": "subworkflow",
                    "child_workflow_id": fake_id,
                },
            ],
        })
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()

    def test_reject_excessive_nesting_depth(self, client):
        """With 2-level max nesting:
        - Parent -> Child (depth 1): allowed
        - Parent -> Child -> Grandchild (depth 2+): rejected

        i=0: depth-0 (simple node) → success
        i=1: depth-1 → depth-0 (no subworkflow) → success
        i=2: depth-2 → depth-1 (HAS subworkflow) → rejected
        """
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        prev_id = None
        for i in range(5):
            nodes = [{"node_id": "a", "title": "A"}]
            if prev_id:
                nodes[0] = {
                    "node_id": "a",
                    "title": "A",
                    "task_type": "subworkflow",
                    "child_workflow_id": prev_id,
                }
            resp = c.post("/api/workflows", json={
                "name": f"depth-{i}",
                "runtime_id": str(rt.id),
                "is_reusable": True,
                "nodes": nodes,
            })
            if i < 2:
                # i=0: no child → success
                # i=1: child is depth-0 (no subworkflow) → success
                assert resp.status_code == 201, f"i={i} should succeed: {resp.text}"
                prev_id = resp.json()["id"]
            else:
                # i=2+: child has subworkflow node → exceeds depth 2
                assert resp.status_code == 400, f"i={i} should fail with 400, got {resp.status_code}"
                assert "depth" in resp.json()["detail"].lower()


class TestIsReusableFlag:
    """Tests for is_reusable workflow flag."""

    def test_create_reusable_workflow(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        resp = c.post("/api/workflows", json={
            "name": "reusable-wf",
            "runtime_id": str(rt.id),
            "is_reusable": True,
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        assert resp.status_code == 201
        assert resp.json()["is_reusable"] is True

    def test_default_not_reusable(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        resp = c.post("/api/workflows", json={
            "name": "regular-wf",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        assert resp.status_code == 201
        assert resp.json()["is_reusable"] is False

    def test_filter_by_reusable(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        c.post("/api/workflows", json={
            "name": "reusable-1",
            "runtime_id": str(rt.id),
            "is_reusable": True,
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        c.post("/api/workflows", json={
            "name": "not-reusable-1",
            "runtime_id": str(rt.id),
            "is_reusable": False,
            "nodes": [{"node_id": "a", "title": "A"}],
        })

        resp = c.get("/api/workflows?is_reusable=true")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(wf["is_reusable"] for wf in items)
        assert any(wf["name"] == "reusable-1" for wf in items)

    def test_update_reusable_flag(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        create = c.post("/api/workflows", json={
            "name": "toggle-reusable",
            "runtime_id": str(rt.id),
            "is_reusable": False,
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        wf_id = create.json()["id"]

        update = c.put(f"/api/workflows/{wf_id}", json={"is_reusable": True})
        assert update.status_code == 200
        assert update.json()["is_reusable"] is True


class TestParentRunId:
    """Tests for parent_run_id tracking."""

    def _create_parent_workflow(self, c, rt, child_id):
        resp = c.post("/api/workflows", json={
            "name": "parent-wf",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "start", "title": "Start"},
                {
                    "node_id": "sub",
                    "title": "Call Child",
                    "task_type": "subworkflow",
                    "child_workflow_id": child_id,
                },
            ],
            "edges": [{"from_node": "start", "to_node": "sub"}],
        })
        return resp.json()["id"]

    def test_child_run_has_parent_run_id(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        child_wf_id = _create_reusable_workflow(c, session, rt, "child-wf")
        parent_wf_id = self._create_parent_workflow(c, rt, child_wf_id)

        run_resp = c.post(f"/api/workflows/{parent_wf_id}/runs", json={})
        assert run_resp.status_code == 201
        parent_run = run_resp.json()

        # Advance to trigger subworkflow launch
        start_task = next(t for t in parent_run["tasks"] if t["node_id"] == "start")
        c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/tasks/{start_task['id']}/complete",
            json={},
        )

        # Check child run was created with parent_run_id
        child_runs = session.query(Run).filter(Run.parent_run_id != None).all()
        assert len(child_runs) >= 1

    def test_list_runs_by_parent(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        wf_resp = c.post("/api/workflows", json={
            "name": "test-wf",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        wf_id = wf_resp.json()["id"]

        parent_run = Run(
            id=uuid.uuid4(),
            runtime_id=rt.id,
            workflow_id=uuid.UUID(wf_id),
            title="Parent Run",
            status="running",
        )
        session.add(parent_run)
        session.flush()

        child_run = Run(
            id=uuid.uuid4(),
            runtime_id=rt.id,
            workflow_id=uuid.UUID(wf_id),
            parent_run_id=parent_run.id,
            title="Child Run",
            status="running",
        )
        session.add(child_run)
        session.flush()

        resp = c.get(f"/api/runs?parent_run_id={parent_run.id}")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(r["id"] == str(child_run.id) for r in items)


class TestCascadeControls:
    """Tests for cascading pause/resume/cancel to child runs."""

    def _create_nested_setup(self, c, session, rt):
        child_wf_id = _create_reusable_workflow(c, session, rt, "child-wf")
        parent_resp = c.post("/api/workflows", json={
            "name": "parent-wf",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "start", "title": "Start"},
                {
                    "node_id": "sub",
                    "title": "Call Child",
                    "task_type": "subworkflow",
                    "child_workflow_id": child_wf_id,
                },
                {"node_id": "end", "title": "End"},
            ],
            "edges": [
                {"from_node": "start", "to_node": "sub"},
                {"from_node": "sub", "to_node": "end"},
            ],
        })
        parent_wf_id = parent_resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{parent_wf_id}/runs", json={})
        return parent_wf_id, run_resp.json()

    def test_pause_cascades_to_child_runs(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        parent_wf_id, parent_run = self._create_nested_setup(c, session, rt)

        # Launch child run by completing start task
        start_task = next(t for t in parent_run["tasks"] if t["node_id"] == "start")
        c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/tasks/{start_task['id']}/complete",
            json={},
        )

        # Pause parent
        pause_resp = c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/pause",
            json={},
        )
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "paused"

        # Verify child run also paused
        child_runs = session.query(Run).filter(
            Run.parent_run_id == uuid.UUID(parent_run["id"])
        ).all()
        assert all(cr.status == "paused" for cr in child_runs)

    def test_resume_cascades_to_child_runs(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        parent_wf_id, parent_run = self._create_nested_setup(c, session, rt)

        # Launch and pause
        start_task = next(t for t in parent_run["tasks"] if t["node_id"] == "start")
        c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/tasks/{start_task['id']}/complete",
            json={},
        )
        c.post(f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/pause", json={})

        # Resume parent
        resume_resp = c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/resume",
            json={},
        )
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "running"

        # Verify child run also resumed
        child_runs = session.query(Run).filter(
            Run.parent_run_id == uuid.UUID(parent_run["id"])
        ).all()
        assert all(cr.status == "running" for cr in child_runs)

    def test_cancel_cascades_to_child_runs(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        parent_wf_id, parent_run = self._create_nested_setup(c, session, rt)

        # Launch child run
        start_task = next(t for t in parent_run["tasks"] if t["node_id"] == "start")
        c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/tasks/{start_task['id']}/complete",
            json={},
        )

        # Cancel parent
        cancel_resp = c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/cancel",
            json={"reason": "operator cancel"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

        # Verify child run also cancelled
        child_runs = session.query(Run).filter(
            Run.parent_run_id == uuid.UUID(parent_run["id"])
        ).all()
        assert all(cr.status == "cancelled" for cr in child_runs)


class TestChildRunPolling:
    """Tests for polling child run status."""

    def test_child_run_completion_advances_parent(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        child_wf_id = _create_reusable_workflow(c, session, rt, "child-wf")

        parent_resp = c.post("/api/workflows", json={
            "name": "parent-wf",
            "runtime_id": str(rt.id),
            "nodes": [
                {
                    "node_id": "sub",
                    "title": "Call Child",
                    "task_type": "subworkflow",
                    "child_workflow_id": child_wf_id,
                },
            ],
        })
        parent_wf_id = parent_resp.json()["id"]

        run_resp = c.post(f"/api/workflows/{parent_wf_id}/runs", json={})
        parent_run = run_resp.json()

        # Manually complete the child run
        child_runs = session.query(Run).filter(
            Run.parent_run_id == uuid.UUID(parent_run["id"])
        ).all()
        for child_run in child_runs:
            child_run.status = "completed"
            for task in session.query(Task).filter(Task.run_id == child_run.id).all():
                task.status = "completed"

        # Advance parent - should complete subworkflow task
        advance_resp = c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/advance",
            json={},
        )
        assert advance_resp.status_code == 200
        sub_task = next(t for t in advance_resp.json()["tasks"] if t["node_id"] == "sub")
        assert sub_task["status"] == "completed"

    def test_child_run_failure_fails_parent(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        child_wf_id = _create_reusable_workflow(c, session, rt, "child-wf")

        parent_resp = c.post("/api/workflows", json={
            "name": "parent-wf",
            "runtime_id": str(rt.id),
            "nodes": [
                {
                    "node_id": "sub",
                    "title": "Call Child",
                    "task_type": "subworkflow",
                    "child_workflow_id": child_wf_id,
                },
            ],
        })
        parent_wf_id = parent_resp.json()["id"]

        run_resp = c.post(f"/api/workflows/{parent_wf_id}/runs", json={})
        parent_run = run_resp.json()

        # Fail the child run
        child_runs = session.query(Run).filter(
            Run.parent_run_id == uuid.UUID(parent_run["id"])
        ).all()
        for child_run in child_runs:
            child_run.status = "failed"
            child_run.error_summary = "Child failed"

        # Advance parent - should fail subworkflow task
        advance_resp = c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/advance",
            json={},
        )
        assert advance_resp.status_code == 200
        sub_task = next(t for t in advance_resp.json()["tasks"] if t["node_id"] == "sub")
        assert sub_task["status"] == "failed"


class TestNestedWorkflowRetry:
    """Tests for retrying nested workflows."""

    def test_retry_parent_retries_child(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        child_wf_id = _create_reusable_workflow(c, session, rt, "child-wf")

        parent_resp = c.post("/api/workflows", json={
            "name": "parent-wf",
            "runtime_id": str(rt.id),
            "nodes": [
                {
                    "node_id": "sub",
                    "title": "Call Child",
                    "task_type": "subworkflow",
                    "child_workflow_id": child_wf_id,
                },
            ],
        })
        parent_wf_id = parent_resp.json()["id"]

        run_resp = c.post(f"/api/workflows/{parent_wf_id}/runs", json={})
        parent_run = run_resp.json()

        # Fail the child run
        child_runs = session.query(Run).filter(
            Run.parent_run_id == uuid.UUID(parent_run["id"])
        ).all()
        for child_run in child_runs:
            child_run.status = "failed"
            child_run.error_summary = "Child failed"
            for task in session.query(Task).filter(Task.run_id == child_run.id).all():
                task.status = "failed"
                task.error_summary = "Task failed"

        # Advance to propagate failure
        c.post(f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/advance", json={})

        # Retry parent
        retry_resp = c.post(
            f"/api/workflows/{parent_wf_id}/runs/{parent_run['id']}/retry",
            json={},
        )
        assert retry_resp.status_code == 200
        assert retry_resp.json()["status"] == "running"

        # Verify child run is also running
        child_runs = session.query(Run).filter(
            Run.parent_run_id == uuid.UUID(parent_run["id"])
        ).all()
        assert all(cr.status == "running" for cr in child_runs)
