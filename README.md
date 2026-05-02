# AI Workflow Control Plane

> 用于观测、治理、审计和复盘 AI 工作流的通用控制平面平台。

[English](#overview) | 中文

## 中文文档

- [当前状态](docs/CURRENT_STATE.zh-CN.md) — 架构、版本、API、运行命令
- [生产部署指南](docs/PRODUCTION_DEPLOYMENT.zh-CN.md) — 生产环境部署步骤
- [国际化方案](docs/I18N_AND_LOCALIZATION_PLAN.md) — i18n 架构与术语表
- [真实场景验收计划](docs/REAL_WORLD_VALIDATION_PLAN.zh-CN.md) — 试点场景、失败案例、验收指标与反馈表

---


<a id="overview"></a>

A generic platform for observing, governing, auditing, and reviewing AI workflows.

## Optimization Release

The v0-v3 platform roadmap is complete. An **Optimization Release** has been finalized on top of v3.0, consolidating productization, security hardening, production operations, and quality improvements. No new features were added — the focus was integration, observability, and operational readiness.

| Area | What Changed |
|------|-------------|
| Navigation | Reorganized into Observe / Govern / Improve / Integrate / Admin / Legacy |
| Legacy deprecation | Old APIs return `Deprecation: true` header; legacy pages grouped under Legacy nav |
| Auth / RBAC / Service tokens | JWT login, 3-role RBAC (admin/operator/viewer), service tokens for machine-to-machine |
| Health / Metrics / Logging | `/health` with DB + worker status matrix, `/api/metrics`, structured logging with correlation IDs |
| Cursor pagination | Runs, Approvals, Audit, Connector failed events support cursor-based pagination |
| Saved filters | localStorage-based, namespaced, sensitive fields stripped |
| Connector replay | Failed connector events can be replayed from the UI |
| Workflow rollback | Workflow definitions support version history and rollback |
| Batch approvals | Approve/reject multiple pending approvals at once |
| Eval guardrail | Recommended eval configs require approval before applying |
| Scheduler observability | Heartbeat files include worker_id and PID; advisory lock mechanism documented |

- Release notes: [docs/OPTIMIZATION_RELEASE_NOTES.md](docs/OPTIMIZATION_RELEASE_NOTES.md)
- Execution plan: [docs/PLATFORM_OPTIMIZATION_EXECUTION_PLAN.md](docs/PLATFORM_OPTIMIZATION_EXECUTION_PLAN.md)
- Current state: [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)

**Next phase (v3.1 candidates):** SSO/OIDC integration, Connector SDK examples, RCA evidence scoring.

## Current Verification Notes

The current Docker-verified build is usable for internal pilot workflows. Core pages load cleanly and the RCA, Runbook, Workflow start, and Approval flows have been verified.

Known non-blocking limitations are tracked in [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md):

- Xiaomi Mimo / MiniMax provider connection requires `MINIMAX_API_KEY`; Docker Compose does not include a real provider key.
- Terminal WebSocket tests have 11 pre-existing Docker/PTTY-related failures.
- Legacy Hermes Tools compatibility tests have 5 pre-existing Dashboard API mock failures.

## What It Is

This is not a single-purpose dashboard, not a single-agent chat app, and not a replacement for any Agent framework. It is a **control plane** that lets you answer:

- What is my AI workflow doing right now?
- Why did it fail?
- Which model, tool, or configuration caused the problem?
- Which tool calls are risky, and did they go through approval?
- What should I do after a failure?
- Did my configuration change actually make things better?

It works across multiple runtimes, models, tools, and human approval gates.

## v1 Capabilities (Complete)

| Module | What It Does |
|---|---|
| **Workflow Observability** | Run list/detail, trace timeline, status/runtime/failure filters, cost/latency/token rollups |
| **Tool Governance** | Risk-level tool policies, allow/confirm/deny decisions, approval inbox |
| **RCA / Runbook** | Root cause analysis with evidence, auto-generated recovery runbooks |
| **Connector Framework** | Unified event ingestion API for any external runtime (7 event types, idempotent, batch) |
| **Eval & Config** | Offline eval scoring, config version tracking, before/after comparison with score delta |
| **Audit Trail** | Approval decisions, config changes, tool calls, and connector errors logged |

## v2.0 Capabilities (Complete)

| Module | What It Does |
|---|---|
| **Workflow Definitions** | Define multi-step DAG workflows with nodes, edges, retry policies, and timeouts |
| **DAG Validation** | Cycle detection via topological sort, rejects invalid edges and duplicate nodes |
| **Lightweight Scheduler** | In-process scheduler that starts ready tasks, handles dependencies, retries, and approvals |
| **Durable Execution** | Advisory-lock task claiming, exponential backoff retries, dead-letter and cancel support |
| **Retry Policy** | Configurable max_retries and backoff_seconds per task node |
| **Timeout Policy** | Configurable timeout_seconds per task node |
| **Human Approval** | Approval nodes block until human approves/rejects via existing Approval model |
| **DAG Visualization** | SVG-based DAG graph with topological layout and status color-coding |

## v3.0 Capabilities (Complete)

| Module | What It Does |
|---|---|
| **Secret Management** | Connector secrets encrypted at rest with Fernet; auto-masked in API responses |
| **Webhook Security** | HMAC-SHA256 signature verification with anti-replay timestamp enforcement |
| **RBAC** | Three roles (admin/operator/viewer) with least-privilege default (viewer) |
| **Audit Logging** | Centralized audit trail for all mutations — connectors, workflows, approvals, evals, users |
| **Users & Teams** | Identity management with role assignment and team organization |
| **Environments** | Dev/staging/prod scoping for runtimes, connectors, and workflows |
| **Retention Policies** | Configurable data lifecycle with dry-run mode and audit-logged cleanup |

## Core Concepts

| Concept | Description |
|---|---|
| **Runtime** | An external AI runtime or automation system (Agents SDK, CI/CD pipeline, code review workflow, etc.) |
| **Run** | A complete AI workflow execution |
| **Task** | A schedulable unit inside a Run |
| **TraceSpan** | An observable event: model call, tool call, handoff, approval, error |
| **ToolCall** | A governed tool invocation with risk level and decision |
| **Approval** | A human approval event for gated actions |
| **Artifact** | A workflow output: report, log excerpt, code diff, RCA, runbook |
| **EvalResult** | An evaluation record for model, prompt, or configuration effectiveness |
| **WorkflowDefinition** | A DAG-based workflow template with task nodes and dependency edges |
| **WorkflowNode** | A task step in a workflow with type, retry policy, and timeout |
| **WorkflowEdge** | A dependency link between workflow nodes |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite |
| Backend | Python FastAPI |
| Database | PostgreSQL (primary) |
| Migrations | Alembic |
| Real-time | SSE (Server-Sent Events) |
| API Schema | Pydantic |

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 20+
- PostgreSQL 14+

### Setup

```bash
# 1. Clone and configure
git clone <repo-url>
cd hermes_free
cp .env.example .env
# Generate a key, then paste it into ENCRYPTION_KEY in .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Start all Docker Compose services
docker compose up -d --build
```

Docker Compose starts PostgreSQL, runs Alembic migrations, starts the backend, frontend, workflow worker, and retention worker. Visit http://localhost:8080.

For local development without containerized backend/frontend:

```bash
# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Run migrations
cd backend
alembic upgrade head

# 3. Start the application
cd ..
./start.sh
```

Visit http://localhost:5173

### Stop

```bash
# Docker Compose services
docker compose down

# Local ./start.sh services
./stop.sh
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `ENVIRONMENT` | No | `development` (default) or `production`. Production requires `ENCRYPTION_KEY` |
| `ENCRYPTION_KEY` | Prod | Fernet key for connector secret encryption. Auto-generated in dev |
| `GITHUB_TOKEN` | No | GitHub Personal Access Token |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |

## API Overview

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/runs` | List workflow runs |
| `GET` | `/api/runs/{id}` | Get run detail with trace |
| `POST` | `/api/runs` | Create a new run |
| `PATCH` | `/api/runs/{id}` | Update run status |
| `POST` | `/api/runs/{id}/spans` | Append trace spans |
| `GET` | `/api/runs/{id}/trace` | Get full trace timeline |
| `GET` | `/api/tools` | List tool calls |
| `GET` | `/api/approvals` | List pending approvals |
| `POST` | `/api/approvals/{id}/approve` | Approve an action |
| `POST` | `/api/approvals/{id}/reject` | Reject an action |
| `GET` | `/api/connectors` | List registered connectors |
| `POST` | `/api/connectors/{id}/events` | Ingest events from runtime |
| `GET` | `/api/evals/summary` | Aggregated eval metrics |
| `GET` | `/api/evals/results` | Paginated eval results |
| `POST` | `/api/evals/run` | Run offline eval and persist |
| `GET` | `/api/config-versions` | List config versions |
| `POST` | `/api/config-versions` | Create config version |
| `POST` | `/api/config-versions/compare` | Compare two config versions |
| `GET` | `/api/workflows` | List workflow definitions |
| `POST` | `/api/workflows` | Create workflow definition |
| `GET` | `/api/workflows/{id}` | Get workflow definition |
| `PUT` | `/api/workflows/{id}` | Update workflow definition |
| `DELETE` | `/api/workflows/{id}` | Delete workflow definition |
| `POST` | `/api/workflows/{id}/runs` | Start workflow run |
| `GET` | `/api/workflows/{id}/runs` | List workflow runs |
| `GET` | `/api/workflows/{id}/runs/{run_id}` | Get workflow run detail |
| `GET` | `/api/users` | List users |
| `POST` | `/api/users` | Create user |
| `GET` | `/api/teams` | List teams |
| `POST` | `/api/teams` | Create team |
| `GET` | `/api/environments` | List environments |
| `POST` | `/api/environments` | Create environment |
| `GET` | `/api/connectors` | List connectors (secrets masked) |
| `POST` | `/api/connectors` | Create connector (secrets encrypted) |

## Project Structure

```
hermes_free/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Application settings
│   ├── database.py          # PostgreSQL connection and session
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic API schemas
│   ├── repositories/        # Data access layer
│   ├── routers/             # API route handlers
│   ├── security/            # Encryption, RBAC, audit, webhook verification
│   ├── workers/             # Background workers (retention cleanup)
│   ├── alembic/             # Database migrations
│   └── connectors/          # Runtime connector adapters
├── frontend/
│   └── src/
│       ├── App.vue
│       ├── components/      # UI components
│       ├── composables/     # Vue composables
│       └── types/           # TypeScript types
├── docs/                    # Project documentation
├── docker-compose.yml
├── start.sh
└── stop.sh
```

## Documentation

- [Product Overview](docs/AI_WORKFLOW_CONTROL_PLANE_OVERVIEW.md) - Why this exists and what it does
- [V1 Release Notes](docs/V1_RELEASE_NOTES.md) - Capabilities, known limitations, and upgrade notes
- [V2 Release Notes](docs/V2_RELEASE_NOTES.md) - v2.0/v2.1 workflow orchestration and durable execution
- [V3 Release Notes](docs/V3_RELEASE_NOTES.md) - Enterprise security, RBAC, audit, and team features
- [Current State](docs/CURRENT_STATE.md) - Architecture, versions, API surface, run commands, known limitations
- [Roadmap](docs/AI_WORKFLOW_CONTROL_PLANE_ROADMAP.md) - Detailed execution plan with task IDs
- [Product Brief](docs/PRODUCT_BRIEF.md) - Product positioning and target users
- [MVP Spec](docs/MVP_SPEC.md) - MVP scope and acceptance criteria
- [Domain Model](docs/DOMAIN_MODEL.md) - Core object model and relationships
- [API Contract](docs/API_CONTRACT.md) - REST API specification
- [Integration Model](docs/INTEGRATION_MODEL.md) - How runtimes connect to the control plane
- [PostgreSQL Schema](docs/POSTGRESQL_SCHEMA.md) - Database schema and migration notes

## License

MIT
