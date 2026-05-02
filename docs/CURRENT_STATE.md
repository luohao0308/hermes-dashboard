# Current State — AI Workflow Control Plane

**Last updated:** 2026-05-02
**Status:** Stabilized for internal pilot (Optimization Release on top of v3.0)

## Optimization Release

The Optimization Release is finalized. All planned productization, security hardening, production operations, and quality improvement tasks are complete. See `docs/OPTIMIZATION_RELEASE_NOTES.md` for full details.

Completed OPT IDs: OPT-00 through OPT-06, OPT-10 through OPT-16, OPT-20 through OPT-25, OPT-30 through OPT-35, OPT-40 through OPT-45, OPT-50 through OPT-51b, OPT-52, OPT-54, OPT-55, OPT-57, OPT-58, OPT-59, OPT-60.

Deferred (low risk): OPT-53 (Connector SDK examples), OPT-56 (RCA evidence score).

### v3.1 Candidates

| Item | Scope |
|------|-------|
| SSO/OIDC | Design doc exists (`docs/SSO_OIDC_DESIGN.md`). Not in current release. |
| Connector SDK examples | Python/Node examples with signature generation |
| RCA evidence score | Quality indicator for root cause analysis |

## Resolved Productization Risks

| Risk | Status |
|---|---|
| Mixed navigation and legacy pages | Done (OPT-10/11/12) |
| `frontend/src/App.vue` is too large | Done (OPT-13) |
| `backend/main.py` still hosts legacy endpoints | Done (OPT-20/21) |
| Old docs still exist | Done (OPT-00–06) |
| Production operations are incomplete | Done (OPT-40–45) |

## Architecture

```
┌─────────────┐     HTTP/WS      ┌──────────────┐     SQLAlchemy     ┌────────────┐
│  Vue 3 SPA  │ ◄──────────────► │  FastAPI App  │ ◄────────────────► │ PostgreSQL │
│  (Vite)     │  SSE for events  │  (backend/)   │  Alembic migrations│  (primary) │
└─────────────┘                  └──────┬───────┘                     └────────────┘
                                        │
                               ┌────────┴────────┐
                               │  Background      │
                               │  Workers         │
                               │  - Scheduler     │
                               │  - Retention     │
                               └─────────────────┘
```

## Completed Versions

| Version | Status | Key Deliverables |
|---------|--------|-----------------|
| v0.1 | Done | Project framing, docs, connector protocol |
| v0.2 | Done | PostgreSQL migration, Alembic, repository layer |
| v1.0 | Done | Run/trace/tool-call APIs, Vue dashboard |
| v1.1 | Done | Tool governance, approval inbox, RCA/runbook |
| v1.2 | Done | Eval scoring, config versioning, comparison |
| v1.3 | Done | Connector framework (7 event types, idempotent, batch) |
| v1.4 | Done | Dashboard polish, knowledge search, SSE |
| v1.5 | Done | Alerting, review dashboard |
| v2.0 | Done | Workflow definitions, DAG validation, scheduler, retry/timeout |
| v2.1 | Done | Durable execution: advisory locks, dead-letter, cancel, exponential backoff |
| v3.0 | Done | Enterprise: encryption, webhook security, RBAC, audit, users/teams, environments, retention |
| Optimization Release | Done | Navigation reorg, legacy deprecation, cursor pagination, saved filters, connector replay, workflow rollback, batch approvals, eval guardrail, scheduler observability |

## Database

- **Engine:** PostgreSQL 16 (via Docker Compose or external)
- **Migrations:** 9 Alembic versions (`001` through `009`)
- **Tables:** 23 (see `docs/POSTGRESQL_SCHEMA.md`)
- **Connection:** `DATABASE_URL` env var (default: `postgresql://postgres:postgres@localhost:5432/ai_workflow`)

## API Surface

~60 REST endpoints across these routers:

