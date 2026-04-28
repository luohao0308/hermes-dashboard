"""Runbook generation from RCA, trace, and session signals."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


def generate_runbook(
    session: dict[str, Any],
    rca: Optional[dict[str, Any]] = None,
    run: Optional[dict[str, Any]] = None,
    spans: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    session_id = session.get("task_id") or session.get("id") or ""
    title = f"{session.get('name') or 'Hermès Session'} 复盘 Runbook"
    root_cause = rca.get("root_cause") if rca else "尚未生成 RCA"
    confidence = float(rca.get("confidence") or 0) if rca else 0
    evidence = rca.get("evidence", []) if rca else []
    next_actions = rca.get("next_actions", []) if rca else []
    severity = _severity(session, rca)
    checklist = _checklist(next_actions, severity)
    execution_steps = _execution_steps(checklist)
    markdown = _markdown(
        title=title,
        session=session,
        rca=rca,
        run=run,
        spans=spans or [],
        severity=severity,
        checklist=checklist,
    )
    return {
        "runbook_id": "",
        "session_id": session_id,
        "rca_report_id": rca.get("report_id") if rca else None,
        "title": title,
        "severity": severity,
        "summary": f"{root_cause}，置信度 {round(confidence * 100)}%。",
        "checklist": checklist,
        "execution_steps": execution_steps,
        "evidence_count": len(evidence),
        "markdown": markdown,
        "generated_at": datetime.now().isoformat(),
        "generator": "rule_based_runbook_v1",
    }


def _severity(session: dict[str, Any], rca: Optional[dict[str, Any]]) -> str:
    status = str(session.get("status") or "").lower()
    if rca and any(item.get("severity") == "high" for item in rca.get("evidence", [])):
        return "high"
    if status in {"failed", "error", "cancelled"}:
        return "medium"
    if rca and rca.get("low_confidence"):
        return "medium"
    return "low"


def _checklist(next_actions: list[str], severity: str) -> list[str]:
    result = list(next_actions[:5])
    if severity in {"high", "medium"}:
        result.append("完成修复后重新运行同类 session，确认 trace 不再出现同类错误")
    result.append("把 runbook、RCA 和关键日志链接到 issue/PR/Notion")
    return _dedupe(result)


def _execution_steps(checklist: list[str]) -> list[dict[str, Any]]:
    steps = []
    for idx, item in enumerate(checklist, start=1):
        requires_confirmation = _requires_confirmation(item)
        steps.append({
            "step_id": f"step-{idx}",
            "label": item,
            "action_type": "confirm_then_execute" if requires_confirmation else "manual_check",
            "requires_confirmation": requires_confirmation,
            "status": "needs_confirmation" if requires_confirmation else "pending",
        })
    return steps


def _requires_confirmation(text: str) -> bool:
    normalized = text.lower()
    keywords = (
        "执行",
        "修复",
        "重启",
        "删除",
        "写入",
        "覆盖",
        "部署",
        "rollback",
        "restart",
        "delete",
        "write",
        "deploy",
        "execute",
    )
    return any(keyword in normalized for keyword in keywords)


def _markdown(
    title: str,
    session: dict[str, Any],
    rca: Optional[dict[str, Any]],
    run: Optional[dict[str, Any]],
    spans: list[dict[str, Any]],
    severity: str,
    checklist: list[str],
) -> str:
    evidence = rca.get("evidence", []) if rca else []
    lines = [
        f"# {title}",
        "",
        "## 摘要",
        "",
        f"- Session: `{session.get('task_id') or session.get('id') or 'unknown'}`",
        f"- 状态: `{session.get('status') or 'unknown'}`",
        f"- 严重级别: `{severity}`",
        f"- 根因: {rca.get('root_cause') if rca else '尚未生成 RCA'}",
        f"- 置信度: {round(float(rca.get('confidence') or 0) * 100) if rca else 0}%",
        "",
        "## 证据",
        "",
    ]
    if evidence:
        for item in evidence[:8]:
            lines.append(f"- [{item.get('source')}] {item.get('title')}: {item.get('detail')}")
    else:
        lines.append("- 暂无 RCA 证据，请先生成失败原因分析。")
    lines.extend([
        "",
        "## Trace",
        "",
        f"- Run: `{run.get('run_id') if run else 'none'}`",
        f"- Span 数: {len(spans)}",
        "",
        "## 处理步骤",
        "",
    ])
    lines.extend(f"- [ ] {item}" for item in checklist)
    lines.extend([
        "",
        "## 验证",
        "",
        "- [ ] 重新运行同类任务",
        "- [ ] 确认告警面板没有新增同类错误",
        "- [ ] 确认最新 trace 的失败 span 已消失或原因已变化",
    ])
    return "\n".join(lines)


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
