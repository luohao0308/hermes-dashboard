# v2.0/v2.1 Release Notes — Workflow Orchestration + Durable Execution

## Overview

v2 introduces DAG-based workflow orchestration with durable background execution.
Workflows are defined as directed acyclic graphs (DAGs) of typed task nodes, executed by a PostgreSQL-backed worker with advisory locks, exponential backoff retry, dead-letter handling, and observability via TraceSpans.

## Capabilities

### v2.0 — Workflow Orchestration

- **DAG definitions:** CRUD API for multi-step workflows with typed nodes and dependency edges
- **Validation:** Cycle detection (Kahn's algorithm), self-loop rejection, duplicate node_id rejection, unknown edge rejection
- **State machine:** `pending → running → completed/failed/cancelled`
- **Approval nodes:** `pending → waiting_approval → running → completed/failed`
- **Per-node retry policy:** `{ max_retries, backoff_seconds }` stored as JSONB
- **Per-node timeout:** `timeout_seconds` for task-level deadlines
- **In-process scheduler:** `_advance_workflow()` called on each task status change

### v2.1 — Durable Execution

- **Background worker:** `python -m workers.workflow_worker` — polls PostgreSQL on configurable interval
- **Advisory locks:** `pg_try_advisory_lock` prevents duplicate task execution across workers
- **Stale lock recovery:** Worker releases locks held by dead workers on startup (configurable threshold)
- **Exponential backoff:** `next_retry_at` set using `backoff * (2 ** (retry_count - 1))`
- **Dead-letter queue:** Tasks with exhausted retries get `status = 'dead_letter'`
- **Workflow timeout:** `workflow_definitions.timeout_seconds` — cancels all tasks on deadline
- **Approval timeout:** `workflow_nodes.approval_timeout_seconds` — rejects stale approvals
- **Concurrency limits:** `workflow_definitions.max_concurrent_tasks` caps parallel running tasks
- **TraceSpan observability:** All state changes (timeout, dead-letter, approval) write TraceSpan records

## Quick Start

### 1. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2. Start the worker (in a separate terminal)

```bash
cd backend
python -m workers.workflow_worker
```

Options:
- `--poll-interval 2` — seconds between polls (default: 2)
- `--stale-lock-seconds 300` — threshold for stale lock recovery (default: 300)
- `--worker-id my-worker` — custom worker ID (default: auto-generated)

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/workflows` | Create workflow definition (DAG validated) |
| `GET` | `/api/workflows` | List workflows |
| `GET` | `/api/workflows/{id}` | Get workflow with nodes and edges |
| `PUT` | `/api/workflows/{id}` | Update workflow (bumps version) |
| `DELETE` | `/api/workflows/{id}` | Delete workflow |
| `POST` | `/api/workflows/{id}/runs` | Start a workflow run |
| `GET` | `/api/workflows/{id}/runs` | List runs |
| `GET` | `/api/workflows/{id}/runs/{run_id}` | Get run detail with tasks |
| `POST` | `.../tasks/{task_id}/complete` | Mark task completed |
| `POST` | `.../tasks/{task_id}/fail` | Mark task failed (triggers retry) |

## Database Schema Changes

### Migration 004 — Workflow Orchestration

- New tables: `workflow_definitions`, `workflow_nodes`, `workflow_edges`
- Modified: `runs` (+`workflow_id`), `tasks` (+`node_id`, +`retry_count`), `approvals` (+`task_id`, +`context_json`)

### Migration 005 — Approval Task Context

- `approvals.task_id` FK to tasks
- `approvals.context_json` JSONB

### Migration 006 — Durable Execution

- `tasks.locked_by` (String, nullable) — worker holding the lock
- `tasks.locked_at` (DateTime, nullable) — lock acquisition time
- `tasks.next_retry_at` (DateTime, nullable) — retry eligibility time
- `workflow_definitions.timeout_seconds` (Integer, nullable)
- `workflow_definitions.max_concurrent_tasks` (Integer, nullable)
- `workflow_nodes.approval_timeout_seconds` (Integer, nullable)
- Indexes: `(status, locked_by)`, `(status)`

## Task Status State Machine

```
pending → running → completed
                ↘ failed → pending (retry with backoff) → running → ...
                         ↘ dead_letter (retries exhausted)
                ↘ cancelled (workflow timeout)
pending → waiting_approval → running → completed/failed
                          ↘ failed (approval timeout/rejection)
```

## Testing

### Unit tests (no PostgreSQL required)

```bash
cd backend
python -m pytest tests/test_v2_hardening.py -v
```

30 tests covering: dependency gating, worker pickup, retry backoff, dead-letter, approval creation, stale lock recovery, workflow timeout, approval timeout, run completion, concurrency limits, TraceSpan writes.

### Integration tests (requires PostgreSQL)

```bash
cd backend
export TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/test_db"
python -m pytest tests/test_workflows_api.py tests/test_durable_execution.py -v
```

### Frontend

```bash
cd frontend
npx vue-tsc --noEmit    # type check
npx vitest run           # unit tests
```

## Durable Execution Coverage Matrix

| Behavior | Worker Method | Test Coverage |
|---|---|---|
| Task pickup (deps met) | `_process_pending_tasks` | TestWorkerPickup (3 tests) |
| Skip task (deps not met) | `_process_pending_tasks` | TestDependencyGating (6 tests) |
| Exponential backoff | `_handle_failed_tasks` | TestRetryBackoff (3 tests) |
| Dead-letter (retries exhausted) | `_move_to_dead_letter` | TestDeadLetter (2 tests) |
| Stale lock recovery | `_recover_stale_locks` | TestStaleLockRecovery (2 tests) |
| Workflow timeout | `_check_workflow_timeouts` | TestWorkflowTimeout (2 tests) |
| Approval timeout | `_check_approval_timeouts` | TestApprovalTimeout (2 tests) |
| Approval creation | `_start_approval_task` | TestApprovalCreation (2 tests) |
| Run completion | `_check_run_completion` | TestRunCompletion (4 tests) |
| Concurrency limits | `_process_run_pending` | TestConcurrencyLimits (1 test) |
| Advisory lock | `_try_lock_task` | TestAdvisoryLock (1 test, PG-only) |
| TraceSpan writes | Multiple | TestTraceSpanCoverage (3 tests) |

## Current Limitations

1. **No conditional branching:** All edges are unconditional. No if/else or switch nodes.
2. **No sub-workflows:** Workflows cannot reference or invoke other workflows.
3. **No workflow versioning rollback:** Version increments on update but no revert mechanism.
4. **No multi-worker coordination beyond advisory locks:** Workers don't communicate or share state.
5. **No persistent task queue:** Tasks are polled from PostgreSQL, not a dedicated queue (Redis/RabbitMQ).
6. **No workflow scheduling:** No cron-like recurring workflow triggers.
7. **No parallel map/reduce:** No built-in fan-out/fan-in pattern.

## Upgrade Notes

- Run migration 006 before starting the worker
- Worker is optional — existing API-driven workflow execution continues to work
- Worker and API can run simultaneously — advisory locks prevent conflicts
- `backoff_seconds` is now enforced (was stored but not applied in v2.0)
- `dead_letter` is a new task status — update any status-enum consumers
- `cancelled` is a new task status for workflow timeout scenarios
