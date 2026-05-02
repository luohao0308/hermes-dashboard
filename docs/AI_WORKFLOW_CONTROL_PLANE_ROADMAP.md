# AI Workflow Control Plane Roadmap

## 1. 目标

本项目定位为通用 AI Workflow Control Plane，用来观察、治理、审计、复盘和优化 AI 工作流。

它不是某个特定 Dashboard，不是单 Agent 聊天应用，也不是替代现有 Agent Runtime 的框架。它的职责是把不同 Runtime、模型、工具、任务流水线和人工审批接入同一个控制面，让用户能回答：

- 当前 AI 工作流在做什么？
- 为什么失败？
- 哪个模型、工具、配置或步骤导致了问题？
- 哪些工具调用有风险，是否经过审批？
- 失败后应该怎么处理？
- 配置改动后是否真的变好？

## 2. 技术基线

### Frontend

- Vue 3
- TypeScript
- Vite
- SSE for timeline and status events
- WebSocket for terminal or interactive long-lived channels
- Later versions may add DAG visualization

### Backend

- FastAPI
- PostgreSQL as primary database
- SQLAlchemy or SQLModel for persistence models
- Alembic for migrations
- Pydantic for API schemas
- SSE for live workflow events
- Connector API for external runtime ingestion

### Storage Policy

PostgreSQL is the primary database for production and local development target architecture.

SQLite must not be introduced as a new primary store. It may only remain as a legacy compatibility path or local temporary fallback during migration.

PostgreSQL stores:

- runtimes
- runs
- tasks
- trace spans
- tool calls
- approvals
- artifacts
- RCA reports
- runbooks
- eval results
- connector configs
- audit logs

## 3. Core Domain Model

### Runtime

An external AI runtime or automation system that emits workflow events.

Examples:

- OpenAI Agents SDK workflow
- self-hosted agent runtime
- GitHub code review pipeline
- CI/CD automation workflow
- data analysis workflow
- customer support quality workflow
- custom webhook connector

### Run

A complete AI workflow execution.

Status:

```text
queued -> running -> waiting_approval -> completed
                                -> failed
                                -> cancelled
```

Required fields:

- id
- runtime_id
- title
- status
- input_summary
- output_summary
- error_summary
- started_at
- ended_at
- duration_ms
- total_tokens
- total_cost
- metadata_json

### Task

A schedulable unit inside a Run.

Status:

```text
pending -> ready -> running -> blocked -> completed
                                      -> failed
                                      -> skipped
```

### TraceSpan

An observable event or operation inside a Run.

Span types:

- model_call
- tool_call
- handoff
- approval
- system_event
- error
- artifact
- eval

### ToolCall

A governed tool invocation.

Risk levels:

- read
- write
- execute
- network
- destructive

Decision values:

```text
allow | confirm | deny
```

### Approval

A human approval event for gated workflow actions.

Status:

```text
pending -> approved
        -> rejected
        -> expired
```

### Artifact

A workflow output or evidence item.

Types:

- markdown
- json
- code_diff
- log_excerpt
- report
- runbook
- rca

### EvalResult

An evaluation record for a runtime, model, prompt, agent config, tool policy, or workflow version.

Metrics:

- success_rate
- latency_ms
- cost
- token_usage
- tool_error_rate
- handoff_count
- approval_count
- failure_category

## 4. Version Roadmap

### Version 0.1: Documentation and Product Positioning

Goal: make the project understandable and executable by future AIs and developers.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V0.1-01 | Rewrite README as AI Workflow Control Plane | Done | P0 | Updated README |
| V0.1-02 | Add `docs/PRODUCT_BRIEF.md` | Done | P0 | Product brief |
| V0.1-03 | Add `docs/MVP_SPEC.md` | Done | P0 | MVP scope |
| V0.1-04 | Add `docs/DOMAIN_MODEL.md` | Done | P0 | Domain model |
| V0.1-05 | Add `docs/API_CONTRACT.md` | Done | P0 | API contract |
| V0.1-06 | Add `docs/INTEGRATION_MODEL.md` | Done | P0 | Runtime integration model |
| V0.1-07 | Move specific legacy integrations into connector examples | Done | P0 | Connector docs |
| V0.1-08 | Archive old phase-specific planning docs | Done | P1 | `docs/archive/` |

Acceptance criteria:

- README no longer positions the project as a single-purpose dashboard or single Agent app.
- Documentation names Runtime, Run, Task, TraceSpan, ToolCall, Approval, Artifact as core objects.
- Old direction documents are either marked historical or moved to archive.
- Human overview and execution roadmap describe the same product direction.

