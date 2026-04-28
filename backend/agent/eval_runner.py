"""Offline Agent eval runner and scoring helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from agent.eval_samples import list_eval_samples


def run_eval_samples(
    category: Optional[str] = None,
    agent_config: Optional[dict[str, Any]] = None,
    tool_specs: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Score eval samples against the current local Agent/tool contract."""
    samples = list_eval_samples(category=category)
    tools = {tool.get("name") for tool in (tool_specs or [])}
    agents = _enabled_agent_names(agent_config or {})
    results = [_score_sample(sample, tools, agents) for sample in samples]
    passed = sum(1 for result in results if result["passed"])
    avg_score = round(sum(result["score"] for result in results) / len(results), 2) if results else 0
    return {
        "eval_run_id": str(uuid.uuid4()),
        "mode": "offline_contract",
        "generated_at": datetime.now().isoformat(),
        "category": category,
        "count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "avg_score": avg_score,
        "results": results,
    }


def _score_sample(sample: dict[str, Any], tools: set[str], agents: set[str]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    score = 100

    expected_agent = str(sample.get("expected_agent") or "").lower()
    if expected_agent and expected_agent not in agents:
        findings.append(_finding("warning", "expected_agent_missing", f"{sample.get('expected_agent')} is not enabled in Agent config"))
        score -= 25

    missing_tools = [tool for tool in sample.get("expected_tools", []) if tool not in tools]
    if missing_tools:
        findings.append(_finding("critical", "missing_tools", ", ".join(missing_tools)))
        score -= 35

    if not sample.get("required_evidence"):
        findings.append(_finding("warning", "missing_required_evidence", "Sample does not declare required evidence"))
        score -= 15

    if len(sample.get("success_criteria", [])) < 2:
        findings.append(_finding("warning", "thin_success_criteria", "Sample should include at least two success criteria"))
        score -= 10

    risk_level = sample.get("risk_level")
    criteria_text = " ".join(sample.get("success_criteria", [])).lower()
    if risk_level == "confirm" and "确认" not in criteria_text and "confirm" not in criteria_text:
        findings.append(_finding("critical", "confirm_sample_without_confirmation", "Confirm-risk samples must require explicit confirmation"))
        score -= 25

    score = max(0, score)
    return {
        "sample_id": sample.get("sample_id"),
        "category": sample.get("category"),
        "title": sample.get("title"),
        "expected_agent": sample.get("expected_agent"),
        "score": score,
        "passed": score >= 80,
        "findings": findings,
        "expected_tools": sample.get("expected_tools", []),
        "required_evidence": sample.get("required_evidence", []),
    }


def _enabled_agent_names(config: dict[str, Any]) -> set[str]:
    agents = config.get("agents") or {}
    names = set()
    for key, agent in agents.items():
        if not agent.get("enabled", True):
            continue
        names.add(str(key).lower())
        names.add(str(agent.get("name") or key).lower())
    return names


def _finding(severity: str, code: str, detail: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "detail": detail}
