"""Guardrail policy evaluation for Agent tool calls."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


POLICY_PATH = Path(__file__).parent / "guardrails.yaml"
_approval_events: dict[str, dict[str, Any]] = {}


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


def evaluate_tool_call(tool_spec: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    risk = tool_spec.get("risk", "read")
    dynamic_signal = _dangerous_operation_signal(tool_spec, params or {})
    if dynamic_signal and risk == "read":
        risk = "execute"
    policy = load_guardrail_policy()
    details = policy.get("tool_policies", {}).get(risk, {})
    decision = details.get("decision", "confirm")
    description = details.get("description", "No guardrail policy configured.")
    if dynamic_signal:
        decision = "confirm" if decision == "allow" else decision
        description = f"{description} Dynamic guardrail matched {dynamic_signal}."
    return {
        "tool": tool_spec.get("name"),
        "risk": risk,
        "decision": decision,
        "description": description,
        "dynamic_signal": dynamic_signal,
    }


def create_approval_event(
    tool_spec: dict[str, Any],
    params: dict[str, Any],
    guardrail: dict[str, Any],
) -> dict[str, Any]:
    event_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    event = {
        "event_id": event_id,
        "tool": tool_spec.get("name"),
        "risk": guardrail.get("risk"),
        "decision": guardrail.get("decision"),
        "description": guardrail.get("description"),
        "params_hash": _params_hash(params),
        "params_preview": _preview_params(params),
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "resolved_by": None,
        "resolution_note": None,
    }
    _approval_events[event_id] = event
    return dict(event)


def list_approval_events(status: str | None = None) -> list[dict[str, Any]]:
    events = list(_approval_events.values())
    if status:
        events = [event for event in events if event.get("status") == status]
    return [
        dict(event)
        for event in sorted(events, key=lambda item: item.get("created_at", ""), reverse=True)
    ]


def resolve_approval_event(
    event_id: str,
    approved: bool,
    resolved_by: str = "local_user",
    note: str | None = None,
) -> dict[str, Any] | None:
    event = _approval_events.get(event_id)
    if not event:
        return None
    if event.get("status") != "pending":
        return dict(event)
    event["status"] = "approved" if approved else "rejected"
    event["updated_at"] = datetime.now().isoformat()
    event["resolved_by"] = resolved_by
    event["resolution_note"] = note
    return dict(event)


def validate_approval_event(event_id: str, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    event = _approval_events.get(event_id)
    if not event:
        raise ValueError("Approval event not found")
    if event.get("tool") != tool_name:
        raise ValueError("Approval event tool mismatch")
    if event.get("params_hash") != _params_hash(params):
        raise ValueError("Approval event params mismatch")
    if event.get("status") != "approved":
        raise PermissionError("Approval event is not approved")
    return dict(event)


def _params_hash(params: dict[str, Any]) -> str:
    payload = json.dumps(params, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _preview_params(params: dict[str, Any]) -> dict[str, Any]:
    preview: dict[str, Any] = {}
    for key, value in params.items():
        text = json.dumps(value, ensure_ascii=False, default=str)
        preview[key] = text[:180]
    return preview


def _dangerous_operation_signal(tool_spec: dict[str, Any], params: dict[str, Any]) -> str | None:
    tool_name = str(tool_spec.get("name") or "").lower()
    payload = json.dumps(params, ensure_ascii=False, sort_keys=True, default=str).lower()
    if any(token in tool_name for token in ("shell", "terminal", "command", "exec")):
        if _matches_any(payload, (
            "rm -rf",
            "rm -fr",
            "sudo ",
            "mkfs",
            "dd if=",
            "chmod -r",
            "chown -r",
            "curl ",
            "wget ",
            "| sh",
            "| bash",
        )):
            return "dangerous_shell"
    if "git" in tool_name or "git " in payload:
        if _matches_any(payload, (
            "reset --hard",
            "clean -fd",
            "push --force",
            "push -f",
            "rebase ",
            "checkout --",
        )):
            return "dangerous_git"
    if any(token in tool_name for token in ("file", "fs", "write", "delete")):
        if _matches_any(payload, (
            '"action": "delete"',
            '"action":"delete"',
            '"action": "write"',
            '"action":"write"',
            '"mode": "w"',
            '"mode":"w"',
            "overwrite",
            "unlink",
            "delete",
        )):
            return "dangerous_file"
    return None


def _matches_any(value: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in value for pattern in patterns)
