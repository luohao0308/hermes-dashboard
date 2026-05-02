"""Pydantic schemas for Connector Framework — v1.3.

Defines the event protocol for external runtimes to ingest data
into the AI Workflow Control Plane.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Event types supported by POST /api/connectors/{id}/events
# ---------------------------------------------------------------------------

ConnectorEventType = Literal[
    "runtime.upserted",
    "run.created",
    "run.updated",
    "span.created",
    "tool_call.created",
    "approval.requested",
    "artifact.created",
]


# ---------------------------------------------------------------------------
# Inbound event schema
# ---------------------------------------------------------------------------

class ConnectorEvent(BaseModel):
    """A single event ingested via the connector event API.

    The event_id field enables idempotent ingestion: duplicate events
    with the same (connector_id, event_id) are silently deduplicated.
    """

    event_type: ConnectorEventType
    event_id: Optional[str] = Field(
        None,
        description="Client-supplied idempotency key. Duplicate (connector_id, event_id) pairs are deduplicated.",
    )
    run_id: Optional[str] = Field(None, description="Target run ID. Required for span/tool_call/approval/artifact events.")
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp of when the event occurred.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-type-specific payload.")


# ---------------------------------------------------------------------------
# ConnectorConfig response schemas
# ---------------------------------------------------------------------------

class ConnectorConfigResponse(BaseModel):
    """Response model for a single connector configuration."""

    id: UUID
    runtime_id: UUID
    connector_type: str
    display_name: str
    enabled: bool
    config_json: Optional[dict[str, Any]] = None
    secret_ref: Optional[str] = None
    environment_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("config_json", mode="before")
    @classmethod
    def mask_secrets(cls, v: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """Mask sensitive fields in config_json for display."""
        if not v:
            return v
        from security.secret_manager import mask_config_secrets
        return mask_config_secrets(v)


class ConnectorListResponse(BaseModel):
    """Paginated list of connectors."""

    items: list[ConnectorConfigResponse]
    total: int


# ---------------------------------------------------------------------------
# Event ingestion response
# ---------------------------------------------------------------------------

class ConnectorEventResult(BaseModel):
    """Result of processing a single event."""

    event_type: str
    event_id: Optional[str] = None
    status: Literal["accepted", "duplicate", "error"]
    resource_id: Optional[str] = Field(None, description="ID of the created/updated resource.")
    detail: Optional[str] = None


class ConnectorEventResponse(BaseModel):
    """Response for POST /api/connectors/{id}/events."""

    connector_id: str
    results: list[ConnectorEventResult]