### Version 0.2: PostgreSQL Infrastructure

Goal: build the production-grade data foundation.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V0.2-01 | Introduce PostgreSQL as primary database | Done | P0 | `DATABASE_URL` based connection |
| V0.2-02 | Add database configuration layer | Done | P0 | settings and session factory |
| V0.2-03 | Add Alembic migration system | Done | P0 | migration directory |
| V0.2-04 | Create initial PostgreSQL schema | Done | P0 | first migration |
| V0.2-05 | Abstract existing trace storage behind repository interfaces | Done | P0 | repository layer |
| V0.2-06 | Migrate chat, RCA, runbook, trace, approval writes to PostgreSQL | Done | P0 | new persistence path |
| V0.2-07 | Add Docker Compose PostgreSQL service | Done | P1 | local database service |
| V0.2-08 | Add test database setup | Done | P1 | isolated test DB |
| V0.2-09 | Document migration and rollback commands | Done | P1 | operations docs |

Acceptance criteria:

- Backend reads `DATABASE_URL` and connects to PostgreSQL.
- Alembic can create the full schema from an empty database.
- Tests can run against an isolated PostgreSQL database.
- New workflow writes go to PostgreSQL.
- SQLite is not used as the primary runtime data store.

### Version 1.0: Workflow Observability MVP

Goal: let users see all workflow runs and trace what happened.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V1.0-01 | Implement `GET /api/runs` | Done | P0 | Run list API |
| V1.0-02 | Implement `GET /api/runs/{run_id}` | Done | P0 | Run detail API |
| V1.0-03 | Implement `POST /api/runs` | Done | P0 | Create run API |
| V1.0-04 | Implement `PATCH /api/runs/{run_id}` | Done | P0 | Update run API |
| V1.0-05 | Implement `POST /api/runs/{run_id}/spans` | Done | P0 | Append span API |
| V1.0-06 | Implement `GET /api/runs/{run_id}/trace` | Done | P0 | Trace API |
| V1.0-07 | Build generic Run list page | Done | P0 | UI page |
| V1.0-08 | Build generic Run detail page | Done | P0 | UI page |
| V1.0-09 | Generalize Trace Timeline | Done | P0 | Runtime-agnostic timeline |
| V1.0-10 | Add status, runtime, failure, date filters | Done | P1 | UI filters |
| V1.0-11 | Add cost, latency, token rollups | Done | P1 | summary cards |

Acceptance criteria:

- Users can list workflow runs from any runtime.
- Users can open a run and inspect its timeline.
- Users can identify the last failed span.
- Timeline does not depend on connector-specific fields.
- At least one connector can write Run and TraceSpan data through generic APIs.

### Version 1.1: Tool Governance and Approval

Goal: control high-risk tool calls inside AI workflows.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V1.1-01 | Normalize tool risk model | Done | P0 | risk enum |
| V1.1-02 | Add tool policy tables | Done | P0 | migration |
| V1.1-03 | Add approval tables | Done | P0 | migration |
| V1.1-04 | Implement `GET /api/tools` | Done | P0 | tool API |
| V1.1-05 | Implement `GET /api/approvals` | Done | P0 | approval inbox API |
| V1.1-06 | Implement `POST /api/approvals/{id}/approve` | Done | P0 | approve API |
| V1.1-07 | Implement `POST /api/approvals/{id}/reject` | Done | P0 | reject API |
| V1.1-08 | Build Approval Inbox UI | Done | P0 | UI page |
| V1.1-09 | Show approval spans in timeline | Done | P1 | timeline nodes |
| V1.1-10 | Write approval decisions to audit log | Done | P1 | audit events |

Acceptance criteria:

- Destructive tools cannot execute silently.
- Confirm-policy tools create pending approvals.
- Approve and reject actions are persisted and auditable.
- Trace timeline shows why a tool call was allowed, denied, or blocked for confirmation.

### Version 1.2: RCA and Runbook

Goal: turn failed runs into evidence-based diagnosis and actionable recovery steps.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V1.2-01 | Define generic RCA schema | Done | P0 | schema |
| V1.2-02 | Persist RCA reports in PostgreSQL | Done | P0 | repository |
| V1.2-03 | Implement `POST /api/runs/{run_id}/rca` | Done | P0 | generate RCA API |
| V1.2-04 | Implement `GET /api/runs/{run_id}/rca` | Done | P0 | read RCA API |
| V1.2-05 | Define generic Runbook schema | Done | P0 | schema |
| V1.2-06 | Persist Runbooks in PostgreSQL | Done | P0 | repository |
| V1.2-07 | Implement `POST /api/runs/{run_id}/runbook` | Done | P0 | generate runbook API |
| V1.2-08 | Implement `GET /api/runs/{run_id}/runbook` | Done | P0 | read runbook API |
| V1.2-09 | Show RCA on Run detail page | Done | P0 | UI section |
| V1.2-10 | Show Runbook on Run detail page | Done | P0 | UI section |
| V1.2-11 | Export RCA and Runbook as Markdown artifacts | Done | P1 | artifact export |

