"""Shared workflow nesting functions for child workflow execution.

This module provides functions for:
- Launching child workflow runs from subworkflow tasks
- Polling child run status and advancing parent tasks
- Cascading control actions (pause/resume/cancel) to child runs
- Retrying child runs without creating duplicates
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import (
    WorkflowDefinition,
    WorkflowNode,
    Run,
    Task,
    TraceSpan,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _compute_duration_ms(started: datetime | None, ended: datetime | None) -> int | None:
    if started and ended:
        # Ensure both datetimes are timezone-aware or both are naive
        if started.tzinfo is not None and ended.tzinfo is None:
            ended = ended.replace(tzinfo=started.tzinfo)
        elif started.tzinfo is None and ended.tzinfo is not None:
            started = started.replace(tzinfo=ended.tzinfo)
        return int((ended - started).total_seconds() * 1000)
    return None


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


def _launch_child_run(
    db: Session,
    parent_run: Run,
    parent_task: Task,
    node: WorkflowNode,
) -> Run:
    """Launch a child workflow run from a subworkflow task.

    Creates a child Run with parent_run_id set, creates Tasks for each node
    in the child workflow, and records child_workflow_version_at_launch.
    """
    child_workflow_id = node.child_workflow_id
    if not child_workflow_id:
        raise ValueError(f"Node {node.node_id} has no child_workflow_id")

    child_workflow = db.get(WorkflowDefinition, child_workflow_id)
    if not child_workflow:
        raise ValueError(f"Child workflow {child_workflow_id} not found")

    now = _now_utc()

    # Record the child workflow version at launch time
    child_version_info = {
        "child_workflow_id": str(child_workflow_id),
        "child_workflow_name": child_workflow.name,
        "child_workflow_version": child_workflow.version,
        "launched_at": now.isoformat(),
    }

    # Merge with existing metadata
    parent_metadata = dict(parent_run.metadata_json or {})
    child_runs = parent_metadata.get("child_runs", [])
    child_runs.append(child_version_info)
    parent_metadata["child_runs"] = child_runs
    parent_run.metadata_json = parent_metadata

    # Create child run
    child_run = Run(
        id=uuid.uuid4(),
        runtime_id=parent_run.runtime_id,
        workflow_id=child_workflow_id,
        parent_run_id=parent_run.id,
        title=f"Child: {child_workflow.name}",
        status="running",
        input_summary=f"Launched by parent run {parent_run.id}",
        metadata_json={"parent_task_id": str(parent_task.id)},
        started_at=now,
    )
    db.add(child_run)
    db.flush()

    # Create tasks for each node in child workflow
    for child_node in child_workflow.nodes:
        task = Task(
            id=uuid.uuid4(),
            run_id=child_run.id,
            node_id=child_node.node_id,
            title=child_node.title,
            status="pending",
            task_type=child_node.task_type,
        )
        db.add(task)

    # Create trace span for child run launch
    db.add(TraceSpan(
        id=uuid.uuid4(),
        run_id=parent_run.id,
        task_id=parent_task.id,
        span_type="subworkflow_launch",
        title=f"Launched child workflow: {child_workflow.name}",
        status="running",
        started_at=now,
        metadata_json={"child_run_id": str(child_run.id)},
    ))

    return child_run


def _poll_child_run(db: Session, parent_task: Task) -> tuple[str, str | None]:
    """Poll child run status and determine parent task transition.

    Returns (new_status, error_summary):
    - ("running", None) if child is still running
    - ("completed", None) if child completed successfully
    - ("failed", error_summary) if child failed
    - ("cancelled", reason) if child was cancelled
    """
    child_run_id = parent_task.metadata_json.get("child_run_id") if parent_task.metadata_json else None
    if not child_run_id:
        return "failed", "No child_run_id in task metadata"

    child_run = db.get(Run, uuid.UUID(child_run_id))
    if not child_run:
        return "failed", f"Child run {child_run_id} not found"

    if child_run.status == "running":
        return "running", None
    elif child_run.status == "completed":
        return "completed", None
    elif child_run.status == "failed":
        return "failed", child_run.error_summary or "Child workflow failed"
    elif child_run.status == "cancelled":
        return "cancelled", child_run.error_summary or "Child workflow cancelled"
    elif child_run.status == "paused":
        return "running", None
    else:
        return "running", None


def _cascade_to_child_runs(
    db: Session,
    run_id: uuid.UUID,
    action: str,
) -> list[uuid.UUID]:
    """Cascade an action (pause/resume/cancel) to all child runs.

    Returns list of affected child run IDs.
    """
    affected = []

    child_runs = db.query(Run).filter(Run.parent_run_id == run_id).all()
    for child_run in child_runs:
        if action == "pause" and child_run.status == "running":
            child_run.status = "paused"
            child_run.updated_at = _now_utc()
            affected.append(child_run.id)
            # Recursively cascade
            affected.extend(_cascade_to_child_runs(db, child_run.id, action))
        elif action == "resume" and child_run.status == "paused":
            child_run.status = "running"
            child_run.updated_at = _now_utc()
            affected.append(child_run.id)
            # Recursively cascade
            affected.extend(_cascade_to_child_runs(db, child_run.id, action))
        elif action == "cancel" and child_run.status in ("running", "paused", "queued"):
            child_run.status = "cancelled"
            child_run.ended_at = _now_utc()
            child_run.duration_ms = _compute_duration_ms(child_run.started_at, child_run.ended_at)
            child_run.updated_at = _now_utc()
            affected.append(child_run.id)
            # Cancel all tasks in child run
            for task in db.query(Task).filter(Task.run_id == child_run.id).all():
                if task.status not in ("completed", "failed", "cancelled", "dead_letter"):
                    task.status = "cancelled"
                    task.ended_at = _now_utc()
                    task.duration_ms = _compute_duration_ms(task.started_at, task.ended_at)
            # Recursively cascade
            affected.extend(_cascade_to_child_runs(db, child_run.id, action))

    return affected


def _retry_child_run(
    db: Session,
    parent_task: Task,
) -> Run | None:
    """Retry an existing child run without creating duplicate.

    Resets failed/cancelled/dead_letter tasks in the child run.
    Returns the child run if retryable, None otherwise.
    """
    child_run_id = parent_task.metadata_json.get("child_run_id") if parent_task.metadata_json else None
    if not child_run_id:
        return None

    child_run = db.get(Run, uuid.UUID(child_run_id))
    if not child_run:
        return None

    if child_run.status not in ("failed", "cancelled"):
        return None

    now = _now_utc()
    retried = 0

    for task in db.query(Task).filter(Task.run_id == child_run.id).all():
        if task.status in ("failed", "cancelled", "dead_letter"):
            task.status = "pending"
            task.error_summary = None
            task.started_at = None
            task.ended_at = None
            task.duration_ms = None
            task.locked_by = None
            task.locked_at = None
            task.next_retry_at = None
            retried += 1

    if retried == 0:
        return None

    child_run.status = "running"
    child_run.error_summary = None
    child_run.ended_at = None
    child_run.duration_ms = None
    child_run.updated_at = now

    db.add(TraceSpan(
        id=uuid.uuid4(),
        run_id=child_run.id,
        span_type="workflow_retried",
        title="Child workflow retry requested",
        status="running",
        started_at=now,
    ))

    return child_run
