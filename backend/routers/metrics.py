"""Metrics endpoint — OPT-43.

GET /api/metrics — returns JSON with system metrics for observability.
No Prometheus/OpenTelemetry dependency; plain JSON for now.

Metrics include:
- Run counts (total, running, failed)
- Pending approvals
- Connector ingestion errors
- Worker heartbeat age
- Dead-letter task count
- Recent eval count
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import func

from database import SessionLocal
from models import Run, Task, Approval, EvalResult, AuditLog
from utils.heartbeat import read_heartbeat

router = APIRouter(tags=["metrics"])


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/api/metrics")
def get_metrics():
    """Return system metrics as JSON.

    Future: can be extended to expose Prometheus or OpenTelemetry format.
    """
    try:
        db = SessionLocal()
    except Exception:
        return {
            "status": "degraded",
            "timestamp": _now_utc().isoformat(),
            "runs": {"total": 0, "running": 0, "failed": 0, "completed": 0},
            "approvals": {"pending": 0},
            "tasks": {"dead_letter": 0},
            "connectors": {"errors_today": 0},
            "evals": {"total": 0},
            "workers": {},
            "error": "Database unavailable",
        }
    try:
        total_runs = db.query(func.count(Run.id)).scalar() or 0
        running_runs = db.query(func.count(Run.id)).filter(Run.status == "running").scalar() or 0
        failed_runs = db.query(func.count(Run.id)).filter(Run.status == "error").scalar() or 0
        completed_runs = db.query(func.count(Run.id)).filter(Run.status == "completed").scalar() or 0

        pending_approvals = db.query(func.count(Approval.id)).filter(Approval.status == "pending").scalar() or 0

        dead_letter_tasks = db.query(func.count(Task.id)).filter(Task.status == "dead_letter").scalar() or 0

        today_start = _now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
        connector_errors_today = (
            db.query(func.count(AuditLog.id))
            .filter(AuditLog.action == "event.error", AuditLog.created_at >= today_start)
            .scalar()
            or 0
        )

        recent_evals = db.query(func.count(EvalResult.id)).scalar() or 0

        workers = {
            name: {
                "status": info["status"],
                "age_seconds": info["age_seconds"],
                **({"worker_id": info["worker_id"]} if info.get("worker_id") else {}),
                **({"pid": info["pid"]} if info.get("pid") else {}),
                **({"version": info["version"]} if info.get("version") else {}),
            }
            for name, info in {
                "scheduler_worker": read_heartbeat("scheduler_worker"),
                "retention_worker": read_heartbeat("retention_worker"),
            }.items()
        }

        overall = "healthy"
        for w in workers.values():
            if w["status"] == "stale":
                overall = "degraded"

        return {
            "status": overall,
            "timestamp": _now_utc().isoformat(),
            "runs": {
                "total": total_runs,
                "running": running_runs,
                "failed": failed_runs,
                "completed": completed_runs,
            },
            "approvals": {"pending": pending_approvals},
            "tasks": {"dead_letter": dead_letter_tasks},
            "connectors": {"errors_today": connector_errors_today},
            "evals": {"total": recent_evals},
            "workers": workers,
        }
    except Exception:
        return {
            "status": "degraded",
            "timestamp": _now_utc().isoformat(),
            "runs": {"total": 0, "running": 0, "failed": 0, "completed": 0},
            "approvals": {"pending": 0},
            "tasks": {"dead_letter": 0},
            "connectors": {"errors_today": 0},
            "evals": {"total": 0},
            "workers": {},
            "error": "Database query failed",
        }
    finally:
        db.close()
