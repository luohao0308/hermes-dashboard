"""Workflow Orchestration API (v2.0).

Endpoints:
    POST   /api/workflows              — create workflow definition
    GET    /api/workflows              — list workflow definitions
    GET    /api/workflows/{id}         — get workflow definition
    PUT    /api/workflows/{id}         — update workflow definition
    DELETE /api/workflows/{id}         — delete workflow definition
    POST   /api/workflows/{id}/runs    — start a workflow run
    GET    /api/workflows/{id}/runs    — list runs for a workflow
    GET    /api/workflows/{id}/runs/{run_id} — get run detail with tasks
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    Run,
    Task,
    TraceSpan,
    Approval,
    WorkflowVersionHistory,
)
from security.audit import write_audit_log
from security.rbac import require_role
from schemas.workflow import (
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
    WorkflowDefinitionResponse,
    WorkflowDefinitionListResponse,
    WorkflowRunCreate,
    WorkflowRunResponse,
    WorkflowRunListResponse,
    WorkflowTaskResponse,
)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# ---------------------------------------------------------------------------
# DAG Validation
# ---------------------------------------------------------------------------


def _validate_dag(
    node_ids: set[str],
    edges: list[tuple[str, str]],
) -> None:
    """Validate that the graph is a DAG (no cycles) using Kahn's algorithm."""
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    adj: dict[str, list[str]] = defaultdict(list)

    for src, dst in edges:
        if src not in node_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Edge references unknown source node: {src}",
            )
        if dst not in node_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Edge references unknown destination node: {dst}",
            )
        adj[src].append(dst)
        in_degree[dst] += 1

    queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
    visited = 0

    while queue:
        node = queue.popleft()
        visited += 1
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited != len(node_ids):
        raise HTTPException(
            status_code=400,
            detail="Workflow graph contains a cycle",
        )


def _validate_edge_references(
    node_ids: set[str],
    edges_create: list,
) -> list[tuple[str, str]]:
    """Convert edge create objects to tuples for DAG validation."""
    return [(e.from_node, e.to_node) for e in edges_create]


# ---------------------------------------------------------------------------
# Scheduler helpers
# ---------------------------------------------------------------------------


def _build_reverse_adjacency(
    edges: list[tuple[str, str]],
) -> dict[str, list[str]]:
    """Build reverse adjacency (who depends on whom)."""
    rev: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        rev[dst].append(src)
    return rev


def _get_retry_policy(node: WorkflowNode) -> dict:
    """Extract retry policy from node, with defaults."""
    policy = node.retry_policy or {}
    return {
        "max_retries": policy.get("max_retries", 3),
        "backoff_seconds": policy.get("backoff_seconds", 1.0),
    }


def _check_dependencies_met(
    task_node_id: str,
    tasks_by_node: dict[str, Task],
    rev_adj: dict[str, list[str]],
) -> bool:
    """Check if all dependency tasks are completed."""
    deps = rev_adj.get(task_node_id, [])
    for dep_node_id in deps:
        dep_task = tasks_by_node.get(dep_node_id)
        if not dep_task or dep_task.status != "completed":
            return False
    return True


def _compute_duration_ms(
    started: Optional[datetime],
    ended: Optional[datetime],
) -> Optional[int]:
    """Compute duration in milliseconds."""
    if started and ended:
        delta = ended - started
        return int(delta.total_seconds() * 1000)
    return None


