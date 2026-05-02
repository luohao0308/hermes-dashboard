"""Pydantic schemas for Tool Governance — v1.1.

Covers ToolCall, Approval, AuditLog, and ToolPolicy API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (string literals matching DB columns)
# ---------------------------------------------------------------------------

RiskLevel = Literal["read", "write", "execute", "network", "destructive"]
PolicyDecision = Literal["allow", "confirm", "deny"]
ApprovalStatus = Literal["pending", "approved", "rejected"]


# ---------------------------------------------------------------------------
# ToolCall schemas
# ---------------------------------------------------------------------------

class ToolCallResponse(BaseModel):
    """Response model for a single ToolCall."""

    id: UUID
    run_id: UUID
    span_id: Optional[UUID] = None
    tool_name: str
    risk_level: str
    decision: str
    status: str
    input_json: Optional[dict[str, Any]] = None
    output_json: Optional[dict[str, Any]] = None
    error_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolCallListResponse(BaseModel):
    """Paginated list of tool calls."""

    items: list[ToolCallResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Approval schemas
# ---------------------------------------------------------------------------

class ApprovalResponse(BaseModel):
    """Response model for a single Approval."""

    id: UUID
    run_id: Optional[UUID] = None
    tool_call_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    status: str
    reason: Optional[str] = None
    requested_by: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_note: Optional[str] = None
    context_json: Optional[dict] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApprovalListResponse(BaseModel):
    """Paginated list of approvals."""

    items: list[ApprovalResponse]
    total: int
    limit: int
    offset: int
    next_cursor: Optional[str] = None
    has_more: bool = False


class ApprovalActionRequest(BaseModel):
    """Request body for POST /api/approvals/{id}/approve or /reject."""

    resolved_by: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = Field(None, description="Resolution note")


# ---------------------------------------------------------------------------
# AuditLog schemas
# ---------------------------------------------------------------------------

class AuditLogResponse(BaseModel):
    """Response model for a single AuditLog entry."""

    id: UUID
    actor_type: Optional[str] = None
    actor_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    before_json: Optional[dict[str, Any]] = None
    after_json: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Tool Policy schemas (read from guardrails.yaml)
# ---------------------------------------------------------------------------

class ToolPolicyItem(BaseModel):
    """A single tool policy entry from guardrails.yaml."""

    risk_level: str
    decision: str
    description: str


class ToolPolicyListResponse(BaseModel):
    """List of tool policies."""

    policies: list[ToolPolicyItem]
