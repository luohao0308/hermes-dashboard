"""Workflow Worker — lightweight background worker for durable execution.

Uses PostgreSQL as the sole source of truth. No in-memory state.

Single-Instance Protection (OPT-59):
    Multiple worker instances CAN run simultaneously — they will NOT
    duplicate work thanks to PostgreSQL advisory locks:

    1. pg_try_advisory_lock(namespace, lock_id) is non-blocking: returns
       true if the lock was acquired, false if another worker holds it.
    2. Each task UUID maps to a stable int lock_id via _task_lock_id().
    3. Lock is released automatically when the DB session ends (COMMIT or
       ROLLBACK), so crashed workers do not leave orphaned locks.
    4. Stale application-level locks (locked_by/locked_at) are recovered
       by _recover_stale_locks() after stale_lock_seconds (default 300s).

    Heartbeat files include worker_id and PID so that /health and
    /api/metrics report which instance is actively processing.

Usage:
    python -m workers.workflow_worker
    python -m workers.workflow_worker --poll-interval 5 --stale-lock-seconds 300
    python -m workers.workflow_worker --worker-id worker-custom-name

Architecture:
    - Polls PostgreSQL for tasks in pending/running/waiting_approval state
    - Acquires advisory lock per task to prevent duplicate execution
    - Handles: task pickup, retry with backoff, dead-letter, approval timeout,
      workflow-level timeout, concurrency limits, stale lock recovery
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import (
    WorkflowDefinition,
    WorkflowNode,
    Run,
    Task,
    Approval,
    TraceSpan,
)

try:
    from security.structured_logging import setup_logging
    setup_logging()
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
logger = logging.getLogger("workflow_worker")

# Advisory lock namespace for workflow tasks
ADVISORY_LOCK_NAMESPACE = 7201


def _task_lock_id(task_id: uuid.UUID) -> int:
    """Convert task UUID to a stable int for pg_try_advisory_lock."""
    return task_id.int % (2**31)


def _compute_duration_ms(started: datetime | None, ended: datetime | None) -> int | None:
    if started and ended:
        return int((ended - started).total_seconds() * 1000)
    return None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _build_reverse_adjacency(edges: list[tuple[str, str]]) -> dict[str, list[str]]:
    rev: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        rev[dst].append(src)
    return rev


def _check_dependencies_met(
    task_node_id: str,
    tasks_by_node: dict[str, Task],
    rev_adj: dict[str, list[str]],
) -> bool:
    deps = rev_adj.get(task_node_id, [])
    for dep_node_id in deps:
        dep_task = tasks_by_node.get(dep_node_id)
        if not dep_task or dep_task.status != "completed":
            return False
    return True


class WorkflowWorker:
    """Lightweight workflow worker backed by PostgreSQL."""

    def __init__(
        self,
        poll_interval: float = 2.0,
        stale_lock_seconds: int = 300,
        worker_id: str | None = None,
    ):
        self.poll_interval = poll_interval
        self.stale_lock_seconds = stale_lock_seconds
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        """Main loop: poll, pickup, advance, sleep."""
        logger.info(
            "Worker %s starting (poll=%ss, stale_lock=%ss)",
            self.worker_id, self.poll_interval, self.stale_lock_seconds,
        )

        # Recover stale locks on startup
        db = SessionLocal()
        try:
            self._recover_stale_locks(db)
        finally:
            db.close()

        while self._running:
            db = SessionLocal()
            try:
                self._tick(db)
            except Exception:
                logger.exception("Error in worker tick")
            finally:
                db.close()
            time.sleep(self.poll_interval)

        logger.info("Worker %s stopped", self.worker_id)

    def _tick(self, db: Session) -> None:
        """Single worker tick: process all actionable items."""
        self._recover_stale_locks(db)
        self._check_workflow_timeouts(db)
        self._check_approval_timeouts(db)
        self._process_pending_tasks(db)
        self._handle_failed_tasks(db)
        self._write_heartbeat()

    def _write_heartbeat(self) -> None:
        """Write heartbeat file for health check monitoring.

        Includes worker_id and PID so that /health and /api/metrics
        can report which instance is actively processing tasks.
        Advisory locks (pg_try_advisory_lock) ensure only one worker
        executes a given task even when multiple instances are running.
        """
        import os
        from utils.heartbeat import write_heartbeat
        write_heartbeat(
            "scheduler_worker",
            worker_id=self.worker_id,
            pid=os.getpid(),
            version="3.0.0",
        )

    # ------------------------------------------------------------------
    # Stale lock recovery
    # ------------------------------------------------------------------

    def _recover_stale_locks(self, db: Session) -> None:
        """Release locks held by dead workers."""
        cutoff = _now_utc() - timedelta(seconds=self.stale_lock_seconds)
        stale = (
            db.query(Task)
            .filter(
                Task.locked_by.isnot(None),
                Task.locked_at < cutoff,
                Task.status.in_(["running", "pending"]),
            )
            .all()
        )
        for task in stale:
            logger.info(
                "Recovering stale lock on task %s (was locked by %s)",
                task.id, task.locked_by,
            )
            task.locked_by = None
            task.locked_at = None
        if stale:
            db.commit()

    # ------------------------------------------------------------------
    # Workflow-level timeout
    # ------------------------------------------------------------------

    def _check_workflow_timeouts(self, db: Session) -> None:
        """Check running workflows against their timeout_seconds."""
        now = _now_utc()
        running_runs = (
            db.query(Run)
            .filter(Run.status == "running", Run.workflow_id.isnot(None))
            .all()
        )
        for run in running_runs:
            wf = db.get(WorkflowDefinition, run.workflow_id)
            if not wf or not wf.timeout_seconds or not run.started_at:
                continue
            elapsed = (now - run.started_at).total_seconds()
            if elapsed > wf.timeout_seconds:
                self._timeout_workflow(db, run, wf.timeout_seconds)

    def _timeout_workflow(self, db: Session, run: Run, timeout: int) -> None:
        """Cancel all tasks and fail the run due to workflow timeout."""
        now = _now_utc()
        logger.warning("Workflow run %s timed out after %ds", run.id, timeout)
        tasks = db.query(Task).filter(Task.run_id == run.id).all()
        for t in tasks:
            if t.status not in ("completed", "failed", "cancelled", "dead_letter"):
                t.status = "cancelled"
                t.ended_at = now
                t.error_summary = f"Workflow timed out after {timeout}s"
                t.locked_by = None
                t.locked_at = None
        run.status = "failed"
        run.ended_at = now
        run.duration_ms = _compute_duration_ms(run.started_at, now)
        run.error_summary = f"Workflow timed out after {timeout}s"
        db.add(TraceSpan(
            id=uuid.uuid4(), run_id=run.id,
            span_type="workflow_timeout", title="Workflow timed out",
            status="failed", error_summary=run.error_summary,
            started_at=now, ended_at=now,
        ))
        db.commit()

    # ------------------------------------------------------------------
    # Approval timeout
    # ------------------------------------------------------------------

    def _check_approval_timeouts(self, db: Session) -> None:
        """Timeout approvals exceeding node's approval_timeout_seconds."""
        now = _now_utc()
        waiting = db.query(Task).filter(Task.status == "waiting_approval").all()
        for task in waiting:
            run = db.get(Run, task.run_id)
            if not run or not run.workflow_id or not task.started_at:
                continue
            node = (
                db.query(WorkflowNode)
                .filter(
                    WorkflowNode.workflow_id == run.workflow_id,
                    WorkflowNode.node_id == task.node_id,
                )
                .first()
            )
            if not node or not node.approval_timeout_seconds:
                continue
            elapsed = (now - task.started_at).total_seconds()
            if elapsed > node.approval_timeout_seconds:
                self._timeout_approval(db, task, run, node.approval_timeout_seconds)

    def _timeout_approval(self, db: Session, task: Task, run: Run, timeout: int) -> None:
        now = _now_utc()
        logger.warning("Approval on task %s timed out after %ds", task.id, timeout)
        approval = (
            db.query(Approval)
            .filter(Approval.task_id == task.id, Approval.status == "pending")
            .first()
        )
        if approval:
            approval.status = "rejected"
            approval.resolved_at = now
            approval.resolved_note = f"Approval timed out after {timeout}s"
        task.status = "failed"
        task.error_summary = f"Approval timed out after {timeout}s"
        task.ended_at = now
        task.duration_ms = _compute_duration_ms(task.started_at, now)
        db.add(TraceSpan(
            id=uuid.uuid4(), run_id=run.id, task_id=task.id,
            span_type="approval_timeout", title=f"Approval timed out: {task.title}",
            status="failed", error_summary=task.error_summary,
            started_at=now, ended_at=now,
        ))
        db.commit()

    # ------------------------------------------------------------------
    # Process pending tasks
    # ------------------------------------------------------------------

    def _process_pending_tasks(self, db: Session) -> None:
        """Pick up pending tasks whose dependencies are met."""
        now = _now_utc()
        running_runs = (
            db.query(Run)
            .filter(Run.status == "running", Run.workflow_id.isnot(None))
            .all()
        )
        for run in running_runs:
            wf = db.get(WorkflowDefinition, run.workflow_id)
            if not wf:
                continue
            self._process_run_pending(db, run, wf, now)

    def _process_run_pending(self, db: Session, run: Run, wf: WorkflowDefinition, now: datetime) -> None:
        active_count = (
            db.query(Task)
            .filter(
                Task.run_id == run.id,
                Task.status.in_(["running", "waiting_approval"]),
            )
            .count()
        )
        limit = wf.max_concurrent_tasks

        tasks = db.query(Task).filter(Task.run_id == run.id).all()
        tasks_by_node: dict[str, Task] = {t.node_id: t for t in tasks if t.node_id}
        edge_tuples = [(e.from_node, e.to_node) for e in wf.edges]
        rev_adj = _build_reverse_adjacency(edge_tuples)
        node_map = {n.node_id: n for n in wf.nodes}

        for task in tasks:
            if task.status != "pending":
                continue
            if task.next_retry_at and task.next_retry_at > now:
                continue
            if task.node_id and not _check_dependencies_met(task.node_id, tasks_by_node, rev_adj):
                continue
            if limit and active_count >= limit:
                return
            if not self._try_lock_task(db, task):
                continue

            node = node_map.get(task.node_id) if task.node_id else None
            if node and node.task_type == "approval":
                self._start_approval_task(db, task, run, node)
            else:
                task.status = "running"
                task.started_at = now
                logger.info("Task %s started by %s", task.id, self.worker_id)

            active_count += 1
            db.commit()

    # ------------------------------------------------------------------
    # Handle failed tasks (retry / dead-letter)
    # ------------------------------------------------------------------

    def _handle_failed_tasks(self, db: Session) -> None:
        """Process failed tasks: retry with backoff or move to dead-letter."""
        now = _now_utc()
        failed = (
            db.query(Task)
            .filter(Task.status == "failed", Task.locked_by == self.worker_id)
            .all()
        )
        for task in failed:
            run = db.get(Run, task.run_id)
            if not run or not run.workflow_id:
                self._unlock_task(task)
                continue
            wf = db.get(WorkflowDefinition, run.workflow_id)
            if not wf:
                self._unlock_task(task)
                continue
            node = (
                db.query(WorkflowNode)
                .filter(
                    WorkflowNode.workflow_id == wf.id,
                    WorkflowNode.node_id == task.node_id,
                )
                .first()
            )
            if not node:
                self._move_to_dead_letter(db, task, "No node definition found")
                continue

            policy = node.retry_policy or {}
            max_retries = policy.get("max_retries", 3)
            backoff = policy.get("backoff_seconds", 1.0)

            if task.retry_count < max_retries:
                task.retry_count += 1
                task.status = "pending"
                task.error_summary = None
                task.ended_at = None
                task.duration_ms = None
                task.next_retry_at = now + timedelta(seconds=backoff * (2 ** (task.retry_count - 1)))
                self._unlock_task(task)
                logger.info(
                    "Task %s scheduled for retry %d/%d at %s",
                    task.id, task.retry_count, max_retries, task.next_retry_at,
                )
            else:
                self._move_to_dead_letter(db, task, f"Exceeded max retries ({max_retries})")
        db.commit()

        # Check run completion
        running_runs = (
            db.query(Run)
            .filter(Run.status == "running", Run.workflow_id.isnot(None))
            .all()
        )
        for run in running_runs:
            self._check_run_completion(db, run)

    # ------------------------------------------------------------------
    # Dead-letter
    # ------------------------------------------------------------------

    def _move_to_dead_letter(self, db: Session, task: Task, reason: str) -> None:
        task.status = "dead_letter"
        task.error_summary = reason
        task.ended_at = _now_utc()
        task.duration_ms = _compute_duration_ms(task.started_at, task.ended_at)
        self._unlock_task(task)
        logger.warning("Task %s moved to dead_letter: %s", task.id, reason)
        db.add(TraceSpan(
            id=uuid.uuid4(), run_id=task.run_id, task_id=task.id,
            span_type="dead_letter", title=f"Dead letter: {task.title}",
            status="failed", error_summary=reason,
            started_at=_now_utc(), ended_at=_now_utc(),
        ))

    # ------------------------------------------------------------------
    # Run completion
    # ------------------------------------------------------------------

    def _check_run_completion(self, db: Session, run: Run) -> None:
        tasks = db.query(Task).filter(Task.run_id == run.id).all()
        statuses = {t.status for t in tasks}
        terminal = {"completed", "failed", "cancelled", "dead_letter"}
        if statuses and statuses <= terminal:
            any_failed = bool(statuses & {"failed", "dead_letter", "cancelled"})
            run.status = "failed" if any_failed else "completed"
            run.ended_at = _now_utc()
            run.duration_ms = _compute_duration_ms(run.started_at, run.ended_at)
            db.add(TraceSpan(
                id=uuid.uuid4(), run_id=run.id,
                span_type="workflow_complete", title=f"Workflow {run.status}",
                status=run.status, started_at=_now_utc(), ended_at=_now_utc(),
            ))
            db.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _try_lock_task(self, db: Session, task: Task) -> bool:
        lock_id = _task_lock_id(task.id)
        result = db.execute(
            text("SELECT pg_try_advisory_lock(:ns, :lock_id)"),
            {"ns": ADVISORY_LOCK_NAMESPACE, "lock_id": lock_id},
        ).scalar()
        if result:
            task.locked_by = self.worker_id
            task.locked_at = _now_utc()
            return True
        return False

    def _unlock_task(self, task: Task) -> None:
        task.locked_by = None
        task.locked_at = None

    def _start_approval_task(
        self, db: Session, task: Task, run: Run, node: WorkflowNode,
    ) -> None:
        db.add(Approval(
            id=uuid.uuid4(), run_id=run.id, task_id=task.id,
            status="pending",
            context_json={"node_id": task.node_id, "workflow_id": str(run.workflow_id)},
        ))
        task.status = "waiting_approval"
        task.started_at = _now_utc()
        db.add(TraceSpan(
            id=uuid.uuid4(), run_id=run.id, task_id=task.id,
            span_type="approval_request", title=f"Approval requested: {task.title}",
            status="running", started_at=_now_utc(),
        ))
        logger.info("Task %s waiting for approval", task.id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Workflow Worker")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--stale-lock-seconds", type=int, default=300)
    parser.add_argument("--worker-id", type=str, default=None)
    args = parser.parse_args()

    worker = WorkflowWorker(
        poll_interval=args.poll_interval,
        stale_lock_seconds=args.stale_lock_seconds,
        worker_id=args.worker_id,
    )

    def handle_signal(signum, frame):
        logger.info("Received signal %s, stopping...", signum)
        worker.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    worker.run()


if __name__ == "__main__":
    main()