def _advance_workflow(db: Session, run: Run) -> None:
    """Advance workflow state: start ready tasks, handle completions.

    Called after each task status change. Persists all state to PostgreSQL.
    """
    workflow = db.get(WorkflowDefinition, run.workflow_id)
    if not workflow:
        return

    edge_tuples = [(e.from_node, e.to_node) for e in workflow.edges]
    node_map = {n.node_id: n for n in workflow.nodes}
    rev_adj = _build_reverse_adjacency(edge_tuples)

    tasks = db.query(Task).filter(Task.run_id == run.id).all()
    tasks_by_node: dict[str, Task] = {}
    for t in tasks:
        if t.node_id:
            tasks_by_node[t.node_id] = t

    any_failed = False
    active_count = sum(1 for t in tasks if t.status in ("running", "waiting_approval"))

    for task in tasks:
        if task.status in ("completed", "cancelled"):
            continue

        if task.status == "failed":
            node = node_map.get(task.node_id) if task.node_id else None
            if node:
                policy = _get_retry_policy(node)
                if task.retry_count < policy["max_retries"]:
                    task.retry_count += 1
                    task.status = "pending"
                    task.error_summary = None
                    task.ended_at = None
                    task.duration_ms = None
                    backoff = policy.get("backoff_seconds", 1.0)
                    task.next_retry_at = datetime.now(timezone.utc) + timedelta(
                        seconds=backoff * (2 ** (task.retry_count - 1))
                    )
                    continue
            any_failed = True
            continue

        if task.status == "pending":
            if task.node_id and _check_dependencies_met(task.node_id, tasks_by_node, rev_adj):
                # Check concurrency limit before starting
                if workflow.max_concurrent_tasks and active_count >= workflow.max_concurrent_tasks:
                    continue
                node = node_map.get(task.node_id)
                if node and node.task_type == "approval":
                    approval = Approval(
                        id=uuid.uuid4(),
                        run_id=run.id,
                        task_id=task.id,
                        status="pending",
                        context_json={"node_id": task.node_id, "workflow_id": str(run.workflow_id)},
                    )
                    db.add(approval)
                    task.status = "waiting_approval"
                    task.started_at = datetime.now(timezone.utc)
                    active_count += 1
                else:
                    task.status = "running"
                    task.started_at = datetime.now(timezone.utc)
                    active_count += 1

        elif task.status == "running":
            pass  # waiting for external completion

        elif task.status == "waiting_approval":
            approval = (
                db.query(Approval)
                .filter(Approval.task_id == task.id, Approval.status != "pending")
                .first()
            )
            if approval:
                if approval.status == "approved":
                    task.status = "completed"
                    task.ended_at = datetime.now(timezone.utc)
                    task.duration_ms = _compute_duration_ms(task.started_at, task.ended_at)
                elif approval.status == "rejected":
                    task.status = "failed"
                    task.error_summary = "Approval rejected"
                    task.ended_at = datetime.now(timezone.utc)
                    task.duration_ms = _compute_duration_ms(task.started_at, task.ended_at)
                    any_failed = True

    db.flush()

    # Check if entire run is done
    tasks_after = db.query(Task).filter(Task.run_id == run.id).all()
    statuses = {t.status for t in tasks_after}
    terminal = {"completed", "failed", "cancelled", "dead_letter"}

    if statuses <= terminal:
        run.ended_at = datetime.now(timezone.utc)
        run.duration_ms = _compute_duration_ms(run.started_at, run.ended_at)
        run.status = "failed" if any_failed else "completed"
        db.commit()
    else:
        db.commit()
        _start_ready_tasks(db, run, node_map, rev_adj, workflow)


def _start_ready_tasks(
    db: Session,
    run: Run,
    node_map: dict[str, WorkflowNode],
    rev_adj: dict[str, list[str]],
    workflow: WorkflowDefinition | None = None,
) -> None:
    """Start any tasks whose dependencies are now met."""
    tasks = db.query(Task).filter(Task.run_id == run.id, Task.status == "pending").all()
    tasks_by_node = {t.node_id: t for t in db.query(Task).filter(Task.run_id == run.id).all() if t.node_id}
    changed = False
    active_count = db.query(Task).filter(
        Task.run_id == run.id,
        Task.status.in_(["running", "waiting_approval"]),
    ).count()
    max_concurrent = workflow.max_concurrent_tasks if workflow else None

    now = datetime.now(timezone.utc)
    for task in tasks:
        if task.next_retry_at and task.next_retry_at > now:
            continue
        if task.node_id and _check_dependencies_met(task.node_id, tasks_by_node, rev_adj):
            if max_concurrent and active_count >= max_concurrent:
                continue
            node = node_map.get(task.node_id)
            if node and node.task_type == "approval":
                approval = Approval(
                    id=uuid.uuid4(),
                    run_id=run.id,
                    task_id=task.id,
                    status="pending",
                    context_json={"node_id": task.node_id, "workflow_id": str(run.workflow_id)},
                )
                db.add(approval)
                task.status = "waiting_approval"
                task.started_at = datetime.now(timezone.utc)
            else:
                task.status = "running"
                task.started_at = datetime.now(timezone.utc)
            active_count += 1
            changed = True

    if changed:
        db.commit()


