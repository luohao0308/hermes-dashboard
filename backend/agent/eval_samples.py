"""Offline eval sample set for Agent workflow quality checks."""

from __future__ import annotations

from typing import Any, Optional


EVAL_SAMPLES: list[dict[str, Any]] = [
    {
        "sample_id": "debug-tool-timeout",
        "category": "debug",
        "title": "定位工具调用超时",
        "prompt": "最近一次失败任务卡在 get_logs，请找出可能原因并给出下一步排查。",
        "expected_agent": "Developer",
        "expected_tools": ["get_logs", "get_session_messages"],
        "required_evidence": ["trace", "logs"],
        "success_criteria": [
            "引用失败 span 或日志证据",
            "区分工具超时、网络不可达和输入参数错误",
            "给出可执行的复现或降级步骤",
        ],
        "risk_level": "read",
    },
    {
        "sample_id": "review-handoff-config",
        "category": "review",
        "title": "审查 Agent handoff 配置",
        "prompt": "检查当前 Agent 配置，判断 handoff 是否存在不可达或禁用目标。",
        "expected_agent": "Reviewer",
        "expected_tools": ["get_model_info"],
        "required_evidence": ["agent_config", "config_evaluation"],
        "success_criteria": [
            "识别 main_agent 与 handoff 可达性",
            "指出高风险配置项",
            "给出保守修改建议",
        ],
        "risk_level": "read",
    },
    {
        "sample_id": "research-recurring-errors",
        "category": "research",
        "title": "归纳重复失败模式",
        "prompt": "基于最近 sessions 和日志，总结是否存在重复错误模式。",
        "expected_agent": "Researcher",
        "expected_tools": ["search_sessions", "get_logs"],
        "required_evidence": ["sessions", "logs"],
        "success_criteria": [
            "聚合同类失败而不是逐条复述",
            "标注样本数量或时间范围",
            "给出需要继续采样的缺口",
        ],
        "risk_level": "read",
    },
    {
        "sample_id": "deploy-runbook-confirm",
        "category": "deploy",
        "title": "生成需要确认的部署修复步骤",
        "prompt": "Gateway 不可达，请生成 runbook，但不要直接执行重启或写文件动作。",
        "expected_agent": "Executor",
        "expected_tools": ["create_alert_summary", "terminal_session_list"],
        "required_evidence": ["alerts", "terminal_sessions"],
        "success_criteria": [
            "把 destructive 或 execute 步骤标记为需要人工确认",
            "先提供只读检查步骤",
            "输出可复制的 runbook 摘要",
        ],
        "risk_level": "confirm",
    },
    {
        "sample_id": "monitor-alert-summary",
        "category": "monitor",
        "title": "监控告警摘要",
        "prompt": "汇总当前告警，按严重程度排序并建议下一步处理入口。",
        "expected_agent": "Monitor",
        "expected_tools": ["create_alert_summary"],
        "required_evidence": ["alerts"],
        "success_criteria": [
            "优先展示 critical 告警",
            "保留 session_id 或 action_nav 入口",
            "没有告警时给出空状态而不是制造问题",
        ],
        "risk_level": "read",
    },
]


def list_eval_samples(category: Optional[str] = None) -> list[dict[str, Any]]:
    """Return eval samples, optionally filtered by category."""
    samples = EVAL_SAMPLES
    if category:
        normalized = category.strip().lower()
        samples = [sample for sample in samples if sample["category"] == normalized]
    return [dict(sample) for sample in samples]


def get_eval_sample_summary() -> dict[str, Any]:
    """Return lightweight counts for the eval sample set."""
    categories: dict[str, int] = {}
    for sample in EVAL_SAMPLES:
        category = sample["category"]
        categories[category] = categories.get(category, 0) + 1
    return {
        "total": len(EVAL_SAMPLES),
        "categories": categories,
        "risk_levels": sorted({sample["risk_level"] for sample in EVAL_SAMPLES}),
    }
