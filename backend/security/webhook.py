"""Webhook signature verification with HMAC-SHA256 and anti-replay.

Verifies incoming webhook payloads using a shared secret.
Includes timestamp-based anti-replay protection.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time


def sign_payload(payload: bytes, secret: str) -> str:
    """Sign a payload with HMAC-SHA256. Returns 'sha256=<hex>' format."""
    digest = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def verify_signature(
    payload: bytes,
    signature: str,
    secret: str,
    tolerance_seconds: int = 300,
) -> bool:
    """Verify webhook signature with anti-replay check.

    Args:
        payload: Raw request body bytes.
        signature: Value of X-Webhook-Signature header.
        secret: Shared webhook secret.
        tolerance_seconds: Max age of timestamp in payload (default 5 min).

    Returns:
        True if signature is valid and timestamp is fresh.

    Raises:
        ValueError: If signature format is invalid or timestamp is stale.
    """
    if not signature:
        raise ValueError("Missing X-Webhook-Signature header")

    if not secret:
        raise ValueError("Webhook secret not configured for this connector")

    # Verify HMAC
    expected = sign_payload(payload, secret)
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid webhook signature")

    # Anti-replay: check timestamp in payload
    try:
        body = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # If payload isn't JSON, skip anti-replay (signature alone is sufficient)
        return True

    if not isinstance(body, dict):
        return True

    ts = body.get("timestamp")
    if ts is None:
        # No timestamp field — skip anti-replay
        return True

    try:
        event_time = float(ts)
    except (ValueError, TypeError):
        # Non-numeric timestamp — try ISO format
        from datetime import datetime
        try:
            event_time = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
        except (ValueError, AttributeError):
            return True  # Can't parse — skip anti-replay

    now = time.time()
    if abs(now - event_time) > tolerance_seconds:
        raise ValueError(
            f"Webhook timestamp is stale (age: {abs(now - event_time):.0f}s, "
            f"tolerance: {tolerance_seconds}s)"
        )

    return True