# ---------------------------------------------------------------------------
# Task timeout check
# ---------------------------------------------------------------------------


def check_task_timeouts(db: Session) -> None:
    """Check all running tasks for timeout. Called periodically."""
    now = datetime.now(timezone.utc)
    running_tasks = db.query(Task).filter(Task.status == "running").all()

    for task in running_tasks:
        if not task.node_id or not task.started_at:
            continue

        run = db.get(Run, task.run_id)
        if not run or not run.workflow_id:
            continue

        node = (
            db.query(WorkflowNode)
            .filter(
                WorkflowNode.workflow_id == run.workflow_id,
                WorkflowNode.node_id == task.node_id,
            )
            .first()
        )
        if not node or not node.timeout_seconds:
            continue

        elapsed = (now - task.started_at).total_seconds()
        if elapsed > node.timeout_seconds:
            task.status = "failed"
            task.error_summary = f"Task timed out after {node.timeout_seconds}s"
            task.ended_at = now
            task.duration_ms = int(elapsed * 1000)

    db.commit()

    # Advance workflows for timed-out tasks
    affected_run_ids = set()
    for task in running_tasks:
        if task.status == "failed" and task.error_summary and "timed out" in task.error_summary:
            affected_run_ids.add(task.run_id)

    for run_id in affected_run_ids:
        run = db.get(Run, run_id)
        if run and run.workflow_id:
            _advance_workflow(db, run)


# ---------------------------------------------------------------------------
# POST /api/workflows
# ---------------------------------------------------------------------------


@router.post("", response_model=WorkflowDefinitionResponse, status_code=201)
def create_workflow(
    body: WorkflowDefinitionCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    node_ids = [n.node_id for n in body.nodes]
    if len(node_ids) != len(set(node_ids)):
        raise HTTPException(status_code=400, detail="Duplicate node_id in workflow")

    node_id_set = set(node_ids)
    edge_tuples = _validate_edge_references(node_id_set, body.edges)
    _validate_dag(node_id_set, edge_tuples)

    workflow = WorkflowDefinition(
        id=uuid.uuid4(),
        runtime_id=body.runtime_id,
        name=body.name,
        description=body.description,
        version=1,
        timeout_seconds=body.timeout_seconds,
        max_concurrent_tasks=body.max_concurrent_tasks,
    )
    db.add(workflow)
    db.flush()

    for n in body.nodes:
        node = WorkflowNode(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            node_id=n.node_id,
            title=n.title,
            task_type=n.task_type,
            config=n.config,
            retry_policy=n.retry_policy.model_dump() if n.retry_policy else None,
            timeout_seconds=n.timeout_seconds,
            approval_timeout_seconds=n.approval_timeout_seconds,
        )
        db.add(node)

    for e in body.edges:
        edge = WorkflowEdge(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            from_node=e.from_node,
            to_node=e.to_node,
        )
        db.add(edge)

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="workflow.created",
        resource_type="workflow",
        resource_id=str(workflow.id),
        after_json={"name": body.name, "node_count": len(body.nodes)},
    )
    db.commit()
    db.refresh(workflow)
    return WorkflowDefinitionResponse.model_validate(workflow)


# ---------------------------------------------------------------------------
# GET /api/workflows
# ---------------------------------------------------------------------------


