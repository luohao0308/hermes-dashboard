# Release Notes

## AgentOps Upgrade

### Stability and Security

- Removed a stale merge-conflict marker from the dashboard.
- Moved frontend API and WebSocket bases into Vite environment configuration.
- Removed a committed Notion token from docs and documented local `.env` usage.
- Added Node 20+ and Python 3.11 runtime requirements.

### Dashboard and Review

- Added AgentOps overview with health score, active work, error signals, model, capability, and token summaries.
- Added session replay pages at `#/sessions/{id}` with metadata, diagnosis, related logs, and message timeline.
- Extended `/tasks/{task_id}` to include model, token, timing, and end reason fields.

### Persistence and Context

- Added SQLite-backed Agent Chat persistence.
- Chat sessions now restore messages after backend restart.
- Chat sessions can carry title, linked Hermès session, and terminal session context fields.

### Alerts and Terminal Safety

- Added `/api/alerts` rule-based alerts with suggested actions.
- Added Dashboard alerts panel.
- Added terminal session list and close APIs.
- Added high-risk terminal command confirmation flow.

### System Configuration

- Added System page for model info, Hermès config, Skills, Plugins, and Cron jobs.

### Trace Timeline

- Added SQLite-backed Agent run trace storage.
- Added trace APIs for run lookup and latest trace lookup.
- Added Trace Timeline component to Session replay pages.
- Agent Chat now emits and stores trace spans for user input, Agent start, handoff, tool events, output, and errors.

## Verification

- `npx vue-tsc --noEmit`
- `npm run test:unit`
- `npm run build`
- `python -m py_compile backend/main.py backend/agent/chat_manager.py backend/agent/__init__.py`
- `pytest backend/tests/test_agent_switch.py::TestChatManagerAPI -q`
