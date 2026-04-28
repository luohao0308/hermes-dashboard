"""Static evaluation for Agent routing configuration."""

from __future__ import annotations

from typing import Any


def evaluate_agent_config(config: dict[str, Any]) -> dict[str, Any]:
    agents = config.get("agents") or {}
    main_agent = config.get("main_agent")
    findings: list[dict[str, Any]] = []
    enabled_names = {
        _agent_name(agent_key, agent_cfg).lower(): agent_key
        for agent_key, agent_cfg in agents.items()
        if agent_cfg.get("enabled", True)
    }
    enabled_ids = {
        agent_key.lower(): agent_key
        for agent_key, agent_cfg in agents.items()
        if agent_cfg.get("enabled", True)
    }

    if main_agent not in agents:
        findings.append(_finding("critical", "主 Agent 不存在", f"`{main_agent}` 不在 agents 配置中"))
    elif not agents[main_agent].get("enabled", True):
        findings.append(_finding("critical", "主 Agent 已禁用", "默认入口 Agent 被禁用，用户消息可能无法正确分发"))

    for agent_key, agent_cfg in agents.items():
        if not agent_cfg.get("enabled", True):
            continue
        handoffs = agent_cfg.get("handoffs") or []
        if not handoffs and agent_key != main_agent:
            findings.append(_finding("warning", "启用 Agent 没有 handoff 出口", f"{_agent_name(agent_key, agent_cfg)} 无法把任务交回其他 Agent"))
        for target in handoffs:
            target_key = _resolve_target(target, enabled_names, enabled_ids)
            if not target_key:
                findings.append(_finding("warning", "handoff 指向不可用 Agent", f"{_agent_name(agent_key, agent_cfg)} -> {target} 当前不可用或不存在"))

    inbound = {agent_key: 0 for agent_key in agents}
    for agent_cfg in agents.values():
        for target in agent_cfg.get("handoffs") or []:
            target_key = _resolve_target(target, enabled_names, enabled_ids)
            if target_key in inbound:
                inbound[target_key] += 1
    for agent_key, count in inbound.items():
        if agent_key != main_agent and agents[agent_key].get("enabled", True) and count == 0:
            findings.append(_finding("info", "启用 Agent 没有入口路径", f"{_agent_name(agent_key, agents[agent_key])} 没有其他 Agent 指向它"))

    score = max(0, 100 - sum(_penalty(item["severity"]) for item in findings))
    return {
        "score": score,
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D",
        "findings": findings,
        "summary": "配置健康" if not findings else f"发现 {len(findings)} 个配置信号",
    }


def _agent_name(agent_key: str, agent_cfg: dict[str, Any]) -> str:
    return str(agent_cfg.get("name") or agent_key)


def _resolve_target(target: str, enabled_names: dict[str, str], enabled_ids: dict[str, str]) -> str | None:
    normalized = target.lower().replace(" ", "_")
    return enabled_ids.get(normalized) or enabled_names.get(target.lower())


def _finding(severity: str, title: str, detail: str) -> dict[str, Any]:
    return {"severity": severity, "title": title, "detail": detail}


def _penalty(severity: str) -> int:
    return {"critical": 35, "warning": 15, "info": 5}.get(severity, 5)
