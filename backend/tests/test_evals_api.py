"""Integration tests for the Eval & Config Version API (v1.4).

Covers:
    GET  /api/evals/summary
    GET  /api/evals/results
    POST /api/evals/run
    GET  /api/config-versions
    POST /api/config-versions
    POST /api/config-versions/compare

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
Each test runs in a rolled-back transaction so tests are isolated.
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from models import Runtime, EvalResult, ConfigVersion, Approval


def _seed_runtime(session, name: str | None = None) -> str:
    """Create a runtime. Returns runtime_id string."""
    rt_id = uuid.uuid4()
    rt = Runtime(id=rt_id, name=name or f"rt-{uuid.uuid4().hex[:6]}", type="agent", status="active")
    session.add(rt)
    session.flush()
    return str(rt_id)


def _seed_eval_result(
    session,
    runtime_id: str,
    *,
    success: bool = True,
    score: float = 0.8,
    config_version: str = "v1",
    sample_name: str = "sample-1",
    latency_ms: int | None = 100,
    cost: float | None = 0.001,
    metrics: dict | None = None,
) -> str:
    """Create an eval result row. Returns id string."""
    row_id = uuid.uuid4()
    row = EvalResult(
        id=row_id,
        runtime_id=uuid.UUID(runtime_id),
        config_version=config_version,
        sample_name=sample_name,
        success=success,
        score=score,
        latency_ms=latency_ms,
        cost=cost,
        metrics_json=metrics or {"tool_error_rate": 0.0, "handoff_count": 1, "approval_count": 0},
        created_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    return str(row_id)


def _seed_config_version(
    session,
    runtime_id: str,
    *,
    version: str = "v1",
    config_type: str = "workflow",
    config_json: dict | None = None,
    evaluation_score: float | None = 0.85,
    requires_approval: bool = False,
    created_by: str = "test",
) -> str:
    """Create a config version. Returns id string."""
    cv_id = uuid.uuid4()
    cv = ConfigVersion(
        id=cv_id,
        runtime_id=uuid.UUID(runtime_id),
        config_type=config_type,
        version=version,
        config_json=config_json or {"model": "gpt-4", "temperature": 0.7},
        evaluation_score=evaluation_score,
        requires_approval=requires_approval,
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
    )
    session.add(cv)
    session.flush()
    return str(cv_id)


# ---------------------------------------------------------------------------
# GET /api/evals/summary
# ---------------------------------------------------------------------------


class TestEvalSummary:
    def test_empty(self, client):
        resp = client
        r = resp.get("/api/evals/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["passed"] == 0
        assert body["failed"] == 0

    def test_with_data(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)
        _seed_eval_result(session, rt_id, success=True, score=0.9, metrics={"tool_error_rate": 0.1, "handoff_count": 2, "approval_count": 1})
        _seed_eval_result(session, rt_id, success=False, score=0.3, metrics={"tool_error_rate": 0.8, "handoff_count": 0, "approval_count": 0})

        r = resp.get("/api/evals/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert body["passed"] == 1
        assert body["failed"] == 1
        assert body["avg_score"] is not None
        assert len(body["by_runtime"]) >= 1
        assert len(body["trend"]) >= 1

    def test_filter_by_runtime(self, client):
        resp = client

        session = client._test_session
        rt1 = _seed_runtime(session, "filter-rt1")
        rt2 = _seed_runtime(session, "filter-rt2")
        _seed_eval_result(session, rt1, success=True, score=0.9)
        _seed_eval_result(session, rt2, success=False, score=0.2)

        r = resp.get(f"/api/evals/summary?runtime_id={rt1}")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["passed"] == 1


# ---------------------------------------------------------------------------
# GET /api/evals/results
# ---------------------------------------------------------------------------


class TestEvalResults:
    def test_pagination(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)
        for i in range(5):
            _seed_eval_result(session, rt_id, sample_name=f"s-{i}", score=0.5 + i * 0.1)

        r = resp.get("/api/evals/results?limit=2&offset=0")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2
        assert body["limit"] == 2
        assert body["offset"] == 0

    def test_filter_by_success(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)
        _seed_eval_result(session, rt_id, success=True, sample_name="pass-1")
        _seed_eval_result(session, rt_id, success=False, sample_name="fail-1")

        r = resp.get("/api/evals/results?success=true")
        assert r.status_code == 200
        body = r.json()
        assert all(item["success"] for item in body["items"])


# ---------------------------------------------------------------------------
# POST /api/evals/run
# ---------------------------------------------------------------------------


class TestEvalRun:
    def test_runtime_not_found(self, client):
        resp = client
        r = resp.post("/api/evals/run", json={
            "runtime_id": str(uuid.uuid4()),
        })
        assert r.status_code == 404

    def test_run_eval(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)

        r = resp.post("/api/evals/run", json={
            "runtime_id": rt_id,
            "config_version": "test-v1",
        })
        assert r.status_code == 200
        body = r.json()
        assert "eval_run_id" in body
        assert body["count"] >= 1
        assert "results" in body

    def test_persists_to_db(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)

        r = resp.post("/api/evals/run", json={
            "runtime_id": rt_id,
            "config_version": "persist-v1",
        })
        assert r.status_code == 200

        # Verify rows were persisted
        count = session.query(EvalResult).filter(
            EvalResult.runtime_id == uuid.UUID(rt_id),
            EvalResult.config_version == "persist-v1",
        ).count()
        assert count >= 1


# ---------------------------------------------------------------------------
# GET /api/config-versions
# ---------------------------------------------------------------------------


class TestConfigVersions:
    def test_empty(self, client):
        resp = client

        session = client._test_session
        # Use a fresh runtime to avoid cross-test pollution
        rt_id = _seed_runtime(session, "cv-empty-rt")
        r = resp.get(f"/api/config-versions?runtime_id={rt_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)
        _seed_config_version(session, rt_id, version="v1")
        _seed_config_version(session, rt_id, version="v2")

        r = resp.get(f"/api/config-versions?runtime_id={rt_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2

    def test_filter_by_type(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)
        _seed_config_version(session, rt_id, version="v1", config_type="workflow")
        _seed_config_version(session, rt_id, version="v2", config_type="tool_policy")

        r = resp.get(f"/api/config-versions?runtime_id={rt_id}&config_type=workflow")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["config_type"] == "workflow"


# ---------------------------------------------------------------------------
# POST /api/config-versions
# ---------------------------------------------------------------------------


class TestCreateConfigVersion:
    def test_create(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)

        r = resp.post("/api/config-versions", json={
            "runtime_id": rt_id,
            "version": "v1-create",
            "config_type": "workflow",
            "config_json": {"model": "claude-3"},
            "created_by": "tester",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["version"] == "v1-create"
        assert body["config_type"] == "workflow"
        assert body["created_by"] == "tester"

    def test_create_with_approval(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)

        r = resp.post("/api/config-versions", json={
            "runtime_id": rt_id,
            "version": "v1-approval",
            "config_json": {"model": "gpt-4"},
            "requires_approval": True,
            "created_by": "admin",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["requires_approval"] is True

        # Verify approval was created
        approval = session.query(Approval).filter(
            Approval.requested_by == "admin",
            Approval.status == "pending",
        ).first()
        assert approval is not None

    def test_runtime_not_found(self, client):
        resp = client
        r = resp.post("/api/config-versions", json={
            "runtime_id": str(uuid.uuid4()),
            "version": "v1",
        })
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/config-versions/compare
# ---------------------------------------------------------------------------


class TestConfigCompare:
    def test_compare(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)
        before_id = _seed_config_version(
            session, rt_id, version="cmp-before",
            config_json={"model": "gpt-4", "temp": 0.5},
            evaluation_score=0.8,
        )
        after_id = _seed_config_version(
            session, rt_id, version="cmp-after",
            config_json={"model": "gpt-4", "temp": 0.7},
            evaluation_score=0.9,
        )

        r = resp.post("/api/config-versions/compare", json={
            "before_version_id": before_id,
            "after_version_id": after_id,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["score_delta"] == pytest.approx(0.1, abs=0.01)
        assert len(body["changes"]) == 1
        assert body["changes"][0]["field"] == "temp"

    def test_compare_with_changes(self, client):
        resp = client

        session = client._test_session
        rt_id = _seed_runtime(session)
        before_id = _seed_config_version(
            session, rt_id, version="diff-before",
            config_json={"a": 1, "b": 2},
            evaluation_score=0.5,
        )
        after_id = _seed_config_version(
            session, rt_id, version="diff-after",
            config_json={"a": 1, "b": 3, "c": 4},
            evaluation_score=0.5,
        )

        r = resp.post("/api/config-versions/compare", json={
            "before_version_id": before_id,
            "after_version_id": after_id,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["score_delta"] == 0.0
        fields = {c["field"] for c in body["changes"]}
        assert "b" in fields
        assert "c" in fields

    def test_compare_not_found(self, client):
        resp = client
        r = resp.post("/api/config-versions/compare", json={
            "before_version_id": str(uuid.uuid4()),
            "after_version_id": str(uuid.uuid4()),
        })
        assert r.status_code == 404
