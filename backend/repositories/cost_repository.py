"""PostgreSQL-backed cost repository.

Tracks API usage costs and budget limits using dedicated ORM models.
Uses per-operation sessions to avoid long-lived session accumulation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.cost import ApiUsageRow, BudgetLimitRow
from repositories.base import CostRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PgCostRepository(CostRepository):
    """PostgreSQL implementation of CostRepository."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def _run_in_session(self, fn, *, read_only: bool = False):
        db = self._session_factory()
        try:
            result = fn(db)
            if not read_only:
                db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_per_1k_input: float,
        cost_per_1k_output: float,
        review_id: Optional[str] = None,
        latency_ms: Optional[int] = None,
        status: str = "success",
    ) -> str:
        def _record(db: Session) -> str:
            cost = (input_tokens / 1000 * cost_per_1k_input) + (
                output_tokens / 1000 * cost_per_1k_output
            )
            usage_id = str(uuid.uuid4())[:12]
            row = ApiUsageRow(
                id=uuid.uuid4(),
                timestamp=_now(),
                provider=provider,
                model=model,
                review_id=review_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost_usd=round(cost, 6),
                latency_ms=latency_ms,
                status=status,
            )
            db.add(row)
            return usage_id
        return self._run_in_session(_record)

    def get_summary(self, period: str = "daily") -> dict[str, Any]:
        def _summary(db: Session) -> dict[str, Any]:
            days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 1)
            cutoff = _now() - timedelta(days=days)
            row = (
                db.query(
                    func.count(ApiUsageRow.id),
                    func.coalesce(func.sum(ApiUsageRow.input_tokens), 0),
                    func.coalesce(func.sum(ApiUsageRow.output_tokens), 0),
                    func.coalesce(func.sum(ApiUsageRow.total_cost_usd), 0),
                )
                .filter(ApiUsageRow.timestamp >= cutoff)
                .one()
            )
            return {
                "period": period,
                "request_count": row[0],
                "total_input_tokens": int(row[1]),
                "total_output_tokens": int(row[2]),
                "total_cost_usd": round(float(row[3]), 4),
            }
        return self._run_in_session(_summary, read_only=True)

    def get_breakdown(self, days: int = 30) -> list[dict[str, Any]]:
        def _breakdown(db: Session) -> list[dict[str, Any]]:
            cutoff = _now() - timedelta(days=days)
            rows = (
                db.query(
                    ApiUsageRow.provider, ApiUsageRow.model,
                    func.count(ApiUsageRow.id), func.sum(ApiUsageRow.total_cost_usd),
                )
                .filter(ApiUsageRow.timestamp >= cutoff)
                .group_by(ApiUsageRow.provider, ApiUsageRow.model)
                .order_by(func.sum(ApiUsageRow.total_cost_usd).desc())
                .all()
            )
            return [
                {"provider": r[0], "model": r[1], "count": r[2], "cost_usd": round(float(r[3]), 4)}
                for r in rows
            ]
        return self._run_in_session(_breakdown, read_only=True)

    def get_trend(self, days: int = 30) -> list[dict[str, Any]]:
        def _trend(db: Session) -> list[dict[str, Any]]:
            cutoff = _now() - timedelta(days=days)
            rows = (
                db.query(func.date(ApiUsageRow.timestamp), func.sum(ApiUsageRow.total_cost_usd))
                .filter(ApiUsageRow.timestamp >= cutoff)
                .group_by(func.date(ApiUsageRow.timestamp))
                .order_by(func.date(ApiUsageRow.timestamp))
                .all()
            )
            return [{"date": str(r[0]), "cost_usd": round(float(r[1]), 4)} for r in rows]
        return self._run_in_session(_trend, read_only=True)

    def set_budget(
        self,
        scope: str,
        limit_usd: float,
        provider: Optional[str] = None,
        alert_threshold: float = 0.8,
    ) -> None:
        def _set(db: Session) -> None:
            existing = (
                db.query(BudgetLimitRow)
                .filter(BudgetLimitRow.scope == scope, BudgetLimitRow.provider == provider)
                .first()
            )
            if existing:
                existing.limit_usd = limit_usd
                existing.alert_threshold = alert_threshold
            else:
                db.add(BudgetLimitRow(
                    id=uuid.uuid4(), scope=scope, provider=provider,
                    limit_usd=limit_usd, alert_threshold=alert_threshold,
                ))
        self._run_in_session(_set)

    def check_alerts(self) -> list[dict[str, Any]]:
        def _check(db: Session) -> list[dict[str, Any]]:
            alerts = []
            budgets = db.query(BudgetLimitRow).all()
            for budget in budgets:
                days = {"daily": 1, "weekly": 7, "monthly": 30}.get(budget.scope, 1)
                cutoff = _now() - timedelta(days=days)
                q = db.query(func.coalesce(func.sum(ApiUsageRow.total_cost_usd), 0)).filter(ApiUsageRow.timestamp >= cutoff)
                if budget.provider:
                    q = q.filter(ApiUsageRow.provider == budget.provider)
                spent = float(q.scalar() or 0)
                limit = float(budget.limit_usd)
                threshold = float(budget.alert_threshold)
                if spent >= limit * threshold:
                    alerts.append({
                        "scope": budget.scope, "provider": budget.provider,
                        "limit_usd": limit, "spent_usd": round(spent, 4),
                        "threshold": threshold, "exceeded": spent >= limit,
                    })
            return alerts
        return self._run_in_session(_check, read_only=True)
