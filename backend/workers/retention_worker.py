"""Retention Policy Worker — v3.0 Enterprise.

Periodically deletes records older than their configured retention_days.
Supports dry-run mode for testing.

Usage:
    python -m workers.retention_worker                  # run with defaults
    python -m workers.retention_worker --dry-run        # preview deletions
    python -m workers.retention_worker --poll-interval 1800  # every 30 min
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from database import engine
from security.audit import write_audit_log
from models import (
    RetentionPolicy,
    Run,
    TraceSpan,
    Approval,
    AuditLog,
    EvalResult,
)

try:
    from security.structured_logging import setup_logging
    setup_logging()
except ImportError:
    pass
logger = logging.getLogger("retention_worker")

RESOURCE_MODEL_MAP = {
    "run": Run,
    "trace_span": TraceSpan,
    "approval": Approval,
    "audit_log": AuditLog,
    "eval_result": EvalResult,
}

RESOURCE_TS_COLUMN = {
    "run": "created_at",
    "trace_span": "started_at",
    "approval": "created_at",
    "audit_log": "created_at",
    "eval_result": "created_at",
}


def run_retention_cycle(dry_run: bool = False) -> dict[str, int]:
    """Execute one retention cycle. Returns counts of deleted records per resource type."""
    session = Session(engine)
    results: dict[str, int] = {}

    try:
        policies = (
            session.query(RetentionPolicy)
            .filter(RetentionPolicy.is_active == True)
            .all()
        )

        if not policies:
            logger.info("No active retention policies found")
            return results

        for policy in policies:
            model = RESOURCE_MODEL_MAP.get(policy.resource_type)
            ts_col_name = RESOURCE_TS_COLUMN.get(policy.resource_type)
            if not model or not ts_col_name:
                logger.warning(f"Unknown resource type: {policy.resource_type}")
                continue

            cutoff = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
            ts_col = getattr(model, ts_col_name)

            count = session.execute(
                select(model.id).where(ts_col < cutoff)
            ).rowcount

            if count == 0:
                results[policy.resource_type] = 0
                continue

            if dry_run:
                logger.info(
                    "[DRY RUN] Would delete %d %s records older than %s",
                    count, policy.resource_type, cutoff.isoformat(),
                    extra={"resource_type": policy.resource_type, "count": count, "dry_run": True},
                )
            else:
                stmt = delete(model).where(ts_col < cutoff)
                session.execute(stmt)
                logger.info(
                    "Deleted %d %s records older than %s",
                    count, policy.resource_type, cutoff.isoformat(),
                    extra={"resource_type": policy.resource_type, "count": count, "dry_run": False},
                )

            results[policy.resource_type] = count

        if not dry_run and results:
            # Log retention actions to audit (before commit)
            write_audit_log(
                session,
                actor_type="worker",
                actor_id="retention_worker",
                action="retention.cleanup",
                resource_type="retention_policy",
                after_json={
                    "deleted": results,
                    "dry_run": False,
                },
            )
            session.commit()

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return results


def main():
    parser = argparse.ArgumentParser(description="Retention policy worker")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=3600,
        help="Seconds between retention cycles (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletions without actually deleting",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    logger.info(
        f"Retention worker started (poll_interval={args.poll_interval}s, "
        f"dry_run={args.dry_run})"
    )

    while True:
        try:
            results = run_retention_cycle(dry_run=args.dry_run)
            if results:
                logger.info(f"Retention cycle complete: {results}")
        except Exception:
            logger.exception("Retention cycle failed")

        _write_heartbeat()
        _sleep_with_heartbeat(args.poll_interval)


def _write_heartbeat() -> None:
    """Write heartbeat file for health check monitoring."""
    from utils.heartbeat import write_heartbeat
    write_heartbeat("retention_worker")


def _sleep_with_heartbeat(total_seconds: int) -> None:
    """Sleep between retention cycles without letting health checks go stale."""
    remaining = max(total_seconds, 0)
    while remaining > 0:
        interval = min(30, remaining)
        time.sleep(interval)
        _write_heartbeat()
        remaining -= interval


if __name__ == "__main__":
    main()
