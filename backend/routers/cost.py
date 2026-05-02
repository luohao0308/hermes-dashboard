"""Cost tracking and budget endpoints."""

from fastapi import APIRouter, Depends, Query

from deps import _cost_tracker
from security.rbac import require_role

router = APIRouter()


@router.get("/api/cost/summary")
async def get_cost_summary(period: str = Query("daily")):
    return _cost_tracker.get_summary(period)


@router.get("/api/cost/breakdown")
async def get_cost_breakdown(days: int = Query(30)):
    return _cost_tracker.get_breakdown(days)


@router.get("/api/cost/trend")
async def get_cost_trend(days: int = Query(30)):
    return _cost_tracker.get_trend(days)


@router.post("/api/cost/budget")
async def set_budget(body: dict, _role: str = Depends(require_role("operator"))):
    _cost_tracker.set_budget(
        scope=body.get("scope", "monthly"),
        limit_usd=body.get("limit_usd", 100),
        provider=body.get("provider"),
        alert_threshold=body.get("alert_threshold", 0.8),
    )
    return {"ok": True}


@router.get("/api/cost/alerts")
async def get_cost_alerts():
    return _cost_tracker.check_alerts()