| Router | Prefix | Auth |
|--------|--------|------|
| auth | `/api/auth` | JWT login, rate-limited |
| runs | `/api/runs` | None |
| tasks | `/api/tasks` | None |
| tools | `/api/tools` | None |
| approvals | `/api/approvals` | RBAC (operator for approve/reject) |
| connectors | `/api/connectors` | RBAC (operator for CRUD), service token or webhook on events |
| evals | `/api/evals` | RBAC (operator for run), rate-limited |
| workflows | `/api/workflows` | RBAC (operator for writes) |
| run-analysis | `/api/runs/{id}/rca`, `…/runbook` | RBAC (operator), rate-limited |
| runtimes | `/api/runtimes` | RBAC (operator for create) |
| cost | `/api/cost` | RBAC (operator for budget) |
| users | `/api/users` | RBAC (admin for writes) |
| teams | `/api/teams` | RBAC (admin for writes) |
| environments | `/api/environments` | RBAC (admin for writes) |
| config-versions | `/api/config-versions` | RBAC (operator for create) |
| chat | `/api/chat` | None |
| health | `/health` | None |
| metrics | `/api/metrics` | None |

Auth: JWT tokens via `POST /api/auth/login`. RBAC via `require_role()` dependency — extracts role from JWT in production, falls back to `X-User-Role` header in dev/test. Service tokens accepted via `X-Service-Token` header or `Authorization: Bearer <token>`.

## Security

| Feature | Implementation |
|---------|---------------|
| Authentication | JWT (HS256) via `POST /api/auth/login`, passlib/bcrypt password hashing |
| Service tokens | `SERVICE_TOKENS` env var (comma-separated), accepted via `X-Service-Token` or `Authorization: Bearer` |
| Secret encryption | Fernet symmetric (`cryptography` package), key from `ENCRYPTION_KEY` env var |
| Webhook verification | HMAC-SHA256 with anti-replay (300s tolerance) |
| RBAC | 3 roles: admin (full), operator (read/write), viewer (read-only). JWT-extracted in production, header fallback in dev/test |
| Audit logging | `write_audit_log()` on all mutations, actor_type=service for service token calls |
| Rate limiting | slowapi on auth login (10/min), connector events (60/min), RCA/runbook (20/min), eval run (10/min) |
| Secret leak protection | `mask_config_secrets()` in API responses, `encrypt_config_secrets()` before storage |
| Production mode | `ENVIRONMENT=production` requires `ENCRYPTION_KEY` or app refuses to start; no header-only auth |

## Background Workers

| Worker | Purpose | Default Interval |
|--------|---------|-----------------|
| Scheduler | Claims ready tasks, starts them, handles retries | 5s |
| Retention | Deletes records past retention_days | 3600s (1 hour) |

Run retention worker:
```bash
cd backend
python -m workers.retention_worker                  # production
python -m workers.retention_worker --dry-run        # preview only
python -m workers.retention_worker --poll-interval 1800  # every 30 min
```

## Tests

**Backend:** `cd backend && python -m pytest tests/ -v`
- `test_v3_enterprise.py`: 31 tests (secret management, webhook, RBAC, audit, schemas, retention, security hardening)
- `test_auth.py`: 12 tests (password hashing, JWT tokens, _extract_role, require_role)
- `test_service_token.py`: 10 tests (token validation, _extract_role, get_current_user)
- `test_secret_leak.py`: 21 tests (encrypt/decrypt roundtrip, masking, connector response leak, audit log leak)
- `test_structured_logging.py`: 13 tests (sanitization, formatter, request_id, actor extraction)
- `test_metrics.py`: 8 tests (read_heartbeat alive/missing/stale/error, read_all_workers, write_heartbeat, endpoint structure)
- `test_health.py`: 10 tests (DB connected/error, worker alive/stale/missing/error, endpoint degraded)
- `test_cursor_pagination.py`: 7 tests (encode/decode, invalid cursor, has_more, filter application, empty result)
- `test_connector_failed_events_cursor.py`: 8 tests (offset pagination, cursor pagination, edge cases)
- Additional test files for workflow, scheduler, durable execution

