"""Tests for repository implementations.

Requires TEST_DATABASE_URL pointing to a test PostgreSQL database.
Example: TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_workflow_test

Each test runs in a rolled-back transaction so tests are isolated.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import sessionmaker


# ---------------------------------------------------------------------------
# TraceRepository
# ---------------------------------------------------------------------------

class TestPgTraceRepository:
    def _make(self, db):
        from repositories.trace_repository import PgTraceRepository
        return PgTraceRepository(lambda: db)

    def test_create_and_get_run(self, db):
        repo = self._make(db)
        run_id = repo.create_run("sess-1", "agent-a", "do something")
        assert run_id
        run = repo.get_run(run_id)
        assert run is not None
        assert run["session_id"] == "sess-1"
        assert run["agent_id"] == "agent-a"
        assert run["status"] == "running"

    def test_complete_run(self, db):
        repo = self._make(db)
        run_id = repo.create_run("sess-2", "agent-b", "task")
        repo.complete_run(run_id, "completed")
        run = repo.get_run(run_id)
        assert run["status"] == "completed"
        assert run["completed_at"] is not None

    def test_find_latest_run_by_session(self, db):
        repo = self._make(db)
        repo.create_run("sess-find", "agent-x", "first")
        repo.create_run("sess-find", "agent-x", "second")
        found = repo.find_latest_run(session_id="sess-find")
        assert found is not None
        assert found["input_summary"] == "second"

    def test_find_latest_run_by_linked(self, db):
        repo = self._make(db)
        repo.create_run("s1", "ag", "a", linked_session_id="link-99")
        found = repo.find_latest_run(linked_session_id="link-99")
        assert found is not None

    def test_add_span_and_list(self, db):
        repo = self._make(db)
        run_id = repo.create_run("s3", "ag", "t")
        sid1 = repo.add_span(run_id, "llm", "call 1", summary="s1")
        sid2 = repo.add_span(run_id, "tool", "call 2", summary="s2")
        spans = repo.list_spans(run_id)
        assert len(spans) == 2
        assert spans[0]["span_id"] == sid1

    def test_get_eval_summary(self, db):
        repo = self._make(db)
        rid = repo.create_run("s4", "ag-eval", "eval task")
        repo.add_span(rid, "tool", "t1")
        repo.complete_run(rid, "completed")
        summary = repo.get_eval_summary()
        assert summary["total_runs"] >= 1

    def test_save_and_get_rca_report(self, db):
        repo = self._make(db)
        rid = repo.create_run("s5", "ag-rca", "rca task")
        report = {"root_cause": "timeout", "category": "infra", "confidence": 0.9, "evidence": ["log1"], "next_actions": ["retry"]}
        saved = repo.save_rca_report("s5", report, run_id=rid)
        assert saved["report_id"]
        latest = repo.get_latest_rca_report("s5")
        assert latest is not None
        assert latest["root_cause"] == "timeout"

    def test_save_and_get_runbook(self, db):
        repo = self._make(db)
        rid = repo.create_run("s6", "ag-rb", "rb task")
        rb = {"severity": "high", "summary": "fix it", "markdown": "# Fix", "checklist": ["step1"]}
        saved = repo.save_runbook("s6", rb, run_id=rid)
        assert saved["runbook_id"]
        latest = repo.get_latest_runbook("s6")
        assert latest is not None
        assert latest["severity"] == "high"

    def test_update_latest_runbook(self, db):
        repo = self._make(db)
        rid = repo.create_run("s7", "ag-urb", "urb task")
        repo.save_runbook("s7", {"severity": "low", "summary": "s", "markdown": "m", "checklist": ["a"]}, run_id=rid)
        repo.update_latest_runbook("s7", {"severity": "low", "summary": "updated", "markdown": "m2", "checklist": ["b"]})
        latest = repo.get_latest_runbook("s7")
        assert latest["summary"] == "updated"

    def test_search_knowledge(self, db):
        repo = self._make(db)
        rid = repo.create_run("s8", "ag-search", "searchable task")
        repo.add_span(rid, "llm", "unique_title_xyz", summary="unique_summary_abc")
        results = repo.search_knowledge("unique_title_xyz")
        assert any(r["title"] == "unique_title_xyz" for r in results)

    def test_search_empty_query(self, db):
        assert self._make(db).search_knowledge("") == []


# ---------------------------------------------------------------------------
# ApprovalRepository
# ---------------------------------------------------------------------------

class TestPgApprovalRepository:
    def _make(self, db):
        from repositories.approval_repository import PgApprovalRepository
        return PgApprovalRepository(lambda: db)

    def test_create_and_get(self, db):
        repo = self._make(db)
        eid = str(uuid.uuid4())
        repo.create({"event_id": eid, "tool": "shell", "description": "rm -rf", "status": "pending"})
        got = repo.get(eid)
        assert got is not None
        assert got["status"] == "pending"

    def test_list_with_filter(self, db):
        repo = self._make(db)
        repo.create({"event_id": str(uuid.uuid4()), "tool": "t", "status": "pending"})
        repo.create({"event_id": str(uuid.uuid4()), "tool": "t", "status": "approved"})
        assert all(e["status"] == "pending" for e in repo.list(status="pending"))

    def test_update_status(self, db):
        repo = self._make(db)
        eid = str(uuid.uuid4())
        repo.create({"event_id": eid, "tool": "t", "status": "pending"})
        updated = repo.update(eid, {"status": "approved", "resolved_by": "admin"})
        assert updated["status"] == "approved"


# ---------------------------------------------------------------------------
# ReviewRepository
# ---------------------------------------------------------------------------

class TestPgReviewRepository:
    def _make(self, db):
        from repositories.review_repository import PgReviewRepository
        return PgReviewRepository(lambda: db)

    def _sample_review(self):
        from review.models import PRReview, ReviewFinding
        return PRReview(
            id=str(uuid.uuid4()), repo="org/repo", pr_number=42,
            pr_title="Fix bug", pr_author="dev", status="completed",
            findings=[ReviewFinding(
                id=str(uuid.uuid4()), file_path="main.py", line_number=10,
                severity="high", category="bug", title="issue", description="a bug",
            )],
            cost_usd=0.05, models_used=["gpt-4"],
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            summary="Found 1 issue",
        )

    def test_save_and_get(self, db):
        repo = self._make(db)
        review = self._sample_review()
        repo.save(review)
        got = repo.get(review.id)
        assert got is not None
        assert got.repo == "org/repo"

    def test_list_reviews(self, db):
        repo = self._make(db)
        repo.save(self._sample_review())
        assert len(repo.list_reviews()) >= 1

    def test_get_stats(self, db):
        repo = self._make(db)
        repo.save(self._sample_review())
        assert repo.get_stats()["total_reviews"] >= 1


# ---------------------------------------------------------------------------
# CostRepository
# ---------------------------------------------------------------------------

class TestPgCostRepository:
    def _make(self, db):
        from repositories.cost_repository import PgCostRepository
        return PgCostRepository(lambda: db)

    def test_record_usage(self, db):
        uid = self._make(db).record_usage("openai", "gpt-4", 1000, 500, 0.03, 0.06)
        assert uid

    def test_get_summary(self, db):
        repo = self._make(db)
        repo.record_usage("openai", "gpt-4", 1000, 500, 0.03, 0.06)
        assert repo.get_summary("daily")["request_count"] >= 1

    def test_budget_alerts(self, db):
        repo = self._make(db)
        repo.set_budget("daily", 0.001, provider="openai", alert_threshold=0.0)
        repo.record_usage("openai", "gpt-4", 10000, 5000, 0.03, 0.06)
        assert len(repo.check_alerts()) >= 1


# ---------------------------------------------------------------------------
# ChatRepository
# ---------------------------------------------------------------------------

class TestPgChatRepository:
    def _make(self, db):
        from repositories.chat_repository import PgChatRepository
        return PgChatRepository(lambda: db)

    def test_create_and_get_session(self, db):
        repo = self._make(db)
        session = repo.create_session(agent_id="main", title="Test")
        got = repo.get_session(session["session_id"])
        assert got is not None
        assert got["agent_id"] == "main"

    def test_append_message(self, db):
        repo = self._make(db)
        sid = repo.create_session()["session_id"]
        msg = repo.append_message(sid, "user", "hello")
        assert msg["role"] == "user"
        assert repo.get_session(sid)["message_count"] == 1

    def test_list_sessions(self, db):
        repo = self._make(db)
        repo.create_session(title="a")
        repo.create_session(title="b")
        assert len(repo.list_sessions()) >= 2

    def test_close_session(self, db):
        repo = self._make(db)
        sid = repo.create_session()["session_id"]
        repo.append_message(sid, "user", "msg")
        assert repo.close_session(sid) is True
        assert repo.get_session(sid) is None

    def test_update_context(self, db):
        repo = self._make(db)
        sid = repo.create_session()["session_id"]
        repo.update_session_context(sid, title="New")
        assert repo.get_session(sid)["title"] == "New"


# ---------------------------------------------------------------------------
# Write-then-read round-trip tests
# ---------------------------------------------------------------------------

class TestPgWriteThenRead:
    """Prove data written to PG can be read back through repository read methods."""

    def test_trace_run_round_trip(self, db):
        from repositories.trace_repository import PgTraceRepository
        repo = PgTraceRepository(lambda: db)
        run_id = repo.create_run("wrt-sess", "wrt-agent", "write then read test")
        assert run_id

        run = repo.get_run(run_id)
        assert run is not None
        assert run["session_id"] == "wrt-sess"
        assert run["agent_id"] == "wrt-agent"
        assert run["status"] == "running"

        repo.complete_run(run_id, "completed")
        run = repo.get_run(run_id)
        assert run["status"] == "completed"
        assert run["completed_at"] is not None

    def test_trace_span_round_trip(self, db):
        from repositories.trace_repository import PgTraceRepository
        repo = PgTraceRepository(lambda: db)
        run_id = repo.create_run("wrt-span", "ag", "span test")
        sid = repo.add_span(run_id, "llm", "test_span", summary="hello world")

        spans = repo.list_spans(run_id)
        assert len(spans) == 1
        assert spans[0]["span_id"] == sid
        assert spans[0]["title"] == "test_span"
        assert spans[0]["summary"] == "hello world"

    def test_rca_round_trip(self, db):
        from repositories.trace_repository import PgTraceRepository
        repo = PgTraceRepository(lambda: db)
        run_id = repo.create_run("wrt-rca", "ag", "rca test")
        report = {
            "root_cause": "disk full",
            "category": "infra",
            "confidence": 0.95,
            "evidence": ["df -h shows 100%"],
            "next_actions": ["cleanup logs"],
        }
        saved = repo.save_rca_report("wrt-rca", report, run_id=run_id)
        assert saved["report_id"]

        latest = repo.get_latest_rca_report("wrt-rca")
        assert latest is not None
        assert latest["root_cause"] == "disk full"
        assert latest["category"] == "infra"
        assert latest["confidence"] == 0.95
        assert "df -h" in latest["evidence"][0]

    def test_runbook_round_trip(self, db):
        from repositories.trace_repository import PgTraceRepository
        repo = PgTraceRepository(lambda: db)
        run_id = repo.create_run("wrt-rb", "ag", "runbook test")
        rb = {
            "severity": "critical",
            "summary": "disk cleanup",
            "markdown": "# Disk Cleanup\n\nRun `du -sh /*`",
            "checklist": ["Check /var/log", "Remove old backups"],
        }
        saved = repo.save_runbook("wrt-rb", rb, run_id=run_id)
        assert saved["runbook_id"]

        latest = repo.get_latest_runbook("wrt-rb")
        assert latest is not None
        assert latest["severity"] == "critical"
        assert latest["summary"] == "disk cleanup"
        assert len(latest["checklist"]) == 2

    def test_approval_round_trip(self, db):
        from repositories.approval_repository import PgApprovalRepository
        repo = PgApprovalRepository(lambda: db)
        eid = str(uuid.uuid4())
        event = {
            "event_id": eid,
            "tool": "shell",
            "description": "rm -rf /tmp/test",
            "status": "pending",
        }
        created = repo.create(event)
        assert created["event_id"] == eid

        got = repo.get(eid)
        assert got is not None
        assert got["status"] == "pending"
        assert got["tool"] == "shell"

        updated = repo.update(eid, {"status": "approved", "resolved_by": "admin"})
        assert updated["status"] == "approved"

        listed = repo.list(status="approved")
        assert any(e["event_id"] == eid for e in listed)

    def test_review_round_trip(self, db):
        from repositories.review_repository import PgReviewRepository
        from review.models import PRReview, ReviewFinding
        repo = PgReviewRepository(lambda: db)
        review = PRReview(
            id=str(uuid.uuid4()),
            repo="org/repo",
            pr_number=99,
            pr_title="WRT test",
            pr_author="tester",
            status="completed",
            findings=[ReviewFinding(
                id=str(uuid.uuid4()), file_path="app.py", line_number=42,
                severity="medium", category="style", title="unused var", description="unused variable",
            )],
            cost_usd=0.12,
            models_used=["claude-sonnet"],
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            summary="1 finding",
        )
        repo.save(review)

        got = repo.get(review.id)
        assert got is not None
        assert got.repo == "org/repo"
        assert got.pr_number == 99
        assert len(got.findings) == 1
        assert got.findings[0].description == "unused variable"

        listed = repo.list_reviews(repo="org/repo")
        assert any(r.id == review.id for r in listed)

        stats = repo.get_stats()
        assert stats["total_reviews"] >= 1

    def test_cost_round_trip(self, db):
        from repositories.cost_repository import PgCostRepository
        repo = PgCostRepository(lambda: db)
        uid = repo.record_usage("anthropic", "claude-sonnet", 2000, 1000, 0.003, 0.015)
        assert uid

        summary = repo.get_summary("daily")
        assert summary["request_count"] >= 1
        assert summary["total_input_tokens"] >= 2000

        breakdown = repo.get_breakdown(days=1)
        assert any(b["provider"] == "anthropic" for b in breakdown)

        trend = repo.get_trend(days=1)
        assert len(trend) >= 1

    def test_chat_round_trip(self, db):
        from repositories.chat_repository import PgChatRepository
        repo = PgChatRepository(lambda: db)
        session = repo.create_session(agent_id="wrt-agent", title="WRT Chat")
        sid = session["session_id"]

        got = repo.get_session(sid)
        assert got is not None
        assert got["agent_id"] == "wrt-agent"
        assert got["title"] == "WRT Chat"

        msg = repo.append_message(sid, "user", "hello from WRT")
        assert msg["role"] == "user"
        assert msg["content"] == "hello from WRT"

        got = repo.get_session(sid)
        assert got["message_count"] == 1

        listed = repo.list_sessions()
        assert any(s["session_id"] == sid for s in listed)

    def test_eval_summary_after_writes(self, db):
        from repositories.trace_repository import PgTraceRepository
        repo = PgTraceRepository(lambda: db)
        r1 = repo.create_run("eval-1", "agent-a", "task 1")
        repo.add_span(r1, "tool", "tool call 1")
        repo.complete_run(r1, "completed")

        r2 = repo.create_run("eval-2", "agent-b", "task 2")
        repo.add_span(r2, "llm", "llm call")
        repo.complete_run(r2, "error")

        summary = repo.get_eval_summary()
        assert summary["total_runs"] >= 2
        assert summary["error_runs"] >= 1
        assert summary["success_rate"] < 1.0
        assert len(summary["agents"]) >= 2

    def test_search_knowledge_after_writes(self, db):
        from repositories.trace_repository import PgTraceRepository
        repo = PgTraceRepository(lambda: db)
        rid = repo.create_run("search-1", "ag", "knowledge test")
        repo.add_span(rid, "tool", "unique_search_title_42", summary="unique_search_body_42")

        results = repo.search_knowledge("unique_search_title_42")
        assert any(r["title"] == "unique_search_title_42" for r in results)
