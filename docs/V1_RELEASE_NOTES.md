# V1 Release Notes

## Summary

v1 delivers a complete, generic AI Workflow Control Plane for observing, governing, auditing, reviewing, and optimizing AI workflows across multiple runtimes.

## Capabilities

### Workflow Observability (v1.0)

- **Run List / Detail** — list and inspect workflow runs from any runtime with status, runtime, failure, and date filters.
- **Trace Timeline** — runtime-agnostic timeline showing model calls, tool calls, handoffs, approvals, errors, and artifacts.
- **Cost / Latency / Token Rollups** — summary cards with aggregated metrics per run.
- **Generic APIs** — `GET/POST /api/runs`, `PATCH /api/runs/{id}`, `POST /api/runs/{id}/spans`, `GET /api/runs/{id}/trace`.

### Tool Governance (v1.1)

- **Risk Model** — tools classified as read, write, execute, network, or destructive.
- **Policy Decisions** — allow, confirm, or deny based on risk level.
- **Approval Inbox** — pending approvals visible in UI, approve/reject with audit trail.
- **Audit Log** — approval decisions, tool calls, and config changes logged.
- **APIs** — `GET /api/tools`, `GET /api/approvals`, `POST /api/approvals/{id}/approve|reject`.

### RCA / Runbook (v1.2)

- **Root Cause Analysis** — generate RCA reports for failed runs, citing trace spans, tool calls, and log excerpts as evidence.
- **Runbook Generation** — auto-generate recovery checkbooks from RCA and trace context.
- **Approval Integration** — high-risk runbook steps enter the approval flow.
- **APIs** — `POST/GET /api/runs/{id}/rca`, `POST/GET /api/runs/{id}/runbook`.

### Connector Framework (v1.3)

- **Unified Event Protocol** — 7 event types: `runtime.upserted`, `run.created`, `run.updated`, `span.created`, `tool_call.created`, `approval.requested`, `artifact.created`.
- **Batch Ingestion** — multiple events in a single `POST /api/connectors/{id}/events` request.
- **Idempotency** — duplicate events deduplicated by `event_id`.
- **Error Resilience** — individual event failures don't block the batch; errors recorded in audit log.
- **Connector Registry** — `GET /api/connectors` lists registered connectors with type, status, and config.

### Eval / Config Optimization (v1.4)

- **Offline Eval** — `POST /api/evals/run` runs deterministic sample-based scoring and persists results.
- **Eval Summary** — `GET /api/evals/summary` aggregates success rate, avg score, latency, cost, tool error rate, handoff/approval counts, with runtime and config version breakdowns and daily trends.
- **Config Versions** — `GET/POST /api/config-versions` for versioned configuration snapshots.
- **Config Compare** — `POST /api/config-versions/compare` shows before/after diffs, score delta, and requires-approval flag.
- **Frontend** — EvalDashboard with summary cards, trend bar chart, breakdown tables; ConfigCompare with version selectors and diff view.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite |
| Backend | Python FastAPI |
| Database | PostgreSQL (primary), managed by Alembic |
| API Schema | Pydantic with `from_attributes` |
| Real-time | SSE (Server-Sent Events) |

## Database Tables (v1)

| Table | Purpose |
|---|---|
| `runtimes` | Registered external AI runtimes |
| `runs` | Complete workflow executions |
| `tasks` | Schedulable units within a run |
| `trace_spans` | Observable events in a run |
| `tool_calls` | Governed tool invocations |
| `approvals` | Human approval events |
| `artifacts` | Workflow outputs |
| `rca_reports` | Root cause analysis reports |
| `runbooks` | Recovery action plans |
| `eval_results` | Evaluation records |
| `config_versions` | Versioned configuration snapshots |
| `connector_configs` | Runtime connector configurations |
| `audit_logs` | Audit trail |

## Known Limitations

- **No webhook signature verification** — connector events are not yet authenticated via HMAC signatures. Add before exposing publicly.
- **No RBAC** — all users have full access. Team permissions planned for v3.0.
- **Eval is offline only** — `POST /api/evals/run` uses hardcoded samples, not live workflow evaluation.
- **No DAG orchestration** — tasks are flat, no dependency graph. Planned for v2.0.
- **No durable execution** — no background worker, retry, or crash recovery. Planned for v2.1.
- **Legacy session APIs still active** — `/api/sessions/*` proxy endpoints remain for backward compatibility with the original Hermes dashboard. These will be deprecated when connector migration is complete.
- **Legacy agent config APIs still active** — `/api/agent/config/*` endpoints remain for agent switching and custom agent management. The generic `/api/config-versions` is the replacement for config versioning.
- **e2e tests not wired** — Playwright e2e tests in `frontend/e2e/` are not configured for vitest and need a separate Playwright runner.

## Upgrade Notes

- Run `alembic upgrade head` to apply migration `003_eval_config_tables.py` (creates `config_versions` table).
- No breaking API changes from v1.3.
- Frontend sidebar now includes "Config Diff" entry for the config comparison page.

## Recommended Test Commands

### Frontend

```bash
cd frontend
npx vitest run           # component tests
npx vue-tsc --noEmit     # type check
```

### Backend (requires PostgreSQL)

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_workflow_test \
  venv/bin/python -m pytest tests/ -v
```

### Backend (without PostgreSQL — skips PG-dependent tests)

```bash
cd backend
venv/bin/python -m pytest tests/ -v \
  --ignore=tests/test_approvals_api.py \
  --ignore=tests/test_connectors_api.py \
  --ignore=tests/test_evals_api.py \
  --ignore=tests/test_repositories.py \
  --ignore=tests/test_run_analysis_api.py \
  --ignore=tests/test_runs_api.py
```

## Next: v2 Workflow Orchestration

The v2 direction adds:

- **Task DAG** — dependency graph between tasks within a run.
- **Conditional Routing** — branch execution based on task outcomes.
- **Retry / Timeout Policies** — configurable per-task retry and timeout.
- **Human Approval Nodes** — approval as a first-class orchestration node.
- **DAG Visualization** — frontend graph showing execution state.

See [ROADMAP.md](AI_WORKFLOW_CONTROL_PLANE_ROADMAP.md) for full v2/v3 plans.