Acceptance criteria:

- A failed run can produce a root cause summary.
- RCA cites TraceSpan, ToolCall, log excerpt, or artifact evidence.
- Runbook produces concrete check and recovery steps.
- Any high-risk runbook action enters the approval flow.

### Version 1.3: Connector Framework

Goal: make the platform runtime-agnostic.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V1.3-01 | Define connector event protocol | Done | P0 | docs and schemas |
| V1.3-02 | Implement connector registry | Done | P0 | registry service |
| V1.3-03 | Implement `GET /api/connectors` | Done | P0 | connector API |
| V1.3-04 | Implement `POST /api/connectors/{id}/events` | Done | P0 | event ingestion API |
| V1.3-05 | Convert legacy dashboard-specific proxy logic into connector example | Done | P0 | connector adapter |
| V1.3-06 | Convert GitHub review pipeline into connector example | Done | P1 | connector adapter |
| V1.3-07 | Document custom connector payloads | Done | P0 | connector guide |
| V1.3-08 | Add runtime and connector filters to Run UI | Done | P1 | UI filters |

Minimum event payload:

```json
{
  "event_type": "span.created",
  "runtime_id": "custom-runtime",
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
```

Acceptance criteria:

- External systems can create runs and append trace spans through HTTP.
- At least two runtime sources can appear in the same Run list.
- Core UI does not depend on connector-specific fields.
- Connector errors are visible as spans or audit events.

### Version 1.4: Eval and Configuration Optimization

Goal: make workflow improvements measurable.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V1.4-01 | Define EvalResult schema | Done | P0 | schema |
| V1.4-02 | Persist evals in PostgreSQL | Done | P0 | repository |
| V1.4-03 | Implement `GET /api/evals/summary` | Done | P0 | summary API |
| V1.4-04 | Implement `POST /api/evals/run` | Done | P0 | eval runner API |
| V1.4-05 | Add configuration version records | Done | P1 | config history table |
| V1.4-06 | Show configuration comparison in UI | Done | P1 | UI section |
| V1.4-07 | Show success, cost, latency, tool error trends | Done | P1 | trend charts |
| V1.4-08 | Backend API tests + frontend component tests | Done | P0 | test coverage |

### Version 1.5: Stabilization and Release Hardening

Goal: ensure v1 is production-ready before entering v2 orchestration.

| ID | Task | Status | Priority | Output |
|---|---|---|---:|---:|---|
| V1.5-01 | Update roadmap v0.1–v1.4 status | Done | P0 | roadmap |
| V1.5-02 | Update OVERVIEW.md progress | Done | P0 | overview |
| V1.5-03 | Tighten README legacy section, highlight v1 capabilities | Done | P0 | README |
| V1.5-04 | Unify frontend navigation for all v1 modules | Done | P0 | Sidebar |
| V1.5-05 | Fix pre-existing test assertion mismatch | Done | P0 | green tests |
| V1.5-06 | Full frontend test suite + vue-tsc | Done | P0 | green CI |
| V1.5-07 | Backend tests + document PG test command | Done | P0 | test docs |
| V1.5-08 | Document legacy API compatibility paths | Done | P1 | compat doc |
| V1.5-09 | Verify docs consistency | Done | P1 | aligned docs |
| V1.5-10 | Generate V1_RELEASE_NOTES.md | Done | P0 | release notes |

Acceptance criteria:

- All v0.1–v1.4 tasks marked Done in roadmap.
- All frontend tests pass, vue-tsc clean.
- No pre-existing test failures.
- Legacy API compatibility paths documented.
- Release notes cover v1 capabilities, known limitations, and v2 direction.

- Users can compare workflow or runtime configuration versions.
- Eval results include success, latency, cost, token usage, and failure category.
- High-risk configuration changes cannot silently become defaults.

### Version 2.0: Workflow Orchestration

