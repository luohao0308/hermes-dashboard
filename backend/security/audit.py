"""Centralized audit logging.

Replaces inline _write_audit helpers scattered across routers.
All mutations to shared resources should call write_audit_log().
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    *,
    actor_type: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    before_json: Optional[dict] = None,
    after_json: Optional[dict] = None,
) -> AuditLog:
    """Write an audit log entry.

    Args:
        db: Database session.
        actor_type: Who performed the action (e.g., "user", "connector", "worker", "system").
        actor_id: Identifier of the actor (e.g., user UUID, connector UUID).
        action: What was done (e.g., "connector.created", "workflow.updated", "approval.approved").
        resource_type: Type of resource affected (e.g., "connector", "workflow", "run").
        resource_id: ID of the affected resource.
        before_json: State before the change (for updates).
        after_json: State after the change (or event details).

    Returns:
        The created AuditLog entry (already flushed to DB).
    """
    log = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_json=before_json,
        after_json=after_json,
    )
    db.add(log)
    db.flush()
    return log
