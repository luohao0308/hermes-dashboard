"""Integration tests for the Run-based RCA and Runbook APIs (v1.2).

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
Each test runs in a rolled-back transaction so tests are isolated.
"""

from __future__ import annotations
import uuid
import pytest
from models import RCAReport, Runbook, Artifact, Run, Runtime


def _seed_run(session, status: str = "error") -> str:
    """Create a runtime + run and return the run_id."""
    rt = Runtime(id=uuid.uuid4(), name=f"rt-{uuid.uuid4().hex[:6]}", type="agent", status="active")
    session.add(rt)
    session.flush()
    run = Run(
        id=uuid.uuid4(),
        runtime_id=rt.id,
        title="test run",
        status=status,
        metadata_json={"session_id": f"sess-{uuid.uuid4().hex[:6]}"},
    )
    session.add(run)
    session.flush()
    return str(run.id)


def _seed_rca(session, run_id: str) -> str:
    """Insert an RCA report and return its id."""
    rca = RCAReport(
        id=uuid.uuid4(),
        run_id=run_id,
        root_cause="Test root cause",
        category="tool",
        confidence=0.85,
        evidence_json={"evidence": [
            {"source": "trace", "title": "Error span", "detail": "tool failed", "severity": "high"},
        ]},
        next_actions_json={"next_actions": ["Check tool config", "Retry"]},
    )
    session.add(rca)
    session.flush()
    return str(rca.id)


def _seed_runbook(session, run_id: str, rca_id: str | None = None) -> str:
    """Insert a runbook and return its id."""
    rb = Runbook(
        id=uuid.uuid4(),
        run_id=run_id,
        severity="high",
        summary="Test runbook summary",
        markdown="# Runbook\n\n## Steps\n\n- [ ] Fix tool config",
        steps_json={
            "checklist": ["Fix tool config", "Retry"],
            "execution_steps": [
                {"step_id": "step-1", "label": "Fix tool config", "action_type": "confirm_then_execute", "requires_confirmation": True, "status": "needs_confirmation"},
            ],
        },
    )
    session.add(rb)
    session.flush()
    return str(rb.id)


# ---------------------------------------------------------------------------
# POST /api/runs/{run_id}/rca
# ---------------------------------------------------------------------------

class TestGenerateRca:
    def test_generate_rca(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)

        resp = c.post(f"/api/runs/{run_id}/rca")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id
        assert "category" in data
        assert "root_cause" in data
        assert "confidence" in data
        assert "evidence" in data
        assert "next_actions" in data
        assert "low_confidence" in data

    def test_generate_rca_not_found(self, client):
        c = client
        resp = c.post(f"/api/runs/{uuid.uuid4()}/rca")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/rca
# ---------------------------------------------------------------------------

class TestGetRca:
    def test_get_existing_rca(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        _seed_rca(session, run_id)

        resp = c.get(f"/api/runs/{run_id}/rca")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id
        assert data["root_cause"] == "Test root cause"
        assert data["category"] == "tool"
        assert data["confidence"] == 0.85

    def test_get_rca_not_found(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)

        resp = c.get(f"/api/runs/{run_id}/rca")
        assert resp.status_code == 404

    def test_get_rca_run_not_found(self, client):
        c = client
        resp = c.get(f"/api/runs/{uuid.uuid4()}/rca")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/runs/{run_id}/runbook
# ---------------------------------------------------------------------------

class TestGenerateRunbook:
    def test_generate_runbook(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)

        resp = c.post(f"/api/runs/{run_id}/runbook")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id
        assert "severity" in data
        assert "summary" in data
        assert "checklist" in data
        assert "markdown" in data

    def test_generate_runbook_uses_existing_rca(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        rca_id = _seed_rca(session, run_id)

        resp = c.post(f"/api/runs/{run_id}/runbook")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rca_report_id"] == rca_id

    def test_generate_runbook_not_found(self, client):
        c = client
        resp = c.post(f"/api/runs/{uuid.uuid4()}/runbook")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/runbook
# ---------------------------------------------------------------------------

class TestGetRunbook:
    def test_get_existing_runbook(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        _seed_runbook(session, run_id)

        resp = c.get(f"/api/runs/{run_id}/runbook")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id
        assert data["severity"] == "high"
        assert data["summary"] == "Test runbook summary"

    def test_get_runbook_not_found(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)

        resp = c.get(f"/api/runs/{run_id}/runbook")
        assert resp.status_code == 404

    def test_get_runbook_run_not_found(self, client):
        c = client
        resp = c.get(f"/api/runs/{uuid.uuid4()}/runbook")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/runs/{run_id}/export
# ---------------------------------------------------------------------------

class TestExportArtifact:
    def test_export_rca(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        _seed_rca(session, run_id)

        resp = c.post(f"/api/runs/{run_id}/export", json={"kind": "rca"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["artifact_type"] == "rca_report"
        assert "RCA Report" in data["title"]
        assert "content_text" in data
        assert len(data["content_text"]) > 0

    def test_export_runbook(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        _seed_runbook(session, run_id)

        resp = c.post(f"/api/runs/{run_id}/export", json={"kind": "runbook"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["artifact_type"] == "runbook"
        assert "Runbook" in data["title"]

    def test_export_rca_not_found(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)

        resp = c.post(f"/api/runs/{run_id}/export", json={"kind": "rca"})
        assert resp.status_code == 404

    def test_export_invalid_kind(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)

        resp = c.post(f"/api/runs/{run_id}/export", json={"kind": "invalid"})
        assert resp.status_code == 400

    def test_export_run_not_found(self, client):
        c = client
        resp = c.post(f"/api/runs/{uuid.uuid4()}/export", json={"kind": "rca"})
        assert resp.status_code == 404
