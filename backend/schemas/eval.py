"""Pydantic schemas for Eval and Config Version APIs — v1.4."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Eval Result
# ---------------------------------------------------------------------------


class EvalResultResponse(BaseModel):
    """Single eval result row."""

    id: UUID
    runtime_id: UUID
    run_id: Optional[UUID] = None
    config_version: Optional[str] = None
    sample_name: Optional[str] = None
    success: Optional[bool] = None
    score: Optional[float] = None
    latency_ms: Optional[int] = None
    cost: Optional[float] = None
    metrics_json: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalResultListResponse(BaseModel):
    """Paginated list of eval results."""

    items: list[EvalResultResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Eval Summary
# ---------------------------------------------------------------------------


class EvalTrendPoint(BaseModel):
    """One day in the eval trend."""

    date: str
    runs: int
    passed: int
    failed: int
    avg_score: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    avg_cost: Optional[float] = None
    tool_error_rate: Optional[float] = None
    handoff_count: Optional[int] = None
    approval_count: Optional[int] = None


class EvalRuntimeBreakdown(BaseModel):
    """Eval summary broken down by runtime."""

    runtime_id: str
    runtime_name: str
    total: int
    passed: int
    failed: int
    avg_score: Optional[float] = None


class EvalConfigBreakdown(BaseModel):
    """Eval summary broken down by config version."""

    config_version: str
    total: int
    passed: int
    failed: int
    avg_score: Optional[float] = None


class EvalSummaryResponse(BaseModel):
    """Aggregated eval summary."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    avg_score: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    avg_cost: Optional[float] = None
    tool_error_rate: Optional[float] = None
    handoff_count: Optional[int] = None
    approval_count: Optional[int] = None
    by_runtime: list[EvalRuntimeBreakdown] = Field(default_factory=list)
    by_config_version: list[EvalConfigBreakdown] = Field(default_factory=list)
    trend: list[EvalTrendPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Eval Run
# ---------------------------------------------------------------------------


class EvalRunRequest(BaseModel):
    """Request to run an offline eval."""

    runtime_id: UUID
    config_version: Optional[str] = None
    category: Optional[str] = None
    sample_name: Optional[str] = None


class EvalSampleResult(BaseModel):
    """Result of a single eval sample."""

    sample_id: Optional[str] = None
    category: Optional[str] = None
    title: Optional[str] = None
    score: float = 0
    passed: bool = False
    findings: list[dict[str, Any]] = Field(default_factory=list)


class EvalRunResponse(BaseModel):
    """Response for POST /api/evals/run."""

    eval_run_id: str
    mode: str
    count: int
    passed: int
    failed: int
    avg_score: float
    results: list[EvalSampleResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Config Version
# ---------------------------------------------------------------------------


class ConfigVersionResponse(BaseModel):
    """A versioned configuration snapshot."""

    id: UUID
    runtime_id: UUID
    config_type: str
    version: str
    config_json: Optional[dict[str, Any]] = None
    evaluation_score: Optional[float] = None
    requires_approval: bool = False
    created_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfigVersionListResponse(BaseModel):
    """Paginated list of config versions."""

    items: list[ConfigVersionResponse]
    total: int


class ConfigVersionCreate(BaseModel):
    """Request to create a config version."""

    runtime_id: UUID
    config_type: str = "workflow"
    version: str
    config_json: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    created_by: Optional[str] = None


# ---------------------------------------------------------------------------
# Config Compare
# ---------------------------------------------------------------------------


class ConfigCompareRequest(BaseModel):
    """Request to compare two config versions."""

    before_version_id: UUID
    after_version_id: UUID


class ConfigFieldChange(BaseModel):
    """A single field difference between two configs."""

    field: str
    before: Any = None
    after: Any = None


class ConfigCompareResponse(BaseModel):
    """Comparison result between two config versions."""

    before: ConfigVersionResponse
    after: ConfigVersionResponse
    score_delta: Optional[float] = None
    changes: list[ConfigFieldChange] = Field(default_factory=list)
    requires_approval: bool = False
    recommended: bool = False
