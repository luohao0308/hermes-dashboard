# v3.0 Enterprise and Team Features — Release Notes

**Status:** Release-ready
**Date:** 2026-05-01

## Summary

v3.0 adds enterprise-grade security, team management, and operational controls to the AI Workflow Control Plane. This release focuses on secret management, webhook security, RBAC, audit logging, and data lifecycle management.

## New Features

### Secret Management (V3.0-03)

Connector secrets (`api_key`, `token`, `secret`, `password`, `webhook_secret`, etc.) are now encrypted at rest using Fernet symmetric encryption.

- **Encryption key:** Set `ENCRYPTION_KEY` environment variable. Generate with:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- **Production mode:** If `ENVIRONMENT=production` and `ENCRYPTION_KEY` is not set, the application raises `RuntimeError` on startup.
- **Development mode:** Auto-generates an ephemeral key with a warning. Encrypted secrets are lost on restart.
- **API responses:** Sensitive fields are automatically masked (`sk-12**********abcd`).
- **Legacy support:** Plaintext secrets in existing `config_json` pass through `decrypt_secret()` without error.

### Webhook Signature Verification (V3.0-06)

Connector event ingestion now verifies `X-Webhook-Signature` using HMAC-SHA256.

- **Signature format:** `sha256=<hex_digest>` in the `X-Webhook-Signature` header.
- **Anti-replay:** Timestamp-based rejection (default tolerance: 300 seconds).
- **Raw body verification:** Uses the actual HTTP request body for signature verification (not re-serialized).
- **Configuration:** Set `webhook_secret` in the connector's `config_json`.

### RBAC Permissions (V3.0-02)

Three roles with hierarchical permissions:

| Role | Permissions |
|------|------------|
| `admin` | Full access — users, teams, configs, workflows, connectors, evals, approvals |
| `operator` | Read/write on workflows, connectors, evals, approvals — no user/team management |
| `viewer` | Read-only on all resources |

- **Default role:** `viewer` (least privilege) when no `X-User-Role` header is present.
- **Header:** Pass `X-User-Role: admin|operator|viewer` (placeholder until SSO integration).

### Audit Logging (V3.0-04)

All mutations write audit log entries via centralized `write_audit_log()`:

| Resource | Actions Audited |
|----------|----------------|
| Connector | created, updated, deleted, event.ingested, event.error |
| Workflow | created, updated, deleted |
| Approval | approved, rejected |
| Eval | eval.run |
| ConfigVersion | config_version.created |
| User | created, updated, deleted |
| Team | created, deleted |
| Environment | created, deleted |
| Retention | retention.cleanup |

### Users and Teams (V3.0-01)

New CRUD endpoints for identity management:

- `GET/POST /api/users` — list and create users
- `GET/PUT/DELETE /api/users/{id}` — read, update, delete users
- `GET/POST /api/teams` — list and create teams
- `GET/DELETE /api/teams/{id}` — read, delete teams

### Environments (V3.0-05)

Environment model for dev/staging/prod scoping:

- `GET/POST /api/environments` — list and create environments
- `GET/DELETE /api/environments/{id}` — read, delete environments
- `environment_id` FK added to `runtimes`, `connector_configs`, `workflow_definitions`
- Seed data: dev (default), staging, prod

### Retention Policies (V3.0-07)

Data lifecycle management with configurable retention periods:

- `RetentionPolicy` model: resource_type, retention_days, is_active
- `workers.retention_worker` — periodic cleanup with dry-run mode
- Supported resource types: run, trace_span, approval, audit_log, eval_result
- All retention deletions are audit-logged

### SSO/OIDC Design (V3.0-08)

Design document only — see `docs/SSO_OIDC_DESIGN.md`:

- OIDC authorization code flow with PKCE
- SAML 2.0 SP-initiated SSO
- JIT user provisioning with group-to-role mapping
- Multi-IdP support
- Implementation deferred to v3.1+

## Database Migration

**Migration:** `alembic/versions/007_v3_enterprise.py`

Creates:
- `teams` table
- `users` table
- `environments` table
- `retention_policies` table

Adds:
- `runtimes.environment_id` (FK → environments)
- `connector_configs.environment_id` (FK → environments)
- `workflow_definitions.environment_id` (FK → environments)

Seeds:
- Default environments: dev (is_default=true), staging, prod

Run migration:
```bash
cd backend && alembic upgrade head
```

## New Files

| File | Purpose |
|------|---------|
| `backend/security/__init__.py` | Security package |
| `backend/security/secret_manager.py` | Fernet encrypt/decrypt/mask |
| `backend/security/webhook.py` | HMAC-SHA256 signature verification |
| `backend/security/audit.py` | Centralized audit log writer |
| `backend/security/rbac.py` | Role-based access control |
| `backend/models/user.py` | User ORM model |
| `backend/models/team.py` | Team ORM model |
| `backend/models/environment.py` | Environment ORM model |
| `backend/models/retention_policy.py` | RetentionPolicy ORM model |
| `backend/alembic/versions/007_v3_enterprise.py` | Migration |
| `backend/schemas/user.py` | User/Team Pydantic schemas |
| `backend/schemas/environment.py` | Environment Pydantic schemas |
| `backend/routers/users.py` | User/Team CRUD API |
| `backend/routers/environments.py` | Environment CRUD API |
| `backend/workers/retention_worker.py` | Retention cleanup worker |
| `backend/tests/test_v3_enterprise.py` | 31 tests |
| `docs/SSO_OIDC_DESIGN.md` | SSO design document |

## Modified Files

| File | Change |
|------|--------|
| `backend/config.py` | Added `encryption_key` setting |
| `backend/requirements.txt` | Added `cryptography>=42.0.0` |
| `backend/models/__init__.py` | Exports new models |
| `backend/models/runtime.py` | Added `environment_id` FK |
| `backend/models/connector_config.py` | Added `environment_id` FK |
| `backend/models/workflow.py` | Added `environment_id` FK |
| `backend/schemas/__init__.py` | Exports new schemas |
| `backend/schemas/connector.py` | Mask secrets in response |
| `backend/routers/connectors.py` | CRUD with encrypt/decrypt/webhook/audit |
| `backend/routers/workflows.py` | Audit logging |
| `backend/routers/approvals.py` | Audit logging, replaced inline helper |
| `backend/routers/evals.py` | Audit logging |
| `backend/main.py` | Mounted users/environments routers |
| `docs/API_CONTRACT.md` | Documented new endpoints |
| `docs/AI_WORKFLOW_CONTROL_PLANE_ROADMAP.md` | Marked v3.0 tasks Done |

## Security Hardening

- **RBAC default:** Deny by default (viewer) when no role header present
- **Webhook body:** Uses raw request body for signature verification (not re-serialized)
- **Encryption key:** Raises `RuntimeError` in production if `ENCRYPTION_KEY` not set
- **Retention audit:** All retention deletions logged to audit table
- **Anti-replay:** Timestamp tolerance of 300 seconds on webhook signatures

## Test Results

```
31 passed, 2 warnings in 1.36s
```

Test classes:
- `TestSecretManager` (7 tests) — encrypt/decrypt/mask/roundtrip
- `TestWebhookVerification` (4 tests) — sign/verify/reject
- `TestRBAC` (4 tests) — admin/operator/viewer permissions
- `TestAuditLogging` (1 test) — write_audit_log
- `TestEnvironmentSchemas` (2 tests) — create/response
- `TestUserSchemas` (4 tests) — create/role validation
- `TestRetentionWorker` (1 test) — dry-run cycle
- `TestSecurityHardening` (8 tests) — RBAC default deny, anti-replay, encryption key, legacy plaintext