Goal: evolve from observation to lightweight orchestration.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V2.0-01 | Design workflow definition schema | Done | P0 | schema |
| V2.0-02 | Add Task DAG data model | Done | P0 | tables |
| V2.0-03 | Validate DAG cycles | Done | P0 | validation logic |
| V2.0-04 | Implement lightweight scheduler | Done | P0 | scheduler service |
| V2.0-05 | Add task retry policy | Done | P1 | retry config |
| V2.0-06 | Add task timeout policy | Done | P1 | timeout config |
| V2.0-07 | Add human approval node | Done | P1 | orchestration node |
| V2.0-08 | Show DAG run graph in frontend | Done | P1 | DAG UI |

Acceptance criteria:

- Users can define a multi-step workflow.
- Tasks respect declared dependencies.
- Failed tasks can retry, fail, or block the workflow.
- DAG visualization shows current execution state.

### Version 2.1: Durable Execution

Goal: support more reliable long-running workflows.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V2.1-01 | Introduce background worker model | Done | P0 | worker process |
| V2.1-02 | Evaluate ARQ, Celery, Dramatiq, Temporal, Hatchet | Done | P0 | decision record |
| V2.1-03 | Persist task execution state | Done | P0 | task state table |
| V2.1-04 | Recover tasks after worker restart | Done | P0 | recovery logic |
| V2.1-05 | Support step-level retry | Done | P1 | retry engine |
| V2.1-06 | Support dead-letter queue | Done | P1 | failed job handling |

Recommended default before adopting a heavier orchestrator:

```text
PostgreSQL + lightweight worker + advisory locks
```

### Version 3.0: Enterprise and Team Features

Goal: support team production use.

| ID | Task | Status | Priority | Output |
|---|---|---:|---:|---|
| V3.0-01 | Add users and teams | Done | P1 | identity tables |
| V3.0-02 | Add RBAC permissions | Done | P1 | permission model |
| V3.0-03 | Add connector secret management | Done | P0 | encrypted secret store |
| V3.0-04 | Complete audit log coverage | Done | P0 | audit system |
| V3.0-05 | Add dev/staging/prod environments | Done | P1 | environment model |
| V3.0-06 | Add webhook signature verification | Done | P0 | connector security |
| V3.0-07 | Add retention policies | Done | P1 | data lifecycle |
| V3.0-08 | Add SSO/OIDC | Done (design doc) | P2 | auth integration |

## 5. PostgreSQL Schema Draft

### runtimes

```text
id
name
type
status
config_json
created_at
updated_at
```

### runs

```text
id
runtime_id
title
status
input_summary
output_summary
error_summary
started_at
ended_at
duration_ms
total_tokens
total_cost
metadata_json
created_at
updated_at
```

### tasks

```text
id
run_id
parent_task_id
title
status
task_type
depends_on_json
started_at
ended_at
duration_ms
error_summary
metadata_json
created_at
updated_at
```

### trace_spans

```text
id
run_id
task_id
parent_span_id
span_type
title
status
agent_name
model_name
tool_name
input_summary
output_summary
error_summary
started_at
ended_at
duration_ms
input_tokens
output_tokens
cost
metadata_json
created_at
```

### tool_calls

```text
id
run_id
span_id
tool_name
risk_level
decision
status
input_json
output_json
error_summary
created_at
updated_at
```

### approvals

```text
id
run_id
tool_call_id
status
reason
requested_by
resolved_by
resolved_note
expires_at
created_at
resolved_at
```

### artifacts

```text
id
run_id
task_id
span_id
artifact_type
title
content_text
content_json
storage_url
created_at
```

### rca_reports

```text
id
run_id
root_cause
category
confidence
evidence_json
next_actions_json
created_at
```

### runbooks

```text
id
run_id
severity
summary
steps_json
markdown
created_at
updated_at
```

### eval_results

```text
id
runtime_id
run_id
config_version
sample_name
success
score
latency_ms
cost
metrics_json
created_at
```

### connector_configs

```text
id
runtime_id
connector_type
display_name
enabled
config_json
secret_ref
created_at
updated_at
```

### audit_logs

```text
id
actor_type
actor_id
action
resource_type
resource_id
before_json
after_json
created_at
```

### workflow_definitions (v2.0)

```text
id
runtime_id
name
description
version
created_at
updated_at
```

### workflow_nodes (v2.0)

```text
id
workflow_id
node_id
title
task_type
config_json
retry_policy_json
timeout_seconds
created_at
```

### workflow_edges (v2.0)

```text
id
workflow_id
from_node
to_node
```

## 6. Documentation Work

### Add

