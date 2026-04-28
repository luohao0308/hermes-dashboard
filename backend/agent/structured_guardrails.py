"""Pydantic guardrails for Agent input and structured outputs."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentInputPayload(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=200)
    agent_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=4000)
    linked_session_id: Optional[str] = Field(default=None, max_length=200)


class RcaEvidencePayload(BaseModel):
    source: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=120)
    detail: str = Field(..., min_length=1, max_length=700)
    severity: str = Field(..., min_length=1, max_length=20)
    timestamp: Optional[Any] = None
    ref: Optional[Any] = None


class RcaOutputPayload(BaseModel):
    report_id: str = ""
    session_id: str
    run_id: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=50)
    root_cause: str = Field(..., min_length=1, max_length=300)
    confidence: float = Field(..., ge=0, le=1)
    evidence: list[RcaEvidencePayload]
    next_actions: list[str]
    low_confidence: bool
    generated_at: str
    analyzer: str = Field(..., min_length=1, max_length=80)
    config_evaluation: Optional[dict[str, Any]] = None


def validate_agent_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate chat input before it reaches an Agent run."""
    try:
        validated = _validate_model(AgentInputPayload, payload)
    except Exception as exc:
        return _blocked("input_schema", str(exc))

    message = validated.message.strip()
    if "\x00" in message:
        return _blocked("input_control_char", "Message contains unsupported control characters")
    return {
        "decision": "allow",
        "reason": "Agent input passed Pydantic validation",
        "payload": _dump_model(validated),
    }


def validate_rca_output(report: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize RCA structured output."""
    validated = _validate_model(RcaOutputPayload, report)
    normalized = _dump_model(validated)
    if not normalized["evidence"]:
        raise ValueError("RCA output must include at least one evidence item")
    if not normalized["next_actions"]:
        raise ValueError("RCA output must include at least one next action")
    normalized["next_actions"] = [str(item)[:300] for item in normalized["next_actions"][:5]]
    normalized["evidence"] = normalized["evidence"][:8]
    return normalized


def _blocked(code: str, detail: str) -> dict[str, Any]:
    return {
        "decision": "deny",
        "reason": code,
        "detail": detail,
    }


def _validate_model(model: type[BaseModel], payload: dict[str, Any]) -> BaseModel:
    if hasattr(model, "model_validate"):
        return model.model_validate(payload)
    return model.parse_obj(payload)


def _dump_model(instance: BaseModel) -> dict[str, Any]:
    if hasattr(instance, "model_dump"):
        return instance.model_dump()
    return instance.dict()
