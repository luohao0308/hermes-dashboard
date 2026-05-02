"""PostgreSQL-backed approval repository.

Maps the legacy ApprovalEventStore interface onto the Approval model.
Uses per-operation sessions to avoid long-lived session accumulation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from models import Approval
from repositories.base import ApprovalRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PgApprovalRepository(ApprovalRepository):
    """PostgreSQL implementation of ApprovalRepository."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def _run_in_session(self, fn, *, read_only: bool = False):
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

    def create(self, event: dict[str, Any]) -> dict[str, Any]:
        def _create(db: Session) -> dict[str, Any]:
            approval = Approval(
                id=uuid.UUID(event["event_id"]) if event.get("event_id") else uuid.uuid4(),
                run_id=uuid.UUID(event["run_id"]) if event.get("run_id") else None,
                status=event.get("status", "pending"),
                reason=event.get("description"),
                requested_by=event.get("tool"),
                resolved_by=event.get("resolved_by"),
                resolved_note=event.get("resolution_note"),
            )
            db.add(approval)
            db.flush()
            return _merge_event(approval, event)
        return self._run_in_session(_create)

    def list(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        def _list(db: Session) -> list[dict[str, Any]]:
            q = db.query(Approval)
            if status:
                q = q.filter(Approval.status == status)
            return [_to_legacy_dict(a) for a in q.order_by(Approval.created_at.desc()).all()]
        return self._run_in_session(_list, read_only=True)

    def get(self, event_id: str) -> Optional[dict[str, Any]]:
        def _get(db: Session) -> Optional[dict[str, Any]]:
            try:
                pk = uuid.UUID(event_id)
            except ValueError:
                return None
            approval = db.get(Approval, pk)
            return _to_legacy_dict(approval) if approval else None
        return self._run_in_session(_get, read_only=True)

    def update(
        self, event_id: str, updates: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        def _update(db: Session) -> Optional[dict[str, Any]]:
            try:
                pk = uuid.UUID(event_id)
            except ValueError:
                return None
            approval = db.get(Approval, pk)
            if not approval:
                return None
            if "status" in updates:
                approval.status = updates["status"]
            if "resolved_by" in updates:
                approval.resolved_by = updates["resolved_by"]
            if "resolution_note" in updates:
                approval.resolved_note = updates["resolution_note"]
            if approval.status in ("approved", "rejected"):
                approval.resolved_at = _now()
            db.flush()
            return _to_legacy_dict(approval)
        return self._run_in_session(_update)


def _merge_event(approval: Approval, original: dict[str, Any]) -> dict[str, Any]:
    return {
        **original,
        "event_id": str(approval.id),
        "status": approval.status,
        "resolved_by": approval.resolved_by,
        "resolution_note": approval.resolved_note,
        "created_at": approval.created_at.isoformat() if approval.created_at else original.get("created_at"),
        "updated_at": approval.resolved_at.isoformat() if approval.resolved_at else original.get("updated_at"),
    }


def _to_legacy_dict(approval: Approval) -> dict[str, Any]:
    return {
        "event_id": str(approval.id),
        "tool": approval.requested_by,
        "risk": None,
        "decision": None,
        "description": approval.reason,
        "params_hash": None,
        "params_preview": None,
        "status": approval.status,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
        "updated_at": approval.resolved_at.isoformat() if approval.resolved_at else None,
        "resolved_by": approval.resolved_by,
        "resolution_note": approval.resolved_note,
    }
