"""PostgreSQL-backed trace repository.

Maps the legacy TraceStore interface (session_id/agent_id lookups) onto
the new schema (Run + TraceSpan + RCAReport + Runbook).  session_id and
agent_id are stored in Run.metadata_json for backward-compatible lookups.

Uses per-operation sessions: each method creates a fresh session, commits,
and closes it. This avoids long-lived session accumulation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import Run, TraceSpan, RCAReport, Runbook, Runtime
from repositories.base import TraceRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PgTraceRepository(TraceRepository):
    """PostgreSQL implementation of TraceRepository."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def _run_in_session(self, fn, *, read_only: bool = False):
        """Execute fn(db) in a fresh session. Commits unless read_only."""
        db = self._session_factory()
        try:
            result = fn(db)
            if not read_only:
                db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # -- Run CRUD -----------------------------------------------------------

    def create_run(
        self,
        session_id: str,
        agent_id: str,
        input_summary: str,
        linked_session_id: Optional[str] = None,
    ) -> str:
        def _create(db: Session) -> str:
            runtime = self._ensure_runtime(db, agent_id)
            run = Run(
                id=uuid.uuid4(),
                runtime_id=runtime.id,
                title=input_summary[:500],
                status="running",
                input_summary=input_summary,
                started_at=_now(),
                metadata_json={
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "linked_session_id": linked_session_id,
                },
            )
            db.add(run)
            db.flush()
            return str(run.id)
        return self._run_in_session(_create)

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        def _complete(db: Session) -> None:
            run = db.get(Run, uuid.UUID(run_id))
            if not run:
                return
            run.status = status
            run.ended_at = _now()
            if run.started_at:
                delta = run.ended_at - run.started_at
                run.duration_ms = int(delta.total_seconds() * 1000)
        self._run_in_session(_complete)

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        def _get(db: Session) -> Optional[dict[str, Any]]:
            run = db.get(Run, uuid.UUID(run_id))
            return _run_to_dict(run) if run else None
        return self._run_in_session(_get, read_only=True)

    def find_latest_run(
        self,
        session_id: Optional[str] = None,
        linked_session_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        def _find(db: Session) -> Optional[dict[str, Any]]:
            q = db.query(Run)
            if session_id:
                q = q.filter(Run.metadata_json["session_id"].as_string() == session_id)
            elif linked_session_id:
                q = q.filter(Run.metadata_json["linked_session_id"].as_string() == linked_session_id)
            else:
                return None
            run = q.order_by(Run.started_at.desc()).first()
            return _run_to_dict(run) if run else None
        return self._run_in_session(_find, read_only=True)

    # -- Span CRUD ----------------------------------------------------------

    def add_span(
        self,
        run_id: str,
        span_type: str,
        title: str,
        summary: str = "",
        agent_name: Optional[str] = None,
        status: str = "completed",
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        def _add(db: Session) -> str:
            span = TraceSpan(
                id=uuid.uuid4(),
                run_id=uuid.UUID(run_id),
                span_type=span_type,
                title=title,
                status=status,
                agent_name=agent_name,
                output_summary=summary[:2000] if summary else None,
                started_at=_now(),
                ended_at=_now(),
                metadata_json=metadata or {},
            )
            db.add(span)
            db.flush()
            return str(span.id)
        return self._run_in_session(_add)

    def list_spans(self, run_id: str) -> list[dict[str, Any]]:
        def _list(db: Session) -> list[dict[str, Any]]:
            spans = (
                db.query(TraceSpan)
                .filter(TraceSpan.run_id == uuid.UUID(run_id))
                .order_by(TraceSpan.created_at.asc())
                .all()
            )
            return [_span_to_dict(s) for s in spans]
        return self._run_in_session(_list, read_only=True)

    # -- Eval summary -------------------------------------------------------

    def get_eval_summary(self) -> dict[str, Any]:
        def _summary(db: Session) -> dict[str, Any]:
            runs = db.query(Run).order_by(Run.started_at.desc()).all()
            spans = db.query(TraceSpan).all()

            status_counts: dict[str, int] = {}
            agent_counts: dict[str, dict[str, Any]] = {}
            durations: list[float] = []
            for run in runs:
                meta = run.metadata_json or {}
                agent_id = meta.get("agent_id", "unknown")
                status_counts[run.status] = status_counts.get(run.status, 0) + 1
                agent_counts.setdefault(agent_id, {"agent_id": agent_id, "runs": 0, "errors": 0})
                agent_counts[agent_id]["runs"] += 1
                if run.status == "error":
                    agent_counts[agent_id]["errors"] += 1
                if run.duration_ms is not None:
                    durations.append(run.duration_ms / 1000)

            span_counts: dict[str, int] = {}
            guardrail_count = 0
            for span in spans:
                span_counts[span.span_type] = span_counts.get(span.span_type, 0) + 1
                if span.span_type == "guardrail":
                    guardrail_count += 1

            total = len(runs)
            errors = status_counts.get("error", 0)
            return {
                "total_runs": total, "error_runs": errors,
                "success_rate": round((total - errors) / total, 4) if total else 0,
                "avg_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0,
                "status_counts": status_counts, "span_counts": span_counts,
                "handoff_count": span_counts.get("handoff", 0),
                "tool_count": span_counts.get("tool", 0),
                "guardrail_count": guardrail_count,
                "agents": sorted(agent_counts.values(), key=lambda item: item["runs"], reverse=True),
                "trend": _build_trend(runs),
            }
        return self._run_in_session(_summary, read_only=True)

    # -- RCA reports --------------------------------------------------------

    def save_rca_report(
        self,
        session_id: str,
        report: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        def _save(db: Session) -> dict[str, Any]:
            resolved_run_id = run_id or self._resolve_run_id(db, session_id)
            rca = RCAReport(
                id=uuid.uuid4(),
                run_id=uuid.UUID(resolved_run_id) if resolved_run_id else uuid.uuid4(),
                root_cause=report.get("root_cause"),
                category=report.get("category"),
                confidence=float(report.get("confidence") or 0),
                evidence_json={"evidence": report.get("evidence", [])},
                next_actions_json={"next_actions": report.get("next_actions", [])},
            )
            db.add(rca)
            db.flush()
            return {**report, "report_id": str(rca.id), "session_id": session_id, "run_id": resolved_run_id}
        return self._run_in_session(_save)

    def get_latest_rca_report(self, session_id: str) -> Optional[dict[str, Any]]:
        def _get(db: Session) -> Optional[dict[str, Any]]:
            run_id = self._resolve_run_id(db, session_id)
            if not run_id:
                return None
            rca = (
                db.query(RCAReport)
                .filter(RCAReport.run_id == uuid.UUID(run_id))
                .order_by(RCAReport.created_at.desc())
                .first()
            )
            if not rca:
                return None
            return {
                "report_id": str(rca.id), "root_cause": rca.root_cause,
                "category": rca.category,
                "confidence": float(rca.confidence) if rca.confidence else 0,
                "evidence": (rca.evidence_json or {}).get("evidence", []),
                "next_actions": (rca.next_actions_json or {}).get("next_actions", []),
            }
        return self._run_in_session(_get, read_only=True)

    # -- Runbooks -----------------------------------------------------------

    def save_runbook(
        self,
        session_id: str,
        runbook: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        def _save(db: Session) -> dict[str, Any]:
            resolved_run_id = run_id or self._resolve_run_id(db, session_id)
            rb = Runbook(
                id=uuid.uuid4(),
                run_id=uuid.UUID(resolved_run_id) if resolved_run_id else uuid.uuid4(),
                severity=runbook.get("severity"),
                summary=runbook.get("summary"),
                markdown=runbook.get("markdown"),
                steps_json={"checklist": runbook.get("checklist", [])},
            )
            db.add(rb)
            db.flush()
            return {**runbook, "runbook_id": str(rb.id), "session_id": session_id, "run_id": resolved_run_id}
        return self._run_in_session(_save)

    def get_latest_runbook(self, session_id: str) -> Optional[dict[str, Any]]:
        def _get(db: Session) -> Optional[dict[str, Any]]:
            run_id = self._resolve_run_id(db, session_id)
            if not run_id:
                return None
            rb = (
                db.query(Runbook)
                .filter(Runbook.run_id == uuid.UUID(run_id))
                .order_by(Runbook.created_at.desc())
                .first()
            )
            return _runbook_to_dict(rb) if rb else None
        return self._run_in_session(_get, read_only=True)

    def update_latest_runbook(
        self, session_id: str, runbook: dict[str, Any]
    ) -> dict[str, Any]:
        def _update(db: Session) -> dict[str, Any]:
            run_id = self._resolve_run_id(db, session_id)
            if not run_id:
                return runbook
            rb = (
                db.query(Runbook)
                .filter(Runbook.run_id == uuid.UUID(run_id))
                .order_by(Runbook.created_at.desc())
                .first()
            )
            if not rb:
                return runbook
            rb.steps_json = {"checklist": runbook.get("checklist", [])}
            rb.markdown = runbook.get("markdown")
            rb.summary = runbook.get("summary")
            db.flush()
            return {**runbook, "runbook_id": str(rb.id), "session_id": session_id, "run_id": run_id}
        return self._run_in_session(_update)

    # -- Knowledge search ---------------------------------------------------

    def search_knowledge(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        def _search(db: Session) -> list[dict[str, Any]]:
            term = query.strip()
            if not term:
                return []
            like = f"%{term}%"
            results: list[dict[str, Any]] = []

            spans = (
                db.query(TraceSpan)
                .filter(or_(TraceSpan.title.ilike(like), TraceSpan.output_summary.ilike(like)))
                .order_by(TraceSpan.created_at.desc()).limit(limit).all()
            )
            for s in spans:
                results.append({
                    "source": "trace", "item_id": str(s.id), "run_id": str(s.run_id),
                    "session_id": None, "title": s.title or "", "summary": s.output_summary or "",
                    "item_type": s.span_type, "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                })

            rcas = (
                db.query(RCAReport)
                .filter(or_(RCAReport.root_cause.ilike(like), RCAReport.category.ilike(like)))
                .order_by(RCAReport.created_at.desc()).limit(limit).all()
            )
            for r in rcas:
                results.append({
                    "source": "rca", "item_id": str(r.id), "run_id": str(r.run_id),
                    "session_id": None, "title": r.root_cause or "",
                    "summary": f"{r.category}: {r.root_cause}" if r.category else r.root_cause or "",
                    "item_type": r.category, "status": str(r.confidence) if r.confidence else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })

            runbooks = (
                db.query(Runbook)
                .filter(or_(Runbook.summary.ilike(like), Runbook.markdown.ilike(like)))
                .order_by(Runbook.created_at.desc()).limit(limit).all()
            )
            for rb in runbooks:
                results.append({
                    "source": "runbook", "item_id": str(rb.id), "run_id": str(rb.run_id),
                    "session_id": None, "title": rb.summary[:100] if rb.summary else "",
                    "summary": rb.summary or "", "item_type": rb.severity, "status": rb.severity,
                    "created_at": rb.created_at.isoformat() if rb.created_at else None,
                })

            results.sort(key=lambda item: item.get("created_at") or "", reverse=True)
            return results[:limit]
        return self._run_in_session(_search, read_only=True)

    # -- Internal helpers ---------------------------------------------------

    def _ensure_runtime(self, db: Session, agent_id: str) -> Runtime:
        runtime = db.query(Runtime).filter(Runtime.name == agent_id).first()
        if runtime:
            return runtime
        runtime = Runtime(id=uuid.uuid4(), name=agent_id, type="agent", status="active")
        db.add(runtime)
        db.flush()
        return runtime

    def _resolve_run_id(self, db: Session, session_id: str) -> Optional[str]:
        run = (
            db.query(Run)
            .filter(Run.metadata_json["session_id"].as_string() == session_id)
            .order_by(Run.started_at.desc())
            .first()
        )
        return str(run.id) if run else None


# -- Dict conversion helpers ------------------------------------------------

def _run_to_dict(run: Run) -> dict[str, Any]:
    meta = run.metadata_json or {}
    return {
        "run_id": str(run.id), "session_id": meta.get("session_id"),
        "agent_id": meta.get("agent_id"), "linked_session_id": meta.get("linked_session_id"),
        "input_summary": run.input_summary, "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.ended_at.isoformat() if run.ended_at else None,
        "duration_ms": run.duration_ms,
    }


def _span_to_dict(span: TraceSpan) -> dict[str, Any]:
    return {
        "span_id": str(span.id), "run_id": str(span.run_id),
        "span_type": span.span_type, "title": span.title,
        "summary": span.output_summary or "", "agent_name": span.agent_name,
        "status": span.status, "metadata": span.metadata_json or {},
        "started_at": span.started_at.isoformat() if span.started_at else None,
        "completed_at": span.ended_at.isoformat() if span.ended_at else None,
    }


def _runbook_to_dict(rb: Runbook) -> dict[str, Any]:
    steps = rb.steps_json or {}
    return {
        "runbook_id": str(rb.id), "title": rb.summary[:100] if rb.summary else "",
        "severity": rb.severity, "summary": rb.summary, "markdown": rb.markdown,
        "checklist": steps.get("checklist", []),
    }


def _build_trend(runs: list[Run]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for run in runs:
        day = run.started_at.strftime("%Y-%m-%d") if run.started_at else "unknown"
        bucket = buckets.setdefault(day, {"date": day, "runs": 0, "errors": 0, "durations": []})
        bucket["runs"] += 1
        if run.status == "error":
            bucket["errors"] += 1
        if run.duration_ms is not None:
            bucket["durations"].append(run.duration_ms / 1000)
    trend = []
    for day in sorted(buckets.keys())[-14:]:
        b = buckets[day]
        d, r, e = b["durations"], b["runs"], b["errors"]
        trend.append({
            "date": day, "runs": r, "errors": e,
            "success_rate": round((r - e) / r, 4) if r else 0,
            "avg_duration_seconds": round(sum(d) / len(d), 2) if d else 0,
        })
    return trend
