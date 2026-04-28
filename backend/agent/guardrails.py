"""Guardrail policy evaluation for Agent tool calls."""

from pathlib import Path
from typing import Any

import yaml


POLICY_PATH = Path(__file__).parent / "guardrails.yaml"


def load_guardrail_policy() -> dict[str, Any]:
    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def list_tool_policies() -> list[dict[str, Any]]:
    policy = load_guardrail_policy()
    tool_policies = policy.get("tool_policies", {})
    return [
        {"risk": risk, **details}
        for risk, details in tool_policies.items()
    ]


def evaluate_tool_call(tool_spec: dict[str, Any]) -> dict[str, Any]:
    risk = tool_spec.get("risk", "read")
    policy = load_guardrail_policy()
    details = policy.get("tool_policies", {}).get(risk, {})
    decision = details.get("decision", "confirm")
    return {
        "tool": tool_spec.get("name"),
        "risk": risk,
        "decision": decision,
        "description": details.get("description", "No guardrail policy configured."),
    }
