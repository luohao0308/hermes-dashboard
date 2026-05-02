# PostgreSQL Schema

## Overview

The AI Workflow Control Plane uses PostgreSQL as its primary database. The schema is managed by Alembic migrations.

## Connection

Set the `DATABASE_URL` environment variable:

```bash
DATABASE_URL=postgresql://user:password@host:5432/database_name
```

Default for local development:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_workflow
```

## Tables

| Table | Purpose | Key Relationships |
|---|---|---|
| `runtimes` | Registered external AI runtimes | — |
| `runs` | Complete workflow executions | FK to `runtimes` |
| `tasks` | Schedulable units within a run | FK to `runs`, self-referencing |
| `trace_spans` | Observable events in a run | FK to `runs`, `tasks`, self-referencing |
| `tool_calls` | Governed tool invocations | FK to `runs`, `trace_spans` |
| `approvals` | Human approval events | FK to `runs`, `tool_calls` |
| `artifacts` | Workflow outputs | FK to `runs`, `tasks`, `trace_spans` |
| `rca_reports` | Root cause analysis reports | FK to `runs` |
| `runbooks` | Recovery action plans | FK to `runs` |
| `eval_results` | Evaluation records | FK to `runtimes`, `runs` |
| `config_versions` | Versioned configuration snapshots | FK to `runtimes` |
| `connector_configs` | Runtime connector configurations | FK to `runtimes` |
| `audit_logs` | Audit trail for all actions | — |
| `teams` | Team organization | — |
| `users` | User accounts with RBAC roles | FK to `teams` |
| `environments` | Dev/staging/prod environments | — |
| `retention_policies` | Data lifecycle rules | — |
| `reviews` | PR code review results | — |
| `api_usage` | API cost tracking records | — |
| `budget_limits` | Budget alert thresholds | — |
| `chat_sessions` | Chat session metadata | — |
| `chat_messages` | Chat message history | FK to `chat_sessions` |

## Migration Commands

### Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Create a new migration

```bash
cd backend
alembic revision --autogenerate -m "description of changes"
```

### Apply all migrations

```bash
cd backend
alembic upgrade head
```

### Rollback one migration

```bash
cd backend
alembic downgrade -1
```

### Check current migration status

```bash
cd backend
alembic current
```

### View migration history

```bash
cd backend
alembic history
```

## Docker Compose

Start PostgreSQL locally:

```bash
docker compose up -d postgres
```

This creates a PostgreSQL 16 instance with:
- User: `postgres`
- Password: `postgres`
- Database: `ai_workflow`
- Port: `5432`
- Data persisted in `postgres_data` volume

## Schema Design Notes

- All primary keys are UUIDs.
- Timestamps use `DateTime(timezone=True)` with UTC.
- JSON fields use PostgreSQL `JSONB` for efficient querying.
- Foreign keys enforce referential integrity.
- Indexes on frequently queried columns (`run_id`, `status`, `runtime_id`).
- `created_at` uses `server_default=func.now()`.
- `updated_at` uses `onupdate=func.now()`.

## Modified Tables (v2.0)

### runs — added columns

| Column | Type | Notes |
|---|---|---|
| `workflow_id` | UUID FK | References `workflow_definitions.id`, nullable, indexed |

### tasks — added columns

| Column | Type | Notes |
|---|---|---|
| `node_id` | String(100) | Nullable, indexed. Links task to workflow node |
| `retry_count` | Integer | Non-null, default 0. Incremented on retry |
| `locked_by` | String(100) | Nullable. Worker ID holding the advisory lock |
| `locked_at` | DateTime(tz) | Nullable. When the lock was acquired |
| `next_retry_at` | DateTime(tz) | Nullable. When retry is eligible (exponential backoff) |

Indexes: `(status, locked_by)`, `(status)`

### approvals — added columns

| Column | Type | Notes |
|---|---|---|
| `task_id` | UUID FK | References `tasks.id`, nullable, indexed |
| `context_json` | JSONB | Nullable. Stores workflow context (node_id, workflow_id) |

## v2.0 Workflow Tables

### workflow_definitions

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Primary key |
| `runtime_id` | UUID FK | References `runtimes.id` |
| `name` | String(200) | Workflow name |
| `description` | Text | Nullable |
| `version` | Integer | Auto-incremented on update |
| `timeout_seconds` | Integer | Nullable. Workflow-level deadline (v2.1) |
| `max_concurrent_tasks` | Integer | Nullable. Limits parallel running tasks (v2.1) |
| `created_at` | DateTime(tz) | Server default now() |
| `updated_at` | DateTime(tz) | On update now() |

### workflow_nodes

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Primary key |
| `workflow_id` | UUID FK | References `workflow_definitions.id`, cascade delete |
| `node_id` | String(100) | Unique within workflow (e.g. "fetch", "process") |
| `title` | String(200) | Display name |
| `task_type` | String(50) | "http", "transform", "approval", etc. |
| `config_json` | JSONB | Node-specific configuration |
| `retry_policy_json` | JSONB | `{ max_retries, backoff_seconds }` |
| `timeout_seconds` | Integer | Nullable, task timeout |
| `approval_timeout_seconds` | Integer | Nullable, approval deadline (v2.1) |
| `created_at` | DateTime(tz) | Server default now() |

Index: `(workflow_id, node_id)`

### workflow_edges

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Primary key |
| `workflow_id` | UUID FK | References `workflow_definitions.id`, cascade delete |
| `from_node` | String(100) | Source node_id |
| `to_node` | String(100) | Target node_id |

Index: `(workflow_id, from_node)` and `(workflow_id, to_node)`
