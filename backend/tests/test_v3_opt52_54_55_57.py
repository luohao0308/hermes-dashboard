"""Integration tests for OPT-52/54/55/57.

OPT-52: Workflow version rollback
OPT-54: Connector failed event replay
OPT-55: Approval batch actions
OPT-57: Eval recommendation guardrail

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
"""

from __future__ import annotations
import uuid
import pytest
from models import (
    Approval, AuditLog, ConnectorConfig, ConfigVersion, FailedEvent,
    Runtime, Run, WorkflowDefinition, WorkflowNode, WorkflowEdge, WorkflowVersionHistory,
)


def _seed_runtime(session, name=None) -> Runtime:
    rt = Runtime(id=uuid.uuid4(), name=name or f"rt-{uuid.uuid4().hex[:6]}", type="agent", status="active")
    session.add(rt)
    session.flush()
    return rt


def _seed_run(session, runtime_id: uuid.UUID) -> Run:
    run = Run(id=uuid.uuid4(), runtime_id=runtime_id, title="test run", status="running")
    session.add(run)
    session.flush()
    return run


def _seed_connector(session, runtime_id: uuid.UUID) -> ConnectorConfig:
    connector = ConnectorConfig(
        id=uuid.uuid4(),
        runtime_id=runtime_id,
        connector_type="github",
        display_name="test-connector",
        enabled=True,
    )
    session.add(connector)
    session.flush()
    return connector


def _seed_workflow(session, runtime_id: uuid.UUID) -> WorkflowDefinition:
    wf = WorkflowDefinition(
        id=uuid.uuid4(),
        runtime_id=runtime_id,
        name="test-workflow",
        description="A test workflow",
        version=1,
        timeout_seconds=300,
    )
    session.add(wf)
    session.flush()
    node = WorkflowNode(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        node_id="n1",
        title="Step 1",
        task_type="action",
    )
    session.add(node)
    edge = WorkflowEdge(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        from_node="start",
        to_node="n1",
    )
    session.add(edge)
    session.flush()
    return wf


def _seed_approval(session, run_id: uuid.UUID, status="pending") -> Approval:
    approval = Approval(
        id=uuid.uuid4(),
        run_id=run_id,
        status=status,
        reason="test approval",
        requested_by="test",
    )
    session.add(approval)
    session.flush()
    return approval


# =========================================================================
# OPT-54: Connector failed event replay
# =========================================================================


class TestFailedEventReplay:
    def test_failed_event_recorded_on_error(self, client):
        """Failed events should be persisted when ingestion fails."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        connector = _seed_connector(session, rt.id)

        # Send an event with invalid run_id (will fail in handler)
        resp = c.post(
            f"/api/connectors/{connector.id}/events",
            json=[{
                "event_type": "run.updated",
                "event_id": "evt-fail-1",
                "run_id": str(uuid.uuid4()),  # non-existent run
                "payload": {"status": "completed"},
            }],
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert results[0]["status"] == "error"

        # Check failed events were recorded
        failed = session.query(FailedEvent).filter(FailedEvent.connector_id == connector.id).all()
        assert len(failed) >= 1
        assert failed[0].event_id == "evt-fail-1"
        assert "not found" in failed[0].error_message.lower()

    def test_list_failed_events(self, client):
        """GET /api/connectors/{id}/failed-events returns persisted failures."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        connector = _seed_connector(session, rt.id)

        # Seed a failed event directly
        fe = FailedEvent(
            connector_id=connector.id,
            event_type="run.updated",
            event_id="evt-list-1",
            payload={"status": "completed"},
            error_message="Run not found",
        )
        session.add(fe)
        session.flush()

        resp = c.get(f"/api/connectors/{connector.id}/failed-events")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(item["event_id"] == "evt-list-1" for item in data["items"])

    def test_replay_failed_event(self, client):
        """POST replay should re-process the event and remove from failed list on success."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        connector = _seed_connector(session, rt.id)

        # Seed a failed event that will succeed on replay (run.created with valid data)
        fe = FailedEvent(
            connector_id=connector.id,
            event_type="run.created",
            event_id="evt-replay-1",
            payload={"title": "Replayed run", "status": "running"},
            error_message="Previous transient error",
        )
        session.add(fe)
        session.flush()

        resp = c.post(f"/api/connectors/{connector.id}/failed-events/{fe.id}/replay")
        assert resp.status_code == 200
        assert resp.json()["status"] == "replayed"

        # Failed event should be removed
        remaining = session.query(FailedEvent).filter(FailedEvent.id == fe.id).count()
        assert remaining == 0

    def test_replay_idempotent_on_failure(self, client):
        """If replay fails again, the failed event should remain with updated error."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        connector = _seed_connector(session, rt.id)

        # This event will fail again (run.updated with non-existent run)
        fe = FailedEvent(
            connector_id=connector.id,
            event_type="run.updated",
            event_id="evt-replay-fail",
            run_id=str(uuid.uuid4()),
            payload={"status": "completed"},
            error_message="Original error",
        )
        session.add(fe)
        session.flush()

        resp = c.post(f"/api/connectors/{connector.id}/failed-events/{fe.id}/replay")
        assert resp.status_code == 422

        # Failed event should still exist
        remaining = session.query(FailedEvent).filter(FailedEvent.id == fe.id).count()
        assert remaining == 1


