"""Pydantic schemas for Runbook — v1.2."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


Severity = Literal["high", "medium", "low"]


class RunbookStepItem(BaseModel):
    """A single execution step in a runbook."""

    step_id: str
    label: str
    action_type: str = Field(description="confirm_then_execute or manual_check")
    requires_confirmation: bool
    status: str = Field(description="needs_confirmation, confirmed, pending, completed, blocked_unsafe")
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
    executed_at: Optional[str] = None
    execution_result: Optional[dict[str, Any]] = None


class RunbookResponse(BaseModel):
    """Response model for a Runbook."""

    runbook_id: str
    run_id: Optional[str] = None
    rca_report_id: Optional[str] = None
    title: str
    severity: Severity
    summary: str
    checklist: list[str] = []
    execution_steps: list[RunbookStepItem] = []
    evidence_count: int = 0
    markdown: str = ""
    generated_at: str
    generator: str

    model_config = {"from_attributes": True}
