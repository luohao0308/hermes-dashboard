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

### Agent Tool Library

- Added SDK-ready read-only Hermès tool specs.
- Added tool discovery API at `GET /api/agent/tools`.
- Added read-only tool invocation API at `POST /api/agent/tools/{tool_name}/invoke`.
- System page now displays the Agent tool library.

### Tool Guardrails

- Added guardrail policy file for tool risk decisions.
- Added `GET /api/agent/guardrails`.
- Tool invocation now evaluates allow/confirm/deny policy before execution.
- System page now displays guardrail policies.

### RCA Analyst

- Added structured session RCA reports with root cause, evidence, confidence, and next actions.
- Added RCA persistence in the Agent trace SQLite database.
- Added `GET/POST /api/sessions/{session_id}/rca`.
- Session replay pages can generate and copy failure analysis reports.

### Chat Session Binding

- Session replay pages can open Agent Chat with the current Hermès session linked.
- Agent Chat reuses existing linked conversations and shows the linked session in the header.
- Agent runs now receive linked session summary context and latest RCA when available.
- Linked session context is stored as a trace span.

### Runbook Automation

- Added rule-based runbook generation from session detail, RCA, and trace data.
- Added `GET/POST /api/sessions/{session_id}/runbook`.
- Runbooks persist in the Agent trace SQLite database.
- Session replay pages can generate and copy Markdown runbooks.

### Handoff Topology

- Agent configuration now shows enabled handoff paths for each Agent.
- The main entry Agent is highlighted and disabled handoff targets are muted.

### Agent Config Evaluation

- Added static Agent configuration scoring for main Agent validity, handoff reachability, and isolated nodes.
- Agent configuration API now returns an `evaluation` block.
- Agent configuration page displays score, grade, and actionable findings.

## Verification

- `npx vue-tsc --noEmit`
- `npm run test:unit`
- `npm run build`
- `python -m py_compile backend/main.py backend/agent/chat_manager.py backend/agent/tracing_store.py backend/agent/tools/hermes_tools.py backend/agent/guardrails.py backend/agent/rca.py backend/agent/runbook.py backend/agent/config_evaluator.py`
- `pytest backend/tests/test_hermes_tools.py backend/tests/test_tracing_store.py backend/tests/test_rca.py backend/tests/test_runbook.py backend/tests/test_config_evaluator.py backend/tests/test_agent_switch.py::TestChatManagerAPI -q`
