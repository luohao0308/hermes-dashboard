"""Rule-based RCA analyst for Hermès sessions.

The deterministic analyzer gives the dashboard useful incident evidence even
when the model runtime is unavailable. It is intentionally shaped like a future
Agents SDK structured output so an RCA Agent can replace or augment it later.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from agent.structured_guardrails import validate_rca_output


ERROR_PATTERN = re.compile(
    r"error|failed|failure|exception|traceback|timeout|timed out|refused|unreachable|"
    r"rate limit|quota|context length|tool call|guardrail|denied|失败|错误|异常|超时|拒绝|不可达",
    re.IGNORECASE,
)

CATEGORY_RULES = [
    (
        "tool",
        re.compile(r"tool|function|handoff|guardrail|denied|工具|门禁|移交", re.IGNORECASE),
        "工具或 handoff 失败",
        [
            "查看失败 span 的工具入参与输出摘要",
            "确认工具 schema、权限门禁和上游 API 是否一致",
            "必要时用同样参数手动重放该工具调用",
        ],
    ),
    (
        "network",
        re.compile(r"timeout|timed out|connection|refused|unreachable|502|503|504|网络|超时|不可达", re.IGNORECASE),
        "网络或上游服务不可达",
        [
            "确认上游 Runtime API、Gateway 和本地代理端口状态",
            "检查最近日志里的 HTTP 状态码和连接错误",
            "重试前先确认上游服务恢复，避免重复失败",
        ],
    ),
    (
        "model",
        re.compile(r"rate limit|quota|context length|model|token|llm|openai|模型|额度|上下文", re.IGNORECASE),
        "模型调用或上下文预算问题",
        [
            "检查模型配置、额度、速率限制和上下文长度",
            "减少输入上下文或切换更合适的模型配置",
            "把模型错误原文附到 issue，便于复现",
        ],
    ),
    (
        "config",
        re.compile(r"config|missing|not found|key|permission|auth|unauthorized|配置|缺少|权限|认证", re.IGNORECASE),
        "配置、权限或凭据问题",
        [
            "检查系统配置中心里的模型、API、插件和权限项",
            "确认所需环境变量、token 和本地服务路径存在",
            "补齐配置后重新运行一次短任务验证",
        ],
    ),
]


def analyze_failure(
    session: dict[str, Any],
    logs: list[dict[str, Any]],
    run: Optional[dict[str, Any]] = None,
    spans: Optional[list[dict[str, Any]]] = None,
    config_evaluation: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return a structured RCA report from session, logs, and trace evidence."""
    spans = spans or []
    evidence = _collect_evidence(session, logs, run, spans, config_evaluation)
    evidence_text = "\n".join(item["detail"] for item in evidence)
    status = str(session.get("status") or "").lower()
    end_reason = str(session.get("end_reason") or "").lower()

    category = "unknown"
    root_cause = "未发现明确失败原因"
    next_actions = [
        "查看原始消息、日志和 trace，补充人工判断",
        "如果任务仍然异常，重新运行并保留最新 trace",
    ]

    for rule_category, pattern, rule_cause, actions in CATEGORY_RULES:
        if pattern.search(evidence_text):
            category = rule_category
            root_cause = rule_cause
            next_actions = actions
            break

    if category == "unknown":
        if any(item.get("source") == "config" for item in evidence):
            category = "config"
            root_cause = "Agent 配置、handoff 或入口策略异常"
            next_actions = [
                "打开 Agent 配置页查看评分和发现项",
                "修复 main_agent、enabled 状态或 handoff 目标后重新评估",
                "重新触发同类 session，确认 trace 路由恢复正常",
            ]
        elif status in {"failed", "cancelled", "error"} or end_reason not in {"", "completed", "success"}:
            root_cause = "任务异常结束，但证据不足以归类"
            next_actions = [
                "优先查看最后一条 assistant/tool 消息和最后一个 trace span",
                "补充更高日志级别后重新触发 RCA",
                "确认该 session 是否被手动取消或外部清理",
            ]
        elif not session.get("messages") and int(session.get("message_count") or 0) == 0:
            category = "data"
            root_cause = "缺少 session 消息记录"
            next_actions = [
                "确认 Hermès API 是否返回该 session 的 messages",
                "检查 session 是否已被清理或仍在初始化",
                "等待下一次同步后重新分析",
            ]

    confidence = _confidence(category, evidence, status, end_reason, spans)
    low_confidence = confidence < 0.6
    if low_confidence:
        next_actions = next_actions + ["当前置信度较低，请人工核对原始 trace 和日志"]

    return validate_rca_output({
        "report_id": "",
        "session_id": session.get("task_id") or session.get("id") or "",
        "run_id": run.get("run_id") if run else None,
        "category": category,
        "root_cause": root_cause,
        "confidence": confidence,
        "evidence": evidence[:8],
        "next_actions": next_actions[:5],
        "low_confidence": low_confidence,
        "generated_at": datetime.now().isoformat(),
        "analyzer": "structured_rca_v2",
        "config_evaluation": config_evaluation,
    })


