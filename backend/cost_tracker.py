"""API cost tracking with budget alerts."""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DB_PATH = Path(__file__).parent / "data" / "costs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usage_id TEXT NOT NULL UNIQUE,
    timestamp TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    review_id TEXT,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_cost_usd REAL NOT NULL,
    latency_ms INTEGER,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budget_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    provider TEXT,
    limit_usd REAL NOT NULL,
    alert_threshold REAL DEFAULT 0.8
);

CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON api_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_provider ON api_usage(provider);
CREATE INDEX IF NOT EXISTS idx_usage_review ON api_usage(review_id);
"""


_cost_repo = None


def configure_cost_repository(repo) -> None:
    """Configure PG repository for read and write operations."""
    global _cost_repo
    _cost_repo = repo


class CostTracker:
    """Tracks API usage costs and budget limits."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or _DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript(_SCHEMA)

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
        """Record a single API usage event. Returns usage_id."""
        if _cost_repo is not None:
            return _cost_repo.record_usage(
                provider, model, input_tokens, output_tokens,
                cost_per_1k_input, cost_per_1k_output,
                review_id, latency_ms, status,
            )
        cost = (input_tokens / 1000 * cost_per_1k_input) + (
            output_tokens / 1000 * cost_per_1k_output
        )
        usage_id = str(uuid.uuid4())[:12]
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO api_usage
                   (usage_id, timestamp, provider, model, review_id,
                    input_tokens, output_tokens, total_cost_usd, latency_ms, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    usage_id,
                    datetime.now(timezone.utc).isoformat(),
                    provider,
                    model,
                    review_id,
                    input_tokens,
                    output_tokens,
                    round(cost, 6),
                    latency_ms,
                    status,
                ),
            )
        return usage_id

    def get_summary(self, period: str = "daily") -> dict:
        """Get cost summary for a period: daily, weekly, monthly."""
        if _cost_repo is not None:
            return _cost_repo.get_summary(period)
        days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 1)
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                """SELECT COUNT(*) as count,
                          SUM(input_tokens) as total_in,
                          SUM(output_tokens) as total_out,
                          SUM(total_cost_usd) as total_cost
                   FROM api_usage
                   WHERE timestamp >= date('now', ?)""",
                (f"-{days} days",),
            ).fetchone()
        return {
            "period": period,
            "request_count": row[0] or 0,
            "total_input_tokens": row[1] or 0,
            "total_output_tokens": row[2] or 0,
            "total_cost_usd": round(row[3] or 0, 4),
        }

    def get_breakdown(self, days: int = 30) -> list[dict]:
        """Get cost breakdown by provider and model."""
        if _cost_repo is not None:
            return _cost_repo.get_breakdown(days)
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                """SELECT provider, model,
                          COUNT(*) as count,
                          SUM(total_cost_usd) as cost
                   FROM api_usage
                   WHERE timestamp >= date('now', ?)
                   GROUP BY provider, model
                   ORDER BY cost DESC""",
                (f"-{days} days",),
            ).fetchall()
        return [
            {"provider": r[0], "model": r[1], "count": r[2], "cost_usd": round(r[3], 4)}
            for r in rows
        ]

    def get_trend(self, days: int = 30) -> list[dict]:
        """Get daily cost trend."""
        if _cost_repo is not None:
            return _cost_repo.get_trend(days)
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                """SELECT date(timestamp) as day, SUM(total_cost_usd) as cost
                   FROM api_usage
                   WHERE timestamp >= date('now', ?)
                   GROUP BY day
                   ORDER BY day""",
                (f"-{days} days",),
            ).fetchall()
        return [{"date": r[0], "cost_usd": round(r[1], 4)} for r in rows]

    def set_budget(
        self, scope: str, limit_usd: float, provider: Optional[str] = None,
        alert_threshold: float = 0.8,
    ) -> None:
        """Set a budget limit."""
        if _cost_repo is not None:
            _cost_repo.set_budget(scope, limit_usd, provider, alert_threshold)
            return
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "DELETE FROM budget_limits WHERE scope = ? AND COALESCE(provider, '') = COALESCE(?, '')",
                (scope, provider or ""),
            )
            conn.execute(
                """INSERT INTO budget_limits (scope, provider, limit_usd, alert_threshold)
                   VALUES (?, ?, ?, ?)""",
                (scope, provider, limit_usd, alert_threshold),
            )

    def check_alerts(self) -> list[dict]:
        """Check if any budget thresholds are exceeded."""
        if _cost_repo is not None:
            return _cost_repo.check_alerts()
        alerts = []
        with sqlite3.connect(str(self._db_path)) as conn:
            budgets = conn.execute(
                "SELECT scope, provider, limit_usd, alert_threshold FROM budget_limits"
            ).fetchall()
            for scope, provider, limit, threshold in budgets:
                days = {"daily": 1, "weekly": 7, "monthly": 30}.get(scope, 1)
                query = "SELECT SUM(total_cost_usd) FROM api_usage WHERE timestamp >= date('now', ?)"
                params: list = [f"-{days} days"]
                if provider:
                    query += " AND provider = ?"
                    params.append(provider)
                spent = conn.execute(query, params).fetchone()[0] or 0.0
                if spent >= limit * threshold:
                    alerts.append({
                        "scope": scope,
                        "provider": provider,
                        "limit_usd": limit,
                        "spent_usd": round(spent, 4),
                        "threshold": threshold,
                        "exceeded": spent >= limit,
                    })
        return alerts
