# Integration Model

## Overview

The AI Workflow Control Plane is runtime-agnostic. External systems connect to it through a **Connector Framework** that translates runtime-specific events into the control plane's universal domain model.

## Architecture

```
┌─────────────────────┐
│  External Runtimes  │
├─────────────────────┤
│  Agents SDK         │──┐
│  CI/CD Pipeline     │  │
│  Code Review Bot    │  │   HTTP Events
│  Data Pipeline      │  ├──────────────────┐
│  Custom Automation  │  │                  │
│  Webhook Source     │──┘                  ▼
└─────────────────────┘         ┌──────────────────┐
                                │  Connector API   │
                                │  POST /api/      │
                                │  connectors/{id}/ │
                                │  events           │
                                └────────┬─────────┘
                                         │
                                         ▼
                                ┌──────────────────┐
                                │  Control Plane   │
                                │                  │
                                │  Runtime         │
                                │  Run             │
                                │  TraceSpan       │
                                │  ToolCall        │
                                │  Approval        │
                                │  Artifact        │
                                │  EvalResult      │
                                └──────────────────┘
```

## Connector Types

### Push Connector (HTTP)

The runtime sends events to the control plane via HTTP.

**Use case:** Real-time workflow observation.

**Flow:**
1. Runtime registers itself via `POST /api/runtimes`.
2. During execution, runtime sends span events via `POST /api/connectors/{id}/events`.
3. Control plane maps events to Run, TraceSpan, ToolCall objects.
4. Frontend updates in real-time via SSE.

**Example payload:**

```json
{
  "event_type": "span.created",
  "runtime_id": "my-agent-runtime",
  "run_id": "run_abc123",
  "timestamp": "2026-04-30T12:00:00Z",
  "payload": {
    "span_type": "model_call",
    "title": "GPT-4o code review",
    "status": "completed",
    "model_name": "gpt-4o",
    "input_summary": "Review PR #42 diff",
    "output_summary": "3 issues found",
    "duration_ms": 120000,
    "input_tokens": 5000,
    "output_tokens": 2000,
    "cost": 0.035
  }
}
```

### Pull Connector (Polling)

The control plane periodically fetches data from an external system.

**Use case:** Batch workflows, historical data import.

**Flow:**
1. Connector config registered via `POST /api/connectors`.
2. Control plane polls the external system on a schedule.
3. New data mapped to domain objects.
4. Changes surfaced in the UI.

**Example:** GitHub PR review connector that polls for completed reviews.

### Webhook Connector

External system pushes notifications to the control plane.

**Use case:** Event-driven integrations (GitHub webhooks, CI/CD callbacks).

**Flow:**
1. Connector registered with a webhook URL.
2. External system sends HTTP POST to the webhook.
3. Control plane validates signature, parses payload, creates domain objects.

## Event Protocol

### Event Types

| Event | Description | Creates |
|---|---|---|
| `run.created` | New workflow run started | Run |
| `run.updated` | Run status changed | Run update |
| `run.completed` | Run finished | Run update |
| `span.created` | New trace span | TraceSpan |
| `span.updated` | Span status changed | TraceSpan update |
| `tool.invoked` | Tool call started | ToolCall + TraceSpan |
| `tool.completed` | Tool call finished | ToolCall update |
| `approval.requested` | Approval needed | Approval |
| `approval.resolved` | Approval decision made | Approval update |
| `artifact.created` | New artifact produced | Artifact |

### Event Envelope

```json
{
  "event_type": "span.created",
  "runtime_id": "string",
  "run_id": "string",
  "timestamp": "ISO8601",
  "idempotency_key": "string (optional)",
  "payload": { ... }
}
```

### Idempotency

Events with the same `idempotency_key` are deduplicated. This allows safe retry without creating duplicate records.

## Legacy Integration Migration

Existing code-review and agent capabilities will be migrated behind connectors:

| Legacy Component | Target Connector | Migration Strategy |
|---|---|---|
| Code Review Pipeline | `github-review-connector` | Wrap existing pipeline as a connector adapter |
| Agent Chat | `agent-sdk-connector` | Map agent events to TraceSpan/ToolCall |
| Hermès Proxy | `hermes-connector` | Keep as optional compatibility layer |
| Cost Tracker | Built into core | Cost data flows through TraceSpan fields |

## Adding a Custom Connector

1. **Register the runtime:**

```bash
curl -X POST http://localhost:8000/api/runtimes \
  -H "Content-Type: application/json" \
  -d '{"name": "My Pipeline", "type": "custom"}'
```

2. **Send events during execution:**

```bash
curl -X POST http://localhost:8000/api/connectors/{id}/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "run.created",
    "runtime_id": "my-pipeline",
    "run_id": "run_001",
    "timestamp": "2026-04-30T12:00:00Z",
    "payload": {
      "title": "Data Processing Pipeline",
      "input_summary": "Process 1000 records"
    }
  }'
```

3. **Query results via the standard API:**

```bash
curl http://localhost:8000/api/runs?runtime_id=my-pipeline
```

## Security

### Webhook Signature Verification

Connectors that receive webhooks should verify the payload signature:

```
X-Signature-256: sha256=<hex-encoded-hmac>
```

### Rate Limiting

The connector API enforces rate limits per runtime to prevent abuse.

### Authentication

Connector endpoints require authentication via API key or token, configured per connector.
