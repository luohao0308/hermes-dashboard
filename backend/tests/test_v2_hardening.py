"""V2 Release Hardening Tests.

Tests worker behaviors using SQLite (no PostgreSQL required).
Advisory lock is mocked since it's PG-specific.

Covers: worker pickup, dependency gating, retry backoff, dead-letter,
approval creation, run completion, TraceSpan writes, concurrency limits.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, types
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    Runtime,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    Run,
    Task,
    Approval,
    TraceSpan,
)
from workers.workflow_worker import WorkflowWorker, _check_dependencies_met, _build_reverse_adjacency


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    # SQLite cannot render JSONB, UUID, or server_default="now()" — patch metadata
    from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB, UUID as PG_UUID
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, PG_JSONB):
                column.type = types.JSON()
            if isinstance(column.type, PG_UUID):
                column.type = types.Uuid(as_uuid=True)
            if column.server_default is not None and "now()" in str(column.server_default):
                column.server_default = None

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # Patch worker's _now_utc to return naive UTC (SQLite strips tzinfo)
    import workers.workflow_worker as ww
    original_now = ww._now_utc
    ww._now_utc = lambda: datetime.now(timezone.utc).replace(tzinfo=None)

    yield session

    session.close()
    engine.dispose()
    ww._now_utc = original_now


def _now():
    """Return naive UTC now — SQLite strips timezone info."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _seed_runtime(session, name: str | None = None) -> Runtime:
    rt = Runtime(
        id=uuid.uuid4(),
        name=name or f"rt-{uuid.uuid4().hex[:6]}",
        type="test",
        status="active",
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(rt)
    session.flush()
    return rt


def _create_workflow(session, rt, nodes, edges=None, **kwargs) -> WorkflowDefinition:
    now = _now()
    wf = WorkflowDefinition(
        id=uuid.uuid4(),
        runtime_id=rt.id,
        name=f"wf-{uuid.uuid4().hex[:6]}",
        created_at=now,
        updated_at=now,
        **kwargs,
    )
    session.add(wf)
    session.flush()

    now = _now()
    for n in nodes:
        node = WorkflowNode(
            id=uuid.uuid4(),
            workflow_id=wf.id,
            node_id=n["node_id"],
            title=n.get("title", n["node_id"]),
            task_type=n.get("task_type", "action"),
            retry_policy=n.get("retry_policy"),
            timeout_seconds=n.get("timeout_seconds"),
            approval_timeout_seconds=n.get("approval_timeout_seconds"),
            created_at=now,
        )
        session.add(node)

    for e in (edges or []):
        edge = WorkflowEdge(
            id=uuid.uuid4(),
            workflow_id=wf.id,
            from_node=e["from_node"],
            to_node=e["to_node"],
            created_at=now,
        )
        session.add(edge)

    session.flush()
    return wf


def _create_run(session, wf) -> Run:
    now = _now()
    run = Run(
        id=uuid.uuid4(),
        runtime_id=wf.runtime_id,
        workflow_id=wf.id,
        title=f"Run: {wf.name}",
        status="running",
        started_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(run)
    session.flush()

    for node in wf.nodes:
        task = Task(
            id=uuid.uuid4(),
            run_id=run.id,
            node_id=node.node_id,
            title=node.title,
            status="pending",
            task_type=node.task_type,
            created_at=now,
            updated_at=now,
        )
        session.add(task)

    session.flush()
    return run


def _mock_try_lock(session, task, worker) -> bool:
    """Simulate advisory lock by setting locked_by directly."""
    if task.locked_by is not None and task.locked_by != worker.worker_id:
        return False
    task.locked_by = worker.worker_id
    task.locked_at = datetime.now(timezone.utc)
    return True


# ---------------------------------------------------------------------------
# Dependency Gating
# ---------------------------------------------------------------------------


class TestDependencyGating:
    def test_dependencies_met_no_deps(self):
        edges: list[tuple[str, str]] = []
        rev = _build_reverse_adjacency(edges)
        tasks = {"a": type("T", (), {"status": "pending"})()}
        assert _check_dependencies_met("a", tasks, rev) is True

    def test_dependencies_met_when_dep_completed(self):
        rev = _build_reverse_adjacency([("a", "b")])
        tasks = {
            "a": type("T", (), {"status": "completed"})(),
            "b": type("T", (), {"status": "pending"})(),
        }
        assert _check_dependencies_met("b", tasks, rev) is True

    def test_dependencies_not_met_when_dep_pending(self):
        rev = _build_reverse_adjacency([("a", "b")])
        tasks = {
            "a": type("T", (), {"status": "pending"})(),
            "b": type("T", (), {"status": "pending"})(),
        }
        assert _check_dependencies_met("b", tasks, rev) is False

    def test_dependencies_not_met_when_dep_running(self):
        rev = _build_reverse_adjacency([("a", "b")])
        tasks = {
            "a": type("T", (), {"status": "running"})(),
            "b": type("T", (), {"status": "pending"})(),
        }
        assert _check_dependencies_met("b", tasks, rev) is False

    def test_diamond_dependencies(self):
        rev = _build_reverse_adjacency([("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])
        tasks = {
            "a": type("T", (), {"status": "completed"})(),
            "b": type("T", (), {"status": "completed"})(),
            "c": type("T", (), {"status": "completed"})(),
            "d": type("T", (), {"status": "pending"})(),
        }
        assert _check_dependencies_met("d", tasks, rev) is True

    def test_diamond_one_dep_incomplete(self):
        rev = _build_reverse_adjacency([("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])
        tasks = {
            "a": type("T", (), {"status": "completed"})(),
            "b": type("T", (), {"status": "completed"})(),
            "c": type("T", (), {"status": "running"})(),
            "d": type("T", (), {"status": "pending"})(),
        }
        assert _check_dependencies_met("d", tasks, rev) is False


# ---------------------------------------------------------------------------
# Worker Pickup
# ---------------------------------------------------------------------------


class TestWorkerPickup:
    def test_pickup_root_task(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(db, rt, nodes=[{"node_id": "a", "title": "A"}])
        run = _create_run(db, wf)
        db.commit()

        worker = WorkflowWorker()
        with patch.object(worker, "_try_lock_task", lambda s, t: _mock_try_lock(s, t, worker)):
            worker._process_pending_tasks(db)

        task = db.query(Task).filter(Task.node_id == "a").first()
        assert task.status == "running"
        assert task.started_at is not None

    def test_skip_task_with_unmet_deps(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A"}, {"node_id": "b", "title": "B"}],
            edges=[{"from_node": "a", "to_node": "b"}],
        )
        run = _create_run(db, wf)
        db.commit()

        worker = WorkflowWorker()
        with patch.object(worker, "_try_lock_task", lambda s, t: _mock_try_lock(s, t, worker)):
            worker._process_pending_tasks(db)

        task_b = db.query(Task).filter(Task.node_id == "b").first()
        assert task_b.status == "pending"

    def test_pickup_dep_task_after_dep_completes(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A"}, {"node_id": "b", "title": "B"}],
            edges=[{"from_node": "a", "to_node": "b"}],
        )
        run = _create_run(db, wf)
        db.commit()

        worker = WorkflowWorker()
        with patch.object(worker, "_try_lock_task", lambda s, t: _mock_try_lock(s, t, worker)):
            worker._process_pending_tasks(db)

        task_a = db.query(Task).filter(Task.node_id == "a").first()
        task_a.status = "completed"
        task_a.ended_at = datetime.now(timezone.utc)
        db.commit()

        with patch.object(worker, "_try_lock_task", lambda s, t: _mock_try_lock(s, t, worker)):
            worker._process_pending_tasks(db)

        task_b = db.query(Task).filter(Task.node_id == "b").first()
        assert task_b.status == "running"


# ---------------------------------------------------------------------------
# Retry Backoff
# ---------------------------------------------------------------------------


class TestRetryBackoff:
    def test_retry_sets_next_retry_at(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A", "retry_policy": {"max_retries": 2, "backoff_seconds": 5.0}}],
        )
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "failed"
        db.commit()

        worker = WorkflowWorker()
        task.locked_by = worker.worker_id
        db.commit()
        worker._handle_failed_tasks(db)

        db.refresh(task)
        assert task.status == "pending"
        assert task.next_retry_at is not None

    def test_backoff_is_exponential(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A", "retry_policy": {"max_retries": 3, "backoff_seconds": 2.0}}],
        )
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "failed"
        db.commit()

        worker = WorkflowWorker()

        # First failure -> retry_count=1, next_retry_at = 2 * 2^0 = 2s
        task.locked_by = worker.worker_id
        db.commit()
        worker._handle_failed_tasks(db)
        db.refresh(task)
        first_next = task.next_retry_at

        task.status = "failed"
        task.locked_by = worker.worker_id
        db.commit()

        # Second failure -> retry_count=2, next_retry_at = 2 * 2^1 = 4s
        worker._handle_failed_tasks(db)
        db.refresh(task)
        second_next = task.next_retry_at

        assert second_next > first_next

    def test_worker_skips_task_with_future_retry(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(db, rt, nodes=[{"node_id": "a", "title": "A"}])
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        db.commit()

        worker = WorkflowWorker()
        with patch.object(worker, "_try_lock_task", lambda s, t: _mock_try_lock(s, t, worker)):
            worker._process_pending_tasks(db)

        db.refresh(task)
        assert task.status == "pending"


# ---------------------------------------------------------------------------
# Dead Letter
# ---------------------------------------------------------------------------


class TestDeadLetter:
    def test_dead_letter_on_exhausted_retries(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A", "retry_policy": {"max_retries": 0, "backoff_seconds": 0}}],
        )
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "failed"
        db.commit()

        worker = WorkflowWorker()
        task.locked_by = worker.worker_id
        db.commit()
        worker._handle_failed_tasks(db)

        db.refresh(task)
        assert task.status == "dead_letter"

    def test_dead_letter_creates_trace_span(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A", "retry_policy": {"max_retries": 0, "backoff_seconds": 0}}],
        )
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "failed"
        db.commit()

        worker = WorkflowWorker()
        task.locked_by = worker.worker_id
        db.commit()
        worker._handle_failed_tasks(db)

        span = db.query(TraceSpan).filter(TraceSpan.span_type == "dead_letter").first()
        assert span is not None
        assert span.task_id == task.id


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------


class TestApprovalCreation:
    def test_approval_node_creates_approval_row(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "approve", "title": "Approve", "task_type": "approval"}],
        )
        run = _create_run(db, wf)
        db.commit()

        worker = WorkflowWorker()
        with patch.object(worker, "_try_lock_task", lambda s, t: _mock_try_lock(s, t, worker)):
            worker._process_pending_tasks(db)

        task = db.query(Task).first()
        assert task.status == "waiting_approval"

        approval = db.query(Approval).filter(Approval.task_id == task.id).first()
        assert approval is not None
        assert approval.status == "pending"

    def test_approval_creates_trace_span(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "approve", "title": "Approve", "task_type": "approval"}],
        )
        run = _create_run(db, wf)
        db.commit()

        worker = WorkflowWorker()
        with patch.object(worker, "_try_lock_task", lambda s, t: _mock_try_lock(s, t, worker)):
            worker._process_pending_tasks(db)

        span = db.query(TraceSpan).filter(TraceSpan.span_type == "approval_request").first()
        assert span is not None


# ---------------------------------------------------------------------------
# Stale Lock Recovery
# ---------------------------------------------------------------------------


class TestStaleLockRecovery:
    def test_recover_stale_locks(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(db, rt, nodes=[{"node_id": "a", "title": "A"}])
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.locked_by = "dead-worker"
        task.locked_at = datetime.now(timezone.utc) - timedelta(seconds=600)
        db.commit()

        worker = WorkflowWorker(stale_lock_seconds=300)
        worker._recover_stale_locks(db)

        db.refresh(task)
        assert task.locked_by is None
        assert task.locked_at is None

    def test_fresh_lock_not_recovered(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(db, rt, nodes=[{"node_id": "a", "title": "A"}])
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.locked_by = "active-worker"
        task.locked_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        db.commit()

        worker = WorkflowWorker(stale_lock_seconds=300)
        worker._recover_stale_locks(db)

        db.refresh(task)
        assert task.locked_by == "active-worker"


# ---------------------------------------------------------------------------
# Workflow Timeout
# ---------------------------------------------------------------------------


class TestWorkflowTimeout:
    def test_timeout_cancels_tasks(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A"}, {"node_id": "b", "title": "B"}],
            edges=[{"from_node": "a", "to_node": "b"}],
            timeout_seconds=1,
        )
        run = _create_run(db, wf)
        run.started_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        db.commit()

        worker = WorkflowWorker()
        worker._check_workflow_timeouts(db)

        db.refresh(run)
        assert run.status == "failed"
        tasks = db.query(Task).filter(Task.run_id == run.id).all()
        for t in tasks:
            assert t.status in ("cancelled", "completed")

    def test_timeout_creates_trace_span(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A"}],
            timeout_seconds=1,
        )
        run = _create_run(db, wf)
        run.started_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        db.commit()

        worker = WorkflowWorker()
        worker._check_workflow_timeouts(db)

        span = db.query(TraceSpan).filter(TraceSpan.span_type == "workflow_timeout").first()
        assert span is not None


# ---------------------------------------------------------------------------
# Approval Timeout
# ---------------------------------------------------------------------------


class TestApprovalTimeout:
    def test_approval_timeout_fails_task(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "approve", "title": "Approve", "task_type": "approval",
                    "approval_timeout_seconds": 5}],
        )
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "waiting_approval"
        task.started_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        db.commit()

        worker = WorkflowWorker()
        worker._check_approval_timeouts(db)

        db.refresh(task)
        assert task.status == "failed"
        assert "timed out" in (task.error_summary or "")

    def test_approval_timeout_rejects_pending_approval(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "approve", "title": "Approve", "task_type": "approval",
                    "approval_timeout_seconds": 5}],
        )
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "waiting_approval"
        task.started_at = datetime.now(timezone.utc) - timedelta(seconds=10)

        approval = Approval(
            id=uuid.uuid4(), run_id=run.id, task_id=task.id,
            status="pending",
            context_json={"node_id": "approve"},
        )
        db.add(approval)
        db.commit()

        worker = WorkflowWorker()
        worker._check_approval_timeouts(db)

        db.refresh(approval)
        assert approval.status == "rejected"


# ---------------------------------------------------------------------------
# Run Completion
# ---------------------------------------------------------------------------


class TestRunCompletion:
    def test_run_completes_when_all_tasks_terminal(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A"}, {"node_id": "b", "title": "B"}],
        )
        run = _create_run(db, wf)
        tasks = db.query(Task).filter(Task.run_id == run.id).all()
        for t in tasks:
            t.status = "completed"
            t.ended_at = datetime.now(timezone.utc)
        db.commit()

        worker = WorkflowWorker()
        worker._check_run_completion(db, run)

        db.refresh(run)
        assert run.status == "completed"

    def test_run_fails_when_any_task_dead_letter(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(db, rt, nodes=[{"node_id": "a", "title": "A"}])
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "dead_letter"
        task.ended_at = datetime.now(timezone.utc)
        db.commit()

        worker = WorkflowWorker()
        worker._check_run_completion(db, run)

        db.refresh(run)
        assert run.status == "failed"

    def test_run_fails_when_any_task_cancelled(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(db, rt, nodes=[{"node_id": "a", "title": "A"}])
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "cancelled"
        task.ended_at = datetime.now(timezone.utc)
        db.commit()

        worker = WorkflowWorker()
        worker._check_run_completion(db, run)

        db.refresh(run)
        assert run.status == "failed"

    def test_completion_creates_trace_span(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(db, rt, nodes=[{"node_id": "a", "title": "A"}])
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "completed"
        task.ended_at = datetime.now(timezone.utc)
        db.commit()

        worker = WorkflowWorker()
        worker._check_run_completion(db, run)

        span = db.query(TraceSpan).filter(TraceSpan.span_type == "workflow_complete").first()
        assert span is not None


# ---------------------------------------------------------------------------
# Concurrency Limits
# ---------------------------------------------------------------------------


class TestConcurrencyLimits:
    def test_respects_max_concurrent_tasks(self, db):
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[
                {"node_id": "a", "title": "A"},
                {"node_id": "b", "title": "B"},
                {"node_id": "c", "title": "C"},
            ],
            edges=[],
            max_concurrent_tasks=1,
        )
        run = _create_run(db, wf)
        db.commit()

        worker = WorkflowWorker()
        with patch.object(worker, "_try_lock_task", lambda s, t: _mock_try_lock(s, t, worker)):
            worker._process_pending_tasks(db)

        tasks = db.query(Task).filter(Task.run_id == run.id).all()
        running = [t for t in tasks if t.status == "running"]
        assert len(running) <= 1


# ---------------------------------------------------------------------------
# TraceSpan Coverage
# ---------------------------------------------------------------------------


class TestTraceSpanCoverage:
    def test_dead_letter_writes_span(self, db):
        """Dead-letter creates a TraceSpan."""
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A",
                    "retry_policy": {"max_retries": 0, "backoff_seconds": 0}}],
        )
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "failed"
        db.commit()

        worker = WorkflowWorker()
        task.locked_by = worker.worker_id
        db.commit()
        worker._handle_failed_tasks(db)

        span = db.query(TraceSpan).filter(TraceSpan.span_type == "dead_letter").first()
        assert span is not None

    def test_workflow_timeout_writes_span(self, db):
        """Workflow timeout creates a TraceSpan."""
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "a", "title": "A"}],
            timeout_seconds=1,
        )
        run = _create_run(db, wf)
        run.started_at = _now() - timedelta(seconds=10)
        db.commit()

        worker = WorkflowWorker()
        worker._check_workflow_timeouts(db)

        span = db.query(TraceSpan).filter(TraceSpan.span_type == "workflow_timeout").first()
        assert span is not None

    def test_approval_timeout_writes_span(self, db):
        """Approval timeout creates a TraceSpan."""
        rt = _seed_runtime(db)
        wf = _create_workflow(
            db, rt,
            nodes=[{"node_id": "approve", "title": "Approve", "task_type": "approval",
                    "approval_timeout_seconds": 5}],
        )
        run = _create_run(db, wf)
        task = db.query(Task).first()
        task.status = "waiting_approval"
        task.started_at = _now() - timedelta(seconds=10)
        db.commit()

        worker = WorkflowWorker()
        worker._check_approval_timeouts(db)

        span = db.query(TraceSpan).filter(TraceSpan.span_type == "approval_timeout").first()
        assert span is not None
