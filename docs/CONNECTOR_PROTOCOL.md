# Connector Event Protocol

This document defines the unified event protocol that external runtimes use to ingest data into the AI Workflow Control Plane.

## Overview

The Connector Framework enables any external runtime (agent, pipeline, workflow engine) to send observability data to the control plane through a single batch endpoint. The protocol is:

- **Unified** — one endpoint for all event types
- **Idempotent** — duplicate events are silently deduplicated via `event_id`
- **Batch-friendly** — multiple events in a single request
- **Error-resilient** — individual event failures don't block the batch

## Endpoint

```
POST /api/connectors/{connector_id}/events
Content-Type: application/json
```

### Request Body

A JSON array of `ConnectorEvent` objects:

```json
[
  {
    "event_type": "run.created",
    "event_id": "unique-id-001",
    "run_id": null,
    "timestamp": "2026-05-01T10:00:00Z",
    "payload": { ... }
  }
]
```

### Response

```json
{
  "connector_id": "uuid",
  "results": [
    {
      "event_type": "run.created",
      "event_id": "unique-id-001",
      "status": "accepted",
      "resource_id": "uuid-of-created-run",
      "detail": null
    }
  ]
}
```

### Result Statuses

| Status | Meaning |
|--------|---------|
| `accepted` | Event processed successfully. `resource_id` contains the created/updated resource ID. |
| `duplicate` | Event with this `event_id` was already processed. `resource_id` contains the original resource ID. |
| `error` | Event processing failed. `detail` contains the error message. |

## Event Types

### `runtime.upserted`

Create or update a runtime.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payload.name` | string | No | Runtime display name |
| `payload.type` | string | No | Runtime type (e.g., "agent", "pipeline") |
| `payload.status` | string | No | Runtime status (e.g., "active", "inactive") |
| `payload.config_json` | object | No | Runtime configuration |

No `run_id` required.

### `run.created`

Create a new workflow run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payload.title` | string | No | Run title (default: "Connector run") |
| `payload.status` | string | No | Initial status (default: "running") |
| `payload.input_summary` | string | No | Summary of the run's input |

Optional `run_id` in the event — if provided, used as the run's ID; otherwise a UUID is generated.

### `run.updated`

Update an existing run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payload.status` | string | No | New status |
| `payload.title` | string | No | New title |
| `payload.output_summary` | string | No | Summary of output |
| `payload.error_summary` | string | No | Error description |
| `payload.total_tokens` | number | No | Total tokens used |
| `payload.total_cost` | number | No | Total cost in USD |

**Required:** `run_id` in the event must point to an existing run.

When `status` is set to `"completed"` or `"error"`, `ended_at` is auto-set and `duration_ms` is computed from `started_at`.

### `span.created`

Create a trace span within a run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payload.span_type` | string | No | Span type (e.g., "llm", "tool_call", "system_event") |
| `payload.title` | string | No | Span title |
| `payload.status` | string | No | Span status (default: "completed") |
| `payload.agent_name` | string | No | Agent that produced this span |
| `payload.model_name` | string | No | Model used (for LLM spans) |
| `payload.tool_name` | string | No | Tool used (for tool spans) |
| `payload.input_summary` | string | No | Input summary |
| `payload.output_summary` | string | No | Output summary |
| `payload.error_summary` | string | No | Error description |
| `payload.input_tokens` | number | No | Input token count |
| `payload.output_tokens` | number | No | Output token count |
| `payload.cost` | number | No | Cost in USD |
| `payload.metadata` | object | No | Additional metadata (merged into span's metadata_json) |

**Required:** `run_id` in the event must point to an existing run.

### `tool_call.created`

Record a tool call within a run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payload.tool_name` | string | No | Tool name (default: "unknown") |
| `payload.risk_level` | string | No | Risk level: "read", "write", "execute", "network", "destructive" |
| `payload.decision` | string | No | Policy decision: "allow", "confirm", "deny" |
| `payload.status` | string | No | Call status (default: "completed") |
| `payload.input_json` | object | No | Tool input |
| `payload.output_json` | object | No | Tool output |
| `payload.error_summary` | string | No | Error description |

**Required:** `run_id` in the event must point to an existing run.

### `approval.requested`

Create a pending approval request.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payload.reason` | string | No | Reason for approval (default: "Connector approval request") |
| `payload.requested_by` | string | No | Who requested (default: "connector") |

**Required:** `run_id` in the event must point to an existing run.

### `artifact.created`

Create an artifact attached to a run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payload.artifact_type` | string | No | Artifact type (default: "generic") |
| `payload.title` | string | No | Artifact title |
| `payload.content_text` | string | No | Text content |
| `payload.content_json` | object | No | JSON content |
| `payload.storage_url` | string | No | External storage URL |

**Required:** `run_id` in the event must point to an existing run.

## Idempotency

Events are deduplicated by `(connector_id, event_id)`. If an event with the same `event_id` has already been processed for the same connector, the duplicate is silently skipped and the original `resource_id` is returned.

Events without `event_id` are never deduplicated — each submission creates a new resource.

## Error Handling

- **Connector not found** → HTTP 404
- **Connector disabled** → HTTP 403
- **Individual event failure** → `status: "error"` in the result, HTTP 200 for the batch
- **Invalid event type** → `status: "error"` with detail "Unsupported event type: ..."
- **Missing required fields** → `status: "error"` with detail describing the validation failure

Errors are also recorded in the `AuditLog` table with `action: "event.error"` for debugging.

## Authentication

> **TODO:** Webhook signature validation is not yet implemented. When added, connectors will have a `secret_ref` field containing the signing key, and the API will validate `X-Webhook-Signature` headers.

## Legacy Dashboard Migration

The legacy dashboard used direct API calls (`POST /api/runs`, `POST /api/runs/{id}/spans`) to record workflow data. To migrate:

1. Create a `ConnectorConfig` with `connector_type: "legacy_dashboard"`.
2. Replace direct API calls with batched connector events.
3. Map existing data structures to the event protocol:

| Legacy API | Event Type | Notes |
|---|---|---|
| `POST /api/runs` | `run.created` | `runtime_id` comes from the connector config |
| `PATCH /api/runs/{id}` | `run.updated` | `run_id` in the event |
| `POST /api/runs/{id}/spans` | `span.created` | `run_id` in the event |
| `POST /api/tools` (guardrails) | `tool_call.created` | `run_id` in the event |

See `CONNECTOR_EXAMPLE_GITHUB_REVIEW.md` for a complete adapter implementation example.
