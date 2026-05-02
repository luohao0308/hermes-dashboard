"""Alert building endpoints."""

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Query
from sqlalchemy import text

from database import SessionLocal
from utils.heartbeat import read_all_workers

router = APIRouter()


def _make_alert(
    severity: str,
    title: str,
    message: str,
    source: str,
    action_label: str,
    action_nav: str,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    alert_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{severity}:{source}:{session_id or title}:{message[:80]}")
    return {
        "id": str(alert_id),
        "severity": severity,
        "title": title,
        "message": message,
        "source": source,
        "session_id": session_id,
        "action_label": action_label,
        "action_nav": action_nav,
        "created_at": datetime.now().isoformat(),
    }


@router.get("/api/alerts")
async def get_alerts(limit: int = Query(10, ge=1, le=50)):
    """Build actionable alerts from local control plane health signals."""
    alerts: list[dict[str, Any]] = []
    now = datetime.now()

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as exc:
        alerts.append(_make_alert(
            severity="critical",
            title="数据库不可用",
            message=f"控制平面无法连接 PostgreSQL：{str(exc)[:160]}",
            source="database",
            action_label="查看系统",
            action_nav="system",
        ))

    workers = read_all_workers()
    for name, info in workers.items():
        status = info.get("status")
        if status in {"missing", "stale", "error"}:
            alerts.append(_make_alert(
                severity="warning" if status == "stale" else "critical",
                title=f"{name.replace('_', '-')} 状态异常",
                message=f"Worker 状态为 {status}，最近心跳 {info.get('age_seconds')} 秒前。",
                source="worker",
                action_label="查看系统",
                action_nav="system",
            ))
            if len(alerts) >= limit:
                break

    if not alerts:
        alerts.append(_make_alert(
            severity="info",
            title="暂无需要介入的告警",
            message="数据库和后台 worker 当前没有触发规则型告警。",
            source="monitor",
            action_label="刷新",
            action_nav="dashboard",
        ))

    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda item: severity_rank.get(item["severity"], 3))
    return {
        "alerts": alerts[:limit],
        "generated_at": now.isoformat(),
        "total": len(alerts[:limit]),
    }
