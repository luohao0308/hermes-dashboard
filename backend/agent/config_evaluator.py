"""Static evaluation for Agent routing configuration."""

from __future__ import annotations

from typing import Any
import copy


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
        "suggestions": _suggestions(findings),
        "summary": "配置健康" if not findings else f"发现 {len(findings)} 个配置信号",
    }


def compare_agent_config(
    base_config: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    proposed = copy.deepcopy(base_config)
    if candidate.get("main_agent"):
        proposed["main_agent"] = candidate["main_agent"]
    for agent_key, enabled in (candidate.get("enabled_overrides") or {}).items():
        if agent_key in proposed.get("agents", {}):
            proposed["agents"][agent_key]["enabled"] = bool(enabled)

    current = evaluate_agent_config(base_config)
    proposed_eval = evaluate_agent_config(proposed)
    return {
        "current": current,
        "candidate": proposed_eval,
        "delta": proposed_eval["score"] - current["score"],
        "changed": {
            "main_agent": {
                "from": base_config.get("main_agent"),
                "to": proposed.get("main_agent"),
            },
            "enabled_overrides": candidate.get("enabled_overrides") or {},
        },
        "recommendation": _comparison_recommendation(current, proposed_eval),
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


def _suggestions(findings: list[dict[str, Any]]) -> list[dict[str, str]]:
    suggestions = []
    for finding in findings:
        title = finding.get("title", "")
        if "主 Agent" in title:
            suggestions.append({
                "title": "恢复可用入口 Agent",
                "detail": "选择一个已启用且具备 Dispatcher 能力的 Agent 作为 main_agent。",
            })
        elif "handoff 指向不可用" in title:
            suggestions.append({
                "title": "修正 handoff 目标",
                "detail": "启用目标 Agent，或从 handoffs 中移除不存在/禁用的目标。",
            })
        elif "没有 handoff 出口" in title:
            suggestions.append({
                "title": "添加回退 handoff",
                "detail": "至少添加 Dispatcher 或 Reviewer 作为回退路径，避免上下文卡死在单个 Agent。",
            })
        elif "没有入口路径" in title:
            suggestions.append({
                "title": "补充入口路径",
                "detail": "从 Dispatcher 或相关专业 Agent 增加一条指向该 Agent 的 handoff。",
            })
    if not suggestions:
        suggestions.append({
            "title": "保持当前配置",
            "detail": "当前静态配置未发现阻塞风险，可继续观察运行指标和失败率。",
        })
    return _dedupe_suggestions(suggestions)


def _dedupe_suggestions(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    result = []
    for item in items:
        key = (item["title"], item["detail"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result[:5]


def _comparison_recommendation(current: dict[str, Any], proposed: dict[str, Any]) -> str:
    delta = proposed["score"] - current["score"]
    if delta > 0:
        return "候选配置静态评分更高，可以考虑保存后观察运行指标。"
    if delta < 0:
        return "候选配置静态评分更低，不建议直接保存为默认配置。"
    return "候选配置评分持平，建议结合实际 run 成功率和 handoff 次数再判断。"
