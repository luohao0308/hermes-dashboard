"""Integration tests for the Approval and Tool Policy APIs (v1.1).

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
Each test runs in a rolled-back transaction so tests are isolated.
"""

from __future__ import annotations
import uuid
import pytest
from models import Approval, AuditLog, Run, Runtime


def _seed_run(session) -> str:
    """Create a runtime + run and return the run_id."""
    rt = Runtime(id=uuid.uuid4(), name=f"rt-{uuid.uuid4().hex[:6]}", type="agent", status="active")
    session.add(rt)
    session.flush()
    run = Run(id=uuid.uuid4(), runtime_id=rt.id, title="test run", status="running")
    session.add(run)
    session.flush()
    return str(run.id)


def _seed_approval(session, run_id: str, status: str = "pending") -> str:
    """Insert an Approval row and return its id."""
    approval = Approval(
        id=uuid.uuid4(),
        run_id=run_id,
        status=status,
        reason="Test approval",
        requested_by="agent",
    )
    session.add(approval)
    session.flush()
    return str(approval.id)


# ---------------------------------------------------------------------------
# GET /api/approvals
# ---------------------------------------------------------------------------

class TestListApprovals:
    def test_empty(self, client):
        c = client
        session = client._test_session
        resp = c.get("/api/approvals")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_list_with_data(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        _seed_approval(session, run_id)
        _seed_approval(session, run_id, status="approved")

        resp = c.get("/api/approvals")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_filter_status(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        _seed_approval(session, run_id, "pending")
        _seed_approval(session, run_id, "approved")

        resp = c.get("/api/approvals", params={"status": "pending"})
        assert resp.status_code == 200
        assert all(a["status"] == "pending" for a in resp.json()["items"])

    def test_filter_run_id(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        _seed_approval(session, run_id)

        resp = c.get("/api/approvals", params={"run_id": run_id})
        assert resp.status_code == 200
        assert all(a["run_id"] == run_id for a in resp.json()["items"])

    def test_pagination(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        for _ in range(5):
            _seed_approval(session, run_id)

        resp = c.get("/api/approvals", params={"limit": 2, "offset": 0})
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5
        assert data["limit"] == 2


# ---------------------------------------------------------------------------
# GET /api/approvals/{id}
# ---------------------------------------------------------------------------

class TestGetApproval:
    def test_get_existing(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        aid = _seed_approval(session, run_id)

        resp = c.get(f"/api/approvals/{aid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == aid
        assert resp.json()["status"] == "pending"

    def test_get_not_found(self, client):
        c = client
        resp = c.get(f"/api/approvals/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/approvals/{id}/approve
# ---------------------------------------------------------------------------

class TestApproveApproval:
    def test_approve(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        aid = _seed_approval(session, run_id)

        resp = c.post(f"/api/approvals/{aid}/approve", json={
            "resolved_by": "test_user",
            "note": "Looks good",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["resolved_by"] == "test_user"
        assert data["resolved_note"] == "Looks good"
        assert data["resolved_at"] is not None

    def test_approve_idempotent_409(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        aid = _seed_approval(session, run_id, "approved")

        resp = c.post(f"/api/approvals/{aid}/approve")
        assert resp.status_code == 409
        assert "already" in resp.json()["detail"]

    def test_approve_not_found(self, client):
        c = client
        resp = c.post(f"/api/approvals/{uuid.uuid4()}/approve")
        assert resp.status_code == 404

    def test_approve_creates_audit_log(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        aid = _seed_approval(session, run_id)

        c.post(f"/api/approvals/{aid}/approve", json={"resolved_by": "auditor"})

        logs = session.query(AuditLog).filter(
            AuditLog.action == "approval.approved",
            AuditLog.resource_id == aid,
        ).all()
        assert len(logs) >= 1
        assert logs[0].actor_id == "auditor"
        assert logs[0].resource_type == "approval"


# ---------------------------------------------------------------------------
# POST /api/approvals/{id}/reject
# ---------------------------------------------------------------------------

class TestRejectApproval:
    def test_reject(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        aid = _seed_approval(session, run_id)

        resp = c.post(f"/api/approvals/{aid}/reject", json={
            "resolved_by": "reviewer",
            "note": "Security concern",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["resolved_by"] == "reviewer"
        assert data["resolved_note"] == "Security concern"

    def test_reject_idempotent_409(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        aid = _seed_approval(session, run_id, "rejected")

        resp = c.post(f"/api/approvals/{aid}/reject")
        assert resp.status_code == 409

    def test_reject_not_found(self, client):
        c = client
        resp = c.post(f"/api/approvals/{uuid.uuid4()}/reject")
        assert resp.status_code == 404

    def test_reject_creates_audit_log(self, client):
        c = client
        session = client._test_session
        run_id = _seed_run(session)
        aid = _seed_approval(session, run_id)

        c.post(f"/api/approvals/{aid}/reject", json={"resolved_by": "gatekeeper"})

        logs = session.query(AuditLog).filter(
            AuditLog.action == "approval.rejected",
            AuditLog.resource_id == aid,
        ).all()
        assert len(logs) >= 1
        assert logs[0].actor_id == "gatekeeper"


# ---------------------------------------------------------------------------
# GET /api/tools
# ---------------------------------------------------------------------------

class TestToolPolicies:
    def test_list_policies(self, client):
        c = client
        resp = c.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "policies" in data
        assert len(data["policies"]) >= 4

    def test_policy_fields(self, client):
        c = client
        resp = c.get("/api/tools")
        policies = resp.json()["policies"]
        risk_levels = {p["risk_level"] for p in policies}
        assert "read" in risk_levels
        assert "destructive" in risk_levels

        read_policy = next(p for p in policies if p["risk_level"] == "read")
        assert read_policy["decision"] == "allow"
        assert "description" in read_policy
