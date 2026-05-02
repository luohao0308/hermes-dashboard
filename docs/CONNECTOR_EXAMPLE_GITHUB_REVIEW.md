# Connector Example: GitHub Code Review Pipeline

This document shows how the existing code review pipeline maps to the generic Connector Framework using the unified event protocol.

## Mapping

| Legacy Component | Control Plane Object | Event Type | Notes |
|---|---|---|---|
| Review session | `Run` | `run.created` | One review = one run |
| Model review step | `TraceSpan` (type: `model_call`) | `span.created` | Each model's review is a span |
| Consensus check | `TraceSpan` (type: `system_event`) | `span.created` | Consensus engine is a system event |
| GitHub PR fetch | `TraceSpan` (type: `tool_call`) | `span.created` | Fetching PR data is a tool call |
| Review result | `Artifact` (type: `report`) | `artifact.created` | The review output is an artifact |
| Guardrail check | `ToolCall` + `Approval` | `tool_call.created`, `approval.requested` | High-risk actions go through approval |
| Cost tracking | `TraceSpan` fields | — | `input_tokens`, `output_tokens`, `cost` |

## Setup

1. Register a Runtime for the GitHub review pipeline:
   ```
   POST /api/runtimes
   {"name": "github-code-review", "type": "connector", "status": "active"}
   ```

2. Create a ConnectorConfig pointing to that runtime:
   ```
   POST /api/connectors
   {"runtime_id": "<runtime_id>", "connector_type": "github_review", "display_name": "GitHub Review Pipeline"}
   ```

3. Note the `connector_id` — all events go through `POST /api/connectors/{connector_id}/events`.

## Event Flow

All events are sent as a batch to `POST /api/connectors/{connector_id}/events`. The API is idempotent: duplicate `event_id` values are silently deduplicated.

```
POST /api/connectors/{connector_id}/events
Content-Type: application/json

[
  {
    "event_type": "run.created",
    "event_id": "gh-review-pr42-start",
    "timestamp": "2026-05-01T10:00:00Z",
    "payload": {
      "title": "Code Review PR #42",
      "input_summary": "Review hermes-free PR #42: Add connector framework",
      "status": "running"
    }
  }
]
```

The response returns a `resource_id` (the run ID) for each accepted event. Use it in subsequent events:

```
POST /api/connectors/{connector_id}/events
[
  {
    "event_type": "span.created",
    "event_id": "gh-review-pr42-fetch",
    "run_id": "<run_id>",
    "timestamp": "2026-05-01T10:00:05Z",
    "payload": {
      "span_type": "tool_call",
      "title": "Fetch PR #42 diff",
      "status": "completed",
      "tool_name": "github_get_diff"
    }
  },
  {
    "event_type": "span.created",
    "event_id": "gh-review-pr42-gpt4",
    "run_id": "<run_id>",
    "timestamp": "2026-05-01T10:00:10Z",
    "payload": {
      "span_type": "model_call",
      "title": "GPT-4o review",
      "status": "completed",
      "model_name": "gpt-4o",
      "input_tokens": 3200,
      "output_tokens": 800,
      "cost": 0.032
    }
  },
  {
    "event_type": "span.created",
    "event_id": "gh-review-pr42-claude",
    "run_id": "<run_id>",
    "timestamp": "2026-05-01T10:00:15Z",
    "payload": {
      "span_type": "model_call",
      "title": "Claude review",
      "status": "completed",
      "model_name": "claude-sonnet",
      "input_tokens": 2800,
      "output_tokens": 600,
      "cost": 0.021
    }
  },
  {
    "event_type": "span.created",
    "event_id": "gh-review-pr42-consensus",
    "run_id": "<run_id>",
    "timestamp": "2026-05-01T10:00:20Z",
    "payload": {
      "span_type": "system_event",
      "title": "Consensus check",
      "status": "completed"
    }
  },
  {
    "event_type": "artifact.created",
    "event_id": "gh-review-pr42-result",
    "run_id": "<run_id>",
    "timestamp": "2026-05-01T10:00:22Z",
    "payload": {
      "artifact_type": "report",
      "title": "Review result for PR #42",
      "content_text": "## Consensus Issues\n1. Missing error handling in connector.py\n2. Inconsistent naming in schema"
    }
  },
  {
    "event_type": "run.updated",
    "event_id": "gh-review-pr42-done",
    "run_id": "<run_id>",
    "timestamp": "2026-05-01T10:00:25Z",
    "payload": {
      "status": "completed",
      "output_summary": "2 consensus issues found",
      "total_tokens": 7400,
      "total_cost": 0.053
    }
  }
]
```

## Adapter Code (Python)

```python
import httpx

class GitHubReviewConnector:
    """Maps code review pipeline events to the connector event API."""

    def __init__(self, control_plane_url: str, connector_id: str):
        self.base_url = control_plane_url
        self.connector_id = connector_id
        self._events: list[dict] = []

    def _add_event(self, event_type: str, event_id: str, payload: dict,
                   run_id: str | None = None, timestamp: str | None = None):
        event = {
            "event_type": event_type,
            "event_id": event_id,
            "payload": payload,
        }
        if run_id:
            event["run_id"] = run_id
        if timestamp:
            event["timestamp"] = timestamp
        self._events.append(event)

    async def flush(self):
        """Send all buffered events in one batch."""
        if not self._events:
            return
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/connectors/{self.connector_id}/events",
                json=self._events,
            )
            resp.raise_for_status()
        self._events.clear()

    def on_review_start(self, pr_number: int, repo: str, event_id: str):
        self._add_event("run.created", event_id, {
            "title": f"Code Review PR #{pr_number}",
            "input_summary": f"Review {repo} PR #{pr_number}",
        })

    def on_model_review(self, run_id: str, model: str, result: dict, event_id: str):
        self._add_event("span.created", event_id, {
            "span_type": "model_call",
            "title": f"{model} review",
            "status": "completed",
            "model_name": model,
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
            "cost": result.get("cost"),
        }, run_id=run_id)

    def on_review_complete(self, run_id: str, summary: str, cost: float,
                           tokens: int, event_id: str):
        self._add_event("run.updated", event_id, {
            "status": "completed",
            "output_summary": summary,
            "total_cost": cost,
            "total_tokens": tokens,
        }, run_id=run_id)
```

## Migration Steps

1. Keep existing code review pipeline code as-is.
2. Create a `ConnectorConfig` in the control plane for the review pipeline.
3. Replace direct API calls (`POST /api/runs`, `POST /api/runs/{id}/spans`) with the connector event adapter.
4. Adapter buffers events and sends them as a batch to `POST /api/connectors/{id}/events`.
5. Control plane stores data in PostgreSQL.
6. Frontend reads from generic Run/Trace API — no review-specific endpoints needed.
7. Event deduplication via `event_id` prevents duplicate data on retries.
