"""Tests for v2.1 Durable Execution.

Covers: worker pickup, stale lock recovery, retry backoff, dead-letter,
workflow timeout, approval timeout, concurrency limits.

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from models import Runtime, WorkflowDefinition, Run, Task, Approval, TraceSpan
from workers.workflow_worker import WorkflowWorker


def _seed_runtime(session, name: str | None = None) -> Runtime:
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
# Stale Lock Recovery
# ---------------------------------------------------------------------------


class TestStaleLockRecovery:
    def test_recover_stale_locks(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "stale-lock",
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
        task_a = next(t for t in run["tasks"] if t["node_id"] == "a")

        # Simulate stale lock
        task = session.get(Task, uuid.UUID(task_a["id"]))
        task.locked_by = "dead-worker"
        task.locked_at = datetime.now(timezone.utc) - timedelta(seconds=600)
        session.commit()

        worker = WorkflowWorker(stale_lock_seconds=300)
        worker._recover_stale_locks(session)

        session.refresh(task)
        assert task.locked_by is None
        assert task.locked_at is None


# ---------------------------------------------------------------------------
# Retry Backoff
# ---------------------------------------------------------------------------


class TestRetryBackoff:
    def test_retry_sets_next_retry_at(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "backoff-test",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A", "retry_policy": {"max_retries": 2, "backoff_seconds": 5.0}},
            ],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        task_a = run["tasks"][0]

        c.post(
            f"/api/workflows/{wf_id}/runs/{run['id']}/tasks/{task_a['id']}/fail",
            json={"error_summary": "fail 1"},
        )

        task = session.get(Task, uuid.UUID(task_a["id"]))
        assert task.next_retry_at is not None
        assert task.next_retry_at > datetime.now(timezone.utc)

    def test_backoff_exponential(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "backoff-exp",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A", "retry_policy": {"max_retries": 3, "backoff_seconds": 2.0}},
            ],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        task_a = run["tasks"][0]

        # First failure
        c.post(f"/api/workflows/{wf_id}/runs/{run['id']}/tasks/{task_a['id']}/fail", json={})
        task = session.get(Task, uuid.UUID(task_a["id"]))
        first_next = task.next_retry_at

        # Prepare for second failure
        task.status = "running"
        task.locked_by = "test"
        session.commit()

        c.post(f"/api/workflows/{wf_id}/runs/{run['id']}/tasks/{task_a['id']}/fail", json={})
        task = session.get(Task, uuid.UUID(task_a["id"]))
        second_next = task.next_retry_at

        assert second_next > first_next


# ---------------------------------------------------------------------------
# Dead Letter
# ---------------------------------------------------------------------------


class TestDeadLetter:
    def test_dead_letter_on_exhausted_retries(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "deadletter",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A", "retry_policy": {"max_retries": 0, "backoff_seconds": 0}},
            ],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        task_a = run["tasks"][0]

        c.post(f"/api/workflows/{wf_id}/runs/{run['id']}/tasks/{task_a['id']}/fail", json={})

        worker = WorkflowWorker()
        task = session.get(Task, uuid.UUID(task_a["id"]))
        task.locked_by = worker.worker_id
        session.commit()

        worker._handle_failed_tasks(session)

        task = session.get(Task, uuid.UUID(task_a["id"]))
        assert task.status == "dead_letter"

    def test_dead_letter_creates_trace_span(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "deadletter-span",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "a", "title": "A", "retry_policy": {"max_retries": 0, "backoff_seconds": 0}},
            ],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        task_a = run["tasks"][0]

        c.post(f"/api/workflows/{wf_id}/runs/{run['id']}/tasks/{task_a['id']}/fail", json={})
        worker = WorkflowWorker()
        task = session.get(Task, uuid.UUID(task_a["id"]))
        task.locked_by = worker.worker_id
        session.commit()

        worker._handle_failed_tasks(session)

        span = session.query(TraceSpan).filter(TraceSpan.span_type == "dead_letter").first()
        assert span is not None


# ---------------------------------------------------------------------------
# Workflow Timeout
# ---------------------------------------------------------------------------


class TestWorkflowTimeout:
    def test_workflow_timeout_cancels_tasks(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "wf-timeout",
            "runtime_id": str(rt.id),
            "timeout_seconds": 1,
            "nodes": [
                {"node_id": "a", "title": "A"},
                {"node_id": "b", "title": "B"},
            ],
            "edges": [{"from_node": "a", "to_node": "b"}],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()

        # Simulate time passing
        run_obj = session.get(Run, uuid.UUID(run["id"]))
        run_obj.started_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        session.commit()

        worker = WorkflowWorker()
        worker._check_workflow_timeouts(session)

        run_obj = session.get(Run, uuid.UUID(run["id"]))
        assert run_obj.status == "failed"
        tasks = session.query(Task).filter(Task.run_id == run_obj.id).all()
        for t in tasks:
            assert t.status in ("cancelled", "completed")


# ---------------------------------------------------------------------------
# Approval Timeout
# ---------------------------------------------------------------------------


class TestApprovalTimeout:
    def test_approval_timeout_fails_task(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "approval-timeout",
            "runtime_id": str(rt.id),
            "nodes": [
                {"node_id": "approve", "title": "Approve", "task_type": "approval",
                 "approval_timeout_seconds": 5},
            ],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        approve_task = run["tasks"][0]

        # Simulate time passing
        task = session.get(Task, uuid.UUID(approve_task["id"]))
        task.started_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        session.commit()

        worker = WorkflowWorker()
        worker._check_approval_timeouts(session)

        task = session.get(Task, uuid.UUID(approve_task["id"]))
        assert task.status == "failed"
        assert "timed out" in (task.error_summary or "")


# ---------------------------------------------------------------------------
# Concurrency Limits
# ---------------------------------------------------------------------------


class TestConcurrencyLimits:
    def test_max_concurrent_tasks_limits_parallelism(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "concurrency",
            "runtime_id": str(rt.id),
            "max_concurrent_tasks": 1,
            "nodes": [
                {"node_id": "a", "title": "A"},
                {"node_id": "b", "title": "B"},
            ],
            "edges": [],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()

        running = [t for t in run["tasks"] if t["status"] == "running"]
        assert len(running) <= 1


# ---------------------------------------------------------------------------
# Advisory Lock
# ---------------------------------------------------------------------------


class TestAdvisoryLock:
    def test_try_lock_task(self, client):
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        resp = c.post("/api/workflows", json={
            "name": "lock-test",
            "runtime_id": str(rt.id),
            "nodes": [{"node_id": "a", "title": "A"}],
        })
        wf_id = resp.json()["id"]
        run_resp = c.post(f"/api/workflows/{wf_id}/runs", json={})
        run = run_resp.json()
        task_a = run["tasks"][0]

        worker = WorkflowWorker()
        task = session.get(Task, uuid.UUID(task_a["id"]))
        locked = worker._try_lock_task(session, task)

        assert locked is True
        assert task.locked_by == worker.worker_id
        assert task.locked_at is not None
