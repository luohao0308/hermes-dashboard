"""Pydantic schemas for Run and TraceSpan API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Run schemas
# ---------------------------------------------------------------------------

class RunCreate(BaseModel):
    """Request body for POST /api/runs."""

    runtime_id: UUID = Field(..., description="ID of the runtime that owns this run")
    title: str = Field(..., min_length=1, max_length=500, description="Human-readable run title")
    input_summary: Optional[str] = Field(None, description="Summary of the run input")
    status: str = Field("queued", max_length=20, description="Initial status: queued, running, completed, error")
    metadata_json: Optional[dict[str, Any]] = Field(None, description="Arbitrary metadata")


class RunUpdate(BaseModel):
    """Request body for PATCH /api/runs/{run_id}."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[str] = Field(None, max_length=20)
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error_summary: Optional[str] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    total_tokens: Optional[int] = None
    total_cost: Optional[float] = None
    metadata_json: Optional[dict[str, Any]] = None


class RunResponse(BaseModel):
    """Response model for a single Run."""

    id: UUID
    runtime_id: UUID
    title: str
    status: str
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error_summary: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    total_tokens: Optional[int] = None
    total_cost: Optional[float] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunListResponse(BaseModel):
    """Paginated list of runs."""

    items: list[RunResponse]
    total: int
    limit: int
    offset: int
    next_cursor: Optional[str] = None
    has_more: bool = False


# ---------------------------------------------------------------------------
# TraceSpan schemas
# ---------------------------------------------------------------------------

class SpanCreate(BaseModel):
    """Request body for POST /api/runs/{run_id}/spans."""

    span_type: str = Field(..., max_length=30, description="Span type: llm, tool, guardrail, handoff, etc.")
    title: str = Field(..., min_length=1, max_length=500, description="Span title")
    status: str = Field("running", max_length=20, description="Span status: running, completed, error")
    parent_span_id: Optional[UUID] = Field(None, description="Parent span for nested traces")
    agent_name: Optional[str] = Field(None, max_length=255)
    model_name: Optional[str] = Field(None, max_length=255)
    tool_name: Optional[str] = Field(None, max_length=255)
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error_summary: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost: Optional[float] = None
    metadata_json: Optional[dict[str, Any]] = None


class SpanResponse(BaseModel):
    """Response model for a single TraceSpan."""

    id: UUID
    run_id: UUID
    task_id: Optional[UUID] = None
    parent_span_id: Optional[UUID] = None
    span_type: str
    title: str
    status: str
    agent_name: Optional[str] = None
    model_name: Optional[str] = None
    tool_name: Optional[str] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error_summary: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost: Optional[float] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TraceResponse(BaseModel):
    """Run with its full trace timeline."""

    run: RunResponse
    spans: list[SpanResponse]