# =========================================================================
# OPT-52: Workflow version rollback
# =========================================================================


class TestWorkflowVersionRollback:
    def test_update_creates_version_snapshot(self, client):
        """Updating a workflow should save the previous version to history."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf = _seed_workflow(session, rt.id)

        resp = c.put(
            f"/api/workflows/{wf.id}",
            json={"name": "updated-workflow", "description": "updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == 2

        # Check version history
        history = (
            session.query(WorkflowVersionHistory)
            .filter(WorkflowVersionHistory.workflow_id == wf.id)
            .all()
        )
        assert len(history) >= 1
        assert history[0].version == 1
        assert history[0].name == "test-workflow"

    def test_list_workflow_versions(self, client):
        """GET /api/workflows/{id}/versions returns version history."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf = _seed_workflow(session, rt.id)

        # Create a version snapshot manually
        snapshot = WorkflowVersionHistory(
            workflow_id=wf.id,
            version=1,
            name=wf.name,
            description=wf.description,
            nodes_json=[{"node_id": "n1", "title": "Step 1", "task_type": "action"}],
            edges_json=[{"from_node": "start", "to_node": "n1"}],
        )
        session.add(snapshot)
        session.flush()

        resp = c.get(f"/api/workflows/{wf.id}/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["version"] == 1

    def test_rollback_restores_version(self, client):
        """POST rollback should restore a previous version and increment version counter."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf = _seed_workflow(session, rt.id)

        # Seed version history
        snapshot = WorkflowVersionHistory(
            workflow_id=wf.id,
            version=1,
            name="original-name",
            description="original desc",
            nodes_json=[{"node_id": "n1", "title": "Original Step", "task_type": "action"}],
            edges_json=[{"from_node": "start", "to_node": "n1"}],
            timeout_seconds=600,
        )
        session.add(snapshot)
        session.flush()

        resp = c.post(
            f"/api/workflows/{wf.id}/rollback",
            json={"version": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "original-name"
        assert data["version"] == 2  # bumped from 1

        # Audit log should have the rollback entry
        audit = (
            session.query(AuditLog)
            .filter(AuditLog.action == "workflow.rollback")
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        assert audit is not None

    def test_rollback_version_not_found(self, client):
        """Rollback to non-existent version should 404."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        wf = _seed_workflow(session, rt.id)

        resp = c.post(
            f"/api/workflows/{wf.id}/rollback",
            json={"version": 999},
        )
        assert resp.status_code == 404


# =========================================================================
# OPT-55: Approval batch actions
# =========================================================================


class TestBatchApproval:
    def test_batch_approve(self, client):
        """POST /api/approvals/batch/approve should approve multiple pending approvals."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        run = _seed_run(session, rt.id)
        a1 = _seed_approval(session, run.id)
        a2 = _seed_approval(session, run.id)

        resp = c.post(
            "/api/approvals/batch/approve",
            json={
                "approval_ids": [str(a1.id), str(a2.id)],
                "resolved_by": "batch_user",
                "note": "batch approved",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 2
        assert data["skipped"] == 0
        assert all(r["status"] == "approved" for r in data["results"])

        # Verify DB state
        session.refresh(a1)
        session.refresh(a2)
        assert a1.status == "approved"
        assert a2.status == "approved"

    def test_batch_reject(self, client):
        """POST /api/approvals/batch/reject should reject multiple pending approvals."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        run = _seed_run(session, rt.id)
        a1 = _seed_approval(session, run.id)
        a2 = _seed_approval(session, run.id)

        resp = c.post(
            "/api/approvals/batch/reject",
            json={
                "approval_ids": [str(a1.id), str(a2.id)],
                "resolved_by": "batch_user",
                "note": "batch rejected",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 2
        assert data["skipped"] == 0
        assert all(r["status"] == "rejected" for r in data["results"])

    def test_batch_skips_already_resolved(self, client):
        """Already-resolved approvals should be skipped, not errored."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        run = _seed_run(session, rt.id)
        a1 = _seed_approval(session, run.id, status="pending")
        a2 = _seed_approval(session, run.id, status="approved")  # already resolved

        resp = c.post(
            "/api/approvals/batch/approve",
            json={"approval_ids": [str(a1.id), str(a2.id)]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 2
        assert data["skipped"] == 1
        statuses = {r["id"]: r["status"] for r in data["results"]}
        assert statuses[str(a1.id)] == "approved"
        assert statuses[str(a2.id)] == "skipped"

    def test_batch_writes_audit_log_per_approval(self, client):
        """Each batch approval should write its own audit log entry."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)
        run = _seed_run(session, rt.id)
        a1 = _seed_approval(session, run.id)
        a2 = _seed_approval(session, run.id)

        c.post(
            "/api/approvals/batch/approve",
            json={"approval_ids": [str(a1.id), str(a2.id)], "resolved_by": "auditor"},
        )

        audit_entries = (
            session.query(AuditLog)
            .filter(AuditLog.action == "approval.approved")
            .all()
        )
        resource_ids = {str(e.resource_id) for e in audit_entries}
        assert str(a1.id) in resource_ids
        assert str(a2.id) in resource_ids


# =========================================================================
# OPT-57: Eval recommendation guardrail
# =========================================================================


class TestEvalRecommendationGuardrail:
    def test_config_version_auto_requires_approval_on_improvement(self, client):
        """Config versions with higher eval score should auto-set requires_approval."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        # Create a baseline config version
        cv1 = ConfigVersion(
            id=uuid.uuid4(),
            runtime_id=rt.id,
            config_type="workflow",
            version="1.0",
            config_json={"param": "old", "evaluation_score": 0.8},
            evaluation_score=0.8,
            requires_approval=False,
        )
        session.add(cv1)
        session.flush()

        # Create a new version with higher score
        resp = c.post(
            "/api/config-versions",
            json={
                "runtime_id": str(rt.id),
                "config_type": "workflow",
                "version": "2.0",
                "config_json": {"param": "new", "evaluation_score": 0.95},
                "requires_approval": False,  # explicitly False
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_approval"] is True  # auto-set due to score improvement

    def test_config_version_no_guardrail_for_lower_score(self, client):
        """Config versions with lower or equal score should not auto-require approval."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        # Create a baseline with high score
        cv1 = ConfigVersion(
            id=uuid.uuid4(),
            runtime_id=rt.id,
            config_type="workflow",
            version="1.0",
            config_json={"param": "old", "evaluation_score": 0.95},
            evaluation_score=0.95,
            requires_approval=False,
        )
        session.add(cv1)
        session.flush()

        # New version with lower score
        resp = c.post(
            "/api/config-versions",
            json={
                "runtime_id": str(rt.id),
                "config_type": "workflow",
                "version": "2.0",
                "config_json": {"param": "new", "evaluation_score": 0.7},
                "requires_approval": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_approval"] is False

    def test_apply_blocked_without_approval(self, client):
        """POST /apply should be blocked if requires_approval=True and no approval."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        cv = ConfigVersion(
            id=uuid.uuid4(),
            runtime_id=rt.id,
            config_type="workflow",
            version="1.0",
            config_json={"param": "val"},
            requires_approval=True,
        )
        session.add(cv)
        session.flush()

        resp = c.post(f"/api/config-versions/{cv.id}/apply")
        assert resp.status_code == 403
        assert "requires approval" in resp.json()["detail"].lower()

    def test_apply_allowed_with_approval(self, client):
        """POST /apply should succeed if an approved approval exists."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        cv = ConfigVersion(
            id=uuid.uuid4(),
            runtime_id=rt.id,
            config_type="workflow",
            version="1.0",
            config_json={"param": "val"},
            requires_approval=True,
        )
        session.add(cv)
        session.flush()

        # Create an approved approval referencing this config version
        approval = Approval(
            id=uuid.uuid4(),
            run_id=None,
            status="approved",
            reason=f"Config version {cv.id} requires approval",
            resolved_by="admin",
        )
        session.add(approval)
        session.flush()

        resp = c.post(f"/api/config-versions/{cv.id}/apply")
        assert resp.status_code == 200
        assert resp.json()["status"] == "applied"

    def test_compare_shows_recommended(self, client):
        """Config compare should indicate recommended when score improves."""
        c = client
        session = client._test_session
        rt = _seed_runtime(session)

        cv_before = ConfigVersion(
            id=uuid.uuid4(),
            runtime_id=rt.id,
            config_type="workflow",
            version="1.0",
            config_json={"param": "old"},
            evaluation_score=0.7,
            requires_approval=False,
        )
        cv_after = ConfigVersion(
            id=uuid.uuid4(),
            runtime_id=rt.id,
            config_type="workflow",
            version="2.0",
            config_json={"param": "new"},
            evaluation_score=0.9,
            requires_approval=True,
        )
        session.add_all([cv_before, cv_after])
        session.flush()

        resp = c.post(
            "/api/config-versions/compare",
            json={
                "before_version_id": str(cv_before.id),
                "after_version_id": str(cv_after.id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommended"] is True
        assert data["requires_approval"] is True
        assert data["score_delta"] == pytest.approx(0.2)
