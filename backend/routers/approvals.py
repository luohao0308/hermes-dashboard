"""Approval API — v1.1 Tool Governance.

Endpoints:
    GET  /api/approvals                — list approvals with filters
    GET  /api/approvals/{id}           — get single approval
    POST /api/approvals/{id}/approve   — approve a pending approval
    POST /api/approvals/{id}/reject    — reject a pending approval
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Approval
from security.audit import write_audit_log
from security.rbac import require_role
from utils.cursor import apply_cursor
from schemas.tool import (
    ApprovalActionRequest,
    ApprovalListResponse,
    ApprovalResponse,
)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# GET /api/approvals — list with filters
# ---------------------------------------------------------------------------

@router.get("", response_model=ApprovalListResponse)
def list_approvals(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    run_id: Optional[uuid.UUID] = Query(None, description="Filter by run ID"),
    task_id: Optional[uuid.UUID] = Query(None, description="Filter by task ID (workflow approval nodes)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    cursor: Optional[str] = Query(None, description="Cursor for keyset pagination"),
    db: Session = Depends(get_db),
):
    query = db.query(Approval)
    if status is not None:
        query = query.filter(Approval.status == status)
    if run_id is not None:
        query = query.filter(Approval.run_id == run_id)
    if task_id is not None:
        query = query.filter(Approval.task_id == task_id)

    total = query.count()

    if cursor is not None:
        items, next_cursor, has_more = apply_cursor(query, Approval, cursor, limit)
    else:
        items = query.order_by(Approval.created_at.desc()).offset(offset).limit(limit).all()
        next_cursor = None
        has_more = (offset + limit) < total

    return ApprovalListResponse(
        items=[ApprovalResponse.model_validate(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
        next_cursor=next_cursor,
        has_more=has_more,
    )






# ---------------------------------------------------------------------------
# POST /api/approvals/batch/approve — batch approve
# ---------------------------------------------------------------------------


class BatchApprovalRequest(BaseModel):
    approval_ids: list[str] = Field(..., min_length=1, max_length=100)
    resolved_by: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = None


class BatchResultItem(BaseModel):
    id: str
    status: str  # "approved", "rejected", "skipped", "not_found"


class BatchApprovalResponse(BaseModel):
    processed: int
    skipped: int
    results: list[BatchResultItem]


@router.post("/batch/approve", response_model=BatchApprovalResponse)
def batch_approve(
    body: BatchApprovalRequest,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    results: list[BatchResultItem] = []
    skipped = 0

    for raw_id in body.approval_ids:
        try:
            approval_id = uuid.UUID(raw_id)
        except ValueError:
            results.append(BatchResultItem(id=raw_id, status="not_found"))
            continue

        approval = db.get(Approval, approval_id)
        if not approval:
            results.append(BatchResultItem(id=raw_id, status="not_found"))
            continue

        if approval.status != "pending":
            skipped += 1
            results.append(BatchResultItem(id=raw_id, status="skipped"))
            continue

        before = {
            "status": approval.status,
            "resolved_by": approval.resolved_by,
        }

        now = _now()
        approval.status = "approved"
        approval.resolved_by = body.resolved_by or "local_user"
        approval.resolved_note = body.note
        approval.resolved_at = now

        write_audit_log(
            db,
            actor_type="user",
            actor_id=body.resolved_by or "local_user",
            action="approval.approved",
            resource_type="approval",
            resource_id=str(approval_id),
            before_json=before,
            after_json={"status": "approved", "resolved_by": approval.resolved_by},
        )
        results.append(BatchResultItem(id=raw_id, status="approved"))

    db.commit()
    return BatchApprovalResponse(
        processed=len(body.approval_ids),
        skipped=skipped,
        results=results,
    )


# ---------------------------------------------------------------------------
# POST /api/approvals/batch/reject — batch reject
# ---------------------------------------------------------------------------


@router.post("/batch/reject", response_model=BatchApprovalResponse)
def batch_reject(
    body: BatchApprovalRequest,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    results: list[BatchResultItem] = []
    skipped = 0

    for raw_id in body.approval_ids:
        try:
            approval_id = uuid.UUID(raw_id)
        except ValueError:
            results.append(BatchResultItem(id=raw_id, status="not_found"))
            continue

        approval = db.get(Approval, approval_id)
        if not approval:
            results.append(BatchResultItem(id=raw_id, status="not_found"))
            continue

        if approval.status != "pending":
            skipped += 1
            results.append(BatchResultItem(id=raw_id, status="skipped"))
            continue

        before = {
            "status": approval.status,
            "resolved_by": approval.resolved_by,
        }

        now = _now()
        approval.status = "rejected"
        approval.resolved_by = body.resolved_by or "local_user"
        approval.resolved_note = body.note
        approval.resolved_at = now

        write_audit_log(
            db,
            actor_type="user",
            actor_id=body.resolved_by or "local_user",
            action="approval.rejected",
            resource_type="approval",
            resource_id=str(approval_id),
            before_json=before,
            after_json={"status": "rejected", "resolved_by": approval.resolved_by},
        )
        results.append(BatchResultItem(id=raw_id, status="rejected"))

    db.commit()
    return BatchApprovalResponse(
        processed=len(body.approval_ids),
        skipped=skipped,
        results=results,
    )


# ---------------------------------------------------------------------------
# GET /api/approvals/{approval_id}
# ---------------------------------------------------------------------------

@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(approval_id: uuid.UUID, db: Session = Depends(get_db)):
    approval = db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return ApprovalResponse.model_validate(approval)


# ---------------------------------------------------------------------------
# POST /api/approvals/{approval_id}/approve
# ---------------------------------------------------------------------------

@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
def approve_approval(
    approval_id: uuid.UUID,
    body: ApprovalActionRequest | None = None,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    approval = db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Approval already {approval.status}",
        )

    payload = body or ApprovalActionRequest()
    before = {
        "status": approval.status,
        "resolved_by": approval.resolved_by,
        "resolved_note": approval.resolved_note,
    }

    now = _now()
    approval.status = "approved"
    approval.resolved_by = payload.resolved_by or "local_user"
    approval.resolved_note = payload.note
    approval.resolved_at = now

    write_audit_log(
        db,
        actor_type="user",
        actor_id=payload.resolved_by or "local_user",
        action="approval.approved",
        resource_type="approval",
        resource_id=str(approval_id),
        before_json=before,
        after_json={
            "status": "approved",
            "resolved_by": approval.resolved_by,
            "resolved_note": approval.resolved_note,
        },
    )

    # Complete the associated task and advance the workflow
    if approval.task_id:
        from models import Task, Run
        task = db.get(Task, approval.task_id)
        if task and task.status == "waiting_approval":
            task.status = "completed"
            task.ended_at = _now()
            if task.started_at:
                task.duration_ms = int((task.ended_at - task.started_at).total_seconds() * 1000)
            if task.run_id:
                run = db.get(Run, task.run_id)
                if run and run.status == "running":
                    from routers.workflows import _advance_workflow
                    _advance_workflow(db, run)

    db.commit()
    db.refresh(approval)
    return ApprovalResponse.model_validate(approval)


# ---------------------------------------------------------------------------
# POST /api/approvals/{approval_id}/reject
# ---------------------------------------------------------------------------

@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
def reject_approval(
    approval_id: uuid.UUID,
    body: ApprovalActionRequest | None = None,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    approval = db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Approval already {approval.status}",
        )

    payload = body or ApprovalActionRequest()
    before = {
        "status": approval.status,
        "resolved_by": approval.resolved_by,
        "resolved_note": approval.resolved_note,
    }

    now = _now()
    approval.status = "rejected"
    approval.resolved_by = payload.resolved_by or "local_user"
    approval.resolved_note = payload.note
    approval.resolved_at = now

    write_audit_log(
        db,
        actor_type="user",
        actor_id=payload.resolved_by or "local_user",
        action="approval.rejected",
        resource_type="approval",
        resource_id=str(approval_id),
        before_json=before,
        after_json={
            "status": "rejected",
            "resolved_by": approval.resolved_by,
            "resolved_note": approval.resolved_note,
        },
    )

    db.commit()
    db.refresh(approval)
    return ApprovalResponse.model_validate(approval)


