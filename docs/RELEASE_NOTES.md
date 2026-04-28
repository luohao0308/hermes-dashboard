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
- Trace Timeline now shows span duration, tool name, token count, input summary, and output summary.
- Added a regression test for stable trace span schema and metadata payloads.

### Agent Tool Library

- Added SDK-ready read-only Hermès tool specs.
- Added tool discovery API at `GET /api/agent/tools`.
- Added read-only tool invocation API at `POST /api/agent/tools/{tool_name}/invoke`.
- System page now displays the Agent tool library.
- Added `create_alert_summary` and `terminal_session_list` tools for Monitor Agent triage.

### Tool Guardrails

- Added guardrail policy file for tool risk decisions.
- Added `GET /api/agent/guardrails`.
- Tool invocation now evaluates allow/confirm/deny policy before execution.
- System page now displays guardrail policies.
- Added guardrail approval events for `confirm` tool calls.
- Added approve/reject APIs for pending guardrail events.
- System page now displays pending guardrail approvals with approve/reject actions.

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
- Agent Chat now shows a linked session context card with RCA and trace counts.

### Runbook Automation

- Added rule-based runbook generation from session detail, RCA, and trace data.
- Added `GET/POST /api/sessions/{session_id}/runbook`.
- Runbooks persist in the Agent trace SQLite database.
- Alerts with linked sessions can trigger Runbook generation directly from the alerts panel.
- Session replay pages can generate and copy Markdown runbooks.
- Added `POST /api/sessions/{session_id}/export` for local Markdown export.
- Added `GET /api/exports` for export directory status and recent Markdown files.
- System page now displays the Markdown sync/export target and recent files.
- Session replay pages now render runbook checklist steps as an execution timeline.

### Handoff Topology

- Agent configuration now shows enabled handoff paths for each Agent.
- The main entry Agent is highlighted and disabled handoff targets are muted.
- Agent handoffs now store structured payloads with reason, priority, expected output, and context refs.
- Trace timeline now shows structured handoff details on session replay pages.
- Handoff events with missing targets now record a Dispatcher fallback span.

### Agent Config Evaluation

- Added static Agent configuration scoring for main Agent validity, handoff reachability, and isolated nodes.
- Added offline Agent eval samples for debug, review, research, deploy, and monitor tasks.
- Agent configuration API now returns an `evaluation` block.
- Agent configuration page displays score, grade, and actionable findings.
- Added aggregate Agent run metrics at `GET /api/agent/evals/summary`.
- Agent configuration page now displays total runs, success rate, average duration, handoffs, tools, and guardrails.
- AgentOps overview now surfaces Agent success rate and run/error counts.
- System page now shows recent Agent performance trend data.
- Added local Agent config change history at `GET /api/agent/config/history`.
- Agent configuration page now shows recent before/after score changes.
- Agent configuration evaluation now includes actionable improvement suggestions.
- Added `POST /api/agent/config/compare` for static A/B config comparison.
- Agent configuration page can compare a candidate main Agent before saving.
- CI now runs AgentOps offline schema/eval tests for config, guardrails, RCA, runbooks, exports, and traces.

## Verification

- `npx vue-tsc --noEmit`
- `npm run test:unit`
- `npm run build`
- `python -m py_compile backend/main.py backend/agent/chat_manager.py backend/agent/tracing_store.py backend/agent/tools/hermes_tools.py backend/agent/guardrails.py backend/agent/rca.py backend/agent/runbook.py backend/agent/config_evaluator.py backend/agent/config_history.py backend/agent/exporter.py`
- `pytest backend/tests/test_hermes_tools.py backend/tests/test_tracing_store.py backend/tests/test_rca.py backend/tests/test_runbook.py backend/tests/test_config_evaluator.py backend/tests/test_config_history.py backend/tests/test_exporter.py backend/tests/test_agent_switch.py::TestChatManagerAPI -q`
