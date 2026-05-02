# Connector SDK Examples

Reference implementations for integrating external runtimes with the AI Workflow Control Plane connector API.

## Protocol Overview

### Endpoint

```
POST /api/connectors/{connector_id}/events
Content-Type: application/json
```

### Authentication (one of)

| Method | Header | Description |
|--------|--------|-------------|
| Service Token | `Authorization: Bearer <token>` | Machine-to-machine auth via `SERVICE_TOKENS` env var |
| Webhook Signature | `X-Webhook-Signature: sha256=<hex>` | HMAC-SHA256 of request body using connector's `webhook_secret` |

### Event Schema

```json
[
  {
    "event_type": "run.created",
    "event_id": "unique-idempotency-key",
    "run_id": "optional-target-run-uuid",
    "timestamp": "2026-05-01T12:00:00Z",
    "payload": { ... }
  }
]
```

### Supported Event Types

| Event Type | Required Fields | Description |
|-----------|----------------|-------------|
| `runtime.upserted` | `payload.name` | Create or update a runtime |
| `run.created` | `payload.title` | Start a new run |
| `run.updated` | `run_id`, `payload.status` | Update run status/summary |
| `span.created` | `run_id`, `payload.title` | Record a trace span |
| `tool_call.created` | `run_id`, `payload.tool_name` | Record a tool invocation |
| `approval.requested` | `run_id` | Request approval for a tool |
| `artifact.created` | `run_id` | Attach an artifact to a run |

### Idempotency

Supply a unique `event_id` per event. Duplicate `(connector_id, event_id)` pairs are silently deduplicated — the server returns `"status": "duplicate"` without re-processing.

### Anti-Replay

Include a `timestamp` field (ISO 8601 or Unix epoch) in each event. The server rejects payloads older than the tolerance window (default 300 seconds).

## HMAC-SHA256 Signing

```
1. Serialize the event batch as JSON
2. Compute HMAC-SHA256(secret, body_bytes)
3. Set header: X-Webhook-Signature: sha256=<hex_digest>
```

### Python

```python
import hmac, hashlib

def sign_payload(payload_bytes: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"
```

### Node.js

```javascript
import { createHmac } from 'node:crypto';

function signPayload(payloadBytes, secret) {
  const digest = createHmac('sha256', secret).update(payloadBytes).digest('hex');
  return `sha256=${digest}`;
}
```

## Retry Strategy

Transient errors (HTTP 429, 5xx) should be retried with exponential backoff:

| Attempt | Delay |
|---------|-------|
| 1 | 1s |
| 2 | 2s |
| 3 | 4s |

Non-transient errors (4xx except 429) should not be retried.

## Example Files

| File | Language | Features |
|------|----------|----------|
| [`examples/connectors/python_client.py`](../examples/connectors/python_client.py) | Python 3.9+ | Signing, batch, retry, idempotency |
| [`examples/connectors/node_client.mjs`](../examples/connectors/node_client.mjs) | Node.js 18+ | Signing, batch, retry, idempotency |

## Running the Examples

### Python

```bash
export CONNECTOR_URL="http://localhost:8000/api/connectors/YOUR_CONNECTOR_ID/events"
export WEBHOOK_SECRET="your-webhook-secret"
# OR
export SERVICE_TOKEN="your-service-token"

python examples/connectors/python_client.py
```

### Node.js

```bash
export CONNECTOR_URL="http://localhost:8000/api/connectors/YOUR_CONNECTOR_ID/events"
export WEBHOOK_SECRET="your-webhook-secret"
# OR
export SERVICE_TOKEN="your-service-token"

node examples/connectors/node_client.mjs
```

## Error Handling

The server returns per-event results in the response:

```json
{
  "connector_id": "...",
  "results": [
    { "event_type": "run.created", "event_id": "...", "status": "accepted", "resource_id": "..." },
    { "event_type": "span.created", "event_id": "...", "status": "error", "detail": "Run not found" }
  ]
}
```

Always check individual event statuses — a batch can partially succeed.
