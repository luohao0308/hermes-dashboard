# MVP Specification

## Scope

The MVP (v1.0) delivers **Workflow Observability** -- the ability to list, inspect, and trace AI workflow runs from any runtime.

## In Scope

### Core Data Model

- **Runtime**: Register and list external AI runtimes
- **Run**: Create, list, update, and detail workflow runs
- **TraceSpan**: Append and query trace spans within a run
- **ToolCall**: Record tool invocations with risk classification
- **Artifact**: Store workflow outputs (reports, diffs, logs)

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/runs` | GET | List runs with filters (status, runtime, date range) |
| `/api/runs/{id}` | GET | Get run detail including summary stats |
| `/api/runs` | POST | Create a new run |
| `/api/runs/{id}` | PATCH | Update run status and summary fields |
| `/api/runs/{id}/spans` | POST | Append trace spans to a run |
| `/api/runs/{id}/trace` | GET | Get full ordered trace timeline |
| `/api/runtimes` | GET | List registered runtimes |
| `/api/runtimes` | POST | Register a new runtime |

### Frontend Pages

- **Run List**: Filterable table of all workflow runs with status, runtime, duration, cost columns
- **Run Detail**: Full trace timeline showing spans, tool calls, errors, and artifacts
- **Runtime Overview**: Summary cards for each connected runtime

### Database

- PostgreSQL as primary store
- Alembic migrations for all core tables
- Repository pattern for data access

## Out of Scope (MVP)

- Tool governance and approval flows (v1.1)
- RCA and runbook generation (v1.2)
- Full connector framework (v1.3)
- Eval and config optimization (v1.4)
- Workflow orchestration / DAG (v2.0)
- Durable execution (v2.1)
- Enterprise features (v3.0)

## Acceptance Criteria

1. Users can list workflow runs from any registered runtime.
2. Users can open a run and inspect its full trace timeline.
3. Users can identify the last failed span in a run.
4. Timeline does not depend on connector-specific fields.
5. At least one connector can write Run and TraceSpan data through generic APIs.
6. Backend connects to PostgreSQL via `DATABASE_URL`.
7. Alembic can create the full schema from an empty database.

## Non-Goals

- Multi-tenant isolation
- Visual DAG editor
- Arbitrary shell execution
- Workflow marketplace
- Replacement for Agent frameworks