@router.get("", response_model=WorkflowDefinitionListResponse)
def list_workflows(
    runtime_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(WorkflowDefinition)
    if runtime_id:
        query = query.filter(WorkflowDefinition.runtime_id == runtime_id)
    total = query.count()
    items = query.order_by(WorkflowDefinition.created_at.desc()).offset(offset).limit(limit).all()
    return WorkflowDefinitionListResponse(
        items=[WorkflowDefinitionResponse.model_validate(w) for w in items],
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /api/workflows/{workflow_id}
# ---------------------------------------------------------------------------


@router.get("/{workflow_id}", response_model=WorkflowDefinitionResponse)
def get_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowDefinitionResponse.model_validate(workflow)


# ---------------------------------------------------------------------------
# PUT /api/workflows/{workflow_id}
# ---------------------------------------------------------------------------


@router.put("/{workflow_id}", response_model=WorkflowDefinitionResponse)
def update_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowDefinitionUpdate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Snapshot current version before modifying
    _snapshot_workflow_version(db, workflow)

    if body.name is not None:
        workflow.name = body.name
    if body.description is not None:
        workflow.description = body.description
    if body.timeout_seconds is not None:
        workflow.timeout_seconds = body.timeout_seconds
    if body.max_concurrent_tasks is not None:
        workflow.max_concurrent_tasks = body.max_concurrent_tasks

    if body.nodes is not None:
        node_ids = [n.node_id for n in body.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise HTTPException(status_code=400, detail="Duplicate node_id in workflow")

        node_id_set = set(node_ids)
        if body.edges is not None:
            edge_defs = body.edges
        else:
            # Use existing edges for validation
            class _E:
                def __init__(self, f, t):
                    self.from_node = f
                    self.to_node = t
            edge_defs = [_E(e.from_node, e.to_node) for e in workflow.edges]

        edge_tuples = _validate_edge_references(node_id_set, edge_defs)
        _validate_dag(node_id_set, edge_tuples)

        # Replace nodes
        for old_node in workflow.nodes:
            db.delete(old_node)
        db.flush()

        for n in body.nodes:
            node = WorkflowNode(
                id=uuid.uuid4(),
                workflow_id=workflow.id,
                node_id=n.node_id,
                title=n.title,
                task_type=n.task_type,
                config=n.config,
                retry_policy=n.retry_policy.model_dump() if n.retry_policy else None,
                timeout_seconds=n.timeout_seconds,
                approval_timeout_seconds=n.approval_timeout_seconds,
            )
            db.add(node)

    if body.edges is not None:
        for old_edge in workflow.edges:
            db.delete(old_edge)
        db.flush()

        for e in body.edges:
            edge = WorkflowEdge(
                id=uuid.uuid4(),
                workflow_id=workflow.id,
                from_node=e.from_node,
                to_node=e.to_node,
            )
            db.add(edge)

    workflow.version += 1
    workflow.updated_at = datetime.now(timezone.utc)
    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="workflow.updated",
        resource_type="workflow",
        resource_id=str(workflow.id),
        after_json={"name": workflow.name, "version": workflow.version},
    )
    db.commit()
    db.refresh(workflow)
    return WorkflowDefinitionResponse.model_validate(workflow)


def _snapshot_workflow_version(db: Session, workflow: WorkflowDefinition) -> None:
    """Save current workflow state to version history before modification."""
    nodes_data = [
        {
            "node_id": n.node_id,
            "title": n.title,
            "task_type": n.task_type,
            "config": n.config,
            "retry_policy": n.retry_policy,
            "timeout_seconds": n.timeout_seconds,
            "approval_timeout_seconds": n.approval_timeout_seconds,
        }
        for n in workflow.nodes
    ]
    edges_data = [
        {"from_node": e.from_node, "to_node": e.to_node}
        for e in workflow.edges
    ]
    snapshot = WorkflowVersionHistory(
        workflow_id=workflow.id,
        version=workflow.version,
        name=workflow.name,
        description=workflow.description,
        nodes_json=nodes_data,
        edges_json=edges_data,
        timeout_seconds=workflow.timeout_seconds,
        max_concurrent_tasks=workflow.max_concurrent_tasks,
    )
    db.add(snapshot)
    db.flush()


# ---------------------------------------------------------------------------
# GET /api/workflows/{workflow_id}/versions — version history
# ---------------------------------------------------------------------------


class WorkflowVersionHistoryItem(BaseModel):
    id: str
    version: int
    name: str
    description: Optional[str] = None
    nodes_json: Optional[list[dict]] = None
    edges_json: Optional[list[dict]] = None
    timeout_seconds: Optional[int] = None
    max_concurrent_tasks: Optional[int] = None
    created_at: datetime
    created_by: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkflowVersionListResponse(BaseModel):
    items: list[WorkflowVersionHistoryItem]
    total: int


@router.get("/{workflow_id}/versions", response_model=WorkflowVersionListResponse)
def list_workflow_versions(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    query = (
        db.query(WorkflowVersionHistory)
        .filter(WorkflowVersionHistory.workflow_id == workflow_id)
    )
    total = query.count()
    items = query.order_by(WorkflowVersionHistory.version.desc()).all()
    return WorkflowVersionListResponse(
        items=[
            WorkflowVersionHistoryItem(
                id=str(i.id),
                version=i.version,
                name=i.name,
                description=i.description,
                nodes_json=i.nodes_json,
                edges_json=i.edges_json,
                timeout_seconds=i.timeout_seconds,
                max_concurrent_tasks=i.max_concurrent_tasks,
                created_at=i.created_at,
                created_by=i.created_by,
            )
            for i in items
        ],
        total=total,
    )


# ---------------------------------------------------------------------------
# POST /api/workflows/{workflow_id}/rollback — rollback to a version
# ---------------------------------------------------------------------------


class WorkflowRollbackRequest(BaseModel):
    version: int = Field(..., description="Version number to rollback to")


@router.post("/{workflow_id}/rollback", response_model=WorkflowDefinitionResponse)
def rollback_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowRollbackRequest,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Find the target version in history
    target = (
        db.query(WorkflowVersionHistory)
        .filter(
            WorkflowVersionHistory.workflow_id == workflow_id,
            WorkflowVersionHistory.version == body.version,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail=f"Version {body.version} not found in history")

    # Snapshot current state before rollback
    _snapshot_workflow_version(db, workflow)

    # Apply the historical version's data
    workflow.name = target.name
    workflow.description = target.description
    workflow.timeout_seconds = target.timeout_seconds
    workflow.max_concurrent_tasks = target.max_concurrent_tasks

    # Replace nodes
    for old_node in workflow.nodes:
        db.delete(old_node)
    db.flush()

    if target.nodes_json:
        for n in target.nodes_json:
            node = WorkflowNode(
                id=uuid.uuid4(),
                workflow_id=workflow.id,
                node_id=n["node_id"],
                title=n["title"],
                task_type=n.get("task_type", "action"),
                config=n.get("config"),
                retry_policy=n.get("retry_policy"),
                timeout_seconds=n.get("timeout_seconds"),
                approval_timeout_seconds=n.get("approval_timeout_seconds"),
            )
            db.add(node)

    # Replace edges
    for old_edge in workflow.edges:
        db.delete(old_edge)
    db.flush()

    if target.edges_json:
        for e in target.edges_json:
            edge = WorkflowEdge(
                id=uuid.uuid4(),
                workflow_id=workflow.id,
                from_node=e["from_node"],
                to_node=e["to_node"],
            )
            db.add(edge)

    workflow.version += 1
    workflow.updated_at = datetime.now(timezone.utc)

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="workflow.rollback",
        resource_type="workflow",
        resource_id=str(workflow.id),
        before_json={"version": target.version},
        after_json={"new_version": workflow.version, "rolled_back_from": body.version},
    )
    db.commit()
    db.refresh(workflow)
    return WorkflowDefinitionResponse.model_validate(workflow)


# ---------------------------------------------------------------------------
# DELETE /api/workflows/{workflow_id}
# ---------------------------------------------------------------------------


@router.delete("/{workflow_id}", status_code=204)
def delete_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="workflow.deleted",
        resource_type="workflow",
        resource_id=str(workflow.id),
        before_json={"name": workflow.name},
    )
    db.delete(workflow)
    db.commit()


# ---------------------------------------------------------------------------
# POST /api/workflows/{workflow_id}/runs
# ---------------------------------------------------------------------------


@router.post("/{workflow_id}/runs", response_model=WorkflowRunResponse, status_code=201)
def start_workflow_run(
    workflow_id: uuid.UUID,
    body: WorkflowRunCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Create Run
    run = Run(
        id=uuid.uuid4(),
        runtime_id=workflow.runtime_id,
        workflow_id=workflow.id,
        title=f"Workflow: {workflow.name}",
        status="running",
        input_summary=body.input_summary,
        metadata_json=body.metadata_json,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()

    # Create Task for each node
    for node in workflow.nodes:
        task = Task(
            id=uuid.uuid4(),
            run_id=run.id,
            node_id=node.node_id,
            title=node.title,
            status="pending",
            task_type=node.task_type,
        )
        db.add(task)

    # Create root TraceSpan
    span = TraceSpan(
        id=uuid.uuid4(),
        run_id=run.id,
        span_type="workflow",
        title=f"Workflow {workflow.name} started",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(span)
    db.commit()

    # Advance workflow to start root tasks
    _advance_workflow(db, run)

    db.flush()
    db.refresh(run)
    tasks = db.query(Task).filter(Task.run_id == run.id).all()
    return _build_run_response(run, tasks)


# ---------------------------------------------------------------------------
# GET /api/workflows/{workflow_id}/runs
# ---------------------------------------------------------------------------


@router.get("/{workflow_id}/runs", response_model=WorkflowRunListResponse)
def list_workflow_runs(
    workflow_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    workflow = db.get(WorkflowDefinition, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    query = db.query(Run).filter(Run.workflow_id == workflow_id)
    total = query.count()
    runs = query.order_by(Run.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for run in runs:
        tasks = db.query(Task).filter(Task.run_id == run.id).all()
        items.append(_build_run_response(run, tasks))

    return WorkflowRunListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /api/workflows/{workflow_id}/runs/{run_id}
# ---------------------------------------------------------------------------


@router.get("/{workflow_id}/runs/{run_id}", response_model=WorkflowRunResponse)
def get_workflow_run(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)
    if not run or run.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Run not found")

    tasks = db.query(Task).filter(Task.run_id == run.id).all()
    return _build_run_response(run, tasks)


# ---------------------------------------------------------------------------
# POST /api/workflows/{workflow_id}/runs/{run_id}/advance
# ---------------------------------------------------------------------------


@router.post("/{workflow_id}/runs/{run_id}/advance", response_model=WorkflowRunResponse)
def advance_workflow_run(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    """Manually advance a workflow run. In production, called by scheduler loop."""
    run = db.get(Run, run_id)
    if not run or run.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status != "running":
        raise HTTPException(status_code=400, detail=f"Run is {run.status}, cannot advance")

    check_task_timeouts(db)
    _advance_workflow(db, run)

    db.refresh(run)
    tasks = db.query(Task).filter(Task.run_id == run.id).all()
    return _build_run_response(run, tasks)


# ---------------------------------------------------------------------------
# POST /api/workflows/{workflow_id}/runs/{run_id}/tasks/{task_id}/complete
# ---------------------------------------------------------------------------


@router.post("/{workflow_id}/runs/{run_id}/tasks/{task_id}/complete")
def complete_workflow_task(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    task_id: uuid.UUID,
    body: dict | None = None,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    """Mark a task as completed and advance the workflow."""
    run = db.get(Run, run_id)
    if not run or run.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Run not found")

    task = db.get(Task, task_id)
    if not task or task.run_id != run_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ("running", "waiting_approval"):
        raise HTTPException(status_code=400, detail=f"Task is {task.status}, cannot complete")

    payload = body or {}
    task.status = "completed"
    task.ended_at = datetime.now(timezone.utc)
    task.duration_ms = _compute_duration_ms(task.started_at, task.ended_at)
    if payload.get("metadata_json"):
        task.metadata_json = payload["metadata_json"]

    db.commit()
    _advance_workflow(db, run)

    db.refresh(run)
    tasks = db.query(Task).filter(Task.run_id == run.id).all()
    return _build_run_response(run, tasks)


# ---------------------------------------------------------------------------
# POST /api/workflows/{workflow_id}/runs/{run_id}/tasks/{task_id}/fail
# ---------------------------------------------------------------------------


@router.post("/{workflow_id}/runs/{run_id}/tasks/{task_id}/fail")
def fail_workflow_task(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    task_id: uuid.UUID,
    body: dict | None = None,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    """Mark a task as failed and advance the workflow (may trigger retry)."""
    run = db.get(Run, run_id)
    if not run or run.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Run not found")

    task = db.get(Task, task_id)
    if not task or task.run_id != run_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "running":
        raise HTTPException(status_code=400, detail=f"Task is {task.status}, cannot fail")

    payload = body or {}
    task.status = "failed"
    task.ended_at = datetime.now(timezone.utc)
    task.duration_ms = _compute_duration_ms(task.started_at, task.ended_at)
    task.error_summary = payload.get("error_summary", "Task failed")

    # Check retry policy
    workflow = db.get(WorkflowDefinition, run.workflow_id)
    node_map = {n.node_id: n for n in workflow.nodes} if workflow else {}
    node = node_map.get(task.node_id) if task.node_id else None
    retried = False
    if node:
        policy = _get_retry_policy(node)
        if task.retry_count < policy["max_retries"]:
            task.retry_count += 1
            task.status = "pending"
            task.error_summary = None
            task.ended_at = None
            task.duration_ms = None
            backoff = policy.get("backoff_seconds", 1.0)
            task.next_retry_at = datetime.now(timezone.utc) + timedelta(
                seconds=backoff * (2 ** (task.retry_count - 1))
            )
            retried = True

    db.commit()

    if retried:
        # Build response first (shows "pending" for retry), then advance
        db.refresh(run)
        tasks = db.query(Task).filter(Task.run_id == run.id).all()
        response = _build_run_response(run, tasks)
        _advance_workflow(db, run)
        return response
    else:
        # Advance first (sets run.status), then build response
        _advance_workflow(db, run)
        db.refresh(run)
        tasks = db.query(Task).filter(Task.run_id == run.id).all()
        return _build_run_response(run, tasks)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_run_response(run: Run, tasks: list[Task]) -> WorkflowRunResponse:
    task_responses = [
        WorkflowTaskResponse(
            id=t.id,
            run_id=t.run_id,
            node_id=t.node_id,
            title=t.title,
            status=t.status,
            task_type=t.task_type,
            depends_on_json=t.depends_on_json,
            started_at=t.started_at,
            ended_at=t.ended_at,
            duration_ms=t.duration_ms,
            error_summary=t.error_summary,
            retry_count=t.retry_count,
            metadata_json=t.metadata_json,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]
    return WorkflowRunResponse(
        id=run.id,
        runtime_id=run.runtime_id,
        workflow_id=run.workflow_id,
        title=run.title,
        status=run.status,
        input_summary=run.input_summary,
        output_summary=run.output_summary,
        error_summary=run.error_summary,
        started_at=run.started_at,
        ended_at=run.ended_at,
        duration_ms=run.duration_ms,
        total_tokens=run.total_tokens,
        total_cost=float(run.total_cost) if run.total_cost else None,
        metadata_json=run.metadata_json,
        created_at=run.created_at,
        updated_at=run.updated_at,
        tasks=task_responses,
    )
