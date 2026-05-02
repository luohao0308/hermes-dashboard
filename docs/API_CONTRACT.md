# API Contract

## Base URL

```
http://localhost:8000/api
```

## Content Type

All request and response bodies use `application/json` unless noted otherwise.

## Common Response Envelope

```json
{
  "data": { ... },
  "error": null,
  "meta": { "total": 100, "page": 1, "limit": 20 }
}
```

Error responses:

```json
{
  "data": null,
  "error": { "code": "NOT_FOUND", "message": "Run not found" },
  "meta": null
}
```

---

## Runtimes

### GET /api/runtimes

List all registered runtimes.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| status | string | all | Filter by status: `active`, `inactive`, `error` |
| page | int | 1 | Page number |
| limit | int | 20 | Items per page (max 100) |

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": "uuid",
      "name": "My Agent Runtime",
      "type": "agent_sdk",
      "status": "active",
      "config_json": {},
      "created_at": "2026-04-30T12:00:00Z",
      "updated_at": "2026-04-30T12:00:00Z"
    }
  ],
  "meta": { "total": 1, "page": 1, "limit": 20 }
}
```

### POST /api/runtimes

Register a new runtime.

**Request Body:**

```json
{
  "name": "My Agent Runtime",
  "type": "agent_sdk",
  "config_json": { "webhook_url": "https://..." }
}
```

**Response:** `201 Created`

---

## Runs

### GET /api/runs

List workflow runs with filters.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| runtime_id | UUID | all | Filter by runtime |
| workflow_id | UUID | all | Filter by workflow definition |
| status | string | all | Filter by status |
| started_after | ISO8601 | - | Filter runs started after this time |
| started_before | ISO8601 | - | Filter runs started before this time |
| page | int | 1 | Page number |
| limit | int | 20 | Items per page (max 100) |
| sort | string | started_at | Sort field |
| order | string | desc | Sort order: `asc`, `desc` |

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": "uuid",
      "runtime_id": "uuid",
      "title": "Code Review PR #42",
      "status": "completed",
      "started_at": "2026-04-30T12:00:00Z",
      "ended_at": "2026-04-30T12:05:00Z",
      "duration_ms": 300000,
      "total_tokens": 15000,
      "total_cost": 0.045,
      "runtime_name": "Code Review Pipeline"
    }
  ],
  "meta": { "total": 50, "page": 1, "limit": 20 }
}
```

### GET /api/runs/{run_id}

Get run detail with summary stats.

**Response:** `200 OK`

```json
{
  "data": {
    "id": "uuid",
    "runtime_id": "uuid",
    "title": "Code Review PR #42",
    "status": "completed",
    "input_summary": "PR #42: Add user authentication",
    "output_summary": "3 issues found, 2 consensus",
    "error_summary": null,
    "started_at": "2026-04-30T12:00:00Z",
    "ended_at": "2026-04-30T12:05:00Z",
    "duration_ms": 300000,
    "total_tokens": 15000,
    "total_cost": 0.045,
    "metadata_json": {},
    "span_count": 12,
    "error_count": 1,
    "tool_call_count": 5
  }
}
```

### POST /api/runs

Create a new run.

**Request Body:**

```json
{
  "runtime_id": "uuid",
  "title": "Code Review PR #42",
  "input_summary": "Review PR #42 for security issues",
  "metadata_json": { "pr_number": 42 }
}
```

**Response:** `201 Created`

### PATCH /api/runs/{run_id}

Update run status or summary fields.

**Request Body:**

```json
{
  "status": "completed",
  "output_summary": "3 issues found",
  "total_tokens": 15000,
  "total_cost": 0.045
}
```

**Response:** `200 OK`

---

## Trace

### POST /api/runs/{run_id}/spans

Append trace spans to a run.

**Request Body:**