def _collect_evidence(
    session: dict[str, Any],
    logs: list[dict[str, Any]],
    run: Optional[dict[str, Any]],
    spans: list[dict[str, Any]],
    config_evaluation: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    status = str(session.get("status") or "unknown")
    end_reason = session.get("end_reason")
    if status not in {"completed", "success", "running", "unknown"} or end_reason:
        evidence.append(_evidence(
            "session",
            "Session 结束状态",
            f"status={status}, end_reason={end_reason or 'none'}",
            "high" if status in {"failed", "error"} else "medium",
            session.get("completed_at") or session.get("started_at"),
        ))

    message_count = int(session.get("message_count") or len(session.get("messages") or []))
    if message_count == 0:
        evidence.append(_evidence(
            "session",
            "缺少消息",
            "Hermès 没有返回该 session 的消息记录",
            "medium",
            session.get("started_at"),
        ))

    for span in spans:
        span_text = " ".join([
            str(span.get("span_type") or ""),
            str(span.get("title") or ""),
            str(span.get("summary") or ""),
            str(span.get("status") or ""),
        ])
        if span.get("status") == "error" or span.get("span_type") == "error" or ERROR_PATTERN.search(span_text):
            evidence.append(_evidence(
                "trace",
                span.get("title") or "异常 trace span",
                span.get("summary") or span_text,
                "high",
                span.get("completed_at") or span.get("started_at"),
                span.get("span_id"),
            ))

    for log in logs:
        message = str(log.get("message") or "")
        level = str(log.get("level") or log.get("type") or "").lower()
        if "error" in level or "warning" in level or ERROR_PATTERN.search(message):
            evidence.append(_evidence(
                "log",
                str(log.get("component") or log.get("type") or level or "日志信号"),
                message[:500],
                "high" if "error" in level or ERROR_PATTERN.search(message) else "medium",
                log.get("timestamp"),
            ))
            if len(evidence) >= 8:
                break

    if run and run.get("status") not in {"completed", "success"}:
        evidence.append(_evidence(
            "trace",
            "Agent run 状态",
            f"run={run.get('run_id')} status={run.get('status')}",
            "medium",
            run.get("completed_at") or run.get("started_at"),
            run.get("run_id"),
        ))

    if config_evaluation:
        score = int(config_evaluation.get("score") or 0)
        findings = config_evaluation.get("findings") or []
        if findings or score < 75:
            first_finding = findings[0] if findings else {}
            evidence.append(_evidence(
                "config",
                first_finding.get("title") or "Agent 配置信号",
                first_finding.get("detail") or f"Agent config score={score}",
                "high" if score < 60 else "medium",
                None,
                "agent_config",
            ))

    if not evidence:
        evidence.append(_evidence(
            "session",
            "未命中异常信号",
            "session、日志和 trace 中没有匹配到明确错误关键词",
            "low",
            session.get("completed_at") or session.get("started_at"),
        ))

    return evidence


def _confidence(
    category: str,
    evidence: list[dict[str, Any]],
    status: str,
    end_reason: str,
    spans: list[dict[str, Any]],
) -> float:
    high_count = sum(1 for item in evidence if item.get("severity") == "high")
    has_trace_error = any(item.get("source") == "trace" and item.get("severity") == "high" for item in evidence)
    if category in {"tool", "network", "model", "config"} and has_trace_error:
        return 0.88
    if category in {"tool", "network", "model", "config"} and high_count:
        return 0.78
    if status in {"failed", "cancelled", "error"} or end_reason not in {"", "completed", "success"}:
        return 0.62 if high_count else 0.48
    if spans and high_count:
        return 0.68
    if category == "data":
        return 0.58
    return 0.35


def _evidence(
    source: str,
    title: str,
    detail: str,
    severity: str,
    timestamp: Any = None,
    ref: Any = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "title": str(title)[:120],
        "detail": str(detail)[:700],
        "severity": severity,
        "timestamp": timestamp,
        "ref": ref,
    }
