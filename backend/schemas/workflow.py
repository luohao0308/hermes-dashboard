"""Pydantic schemas for Workflow Orchestration (v2.0)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Retry Policy
# ---------------------------------------------------------------------------


class RetryPolicyCreate(BaseModel):
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_seconds: float = Field(default=1.0, ge=0)


class RetryPolicyResponse(BaseModel):
    max_retries: int
    backoff_seconds: float

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Workflow Nodes & Edges
# ---------------------------------------------------------------------------


class WorkflowNodeCreate(BaseModel):
    node_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(..., min_length=1, max_length=500)
    task_type: str = Field(default="action", max_length=50)
    config: Optional[dict] = None
    retry_policy: Optional[RetryPolicyCreate] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=0)
    approval_timeout_seconds: Optional[int] = Field(default=None, ge=0)


class WorkflowEdgeCreate(BaseModel):
    from_node: str
    to_node: str


class WorkflowNodeResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    node_id: str
    title: str
    task_type: str
    config: Optional[dict] = None
    retry_policy: Optional[dict] = None
    timeout_seconds: Optional[int] = None
    approval_timeout_seconds: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowEdgeResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    from_node: str
    to_node: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Workflow Definition
# ---------------------------------------------------------------------------


class WorkflowDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    runtime_id: uuid.UUID
    description: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=0)
    max_concurrent_tasks: Optional[int] = Field(default=None, ge=1)
    nodes: list[WorkflowNodeCreate] = Field(..., min_length=1)
    edges: list[WorkflowEdgeCreate] = Field(default_factory=list)


class WorkflowDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=0)
    max_concurrent_tasks: Optional[int] = Field(default=None, ge=1)
    nodes: Optional[list[WorkflowNodeCreate]] = None
    edges: Optional[list[WorkflowEdgeCreate]] = None


class WorkflowDefinitionResponse(BaseModel):
    id: uuid.UUID
    runtime_id: uuid.UUID
    name: str
    description: Optional[str] = None
    version: int
    timeout_seconds: Optional[int] = None
    max_concurrent_tasks: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    nodes: list[WorkflowNodeResponse] = []
    edges: list[WorkflowEdgeResponse] = []

    model_config = {"from_attributes": True}


class WorkflowDefinitionListResponse(BaseModel):
    items: list[WorkflowDefinitionResponse]
    total: int


# ---------------------------------------------------------------------------
# Workflow Run
# ---------------------------------------------------------------------------


class WorkflowRunCreate(BaseModel):
    input_summary: Optional[str] = None
    metadata_json: Optional[dict] = None


class WorkflowTaskResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    node_id: Optional[str] = None
    title: str
    status: str
    task_type: Optional[str] = None
    depends_on_json: Optional[dict] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_summary: Optional[str] = None
    retry_count: int = 0
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    metadata_json: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunResponse(BaseModel):
    id: uuid.UUID
    runtime_id: uuid.UUID
    workflow_id: Optional[uuid.UUID] = None
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
    metadata_json: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    tasks: list[WorkflowTaskResponse] = []

    model_config = {"from_attributes": True}


class WorkflowRunListResponse(BaseModel):
    items: list[WorkflowRunResponse]
    total: int
