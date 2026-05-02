# CI Matrix

**Last updated:** 2026-05-01
**Applies to:** AI Workflow Control Plane v3.0+

---

## Overview

This document defines the CI jobs required to validate the platform before merging. Each job targets a specific risk area.

---

## Jobs

| Job | Purpose | Trigger | Requirements |
|-----|---------|---------|-------------|
| frontend-typecheck | Verify TypeScript types | PR, push | Node.js 20+ |
| frontend-unit | Run Vitest unit tests | PR, push | Node.js 20+ |
| backend-unit | Backend tests without PG | PR, push | Python 3.9+ |
| backend-pg | Backend integration tests with PostgreSQL | PR, push | Python 3.9+, PostgreSQL |
| alembic-empty | Validate migration from empty DB | PR | Python 3.9+, PostgreSQL |
| python-compat | Verify Python 3.9 compatibility | PR | Python 3.9 |
| security-tests | Run auth, RBAC, secret leak tests | PR, push | Python 3.9+ |

---

## Job Details

### 1. frontend-typecheck

```bash
cd frontend
npm ci
npx vue-tsc --noEmit
```

**Catches:** Type errors, missing imports, interface mismatches.

### 2. frontend-unit

```bash
cd frontend
npm ci
npm run test:unit
```

**Catches:** Component logic errors, composable regressions.

### 3. backend-unit

```bash
cd backend
python -m pip install -r requirements.txt
ENVIRONMENT=test python -m pytest tests/ -v --ignore=tests/test_terminal_ws.py -x
```

**Catches:** Logic errors, schema validation, unit-level regressions.
**Note:** Some tests require PostgreSQL; use backend-pg for full coverage.

### 4. backend-pg

```bash
cd backend
python -m pip install -r requirements.txt
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ai_workflow_test"
export TEST_DATABASE_URL="$DATABASE_URL"
export ENVIRONMENT=test
alembic upgrade head
python -m pytest tests/ -v -x
```

**Requires:** PostgreSQL service (Docker or GitHub Actions service).
**Catches:** Database query errors, migration issues, integration failures.

### 5. alembic-empty

```bash
cd backend
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ai_workflow_empty_test"
export ENVIRONMENT=test
createdb ai_workflow_empty_test
alembic upgrade head
alembic downgrade base
alembic upgrade head
dropdb ai_workflow_empty_test
```

**Catches:** Migration idempotency, missing table/column errors on fresh DB.

### 6. python-compat

```bash
python3.9 -m pip install -r requirements.txt
cd backend
python3.9 -c "import main; print('Import OK')"
python3.9 -m py_compile main.py
python3.9 -m py_compile config.py
python3.9 -m py_compile security/auth.py
python3.9 -m py_compile security/rbac.py
```

**Catches:** Syntax or typing features not available in Python 3.9 (e.g., `X | Y` union syntax, `match` statements).

### 7. security-tests

```bash
cd backend
python -m pip install -r requirements.txt
export ENVIRONMENT=test
export SERVICE_TOKENS="test-token-abc,test-token-xyz"
export JWT_SECRET="test-jwt-secret"
python -m pytest tests/test_auth.py tests/test_service_token.py tests/test_secret_leak.py tests/test_v3_enterprise.py tests/test_structured_logging.py -v
```

**Catches:** Auth bypass, secret leaks, RBAC regression, encryption failures.

---

## GitHub Actions Workflow

The workflow is at `.github/workflows/ci.yml`. It covers:

- frontend-typecheck + frontend-unit (Node.js 20)
- backend-unit (Python 3.11)
- security-tests (Python 3.11)
- frontend build + artifact upload
- security audit (safety + npm audit)

The full backend-pg and alembic-empty jobs require a PostgreSQL service container and are documented but not yet in the workflow. Enable when a CI PostgreSQL instance is available.

---

## Local Pre-Merge Checklist

Before pushing, run locally:

```bash
# Frontend
cd frontend && npx vue-tsc --noEmit && npm run test:unit

# Backend
cd backend && ENVIRONMENT=test SERVICE_TOKENS="test-abc" JWT_SECRET="test" \
  python -m pytest tests/test_auth.py tests/test_service_token.py tests/test_secret_leak.py tests/test_v3_enterprise.py tests/test_structured_logging.py tests/test_metrics.py -v
```

---

## Risk Matrix

| Risk | Covered by |
|------|-----------|
| Type errors | frontend-typecheck |
| Component regressions | frontend-unit |
| Backend logic errors | backend-unit |
| Database integration | backend-pg |
| Migration failures | alembic-empty |
| Python version compat | python-compat |
| Auth/RBAC/secret leaks | security-tests |
