# Platform Optimization Release Notes

**Status:** Finalized
**Date:** 2026-05-01

All tasks from `PLATFORM_OPTIMIZATION_EXECUTION_PLAN.md` completed across
phases 0–5. This document summarizes what shipped.

---

## Phase 0: Documentation Reset (OPT-00 to OPT-06)

- Rewrote README, ARCHITECTURE, OPERATIONS, CHECKLIST for v3 control plane
- Created PRODUCT_OPTIMIZATION_OVERVIEW.md and PLATFORM_OPTIMIZATION_EXECUTION_PLAN.md
- Archived legacy Hermès diagrams and old release summaries
- Verified cross-document consistency

## Phase 1: Frontend (OPT-10 to OPT-16)

| ID | What Changed |
|----|-------------|
| OPT-10 | Navigation split into Observe, Govern, Improve, Integrate, Admin, Legacy |
| OPT-11 | Sidebar branding changed from "Code Review" to "AI Control Plane" |
| OPT-12 | Legacy pages (Code Review, Agent Chat, Terminal) grouped under Legacy |
| OPT-13 | App.vue decomposed: navigation config, page shell, workflow composables extracted |
| OPT-14 | Shared LoadingState, EmptyState, ErrorState components |
| OPT-15 | Unified detail page framework (header metrics, timeline, artifacts, audit) |
| OPT-16 | Navigation and core page smoke tests |

## Phase 2: Backend (OPT-20 to OPT-25)

| ID | What Changed |
|----|-------------|
| OPT-20 | Legacy routers extracted from main.py into dedicated legacy router |
| OPT-21 | Legacy APIs return `Deprecation: true` header with Link to replacement |
| OPT-22 | Legacy bridge capabilities documented as connector/legacy adapter patterns |
| OPT-23 | SQLite fallback marked read-only; new writes go to PostgreSQL only |
| OPT-24 | Service layer extraction for workflows, connectors, run_analysis |
| OPT-25 | Legacy API backward-compatibility tests |

## Phase 3: Security (OPT-30 to OPT-35)

| ID | What Changed |
|----|-------------|
| OPT-30 | Auth MVP: local user login with session/JWT, header role restricted to dev/test |
| OPT-31 | RBAC on all write endpoints: POST/PUT/PATCH/DELETE require operator+ role |
| OPT-32 | Service tokens for connector ingestion and worker internal APIs |
| OPT-33 | Rate limiting on connector, auth, RCA, runbook, eval endpoints |
| OPT-34 | Audit UI with actor/resource/action/time filters |
| OPT-35 | Secret leak tests: responses, logs, audit, error paths verified clean |

## Phase 4: Operations (OPT-40 to OPT-45)

| ID | What Changed |
|----|-------------|
| OPT-40 | PRODUCTION_DEPLOYMENT.md with web, scheduler, retention, PostgreSQL setup |
| OPT-41 | /health endpoint with DB, worker, retention, connector ingestion status matrix |
| OPT-42 | Structured logging with request_id, run_id, workflow_id, actor_id correlation |
| OPT-43 | /api/metrics endpoint: runs, worker lag, approvals, connector errors, evals |
| OPT-44 | Backup/restore runbook: PostgreSQL backup, restore, migration rollback |
| OPT-45 | CI matrix: Python 3.9, frontend, backend with PostgreSQL, Alembic empty DB |

## Phase 5: Quality (OPT-50 to OPT-59)

| ID | What Changed |
|----|-------------|
| OPT-50 | Cursor-based pagination on Runs, Approvals, Audit (offset preserved for compat) |
| OPT-51 | Saved filters in localStorage, namespaced, sensitive fields stripped |
| OPT-51b | Audit UI enhancements: quick-filter chips, resource_id search, JSON/CSV export |
| OPT-52 | Workflow version history and rollback to previous versions |
| OPT-54 | Failed connector event replay from UI |
| OPT-55 | Batch approve/reject actions in approval inbox |
| OPT-57 | Eval recommendation guardrail: recommended configs require approval before apply |
| OPT-58 | Connector failed events cursor pagination (offset preserved) |
| OPT-59 | Scheduler heartbeat includes worker_id/PID; advisory lock mechanism documented |

## Not Done

| ID | Reason |
|----|--------|
| OPT-53 | Connector SDK examples — deferred, low risk |
| OPT-56 | RCA evidence score — deferred, needs design |

## Test Coverage

- Frontend: 145/145 tests passing, vue-tsc clean
- Backend: 476 unit/integration tests passing
- Alembic migrations: 001–009 verified

## Key Files

| Area | Files |
|------|-------|
| Navigation | `frontend/src/composables/useNavigation.ts` |
| Shared components | `frontend/src/components/LoadingState.vue`, `EmptyState.vue`, `ErrorState.vue` |
| Cursor pagination | `backend/utils/cursor.py` |
| RBAC | `backend/security/rbac.py` |
| Audit | `backend/security/audit.py` |
| Heartbeat | `backend/utils/heartbeat.py` |
| Health | `backend/routers/health.py` |
| Metrics | `backend/routers/metrics.py` |
| Worker | `backend/workers/workflow_worker.py` |
| Migration 008 | `backend/alembic/versions/008_opt52_54_tables.py` |
| Migration 009 | `backend/alembic/versions/009_make_approval_run_id_nullable.py` |

---

## Intentionally Not Included

These items were explicitly scoped out of the Optimization Release and are
planned for future versions:

| Item | Reason | Target |
|------|--------|--------|
| SSO/OIDC | Design doc exists (`docs/SSO_OIDC_DESIGN.md`); requires IdP integration decisions | v3.1 |
| Full external queue engine | Current PostgreSQL-based scheduler with advisory locks is sufficient for single-process workloads | Future |
| Visual workflow editor | Workflows are API/JSON-defined; no drag-and-drop DAG builder | Future |
| Connector SDK examples | Low risk, deferred (OPT-53) | Future |
| RCA evidence score | Needs design work (OPT-56) | Future |

## Final Verification

| Check | Command | Result |
|-------|---------|--------|
| Frontend typecheck | `cd frontend && npx vue-tsc --noEmit` | Clean |
| Frontend unit tests | `cd frontend && npm run test:unit` | 145/145 pass |
| Backend security tests | `pytest test_v3_enterprise.py test_auth.py test_service_token.py test_secret_leak.py` | 74 pass |
| Backend health/metrics | `pytest test_health.py test_metrics.py test_structured_logging.py` | 31 pass |
| Backend cursor pagination | `pytest test_cursor_pagination.py test_connector_failed_events_cursor.py` | 15 pass |
| Alembic migration | `alembic upgrade head` | 9 migrations (001–009) |
| Document consistency | `grep` for legacy branding in non-archive docs | Only contextual references |
