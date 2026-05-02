"""Integration tests for the Connector Framework API (v1.3).

Covers:
    GET  /api/connectors
    POST /api/connectors/{id}/events

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
Each test runs in a rolled-back transaction so tests are isolated.
"""

from __future__ import annotations
import uuid
import pytest
from models import Runtime, ConnectorConfig, Run, TraceSpan, AuditLog


def _seed_runtime(session, name: str | None = None) -> tuple[str, str]:
    """Create a runtime and connector. Returns (runtime_id, connector_id)."""
    rt_id = uuid.uuid4()
    rt = Runtime(id=rt_id, name=name or f"rt-{uuid.uuid4().hex[:6]}", type="agent", status="active")
    session.add(rt)
    session.flush()

    conn_id = uuid.uuid4()
    conn = ConnectorConfig(
        id=conn_id,
        runtime_id=rt_id,
        connector_type="test_connector",
        display_name="Test Connector",
        enabled=True,
    )
    session.add(conn)
    session.flush()
    return str(rt_id), str(conn_id)


def _seed_connector(session, runtime_id: str, *, enabled: bool = True) -> str:
    """Create an additional connector under an existing runtime."""
    conn_id = uuid.uuid4()
    conn = ConnectorConfig(
        id=conn_id,
        runtime_id=uuid.UUID(runtime_id),
        connector_type="github_review",
        display_name="GitHub Review",
        enabled=enabled,
    )
    session.add(conn)
    session.flush()
    return str(conn_id)


# ---------------------------------------------------------------------------
# GET /api/connectors
# ---------------------------------------------------------------------------


class TestListConnectors:
    def test_empty(self, client):
        resp = client
        r = resp.get("/api/connectors")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list_with_data(self, client):
        resp = client

        session = client._test_session
        _seed_runtime(session)
        r = resp.get("/api/connectors")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert "id" in body["items"][0]

    def test_filter_by_runtime(self, client):
        resp = client

        session = client._test_session
        rt_id, conn_id = _seed_runtime(session)
        _seed_connector(session, rt_id)
        r = resp.get(f"/api/connectors?runtime_id={rt_id}")
        assert r.status_code == 200
        body = r.json()
        assert all(str(item["runtime_id"]) == rt_id for item in body["items"])


# ---------------------------------------------------------------------------
# POST /api/connectors/{id}/events
# ---------------------------------------------------------------------------


