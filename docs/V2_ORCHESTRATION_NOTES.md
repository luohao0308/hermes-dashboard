# v2.0/v2.1 Workflow Orchestration — Release Notes

## Capabilities

### Workflow Definitions
- Define multi-step DAG workflows with typed task nodes and dependency edges
- CRUD API: `POST/GET/PUT/DELETE /api/workflows`
- Version auto-increment on update
- Filter by `runtime_id`

### DAG Validation
- Cycle detection via Kahn's algorithm (topological sort) on create/update
- Rejects self-loops, duplicate node_ids, and edges referencing unknown nodes
- Validation runs before persistence — invalid graphs never enter the database

### Background Worker (v2.1)
- PostgreSQL-backed worker (`python -m workers.workflow_worker`) — no external dependencies
- Uses `pg_try_advisory_lock` to prevent duplicate task execution across workers
- Polls PostgreSQL for actionable tasks on configurable interval (default 2s)
- State machine per task:
  ```
  pending → running → completed
                  ↘ failed → pending (retry, with exponential backoff) → running → ...
                  ↘ dead_letter (retries exhausted)
                  ↘ cancelled (workflow timeout)
  ```
- Approval nodes: `pending → waiting_approval → running → completed/failed`
- Worker handles: task pickup, retry with backoff, dead-letter, approval timeout,
  workflow-level timeout, concurrency limits, stale lock recovery
- Run-level completion: when all tasks reach terminal state (`completed`/`failed`/`cancelled`/`dead_letter`), run is marked `completed` or `failed`

### Task Retry Policy (v2.1: enforced with backoff)
- Per-node `retry_policy` JSONB: `{ "max_retries": 3, "backoff_seconds": 1.0 }`
- **Defaults** (when `retry_policy` is null):
  - `max_retries`: 3
  - `backoff_seconds`: 1.0
- On task failure: if `retry_count < max_retries`, task resets to `pending`, `retry_count` increments, and `next_retry_at` is set using exponential backoff: `backoff * (2 ** (retry_count - 1))`
- Worker skips tasks where `next_retry_at > now`
- **Boundary:** `max_retries=0` means no retry — task moves to `dead_letter` immediately

### Task Timeout Policy
- Per-node `timeout_seconds` (integer, nullable)
- **Default:** null (no timeout)
- Worker's `_check_workflow_timeouts()` scans running workflows, compares elapsed time against workflow `timeout_seconds`
- Timed-out workflows: all non-terminal tasks marked `cancelled`, run marked `failed`

### Workflow-Level Timeout (v2.1)
- `workflow_definitions.timeout_seconds` (integer, nullable)
- Worker checks running runs against this deadline on each tick
- On timeout: all pending/running tasks → `cancelled`, run → `failed`

### Approval Timeout (v2.1)
- `workflow_nodes.approval_timeout_seconds` (integer, nullable)
- Worker checks `waiting_approval` tasks against this deadline
- On timeout: approval → `rejected`, task → `failed`

### Human Approval Nodes
- Nodes with `task_type="approval"` create an `Approval` row (status=pending) when dependencies are met
- Task status becomes `waiting_approval`
- Scheduler checks for resolved approvals: `approved` → task becomes `running`, `rejected` → task becomes `failed`
- Approvals are visible via `GET /api/approvals?task_id={task_id}` (Approval Inbox)
- Resolution via existing `POST /api/approvals/{id}/approve` or `/reject`

### Frontend
- **WorkflowList.vue:** Card grid with name, version, node/edge counts, pagination
- **WorkflowDetail.vue:** SVG DAG graph with topological layout, color-coded by task status (completed=green, running=blue, failed=red), nodes table, runs table
- Navigation: Sidebar "Workflows" entry, hash-based routing `#/workflows`

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/workflows` | Create workflow definition (DAG validated) |
| `GET` | `/api/workflows` | List workflows (filter: `runtime_id`) |
| `GET` | `/api/workflows/{id}` | Get workflow with nodes and edges |
| `PUT` | `/api/workflows/{id}` | Update workflow (bumps version) |
| `DELETE` | `/api/workflows/{id}` | Delete workflow (cascade nodes/edges) |
| `POST` | `/api/workflows/{id}/runs` | Start a workflow run |
| `GET` | `/api/workflows/{id}/runs` | List runs for a workflow |
| `GET` | `/api/workflows/{id}/runs/{run_id}` | Get run detail with tasks |
| `POST` | `/api/workflows/{id}/runs/{run_id}/advance` | Manually advance scheduler |
| `POST` | `.../tasks/{task_id}/complete` | Mark task completed |
| `POST` | `.../tasks/{task_id}/fail` | Mark task failed (may trigger retry) |

### Integration with Existing APIs

| Existing API | Integration |
|---|---|
| `GET /api/runs` | Now supports `?workflow_id=` filter to include/exclude workflow runs |
| `GET /api/approvals` | Now supports `?task_id=` filter for workflow approval nodes |
| `GET /api/approvals/{id}/approve` | Works for workflow approvals (Approval has `task_id` FK) |
| `GET /api/approvals/{id}/reject` | Works for workflow approvals |

## Database Schema

New tables: `workflow_definitions`, `workflow_nodes`, `workflow_edges`

Modified tables:
- `runs` — added `workflow_id` (FK → workflow_definitions, nullable, indexed)
- `tasks` — added `node_id` (String, nullable, indexed), `retry_count` (Integer, default 0)
- `approvals` — added `task_id` (FK → tasks, nullable, indexed), `context_json` (JSONB, nullable)

Migrations: `004_workflow_orchestration.py`, `005_approval_task_context.py`

## Known Limitations

1. ~~**No background scheduler:**~~ Resolved in v2.1 — `WorkflowWorker` polls PostgreSQL automatically.
2. ~~**No parallel task execution model:**~~ Resolved in v2.1 — `max_concurrent_tasks` limits parallelism.
3. ~~**No workflow-level timeout:**~~ Resolved in v2.1 — `workflow_definitions.timeout_seconds`.
4. **No conditional branching:** All edges are unconditional. No if/else or switch nodes.
5. **No sub-workflows:** Workflows cannot reference or invoke other workflows.
6. **No workflow versioning rollback:** Version increments on update but there's no way to revert to a previous version.
7. ~~**Approval nodes have no timeout:**~~ Resolved in v2.1 — `workflow_nodes.approval_timeout_seconds`.
8. ~~**Backoff is not enforced:**~~ Resolved in v2.1 — exponential backoff via `next_retry_at`.

## v2.1 Durable Execution (Included)

- Background worker: `python -m workers.workflow_worker` (PostgreSQL + advisory locks)
- Stale lock recovery on worker startup (configurable threshold)
- Step-level retry with exponential backoff (`next_retry_at`)
- Dead-letter queue for permanently failed tasks (`status = 'dead_letter'`)
- Workflow-level timeout (`workflow_definitions.timeout_seconds`)
- Approval timeout (`workflow_nodes.approval_timeout_seconds`)
- Concurrency limits (`workflow_definitions.max_concurrent_tasks`)
- All state changes write `TraceSpan` records for observability
