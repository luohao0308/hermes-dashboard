# Release Checklist

Use this checklist before tagging or deploying the AI Workflow Control Plane.

## Optimization Release Verification

Run these before declaring the Optimization Release final:

- [ ] Frontend typecheck: `cd frontend && npx vue-tsc --noEmit`
- [ ] Frontend unit tests: `cd frontend && npm run test:unit` (145 tests, 20 files)
- [ ] Backend security tests: `cd backend && python -m pytest tests/test_v3_enterprise.py tests/test_auth.py tests/test_service_token.py tests/test_secret_leak.py -v`
- [ ] Backend health/metrics tests: `cd backend && python -m pytest tests/test_health.py tests/test_metrics.py tests/test_structured_logging.py -v`
- [ ] Backend cursor pagination tests: `cd backend && python -m pytest tests/test_cursor_pagination.py tests/test_connector_failed_events_cursor.py -v`
- [ ] Alembic migration: `cd backend && alembic upgrade head` (9 migrations, 001–009)
- [ ] Document consistency: `grep -rn "Hermès Dashboard\|Code Review Pipeline\|Bridge Server" docs/ README.md --include="*.md" | grep -v archive` — only contextual references allowed

## Product Direction

- [ ] README, `CURRENT_STATE.md`, and `ARCHITECTURE.md` all describe the project as AI Workflow Control Plane.
- [ ] Legacy Hermès / Code Review / single-Agent content appears only in archive, connector examples, or legacy compatibility notes.
- [ ] Navigation presents Observe / Govern / Improve / Integrate / Admin / Legacy clearly.

## Code Quality

- [ ] Frontend typecheck passes: `cd frontend && npx vue-tsc --noEmit`.
- [ ] Frontend unit tests pass: `cd frontend && npm run test:unit`.
- [ ] Frontend build passes: `cd frontend && npm run build`.
- [ ] Backend tests pass without optional PG integration where applicable.
- [ ] Backend PG integration tests pass with `TEST_DATABASE_URL`.
- [ ] No new Python 3.12-only syntax is introduced; project remains Python 3.9+ compatible.

## Database and Migrations

- [ ] `alembic upgrade head` succeeds on an empty PostgreSQL database.
- [ ] Migration rollback path is documented for the release.
- [ ] New models, migrations, and `POSTGRESQL_SCHEMA.md` are aligned.
- [ ] New writes go to PostgreSQL, not SQLite.
- [ ] Any legacy SQLite fallback is read-only or documented as compatibility.

## Security

- [ ] Production requires `ENVIRONMENT=production` and `ENCRYPTION_KEY`.
- [ ] Connector secrets are encrypted at rest and masked in API responses.
- [ ] No secret appears in logs, audit records, error messages, or snapshots.
- [ ] Webhook signatures use raw request body and timestamp anti-replay.
- [ ] All write endpoints have RBAC coverage or a tracked exception.
- [ ] Viewer cannot perform write operations.
- [ ] Operator cannot manage users, teams, environments, retention, or secrets.
- [ ] Audit logs are written for connector, workflow, approval, eval, config, user, team, environment, retention, and secret mutations.

## Runtime and Workers

- [ ] API process starts successfully.
- [ ] Scheduler worker starts and can advance a workflow run.
- [ ] Retention worker dry-run works before production deletion.
- [ ] Task retries respect `backoff_seconds`.
- [ ] Workflow timeout and approval timeout behavior is tested.
- [ ] Dead-letter status is visible in API and UI.

## Connectors

- [ ] Connector event ingestion accepts valid signed payloads.
- [ ] Invalid, missing, or expired signatures are rejected when signing is configured.
- [ ] Ingestion errors are audit logged.
- [ ] Batch ingestion idempotency is tested.
- [ ] Connector examples match the current protocol.

## Frontend UX

- [ ] Main brand is AI Control Plane.
- [ ] Legacy pages are grouped and visually secondary.
- [ ] Loading, empty, error, unauthorized states are handled for core pages.
- [ ] Runs, Workflows, Approvals, Evals, Connectors and Config pages render without mocked assumptions.
- [ ] Large tables have pagination or a documented limitation.

## Operations

- [ ] `.env.example` includes all required production variables.
- [ ] `PRODUCTION_DEPLOYMENT.md` is current.
- [ ] Backup and restore steps are documented.
- [ ] Health checks are documented for API, DB, scheduler worker, retention worker, and connector ingestion.
- [ ] Known limitations are updated in `CURRENT_STATE.md`.

## Documentation

- [ ] `API_CONTRACT.md` reflects implemented endpoints.
- [ ] `POSTGRESQL_SCHEMA.md` reflects migrations.
- [ ] Release notes are updated for the version.
- [ ] Historical docs are in `docs/archive/`.
- [ ] New optimization work is tracked in `PLATFORM_OPTIMIZATION_EXECUTION_PLAN.md`.

## Deployment

- [ ] Staging deployment completed.
- [ ] Smoke test completed:
  - create runtime
  - create run
  - append span
  - create connector
  - ingest signed event
  - start workflow
  - approve approval
  - generate RCA/runbook
  - run eval summary
- [ ] Rollback plan is ready.
- [ ] Database backup exists.
- [ ] Post-deploy monitoring window is assigned.
