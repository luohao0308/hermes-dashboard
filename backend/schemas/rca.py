"""Pydantic schemas for RCA (Root Cause Analysis) — v1.2."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


EvidenceSeverity = Literal["high", "medium", "low"]


class RCAEvidenceItem(BaseModel):
    """A single piece of evidence from RCA analysis."""

    source: str = Field(description="Evidence source: session, trace, log, config")
    title: str
    detail: str
    severity: EvidenceSeverity
    timestamp: Optional[str] = None
    ref: Optional[str] = None


class RCAReportResponse(BaseModel):
    """Response model for an RCA report."""

    report_id: str
    run_id: Optional[str] = None
    category: str = Field(description="tool, network, model, config, data, or unknown")
    root_cause: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[RCAEvidenceItem] = []
    next_actions: list[str] = []
    low_confidence: bool
    generated_at: str
    analyzer: str

    model_config = {"from_attributes": True}
