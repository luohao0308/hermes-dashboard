"""Generic Run and TraceSpan API — v1.0 Workflow Observability MVP.

Endpoints:
    GET  /api/runs                  — list runs with filters
    GET  /api/runs/{run_id}         — get single run
    POST /api/runs                  — create a run
    PATCH /api/runs/{run_id}        — update a run
    POST /api/runs/{run_id}/spans   — add a span to a run
    GET  /api/runs/{run_id}/trace   — get run with full trace timeline
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Run, TraceSpan, Runtime
from security.rbac import require_role
from utils.cursor import apply_cursor
from schemas.run import (
    RunCreate,
    RunUpdate,
    RunResponse,
    RunListResponse,
    SpanCreate,
    SpanResponse,
    TraceResponse,
)

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# GET /api/runs — list with filters
# ---------------------------------------------------------------------------

@router.get("", response_model=RunListResponse)
def list_runs(
    runtime_id: Optional[uuid.UUID] = Query(None, description="Filter by runtime ID"),
    workflow_id: Optional[uuid.UUID] = Query(None, description="Filter by workflow definition ID"),
    status: Optional[str] = Query(None, description="Filter by status: queued, running, completed, error"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination (ignored when cursor is set)"),
    cursor: Optional[str] = Query(None, description="Cursor for keyset pagination"),
    db: Session = Depends(get_db),
):
    query = db.query(Run)
    if runtime_id is not None:
        query = query.filter(Run.runtime_id == runtime_id)
    if workflow_id is not None:
        query = query.filter(Run.workflow_id == workflow_id)
    if status is not None:
        query = query.filter(Run.status == status)

    total = query.count()

    if cursor is not None:
        items, next_cursor, has_more = apply_cursor(query, Run, cursor, limit)
    else:
        items = query.order_by(Run.created_at.desc()).offset(offset).limit(limit).all()
        next_cursor = None
        has_more = (offset + limit) < total

    return RunListResponse(
        items=[RunResponse.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
        next_cursor=next_cursor,
        has_more=has_more,
    )


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}
# ---------------------------------------------------------------------------

@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse.model_validate(run)


# ---------------------------------------------------------------------------
# POST /api/runs
# ---------------------------------------------------------------------------

@router.post("", response_model=RunResponse, status_code=201)
def create_run(
    body: RunCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    runtime = db.get(Runtime, body.runtime_id)
    if not runtime:
        raise HTTPException(status_code=400, detail=f"Runtime {body.runtime_id} not found")

    now = _now()
    run = Run(
        id=uuid.uuid4(),
        runtime_id=body.runtime_id,
        title=body.title,
        status=body.status,
        input_summary=body.input_summary,
        started_at=now,
        metadata_json=body.metadata_json,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return RunResponse.model_validate(run)


# ---------------------------------------------------------------------------
# PATCH /api/runs/{run_id}
# ---------------------------------------------------------------------------

@router.patch("/{run_id}", response_model=RunResponse)
def update_run(
    run_id: uuid.UUID,
    body: RunUpdate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(run, field, value)

    # Auto-set ended_at and duration when status transitions to terminal state
    if body.status in ("completed", "error") and run.ended_at is None:
        run.ended_at = _now()
        if run.started_at:
            delta = run.ended_at - run.started_at
            run.duration_ms = int(delta.total_seconds() * 1000)

    db.commit()
    db.refresh(run)
    return RunResponse.model_validate(run)


# ---------------------------------------------------------------------------
# POST /api/runs/{run_id}/spans
# ---------------------------------------------------------------------------

@router.post("/{run_id}/spans", response_model=SpanResponse, status_code=201)
def create_span(
    run_id: uuid.UUID,
    body: SpanCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    now = _now()
    span = TraceSpan(
        id=uuid.uuid4(),
        run_id=run_id,
        parent_span_id=body.parent_span_id,
        span_type=body.span_type,
        title=body.title,
        status=body.status,
        agent_name=body.agent_name,
        model_name=body.model_name,
        tool_name=body.tool_name,
        input_summary=body.input_summary,
        output_summary=body.output_summary,
        error_summary=body.error_summary,
        started_at=now,
        ended_at=now,
        input_tokens=body.input_tokens,
        output_tokens=body.output_tokens,
        cost=body.cost,
        metadata_json=body.metadata_json,
    )
    db.add(span)
    db.commit()
    db.refresh(span)
    return SpanResponse.model_validate(span)


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/trace
# ---------------------------------------------------------------------------

@router.get("/{run_id}/trace", response_model=TraceResponse)
def get_trace(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    spans = (
        db.query(TraceSpan)
        .filter(TraceSpan.run_id == run_id)
        .order_by(TraceSpan.created_at.asc())
        .all()
    )
    return TraceResponse(
        run=RunResponse.model_validate(run),
        spans=[SpanResponse.model_validate(s) for s in spans],
    )