**Frontend:** `cd frontend && npm run test:unit` — 145 tests across 20 files
- Type check: `cd frontend && npx vue-tsc --noEmit`

## Run Commands

```bash
# Start everything
./start.sh

# Start just backend
cd backend && uvicorn main:app --reload --port 8000

# Start just frontend
cd frontend && npm run dev

# Run migrations
cd backend && alembic upgrade head

# Create new migration
cd backend && alembic revision --autogenerate -m "description"

# Run tests
cd backend && python -m pytest tests/ -v

# Stop everything
./stop.sh
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `ENVIRONMENT` | No | `development` | `development`, `test`, or `production` |
| `ENCRYPTION_KEY` | Prod | auto-generated | Fernet key for secret encryption |
| `JWT_SECRET` | Prod | `change-me-in-production` | Secret for signing JWT tokens |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | No | `480` | Token expiry (8 hours default) |
| `SERVICE_TOKENS` | No | — | Comma-separated service tokens for machine-to-machine auth |
| `SCHEDULER_HEARTBEAT_PATH` | No | `/tmp/hermes_scheduler_worker_heartbeat` | Scheduler worker heartbeat file path |
| `RETENTION_HEARTBEAT_PATH` | No | `/tmp/hermes_retention_worker_heartbeat` | Retention worker heartbeat file path |
| `WORKER_HEARTBEAT_STALE_SECONDS` | No | `120` | Seconds before a worker heartbeat is considered stale |
| `TEST_DATABASE_URL` | No | — | Isolated DB for pytest |
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | Frontend API base URL |
| `VITE_WS_BASE_URL` | No | `ws://localhost:8000` | Frontend WebSocket URL |

## Known Limitations

1. **No SSO/OIDC implementation** — design doc only (`docs/SSO_OIDC_DESIGN.md`), planned for v3.1
2. **Scheduler is not a distributed workflow engine** — uses PostgreSQL advisory locks for multi-instance safety, but each process runs a single poll loop. Not a replacement for Celery, Temporal, or similar.
3. **No visual workflow editor** — workflows are defined via API or JSON; no drag-and-drop DAG builder.

## Test Status

**Local:** 305 passed, 172 skipped, 0 failed — full green.

**Docker:** 305 passed, 172 skipped, 0 failed — full green.

Both environments pass all tests. CI/release acceptance uses the same test suite.

## Current Verification Notes

The control plane is usable for internal pilot flows. Dashboard pages load, RCA/runbook generation works, workflow start works, approval approve/reject works, and frontend validation shows no `undefined` user-facing error text.

Known non-blocking limitations:

1. **Xiaomi Mimo provider connection** — Provider `test-mimo` can be registered, but `MINIMAX_API_KEY` is not configured in `docker-compose.yml`. Connection testing returns a clear missing/unavailable API key error. This is a deployment configuration gap, not a core workflow blocker.

## Key Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, router mounting |
| `backend/config.py` | Settings (Pydantic BaseSettings) |
| `backend/database.py` | SQLAlchemy engine and session |
| `backend/models/` | 23 SQLAlchemy ORM models |
| `backend/schemas/` | Pydantic request/response schemas |
| `backend/routers/` | 18 API route modules |
| `backend/security/` | Auth (JWT, bcrypt), encryption, RBAC, audit, webhook verification, structured logging |
| `backend/routers/auth.py` | Login/logout/me endpoints, JWT issuance |
| `backend/workers/` | Scheduler and retention workers |
| `backend/alembic/` | 8 database migrations |
| `frontend/src/App.vue` | Root Vue component |
| `frontend/src/components/` | 15 Vue components |
| `frontend/src/composables/` | Vue composables |
| `frontend/src/types/` | TypeScript type definitions |
