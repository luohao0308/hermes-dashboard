"""Audit Log API — v3.0 Enterprise.

Endpoints:
    GET /api/audit-logs — list audit log entries with filters
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import AuditLog
from security.rbac import require_role
from utils.cursor import apply_cursor

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class AuditLogEntry(BaseModel):
    id: str
    actor_type: Optional[str]
    actor_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    logs: list[AuditLogEntry]
    total: int
    next_cursor: Optional[str] = None
    has_more: bool = False


def _summarize(log: AuditLog) -> Optional[str]:
    """Build a human-readable summary from audit log fields."""
    parts = []
    if log.actor_type and log.actor_id:
        parts.append(f"{log.actor_type}:{log.actor_id}")
    parts.append(log.action)
    if log.resource_type:
        parts.append(log.resource_type)
    if log.resource_id:
        parts.append(log.resource_id[:12])
    return " ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# GET /api/audit-logs — list with filters
# ---------------------------------------------------------------------------


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    actor_type: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    cursor: Optional[str] = Query(None, description="Cursor for keyset pagination"),
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    """List audit log entries with optional filters.

    Requires operator or admin role.
    """
    query = db.query(AuditLog)

    if actor_type:
        query = query.filter(AuditLog.actor_type == actor_type)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)

    total = query.count()

    if cursor is not None:
        logs, next_cursor, has_more = apply_cursor(query, AuditLog, cursor, limit)
    else:
        logs = (
            query.order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        next_cursor = None
        has_more = (offset + limit) < total

    entries = []
    for log in logs:
        entries.append(AuditLogEntry(
            id=str(log.id),
            actor_type=log.actor_type,
            actor_id=log.actor_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            summary=_summarize(log),
            created_at=log.created_at,
        ))

    return AuditLogListResponse(
        logs=entries,
        total=total,
        next_cursor=next_cursor,
        has_more=has_more,
    )
