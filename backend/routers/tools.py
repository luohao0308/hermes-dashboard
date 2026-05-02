"""Tool Policy API — v1.1 Tool Governance.

Endpoints:
    GET /api/tools — list configured tool policies from guardrails.yaml
"""

from __future__ import annotations

import yaml
from pathlib import Path

from fastapi import APIRouter

from schemas.tool import ToolPolicyItem, ToolPolicyListResponse

router = APIRouter(prefix="/api/tools", tags=["tools"])

GUARDRAILS_YAML = Path(__file__).resolve().parent.parent / "agent" / "guardrails.yaml"


@router.get("", response_model=ToolPolicyListResponse)
def list_tool_policies():
    """Read guardrails.yaml and return tool policies."""
    with open(GUARDRAILS_YAML) as f:
        data = yaml.safe_load(f) or {}

    raw = data.get("tool_policies", {})
    policies = [
        ToolPolicyItem(
            risk_level=risk_level,
            decision=entry.get("decision", "allow"),
            description=entry.get("description", ""),
        )
        for risk_level, entry in raw.items()
    ]
    return ToolPolicyListResponse(policies=policies)