```json
{
  "spans": [
    {
      "span_type": "model_call",
      "title": "GPT-4o review",
      "status": "completed",
      "model_name": "gpt-4o",
      "input_summary": "Review PR diff",
      "output_summary": "3 issues found",
      "started_at": "2026-04-30T12:00:00Z",
      "ended_at": "2026-04-30T12:02:00Z",
      "duration_ms": 120000,
      "input_tokens": 5000,
      "output_tokens": 2000,
      "cost": 0.035
    }
  ]
}
```

**Response:** `201 Created`

### GET /api/runs/{run_id}/trace

Get full ordered trace timeline for a run.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| span_type | string | all | Filter by span type |

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": "uuid",
      "run_id": "uuid",
      "task_id": null,
      "parent_span_id": null,
      "span_type": "model_call",
      "title": "GPT-4o review",
      "status": "completed",
      "agent_name": null,
      "model_name": "gpt-4o",
      "tool_name": null,
      "input_summary": "Review PR diff",
      "output_summary": "3 issues found",
      "error_summary": null,
      "started_at": "2026-04-30T12:00:00Z",
      "ended_at": "2026-04-30T12:02:00Z",
      "duration_ms": 120000,
      "input_tokens": 5000,
      "output_tokens": 2000,
      "cost": 0.035,
      "metadata_json": {}
    }
  ]
}
```

---

## Tools

### GET /api/tools

List tool calls across runs.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| run_id | UUID | all | Filter by run |
| risk_level | string | all | Filter by risk level |
| decision | string | all | Filter by decision |
| page | int | 1 | Page number |
| limit | int | 20 | Items per page |

**Response:** `200 OK`

---

## Approvals

### GET /api/approvals

List approval events.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| status | string | pending | Filter by status: `pending`, `approved`, `rejected`, `expired` |
| run_id | UUID | all | Filter by run |
| task_id | UUID | all | Filter by task (workflow approval nodes) |
| page | int | 1 | Page number |
| limit | int | 20 | Items per page |

**Response:** `200 OK`

### POST /api/approvals/{approval_id}/approve

Approve a pending action.

**Request Body:**

```json
{
  "resolved_by": "admin@example.com",
  "resolved_note": "Approved for production deployment"
}
```

**Response:** `200 OK`

### POST /api/approvals/{approval_id}/reject

Reject a pending action.

**Request Body:**

```json
{
  "resolved_by": "admin@example.com",
  "resolved_note": "Too risky for production"
}
```

**Response:** `200 OK`

---

## Connectors

### GET /api/connectors

List registered connectors.

**Response:** `200 OK`

### POST /api/connectors/{connector_id}/events

Ingest events from an external runtime. Accepts a JSON array of events (batch).

**Request Body:**

```json
[
  {
    "event_type": "span.created",
    "event_id": "unique-id-001",
    "run_id": "run_123",
    "timestamp": "2026-04-30T12:00:00Z",
    "payload": {
      "span_type": "tool_call",
      "title": "Run tests",
      "status": "completed",
      "input_summary": "npm run test",
      "output_summary": "42 tests passed"
    }
  }
]
```

**Response:** `200 OK` — includes connector_id and results array with per-event status (accepted, duplicate, error)

---

## Artifacts

### GET /api/runs/{run_id}/artifacts

List artifacts for a run.

**Response:** `200 OK`

### GET /api/artifacts/{artifact_id}

Get a single artifact by ID.

**Response:** `200 OK`

---

## RCA

### POST /api/runs/{run_id}/rca

Generate an RCA report for a failed run.

**Response:** `201 Created`

### GET /api/runs/{run_id}/rca

Get the RCA report for a run.

**Response:** `200 OK`

---

## Runbooks

### POST /api/runs/{run_id}/runbook

Generate a runbook from RCA and trace context.

**Response:** `201 Created`

### GET /api/runs/{run_id}/runbook

Get the runbook for a run.

**Response:** `200 OK`

---

## Evals

### GET /api/evals/summary

Get aggregated eval metrics.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| runtime_id | UUID | all | Filter by runtime |
| config_version | string | all | Filter by config version |
| from_date | string | all | Filter from date (YYYY-MM-DD) |
| to_date | string | all | Filter to date (YYYY-MM-DD) |

**Response:** `200 OK` — includes total, passed, failed, avg_score, avg_latency_ms, avg_cost, tool_error_rate, handoff_count, approval_count, by_runtime, by_config_version, trend

### GET /api/evals/results

List eval results with pagination.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| runtime_id | UUID | all | Filter by runtime |
| config_version | string | all | Filter by config version |
| sample_name | string | all | Filter by sample name |
| success | bool | all | Filter by success |
| limit | int | 50 | Items per page (max 200) |
| offset | int | 0 | Offset |

**Response:** `200 OK`

### POST /api/evals/run

Run offline eval and persist results.

**Request Body:**

```json
{
  "runtime_id": "uuid",
  "config_version": "v2",
  "category": "security"
}
```

**Response:** `200 OK` — includes eval_run_id, mode, count, passed, failed, avg_score, results

---

## Config Versions

### GET /api/config-versions

List config versions.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| runtime_id | UUID | all | Filter by runtime |
| config_type | string | all | Filter by type (workflow, tool_policy, etc.) |
| limit | int | 50 | Items per page |
| offset | int | 0 | Offset |

**Response:** `200 OK`

### POST /api/config-versions

Create a config version.

**Request Body:**

```json
{
  "runtime_id": "uuid",
  "config_type": "workflow",
  "version": "v2",
  "config_json": { "model": "gpt-4", "temperature": 0.7 },
  "requires_approval": false,
  "created_by": "admin"
}
```

**Response:** `200 OK`

If `requires_approval` is true, a pending Approval is also created.

### POST /api/config-versions/compare

Compare two config versions.

**Request Body:**

```json
{
  "before_version_id": "uuid",
  "after_version_id": "uuid"
}
```

**Response:** `200 OK` — includes before, after, score_delta, changes, requires_approval

---

## Workflow Orchestration (v2.0/v2.1)

### Background Worker

Start the durable execution worker:

```bash
python -m workers.workflow_worker --poll-interval 2 --stale-lock-seconds 300
```

The worker polls PostgreSQL for actionable tasks, acquires advisory locks to prevent duplicate execution, and handles: task pickup, retry with exponential backoff, dead-letter, approval timeout, workflow timeout, concurrency limits, and stale lock recovery.

### GET /api/workflows

List workflow definitions with pagination.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `limit` | int | No | Max results (default 20) |
| `offset` | int | No | Pagination offset |

**Response:** `200 OK` — `{ items: WorkflowDefinition[], total: int }`

### POST /api/workflows

Create a new workflow definition.

**Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `runtime_id` | uuid | Yes | Target runtime |
| `name` | string | Yes | Workflow name |
| `description` | string | No | Description |
| `timeout_seconds` | int | No | Workflow-level deadline in seconds (v2.1) |
| `max_concurrent_tasks` | int | No | Max parallel running tasks (v2.1) |
| `nodes` | array | Yes | Task nodes with node_id, title, task_type, retry_policy, timeout_seconds, approval_timeout_seconds |
| `edges` | array | Yes | DAG edges with from_node, to_node |

**Response:** `201 Created` — full WorkflowDefinition with DAG validation

**Validation:** Rejects cycles (Kahn's algorithm), duplicate node_ids, and edges referencing unknown nodes.

### GET /api/workflows/{id}

Get a single workflow definition with nodes and edges.

**Response:** `200 OK` — `WorkflowDefinition`

### PUT /api/workflows/{id}

Update a workflow definition (creates new version).

**Body:** Same as POST.

**Response:** `200 OK` — updated `WorkflowDefinition`

### DELETE /api/workflows/{id}

Delete a workflow definition and its nodes/edges.

**Response:** `204 No Content`

### POST /api/workflows/{id}/runs

Start a new workflow run. Creates Run + Tasks from workflow nodes, respecting DAG dependencies.

**Response:** `201 Created` — `WorkflowRunDetail` with tasks

### GET /api/workflows/{id}/runs

List runs for a workflow.

**Response:** `200 OK` — `{ items: WorkflowRunDetail[], total: int }`

### GET /api/workflows/{id}/runs/{run_id}

Get run detail with tasks.

**Response:** `200 OK` — `WorkflowRunDetail`

### POST /api/workflows/{id}/runs/{run_id}/advance

Advance the workflow scheduler — starts ready tasks, processes completions, handles retries.

**Response:** `200 OK` — updated `WorkflowRunDetail`

---

## v3.0 Enterprise Endpoints

### Users

#### GET /api/users

List users with optional filters.

| Parameter | Type | Default | Description |
|---|---|---|---|
| team_id | UUID | all | Filter by team |
| role | string | all | Filter by role |
| limit | int | 50 | Page size (1-200) |
| offset | int | 0 | Pagination offset |

**Response:** `200 OK` — `{ items: UserResponse[], total: int }`

#### POST /api/users

Create a user. Requires admin role.

**Body:** `{ email, display_name, team_id?, role? }`

**Response:** `201 Created` — `UserResponse`

#### GET /api/users/{id}

Get user detail.

**Response:** `200 OK` — `UserResponse`

#### PUT /api/users/{id}

Update user. Requires admin role.

**Body:** `{ display_name?, role?, team_id?, is_active? }`

**Response:** `200 OK` — `UserResponse`

#### DELETE /api/users/{id}

Delete user. Requires admin role.

**Response:** `204 No Content`

### Teams

#### GET /api/teams

List teams.

**Response:** `200 OK` — `{ items: TeamResponse[], total: int }`

#### POST /api/teams

Create a team. Requires admin role.

**Body:** `{ name, description? }`

**Response:** `201 Created` — `TeamResponse`

#### GET /api/teams/{id}

Get team detail.

**Response:** `200 OK` — `TeamResponse`

#### DELETE /api/teams/{id}

Delete team. Requires admin role.

**Response:** `204 No Content`

### Environments

#### GET /api/environments

List environments.

**Response:** `200 OK` — `{ items: EnvironmentResponse[], total: int }`

#### POST /api/environments

Create an environment. Requires admin role.

**Body:** `{ name, description?, is_default? }`

**Response:** `201 Created` — `EnvironmentResponse`

#### GET /api/environments/{id}

Get environment detail.

**Response:** `200 OK` — `EnvironmentResponse`

#### DELETE /api/environments/{id}

Delete environment. Requires admin role.

**Response:** `204 No Content`

### Connector Management (v3.0 enhancements)

#### POST /api/connectors

Create a connector. Secrets in `config_json` are automatically encrypted.

**Body:** `{ runtime_id, connector_type, display_name, enabled?, config_json?, secret_ref?, environment_id? }`

**Response:** `201 Created` — `ConnectorConfigResponse` (secrets masked)

#### PUT /api/connectors/{id}

Update a connector. Secrets re-encrypted on change.

**Body:** `{ display_name?, enabled?, config_json?, secret_ref?, environment_id? }`

**Response:** `200 OK` — `ConnectorConfigResponse` (secrets masked)

#### DELETE /api/connectors/{id}

Delete connector.

**Response:** `204 No Content`

### RBAC

Roles: `admin` (full access), `operator` (read/write), `viewer` (read-only)

Pass role via `X-User-Role` header (placeholder — SSO integration will set automatically).

---

## SSE Events

### GET /api/events

Server-Sent Events stream for real-time updates.

**Event Types:**

| Event | Description |
|---|---|
| `run.created` | New run created |
| `run.updated` | Run status changed |
| `span.created` | New trace span appended |
| `approval.requested` | New approval requested |
| `approval.resolved` | Approval approved or rejected |

**Format:**

```
event: run.created
data: {"run_id": "uuid", "status": "running", "title": "..."}
```