| Document | Priority | Purpose |
|---|---:|---|
| `docs/AI_WORKFLOW_CONTROL_PLANE_OVERVIEW.md` | P0 | Human-readable overview |
| `docs/AI_WORKFLOW_CONTROL_PLANE_ROADMAP.md` | P0 | AI/developer execution plan |
| `docs/PRODUCT_BRIEF.md` | P0 | Product positioning and users |
| `docs/MVP_SPEC.md` | P0 | MVP scope and acceptance |
| `docs/DOMAIN_MODEL.md` | P0 | Object model |
| `docs/API_CONTRACT.md` | P0 | API contract |
| `docs/INTEGRATION_MODEL.md` | P0 | Runtime integration model |
| `docs/POSTGRESQL_SCHEMA.md` | P0 | Database schema and migration notes |
| `docs/CONNECTOR_GUIDE.md` | P1 | Connector implementation guide |

### Rewrite

| Document | Action |
|---|---|
| `README.md` | Rewrite around the generic AI Workflow Control Plane direction |
| `docs/ARCHITECTURE.md` | Rewrite around Control Plane API, PostgreSQL, connector registry, and generic UI |
| `docs/OPERATIONS.md` | Add PostgreSQL, migration, connector, and secret-management operations |
| `docs/CHECKLIST.md` | Add migration, connector contract, approval flow, and audit checks |

### Archive

| Document | Reason |
|---|---|
| phase-specific legacy plans | historical direction, too narrow |
| SDK-specific roadmap | should merge into generic roadmap |
| integration notes unrelated to core control plane | keep as integration examples, not product center |

## 7. Progress Summary

| Version | Name | Current Progress | Target |
|---|---|---:|---:|
| 0.1 | Documentation and positioning | 100% | 100% |
| 0.2 | PostgreSQL infrastructure | 100% | 100% |
| 1.0 | Workflow Observability MVP | 100% | 100% |
| 1.1 | Tool Governance | 100% | 100% |
| 1.2 | RCA / Runbook | 100% | 100% |
| 1.3 | Connector Framework | 100% | 100% |
| 1.4 | Eval / Config Optimization | 100% | 100% |
| 1.5 | Stabilization / Release Hardening | 100% | 100% |
| 2.0 | Workflow Orchestration | 5% | 100% |
| 2.1 | Durable Execution | 100% | 100% |
| 3.0 | Enterprise Features | 0% | 100% |

## 8. Recommended Implementation Order

1. Finish documentation and product positioning.
2. Add PostgreSQL schema, migrations, and database configuration.
3. Migrate trace, RCA, runbook, approval, artifact, and eval storage to PostgreSQL.
4. Introduce generic Run and Trace APIs.
5. Generalize frontend pages around Runtime, Run, TraceSpan, ToolCall, Approval, and Artifact.
6. Add connector framework and move legacy integrations behind connectors.
7. Add eval/config optimization.
8. Add DAG orchestration and durable execution only after MVP is stable.

The first implementation stage should follow this priority:

```text
visible -> inspectable -> governable -> recoverable -> extensible
```

## 9. Global Acceptance Criteria

### Product

- The project is described as a generic AI Workflow Control Plane.
- Documentation does not position a single runtime or single Agent as the product center.
- New contributors can understand what to build without re-deciding the product direction.

### Technical

- PostgreSQL is the primary database.
- Alembic can create the schema from an empty database.
- Runtime, Run, Task, TraceSpan, ToolCall, Approval, Artifact, and EvalResult are first-class concepts.
- At least one connector can ingest workflow data through generic APIs.
- Frontend can show runs from more than one runtime source.

### Security

- Destructive tool calls require approval.
- Approvals are audit logged.
- Connector webhooks should support signature verification before production use.
- Secrets are not stored in plaintext JSON config fields.

### Functional

- Failed runs can produce RCA.
- RCA cites evidence.
- Runbooks can be generated from RCA and trace context.
- High-risk runbook actions require approval.
- Eval data can compare configuration effectiveness.

## 10. Explicit Non-Goals for MVP

Do not build these in MVP:

- enterprise RBAC
- multi-tenant isolation
- full visual DAG editor
- arbitrary shell auto-execution
- workflow marketplace
- replacement for existing Agent frameworks
- large-scale distributed scheduler

These belong to v2 or v3.

## 11. Instructions for Future AI Implementers

- Do not keep positioning the project as a specific system dashboard.
- Do not make Agent the only core object.
- Use Runtime, Run, Task, TraceSpan, ToolCall, Approval, Artifact, and EvalResult as the core vocabulary.
- New primary persistence must target PostgreSQL.
- Do not introduce new SQLite primary stores.
- Existing features may remain, but they should move behind connector or compatibility layers.
- Stabilize documentation and API contracts before large code rewrites.