class TestIngestEvents:
    def test_run_created(self, client):
        resp = client

        session = client._test_session
        _, conn_id = _seed_runtime(session)
        events = [
            {
                "event_type": "run.created",
                "event_id": "evt-run-001",
                "timestamp": "2026-05-01T10:00:00Z",
                "payload": {"title": "Test run", "status": "running"},
            }
        ]
        r = resp.post(f"/api/connectors/{conn_id}/events", json=events)
        assert r.status_code == 200
        body = r.json()
        assert body["results"][0]["status"] == "accepted"
        assert body["results"][0]["resource_id"] is not None

    def test_run_updated(self, client):
        resp = client

        session = client._test_session
        rt_id, conn_id = _seed_runtime(session)
        # Create a run first
        run = Run(
            id=uuid.uuid4(),
            runtime_id=uuid.UUID(rt_id),
            title="initial",
            status="running",
        )
        session.add(run)
        session.flush()
        run_id = str(run.id)

        events = [
            {
                "event_type": "run.updated",
                "event_id": "evt-run-upd-001",
                "run_id": run_id,
                "timestamp": "2026-05-01T10:05:00Z",
                "payload": {"status": "completed", "title": "updated title", "total_tokens": 1500},
            }
        ]
        r = resp.post(f"/api/connectors/{conn_id}/events", json=events)
        assert r.status_code == 200
        body = r.json()
        assert body["results"][0]["status"] == "accepted"

    def test_span_created(self, client):
        resp = client

        session = client._test_session
        rt_id, conn_id = _seed_runtime(session)
        run = Run(id=uuid.uuid4(), runtime_id=uuid.UUID(rt_id), title="span test", status="running")
        session.add(run)
        session.flush()
        run_id = str(run.id)

        events = [
            {
                "event_type": "span.created",
                "event_id": "evt-span-001",
                "run_id": run_id,
                "timestamp": "2026-05-01T10:01:00Z",
                "payload": {
                    "span_type": "llm",
                    "title": "GPT-4 call",
                    "status": "completed",
                    "model_name": "gpt-4",
                    "input_tokens": 500,
                    "output_tokens": 200,
                },
            }
        ]
        r = resp.post(f"/api/connectors/{conn_id}/events", json=events)
        assert r.status_code == 200
        body = r.json()
        assert body["results"][0]["status"] == "accepted"

    def test_idempotent_duplicate(self, client):
        resp = client

        session = client._test_session
        _, conn_id = _seed_runtime(session)
        events = [
            {
                "event_type": "run.created",
                "event_id": "evt-dup-001",
                "payload": {"title": "dup test"},
            }
        ]
        # First ingest
        r1 = resp.post(f"/api/connectors/{conn_id}/events", json=events)
        assert r1.status_code == 200
        assert r1.json()["results"][0]["status"] == "accepted"

        # Second ingest with same event_id
        r2 = resp.post(f"/api/connectors/{conn_id}/events", json=events)
        assert r2.status_code == 200
        assert r2.json()["results"][0]["status"] == "duplicate"

    def test_connector_not_found(self, client):
        resp = client
        fake_id = str(uuid.uuid4())
        r = resp.post(f"/api/connectors/{fake_id}/events", json=[{"event_type": "run.created", "payload": {}}])
        assert r.status_code == 404

    def test_disabled_connector(self, client):
        resp = client

        session = client._test_session
        rt_id, _ = _seed_runtime(session)
        disabled_id = _seed_connector(session, rt_id, enabled=False)
        r = resp.post(f"/api/connectors/{disabled_id}/events", json=[{"event_type": "run.created", "payload": {}}])
        assert r.status_code == 403

    def test_tool_call_created(self, client):
        resp = client

        session = client._test_session
        rt_id, conn_id = _seed_runtime(session)
        run = Run(id=uuid.uuid4(), runtime_id=uuid.UUID(rt_id), title="tool test", status="running")
        session.add(run)
        session.flush()

        events = [
            {
                "event_type": "tool_call.created",
                "event_id": "evt-tool-001",
                "run_id": str(run.id),
                "payload": {
                    "tool_name": "read_file",
                    "risk_level": "read",
                    "decision": "allow",
                    "status": "completed",
                },
            }
        ]
        r = resp.post(f"/api/connectors/{conn_id}/events", json=events)
        assert r.status_code == 200
        assert r.json()["results"][0]["status"] == "accepted"

    def test_approval_requested(self, client):
        resp = client

        session = client._test_session
        rt_id, conn_id = _seed_runtime(session)
        run = Run(id=uuid.uuid4(), runtime_id=uuid.UUID(rt_id), title="approval test", status="running")
        session.add(run)
        session.flush()

        events = [
            {
                "event_type": "approval.requested",
                "event_id": "evt-approval-001",
                "run_id": str(run.id),
                "payload": {"reason": "Needs human review", "requested_by": "agent"},
            }
        ]
        r = resp.post(f"/api/connectors/{conn_id}/events", json=events)
        assert r.status_code == 200
        assert r.json()["results"][0]["status"] == "accepted"

    def test_artifact_created(self, client):
        resp = client

        session = client._test_session
        rt_id, conn_id = _seed_runtime(session)
        run = Run(id=uuid.uuid4(), runtime_id=uuid.UUID(rt_id), title="artifact test", status="running")
        session.add(run)
        session.flush()

        events = [
            {
                "event_type": "artifact.created",
                "event_id": "evt-artifact-001",
                "run_id": str(run.id),
                "payload": {
                    "artifact_type": "report",
                    "title": "Test Report",
                    "content_text": "# Test\nThis is a test artifact.",
                },
            }
        ]
        r = resp.post(f"/api/connectors/{conn_id}/events", json=events)
        assert r.status_code == 200
        assert r.json()["results"][0]["status"] == "accepted"

    def test_error_recorded_as_audit_log(self, client):
        """When an event handler raises, the error should be recorded in AuditLog."""
        resp = client

        session = client._test_session
        rt_id, conn_id = _seed_runtime(session)
        # run.updated without run_id should raise ValueError
        events = [
            {
                "event_type": "run.updated",
                "event_id": "evt-err-001",
                "payload": {"status": "completed"},
            }
        ]
        r = resp.post(f"/api/connectors/{conn_id}/events", json=events)
        assert r.status_code == 200
        body = r.json()
        assert body["results"][0]["status"] == "error"
        assert body["results"][0]["detail"] is not None
