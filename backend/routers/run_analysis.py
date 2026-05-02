"""Run-based RCA and Runbook API — v1.2.

Endpoints:
    POST /api/runs/{run_id}/rca        — generate RCA from run data
    GET  /api/runs/{run_id}/rca        — retrieve latest RCA
    POST /api/runs/{run_id}/runbook    — generate Runbook from RCA + trace
    GET  /api/runs/{run_id}/runbook    — retrieve latest Runbook
    POST /api/runs/{run_id}/export     — export RCA/Runbook as Markdown artifact
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import get_db
from models import Run, TraceSpan, RCAReport, Runbook, Artifact
from schemas.rca import RCAReportResponse
from schemas.runbook import RunbookResponse
from security.rbac import require_role
from agent.rca import analyze_failure
from agent.runbook import generate_runbook

router = APIRouter(prefix="/api/runs", tags=["run-analysis"])
limiter = Limiter(key_func=get_remote_address)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers: ORM -> dict conversion for agent functions
# ---------------------------------------------------------------------------


def _run_to_context(run: Run) -> dict[str, Any]:
    meta = run.metadata_json or {}
    return {
        "run_id": str(run.id),
        "session_id": meta.get("session_id") or str(run.id),
        "agent_id": meta.get("agent_id", "unknown"),
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.ended_at.isoformat() if run.ended_at else None,
        "duration_ms": run.duration_ms,
    }


def _span_to_context(span: TraceSpan) -> dict[str, Any]:
    return {
        "span_id": str(span.id),
        "run_id": str(span.run_id),
        "span_type": span.span_type,
        "title": span.title,
        "summary": span.output_summary or "",
        "status": span.status,
        "agent_name": span.agent_name,
        "metadata": span.metadata_json or {},
        "started_at": span.started_at.isoformat() if span.started_at else None,
        "completed_at": span.ended_at.isoformat() if span.ended_at else None,
    }


def _session_from_run(run: Run) -> dict[str, Any]:
    meta = run.metadata_json or {}
    status = run.status
    if status == "completed":
        end_reason = "completed"
    elif status == "error":
        end_reason = "error"
    else:
        end_reason = ""
    return {
        "task_id": meta.get("session_id") or str(run.id),
        "id": str(run.id),
        "name": run.title,
        "status": status,
        "end_reason": end_reason,
        "messages": [],
        "message_count": 0,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.ended_at.isoformat() if run.ended_at else None,
    }


# ---------------------------------------------------------------------------
# ORM -> response dict
# ---------------------------------------------------------------------------


def _rca_to_response(rca: RCAReport) -> dict[str, Any]:
    evidence_raw = (rca.evidence_json or {}).get("evidence", [])
    next_actions = (rca.next_actions_json or {}).get("next_actions", [])
    confidence = float(rca.confidence) if rca.confidence else 0
    return {
        "report_id": str(rca.id),
        "run_id": str(rca.run_id),
        "category": rca.category or "unknown",
        "root_cause": rca.root_cause or "",
        "confidence": confidence,
        "evidence": evidence_raw,
        "next_actions": next_actions,
        "low_confidence": confidence < 0.6,
        "generated_at": rca.created_at.isoformat() if rca.created_at else "",
        "analyzer": "structured_rca_v2",
    }


def _runbook_to_response(rb: Runbook) -> dict[str, Any]:
    steps_data = rb.steps_json or {}
    checklist = steps_data.get("checklist", [])
    execution_steps = steps_data.get("execution_steps", [])
    return {
        "runbook_id": str(rb.id),
        "run_id": str(rb.run_id),
        "rca_report_id": None,
        "title": (rb.summary or "")[:100],
        "severity": rb.severity or "low",
        "summary": rb.summary or "",
        "checklist": checklist,
        "execution_steps": execution_steps,
        "evidence_count": 0,
        "markdown": rb.markdown or "",
        "generated_at": rb.created_at.isoformat() if rb.created_at else "",
        "generator": "rule_based_runbook_v1",
    }


# ---------------------------------------------------------------------------
# POST /api/runs/{run_id}/rca
# ---------------------------------------------------------------------------


@router.post("/{run_id}/rca", response_model=RCAReportResponse)
@limiter.limit("20/minute")
def generate_rca(
    request: Request,
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    spans = (
        db.query(TraceSpan)
        .filter(TraceSpan.run_id == run_id)
        .order_by(TraceSpan.created_at.asc())
        .all()
    )

    session = _session_from_run(run)
    run_ctx = _run_to_context(run)
    span_dicts = [_span_to_context(s) for s in spans]

    report = analyze_failure(
        session=session, logs=[], run=run_ctx, spans=span_dicts, config_evaluation=None,
    )

    rca = RCAReport(
        id=uuid.uuid4(),
        run_id=run_id,
        root_cause=report.get("root_cause"),
        category=report.get("category"),
        confidence=float(report.get("confidence") or 0),
        evidence_json={"evidence": report.get("evidence", [])},
        next_actions_json={"next_actions": report.get("next_actions", [])},
    )
    db.add(rca)
    db.commit()
    db.refresh(rca)

    return _rca_to_response(rca)


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/rca
# ---------------------------------------------------------------------------


@router.get("/{run_id}/rca", response_model=RCAReportResponse)
def get_latest_rca(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    rca = (
        db.query(RCAReport)
        .filter(RCAReport.run_id == run_id)
        .order_by(RCAReport.created_at.desc())
        .first()
    )
    if not rca:
        raise HTTPException(status_code=404, detail="No RCA report found for this run")

    return _rca_to_response(rca)


# ---------------------------------------------------------------------------
# POST /api/runs/{run_id}/runbook
# ---------------------------------------------------------------------------


@router.post("/{run_id}/runbook", response_model=RunbookResponse)
@limiter.limit("20/minute")
def generate_runbook_for_run(
    request: Request,
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    spans = (
        db.query(TraceSpan)
        .filter(TraceSpan.run_id == run_id)
        .order_by(TraceSpan.created_at.asc())
        .all()
    )

    session = _session_from_run(run)
    run_ctx = _run_to_context(run)
    span_dicts = [_span_to_context(s) for s in spans]

    # Get or generate RCA first
    rca_orm = (
        db.query(RCAReport)
        .filter(RCAReport.run_id == run_id)
        .order_by(RCAReport.created_at.desc())
        .first()
    )
    if rca_orm:
        rca_dict = _rca_to_response(rca_orm)
    else:
        rca_dict = analyze_failure(
            session=session, logs=[], run=run_ctx, spans=span_dicts, config_evaluation=None,
        )
        rca_orm = RCAReport(
            id=uuid.uuid4(),
            run_id=run_id,
            root_cause=rca_dict.get("root_cause"),
            category=rca_dict.get("category"),
            confidence=float(rca_dict.get("confidence") or 0),
            evidence_json={"evidence": rca_dict.get("evidence", [])},
            next_actions_json={"next_actions": rca_dict.get("next_actions", [])},
        )
        db.add(rca_orm)
        db.flush()

    runbook_dict = generate_runbook(session, rca=rca_dict, run=run_ctx, spans=span_dicts)

    rb = Runbook(
        id=uuid.uuid4(),
        run_id=run_id,
        severity=runbook_dict.get("severity"),
        summary=runbook_dict.get("summary"),
        markdown=runbook_dict.get("markdown"),
        steps_json={
            "checklist": runbook_dict.get("checklist", []),
            "execution_steps": runbook_dict.get("execution_steps", []),
        },
    )
    db.add(rb)
    db.commit()
    db.refresh(rb)

    result = _runbook_to_response(rb)
    result["rca_report_id"] = str(rca_orm.id)
    result["execution_steps"] = runbook_dict.get("execution_steps", [])
    result["evidence_count"] = runbook_dict.get("evidence_count", 0)
    return result


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/runbook
# ---------------------------------------------------------------------------


@router.get("/{run_id}/runbook", response_model=RunbookResponse)
def get_latest_runbook(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    rb = (
        db.query(Runbook)
        .filter(Runbook.run_id == run_id)
        .order_by(Runbook.created_at.desc())
        .first()
    )
    if not rb:
        raise HTTPException(status_code=404, detail="No runbook found for this run")

    return _runbook_to_response(rb)


# ---------------------------------------------------------------------------
# POST /api/runs/{run_id}/export — export RCA/Runbook as Markdown artifact
# ---------------------------------------------------------------------------


class ExportRequest(BaseModel):
    kind: str = Field(description="rca or runbook")


@router.post("/{run_id}/export")
def export_as_artifact(
    run_id: uuid.UUID,
    body: ExportRequest,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if body.kind == "rca":
        rca = (
            db.query(RCAReport)
            .filter(RCAReport.run_id == run_id)
            .order_by(RCAReport.created_at.desc())
            .first()
        )
        if not rca:
            raise HTTPException(status_code=404, detail="No RCA report found")
        rca_dict = _rca_to_response(rca)
        content = _rca_markdown(rca_dict)
        title = f"RCA Report — {run.title or str(run.id)[:8]}"
        artifact_type = "rca_report"
    elif body.kind == "runbook":
        rb = (
            db.query(Runbook)
            .filter(Runbook.run_id == run_id)
            .order_by(Runbook.created_at.desc())
            .first()
        )
        if not rb:
            raise HTTPException(status_code=404, detail="No runbook found")
        content = rb.markdown or ""
        title = f"Runbook — {run.title or str(run.id)[:8]}"
        artifact_type = "runbook"
    else:
        raise HTTPException(status_code=400, detail="kind must be 'rca' or 'runbook'")

    artifact = Artifact(
        id=uuid.uuid4(),
        run_id=run_id,
        artifact_type=artifact_type,
        title=title,
        content_text=content,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    return {
        "artifact_id": str(artifact.id),
        "artifact_type": artifact_type,
        "title": title,
        "content_text": content,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else "",
    }


def _rca_markdown(rca: dict[str, Any]) -> str:
    lines = [
        "# RCA Report",
        "",
        f"- Run: `{rca.get('run_id', 'unknown')}`",
        f"- Category: `{rca.get('category', 'unknown')}`",
        f"- Confidence: {round(rca.get('confidence', 0) * 100)}%",
        f"- Root Cause: {rca.get('root_cause', '')}",
        "",
        "## Evidence",
        "",
    ]
    for item in rca.get("evidence", []):
        lines.append(f"- [{item.get('source')}] {item.get('title')}: {item.get('detail')}")
    lines.extend(["", "## Next Actions", ""])
    for action in rca.get("next_actions", []):
        lines.append(f"- {action}")
    return "\n".join(lines)
