# Project Overview

Category: architecture
Tags: overview, architecture, control-plane, product
Confidence: high
Sources: README.md, docs/ARCHITECTURE.md, docs/CURRENT_STATE.md

Hermes Free is an AI Workflow Control Plane: a runtime-agnostic platform for observing, governing, auditing, and reviewing AI workflows. The product center is not a single-agent chat app or a code-review-only dashboard. Those surfaces exist as compatibility and legacy-adjacent capabilities around the control-plane core.

Core user questions the system is designed to answer:

- What is an AI workflow doing right now?
- Why did a workflow fail?
- Which model, tool, or configuration caused a problem?
- Which tool calls were risky, and were they approved?
- What recovery steps or runbooks are available after failure?
- Did an eval or config change improve behavior?

Primary capabilities:

- Workflow observability: runs, tasks, trace timelines, spans, cost, latency, and token rollups.
- Governance: tool risk policy, approval inbox, batch approvals, and audit logging.
- RCA/runbook: failure analysis with evidence and recovery instructions.
- Connector ingestion: runtime-agnostic event API for external runtimes and CI/agent systems.
- Eval/config: offline evals, config version history, comparison, and guarded recommended changes.
- Enterprise/admin: auth, RBAC, users, teams, environments, encrypted connector secrets, and retention.

Technology stack:

- Frontend: Vue 3, TypeScript, Vite, Naive UI, vue-i18n, Vitest, and Playwright.
- Backend: FastAPI, Pydantic settings/schemas, SQLAlchemy, and Alembic.
- Database: PostgreSQL primary store.
- Realtime: Server-Sent Events plus WebSocket and terminal compatibility surfaces.
- Workers: workflow scheduler worker and retention worker.

Important cross-links:

- [[system-architecture]]
- [[codebase-map]]
- [[development-and-verification]]
- [[current-state-and-risks]]
