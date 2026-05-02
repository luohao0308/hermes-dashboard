"""Connector SDK example — Python client for AI Workflow Control Plane.

Demonstrates:
  - HMAC-SHA256 webhook signature generation
  - Timestamp-based anti-replay
  - Batch event ingestion
  - Retry with exponential backoff
  - event_id idempotency
  - Error handling

Usage:
    export CONNECTOR_URL="http://localhost:8000/api/connectors/YOUR_CONNECTOR_ID/events"
    export WEBHOOK_SECRET="your-webhook-secret"
    export SERVICE_TOKEN="your-service-token"  # alternative to webhook secret
    python python_client.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONNECTOR_URL = os.environ.get(
    "CONNECTOR_URL",
    "http://localhost:8000/api/connectors/00000000-0000-0000-0000-000000000000/events",
)
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
SERVICE_TOKEN = os.environ.get("SERVICE_TOKEN", "")

MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0


# ---------------------------------------------------------------------------
# HMAC-SHA256 signature
# ---------------------------------------------------------------------------


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for a payload.

    Returns:
        Signature in 'sha256=<hex>' format, matching the server's
        X-Webhook-Signature verification.
    """
    digest = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


# ---------------------------------------------------------------------------
# Event builder
# ---------------------------------------------------------------------------


def make_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    run_id: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Build a single connector event with anti-replay timestamp.

    Args:
        event_type: One of the supported ConnectorEventType values.
        payload: Event-type-specific data.
        run_id: Required for span/tool_call/approval/artifact events.
        event_id: Idempotency key. Auto-generated if not provided.

    Returns:
        Event dict ready for JSON serialization.
    """
    return {
        "event_type": event_type,
        "event_id": event_id or str(uuid.uuid4()),
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }


# ---------------------------------------------------------------------------
# HTTP sender with retry
# ---------------------------------------------------------------------------


def send_events(
    events: list[dict[str, Any]],
    *,
    connector_url: str = CONNECTOR_URL,
    webhook_secret: str = WEBHOOK_SECRET,
    service_token: str = SERVICE_TOKEN,
) -> dict[str, Any]:
    """Send a batch of events to the connector ingestion endpoint.

    Implements exponential backoff retry on transient failures (429, 5xx).

    Args:
        events: List of event dicts from make_event().
        connector_url: Full URL to POST /api/connectors/{id}/events.
        webhook_secret: Shared secret for HMAC signing (if using webhook auth).
        service_token: Bearer token (if using service token auth).

    Returns:
        Parsed JSON response from the server.

    Raises:
        HTTPError: On non-transient HTTP errors (4xx except 429).
        RuntimeError: After all retries exhausted.
    """
    body_bytes = json.dumps(events).encode("utf-8")

    headers: dict[str, str] = {
        "Content-Type": "application/json",
    }

    # Auth: prefer service token, fall back to webhook signature
    if service_token:
        headers["Authorization"] = f"Bearer {service_token}"
    elif webhook_secret:
        headers["X-Webhook-Signature"] = sign_payload(body_bytes, webhook_secret)

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            req = Request(connector_url, data=body_bytes, headers=headers, method="POST")
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))

        except HTTPError as exc:
            status = exc.code
            # Retry on 429 (rate limit) and 5xx (server error)
            if status == 429 or status >= 500:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = BACKOFF_BASE_SECONDS * (2 ** attempt)
                    time.sleep(delay)
                    continue
            # Non-transient error — raise immediately
            raise

        except URLError as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                delay = BACKOFF_BASE_SECONDS * (2 ** attempt)
                time.sleep(delay)
                continue

    raise RuntimeError(f"All {MAX_RETRIES} retries exhausted") from last_error


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------


def main() -> None:
    """Demonstrate batch event ingestion with idempotency."""

    run_id = str(uuid.uuid4())

    # Build a batch of events
    events = [
        # 1. Create a run
        make_event("run.created", {
            "title": "Example connector run",
            "status": "running",
            "input_summary": "Processing 3 items",
        }, run_id=run_id),

        # 2. Record a span
        make_event("span.created", {
            "span_type": "llm",
            "title": "GPT-4 completion",
            "status": "completed",
            "model_name": "gpt-4",
            "input_tokens": 500,
            "output_tokens": 200,
            "cost": 0.003,
        }, run_id=run_id),

        # 3. Record a tool call
        make_event("tool_call.created", {
            "tool_name": "search_docs",
            "risk_level": "read",
            "decision": "allow",
            "status": "completed",
            "input_json": {"query": "connector SDK"},
            "output_json": {"results": 5},
        }, run_id=run_id),

        # 4. Complete the run
        make_event("run.updated", {
            "status": "completed",
            "output_summary": "Processed all items successfully",
            "total_tokens": 700,
            "total_cost": 0.003,
        }, run_id=run_id),
    ]

    print(f"Sending {len(events)} events to {CONNECTOR_URL}")
    result = send_events(events)
    print(json.dumps(result, indent=2))

    # Demonstrate idempotency: send the same events again
    print("\nRe-sending same events (should be deduplicated)...")
    result2 = send_events(events)
    print(json.dumps(result2, indent=2))


if __name__ == "__main__":
    main()
