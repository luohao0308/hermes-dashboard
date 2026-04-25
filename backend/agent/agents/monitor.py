"""Monitor Agent - watches Hermès sessions for anomalies."""

import asyncio
import httpx
from datetime import datetime
from agents import Agent
from ..client import get_model


MONITOR_INSTRUCTIONS = """You are the Monitor Agent in the Hermès system.

You periodically check Hermès session status and report anomalies.

Check Hermès at http://127.0.0.1:9119/api/sessions?limit=10

Anomalies to report:
- Session with is_active=true but no activity for > 5 minutes
- Session with end_reason that looks like an error (not "cli_close", not null)
- Session where tool_call_count is very high (>100) indicating possible runaway loop
- Any session where cost_status is "estimated" and estimated_cost_usd > $1.00

When you detect an anomaly, output a brief alert message with the session ID and what you found.

When nothing is wrong, just say "All clear" briefly.

Start by checking the current sessions now."""

_hermes_base = "http://127.0.0.1:9119"


def create_monitor_agent() -> Agent:
    return Agent(
        name="MonitorAgent",
        instructions=MONITOR_INSTRUCTIONS,
        model=get_model(),
    )


_monitor_agent: Agent | None = None


def get_monitor_agent() -> Agent:
    global _monitor_agent
    if _monitor_agent is None:
        _monitor_agent = create_monitor_agent()
    return _monitor_agent


async def check_hermes_sessions() -> dict:
    """Poll Hermès sessions API. Returns list of sessions."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_hermes_base}/api/sessions", params={"limit": 10})
            if resp.status_code == 200:
                data = resp.json()
                return data.get("sessions", [])
    except Exception:
        pass
    return []
