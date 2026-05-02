"""Connector Framework API — v1.3 + v3.0 enhancements.

Endpoints:
    GET    /api/connectors              — list connector configurations
    POST   /api/connectors              — create connector (encrypts secrets)
    PUT    /api/connectors/{id}         — update connector (encrypts secrets)
    DELETE /api/connectors/{id}         — delete connector
    POST   /api/connectors/{id}/events  — ingest events (webhook signature verified)

Event ingestion is idempotent: duplicate (connector_id, event_id) pairs
are silently deduplicated. Connector errors are recorded as trace spans
and audit log entries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import get_db
from models import (
    ConnectorConfig,
    Runtime,
    Run,
    TraceSpan,
    ToolCall,
    Approval,
    Artifact,
    FailedEvent,
)
from schemas.connector import (
    ConnectorEvent,
    ConnectorConfigResponse,
    ConnectorListResponse,
    ConnectorEventResult,
    ConnectorEventResponse,
)
from security.audit import write_audit_log
from security.secret_manager import encrypt_config_secrets, decrypt_config_secrets
from security.rbac import require_role
from security.webhook import verify_signature
from utils.cursor import apply_cursor

import logging
_logger = logging.getLogger("connector")

router = APIRouter(prefix="/api/connectors", tags=["connectors"])
limiter = Limiter(key_func=get_remote_address)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# GET /api/connectors — list connector configurations
# ---------------------------------------------------------------------------


@router.get("", response_model=ConnectorListResponse)
def list_connectors(
    runtime_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ConnectorConfig)
    if runtime_id is not None:
        query = query.filter(ConnectorConfig.runtime_id == runtime_id)
    items = query.order_by(ConnectorConfig.created_at.desc()).all()
    return ConnectorListResponse(
        items=[ConnectorConfigResponse.model_validate(c) for c in items],
        total=len(items),
    )


# ---------------------------------------------------------------------------
# POST /api/connectors — create connector (encrypts secrets)
# ---------------------------------------------------------------------------


class ConnectorCreateRequest(BaseModel):
    runtime_id: uuid.UUID
    connector_type: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=255)
    enabled: bool = True
    config_json: Optional[dict[str, Any]] = None
    secret_ref: Optional[str] = None
    environment_id: Optional[uuid.UUID] = None


@router.post("", response_model=ConnectorConfigResponse, status_code=201)
def create_connector(
    body: ConnectorCreateRequest,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    encrypted_config = encrypt_config_secrets(body.config_json)
    connector = ConnectorConfig(
        runtime_id=body.runtime_id,
        connector_type=body.connector_type,
        display_name=body.display_name,
        enabled=body.enabled,
        config_json=encrypted_config,
        secret_ref=body.secret_ref,
        environment_id=body.environment_id,
    )
    db.add(connector)
    db.flush()
    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="connector.created",
        resource_type="connector",
        resource_id=str(connector.id),
        after_json={"display_name": body.display_name, "connector_type": body.connector_type},
    )
    db.commit()
    db.refresh(connector)
    return ConnectorConfigResponse.model_validate(connector)


# ---------------------------------------------------------------------------
# PUT /api/connectors/{id} — update connector (encrypts secrets)
# ---------------------------------------------------------------------------


class ConnectorUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None
    config_json: Optional[dict[str, Any]] = None
    secret_ref: Optional[str] = None
    environment_id: Optional[uuid.UUID] = None


@router.put("/{connector_id}", response_model=ConnectorConfigResponse)
def update_connector(
    connector_id: uuid.UUID,
    body: ConnectorUpdateRequest,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    connector = db.get(ConnectorConfig, connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    before = {"display_name": connector.display_name, "enabled": connector.enabled}

    if body.display_name is not None:
        connector.display_name = body.display_name
    if body.enabled is not None:
        connector.enabled = body.enabled
    if body.config_json is not None:
        connector.config_json = encrypt_config_secrets(body.config_json)
    if body.secret_ref is not None:
        connector.secret_ref = body.secret_ref
    if body.environment_id is not None:
        connector.environment_id = body.environment_id

    db.flush()
    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="connector.updated",
        resource_type="connector",
        resource_id=str(connector.id),
        before_json=before,
        after_json={"display_name": connector.display_name, "enabled": connector.enabled},
    )
    db.commit()
    db.refresh(connector)
    return ConnectorConfigResponse.model_validate(connector)


# ---------------------------------------------------------------------------
# DELETE /api/connectors/{id} — delete connector
# ---------------------------------------------------------------------------


@router.delete("/{connector_id}", status_code=204)
def delete_connector(
    connector_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    connector = db.get(ConnectorConfig, connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="connector.deleted",
        resource_type="connector",
        resource_id=str(connector.id),
        before_json={"display_name": connector.display_name, "connector_type": connector.connector_type},
    )
    db.delete(connector)
    db.commit()


# ---------------------------------------------------------------------------
# POST /api/connectors/{id}/events — ingest events
# ---------------------------------------------------------------------------


@router.post("/{connector_id}/events", response_model=ConnectorEventResponse)
@limiter.limit("60/minute")
async def ingest_events(
    connector_id: uuid.UUID,
    request: Request,
    body: list[ConnectorEvent],
    db: Session = Depends(get_db),
):
    connector = db.get(ConnectorConfig, connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    if not connector.enabled:
        raise HTTPException(status_code=403, detail="Connector is disabled")

    # Auth: service token OR webhook signature
    from security.auth import validate_service_token

    service_token = request.headers.get("X-Service-Token", "")
    auth_header = request.headers.get("Authorization", "")
    bearer_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    has_service_token = (
        (service_token and validate_service_token(service_token))
        or (bearer_token and validate_service_token(bearer_token))
    )

    if not has_service_token:
        # Fall back to webhook signature verification
        config = connector.config_json or {}
        webhook_secret = config.get("webhook_secret")
        if webhook_secret:
            try:
                from security.secret_manager import decrypt_secret
                webhook_secret = decrypt_secret(webhook_secret)
            except ValueError:
                pass

            signature = request.headers.get("X-Webhook-Signature", "")
            raw_body = await request.body()
            try:
                verify_signature(raw_body, signature, webhook_secret)
            except ValueError as exc:
                raise HTTPException(status_code=401, detail=str(exc))

    runtime_id = connector.runtime_id
    results: list[ConnectorEventResult] = []
    actor_type = "service" if has_service_token else "connector"

    _logger.info(
        "connector_ingestion_start",
        extra={
            "connector_id": str(connector_id),
            "actor_type": actor_type,
            "event_count": len(body),
        },
    )

    for event in body:
        try:
            result = _process_event(db, connector_id, runtime_id, event)
            results.append(result)
        except Exception as exc:
            _logger.warning(
                "connector_event_error",
                extra={
                    "connector_id": str(connector_id),
                    "actor_type": actor_type,
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                },
                exc_info=True,
            )
            write_audit_log(
                db,
                actor_type=actor_type,
                actor_id=str(connector_id),
                action="event.error",
                resource_type="connector_event",
                resource_id=event.event_id,
                after_json={"event_type": event.event_type, "error": str(exc)},
            )
            # Persist failed event for replay
            failed = FailedEvent(
                connector_id=connector_id,
                event_type=event.event_type,
                event_id=event.event_id,
                run_id=event.run_id,
                payload=event.payload,
                error_message=str(exc)[:1000],
            )
            db.add(failed)
            results.append(ConnectorEventResult(
                event_type=event.event_type,
                event_id=event.event_id,
                status="error",
                detail=str(exc)[:500],
            ))

    accepted = sum(1 for r in results if r.status == "accepted")
    errors = sum(1 for r in results if r.status == "error")
    _logger.info(
        "connector_ingestion_complete",
        extra={
            "connector_id": str(connector_id),
            "actor_type": actor_type,
            "accepted": accepted,
            "errors": errors,
            "total": len(results),
        },
    )

    db.commit()
    return ConnectorEventResponse(
        connector_id=str(connector_id),
        results=results,
    )


# ---------------------------------------------------------------------------
# Event processing
# ---------------------------------------------------------------------------


def _process_event(
    db: Session,
    connector_id: uuid.UUID,
    runtime_id: uuid.UUID,
    event: ConnectorEvent,
) -> ConnectorEventResult:
    if event.event_id:
        existing = _find_duplicate(db, connector_id, event.event_id)
        if existing:
            return ConnectorEventResult(
                event_type=event.event_type,
                event_id=event.event_id,
                status="duplicate",
                resource_id=existing,
            )

    handler = _EVENT_HANDLERS.get(event.event_type)
    if not handler:
        return ConnectorEventResult(
            event_type=event.event_type,
            event_id=event.event_id,
            status="error",
            detail=f"Unsupported event type: {event.event_type}",
        )

    resource_id = handler(db, runtime_id, event, connector_id=connector_id)

    if event.event_id and resource_id:
        _record_event_id(db, connector_id, event.event_id, resource_id)

    return ConnectorEventResult(
        event_type=event.event_type,
        event_id=event.event_id,
        status="accepted",
        resource_id=resource_id,
    )


def _find_duplicate(
    db: Session,
    connector_id: uuid.UUID,
    event_id: str,
) -> Optional[str]:
    existing = (
        db.query(Run)
        .filter(
            Run.metadata_json["connector_id"].as_string() == str(connector_id),
            Run.metadata_json["connector_event_id"].as_string() == event_id,
        )
        .first()
    )
    if existing:
        return str(existing.id)

    existing_span = (
        db.query(TraceSpan)
        .filter(
            TraceSpan.metadata_json["connector_event_id"].as_string() == event_id,
        )
        .first()
    )
    if existing_span:
        return str(existing_span.id)

    return None


def _record_event_id(
    db: Session,
    connector_id: uuid.UUID,
    event_id: str,
    resource_id: str,
) -> None:
    write_audit_log(
        db,
        actor_type="connector",
        actor_id=str(connector_id),
        action="event.ingested",
        resource_type="connector_event",
        resource_id=resource_id,
        after_json={"event_id": event_id},
    )


# ---------------------------------------------------------------------------
# Event type handlers
# ---------------------------------------------------------------------------


def _handle_runtime_upserted(
    db: Session,
    runtime_id: uuid.UUID,
    event: ConnectorEvent,
    **kwargs,
) -> str:
    payload = event.payload
    runtime = db.get(Runtime, runtime_id)
    if runtime:
        if payload.get("name"):
            runtime.name = payload["name"]
        if payload.get("status"):
            runtime.status = payload["status"]
        if payload.get("config_json"):
            runtime.config_json = payload["config_json"]
        db.flush()
        return str(runtime.id)
    else:
        runtime = Runtime(
            id=runtime_id,
            name=payload.get("name", f"runtime-{str(runtime_id)[:8]}"),
            type=payload.get("type", "connector"),
            status=payload.get("status", "active"),
            config_json=payload.get("config_json"),
        )
        db.add(runtime)
        db.flush()
        return str(runtime.id)


def _handle_run_created(
    db: Session,
    runtime_id: uuid.UUID,
    event: ConnectorEvent,
    connector_id: uuid.UUID = None,
    **kwargs,
) -> str:
    payload = event.payload
    run_id = uuid.UUID(event.run_id) if event.run_id else uuid.uuid4()
    run = Run(
        id=run_id,
        runtime_id=runtime_id,
        title=payload.get("title", "Connector run"),
        status=payload.get("status", "running"),
        input_summary=payload.get("input_summary"),
        started_at=_parse_ts(event.timestamp),
        metadata_json={
            "connector_id": str(connector_id) if connector_id else str(event.event_id),
            "connector_event_id": event.event_id,
            "source": "connector",
        },
    )
    db.add(run)
    db.flush()
    return str(run.id)


def _handle_run_updated(
    db: Session,
    runtime_id: uuid.UUID,
    event: ConnectorEvent,
    **kwargs,
) -> str:
    if not event.run_id:
        raise ValueError("run_id required for run.updated")
    run = db.get(Run, uuid.UUID(event.run_id))
    if not run:
        raise ValueError(f"Run {event.run_id} not found")

    payload = event.payload
    if "status" in payload:
        run.status = payload["status"]
    if "title" in payload:
        run.title = payload["title"]
    if "output_summary" in payload:
        run.output_summary = payload["output_summary"]
    if "error_summary" in payload:
        run.error_summary = payload["error_summary"]
    if "total_tokens" in payload:
        run.total_tokens = payload["total_tokens"]
    if "total_cost" in payload:
        run.total_cost = payload["total_cost"]

    if payload.get("status") in ("completed", "error"):
        run.ended_at = _parse_ts(event.timestamp) or _now()
        if run.started_at:
            delta = run.ended_at - run.started_at
            run.duration_ms = int(delta.total_seconds() * 1000)

    db.flush()
    return str(run.id)


def _handle_span_created(
    db: Session,
    runtime_id: uuid.UUID,
    event: ConnectorEvent,
    **kwargs,
) -> str:
    if not event.run_id:
        raise ValueError("run_id required for span.created")
    run = db.get(Run, uuid.UUID(event.run_id))
    if not run:
        raise ValueError(f"Run {event.run_id} not found")

    payload = event.payload
    span = TraceSpan(
        id=uuid.uuid4(),
        run_id=run.id,
        span_type=payload.get("span_type", "generic"),
        title=payload.get("title", "Connector span"),
        status=payload.get("status", "completed"),
        agent_name=payload.get("agent_name"),
        model_name=payload.get("model_name"),
        tool_name=payload.get("tool_name"),
        input_summary=payload.get("input_summary"),
        output_summary=payload.get("output_summary"),
        error_summary=payload.get("error_summary"),
        started_at=_parse_ts(event.timestamp) or _now(),
        ended_at=_parse_ts(event.timestamp) or _now(),
        input_tokens=payload.get("input_tokens"),
        output_tokens=payload.get("output_tokens"),
        cost=payload.get("cost"),
        metadata_json={
            "connector_event_id": event.event_id,
            "source": "connector",
            **(payload.get("metadata") or {}),
        },
    )
    db.add(span)
    db.flush()
    return str(span.id)


def _handle_tool_call_created(
    db: Session,
    runtime_id: uuid.UUID,
    event: ConnectorEvent,
    **kwargs,
) -> str:
    if not event.run_id:
        raise ValueError("run_id required for tool_call.created")

    payload = event.payload
    tc = ToolCall(
        id=uuid.uuid4(),
        run_id=uuid.UUID(event.run_id),
        tool_name=payload.get("tool_name", "unknown"),
        risk_level=payload.get("risk_level", "read"),
        decision=payload.get("decision", "allow"),
        status=payload.get("status", "completed"),
        input_json=payload.get("input_json"),
        output_json=payload.get("output_json"),
        error_summary=payload.get("error_summary"),
    )
    db.add(tc)
    db.flush()
    return str(tc.id)


def _handle_approval_requested(
    db: Session,
    runtime_id: uuid.UUID,
    event: ConnectorEvent,
    **kwargs,
) -> str:
    if not event.run_id:
        raise ValueError("run_id required for approval.requested")

    payload = event.payload
    approval = Approval(
        id=uuid.uuid4(),
        run_id=uuid.UUID(event.run_id),
        status="pending",
        reason=payload.get("reason", "Connector approval request"),
        requested_by=payload.get("requested_by", "connector"),
    )
    db.add(approval)
    db.flush()
    return str(approval.id)


def _handle_artifact_created(
    db: Session,
    runtime_id: uuid.UUID,
    event: ConnectorEvent,
    **kwargs,
) -> str:
    if not event.run_id:
        raise ValueError("run_id required for artifact.created")

    payload = event.payload
    artifact = Artifact(
        id=uuid.uuid4(),
        run_id=uuid.UUID(event.run_id),
        artifact_type=payload.get("artifact_type", "generic"),
        title=payload.get("title", "Connector artifact"),
        content_text=payload.get("content_text"),
        content_json=payload.get("content_json"),
        storage_url=payload.get("storage_url"),
    )
    db.add(artifact)
    db.flush()
    return str(artifact.id)


_EVENT_HANDLERS = {
    "runtime.upserted": _handle_runtime_upserted,
    "run.created": _handle_run_created,
    "run.updated": _handle_run_updated,
    "span.created": _handle_span_created,
    "tool_call.created": _handle_tool_call_created,
    "approval.requested": _handle_approval_requested,
    "artifact.created": _handle_artifact_created,
}


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# GET /api/connectors/{id}/failed-events — list failed ingestion events
# ---------------------------------------------------------------------------


class FailedEventResponse(BaseModel):
    id: str
    connector_id: str
    event_type: str
    event_id: Optional[str] = None
    run_id: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    error_message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FailedEventListResponse(BaseModel):
    items: list[FailedEventResponse]
    total: int
    limit: int = 50
    offset: int = 0
    next_cursor: Optional[str] = None
    has_more: bool = False


@router.get("/{connector_id}/failed-events", response_model=FailedEventListResponse)
def list_failed_events(
    connector_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    cursor: Optional[str] = Query(None, description="Cursor for keyset pagination"),
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    connector = db.get(ConnectorConfig, connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    query = db.query(FailedEvent).filter(FailedEvent.connector_id == connector_id)
    total = query.count()

    if cursor is not None:
        items, next_cursor, has_more = apply_cursor(query, FailedEvent, cursor, limit)
    else:
        items = (
            query.order_by(FailedEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        next_cursor = None
        has_more = (offset + limit) < total

    return FailedEventListResponse(
        items=[
            FailedEventResponse(
                id=str(i.id),
                connector_id=str(i.connector_id),
                event_type=i.event_type,
                event_id=str(i.event_id) if i.event_id else None,
                run_id=str(i.run_id) if i.run_id else None,
                payload=i.payload,
                error_message=i.error_message,
                created_at=i.created_at,
            )
            for i in items
        ],
        total=total,
        limit=limit,
        offset=offset,
        next_cursor=next_cursor,
        has_more=has_more,
    )


# ---------------------------------------------------------------------------
# POST /api/connectors/{id}/failed-events/{event_id}/replay — replay event
# ---------------------------------------------------------------------------


@router.post("/{connector_id}/failed-events/{event_id}/replay")
def replay_failed_event(
    connector_id: uuid.UUID,
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    connector = db.get(ConnectorConfig, connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    failed = (
        db.query(FailedEvent)
        .filter(
            FailedEvent.connector_id == connector_id,
            FailedEvent.id == event_id,
        )
        .first()
    )
    if not failed:
        raise HTTPException(status_code=404, detail="Failed event not found")

    # Reconstruct the original event and replay through normal ingestion
    replay_event = ConnectorEvent(
        event_type=failed.event_type,
        event_id=failed.event_id,
        run_id=failed.run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        payload=failed.payload or {},
    )

    runtime_id = connector.runtime_id
    try:
        result = _process_event(db, connector_id, runtime_id, replay_event)
        if result.status == "accepted":
            # Remove from failed events on success
            db.delete(failed)
            write_audit_log(
                db,
                actor_type="user",
                actor_id="api",
                action="event.replayed",
                resource_type="connector_event",
                resource_id=result.resource_id,
                after_json={"original_event_id": failed.event_id},
            )
            db.commit()
            return {"status": "replayed", "resource_id": result.resource_id}
        else:
            return {"status": result.status, "detail": result.detail}
    except Exception as exc:
        # Update error message on re-failure
        failed.error_message = str(exc)[:1000]
        db.flush()
        write_audit_log(
            db,
            actor_type="user",
            actor_id="api",
            action="event.replay_failed",
            resource_type="connector_event",
            resource_id=str(failed.id),
            after_json={"error": str(exc)},
        )
        db.commit()
        raise HTTPException(status_code=422, detail=f"Replay failed: {exc}")
