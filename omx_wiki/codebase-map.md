# Codebase Map

Category: reference
Tags: code-map, backend, frontend, tests, docs
Confidence: high
Sources: repository file tree, backend/main.py, frontend/src/composables/useNavigation.ts, frontend/package.json, backend/requirements.txt

Top-level layout:

- `README.md`: product overview, release summary, quick start, and API summary.
- `docs/`: architecture, API contract, domain model, deployment, current state, connector protocol, operations, and release notes.
- `backend/`: FastAPI app, models, schemas, routers, security modules, workers, providers, repositories, agent compatibility surfaces, and backend tests.
- `frontend/`: Vue 3 SPA, Vite config, components, composables, i18n, styles, frontend unit tests, and e2e tests.
- `examples/connectors/`: Python and Node connector client examples.
- `docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.frontend`: containerized runtime.
- `start.sh`, `stop.sh`: local development process management.

Backend structure:

- `backend/main.py`: application factory and lifespan, middleware, router mounting, SSE generator, and direct compatibility endpoints.
- `backend/routers/`: product API modules for runs, workflows, connectors, approvals, tools, evals, audit, auth, metrics, environments, users, runtimes, and analysis.
- `backend/models/`: SQLAlchemy ORM models for runs, tasks, trace spans, approvals, artifacts, workflows, users, teams, environments, audit logs, retention, connector configs, evals, and related records.
- `backend/schemas/`: Pydantic request/response schemas.
- `backend/repositories/`: repository layer and PostgreSQL repository factory.
- `backend/security/`: auth, RBAC, audit, secret management, structured logging, and webhook verification.
- `backend/workers/`: workflow scheduler and retention worker.
- `backend/provider/`: provider registry and adapters for OpenAI, Anthropic, Ollama, and OpenAI-compatible providers.
- `backend/agent/` and `backend/review/`: compatibility and legacy-adjacent agent/review functionality.

Frontend structure:

- `frontend/src/App.vue`: root application shell and view composition.
- `frontend/src/components/`: dashboard panels and feature surfaces such as RunList, RunDetail, WorkflowList, ApprovalInbox, EvalDashboard, AuditLogPanel, Terminal, and AgentChat.
- `frontend/src/composables/`: API access and UI state helpers including navigation, SSE, workflow APIs, approval APIs, eval APIs, audit APIs, saved filters, formatting, and toast handling.
- `frontend/src/i18n/`: English and Chinese locale files.
- `frontend/src/types/index.ts`: shared frontend types.
- `frontend/src/styles/` and `frontend/src/style.css`: global styling.

Navigation:

- Hash routes are defined in `frontend/src/composables/useNavigation.ts`.
- Main routes include dashboard, runs, workflows, approvals, eval, config compare, providers, connectors, environments, knowledge, costs, guardrails, system, agents, terminal, chat, and audit.
- `LEGACY_NAV_IDS` is currently an empty set, so no visible route is marked legacy by that composable.

Related pages:

- [[project-overview]]
- [[system-architecture]]
- [[development-and-verification]]
