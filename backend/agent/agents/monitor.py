"""Monitor Agent - watches control-plane health signals."""

from agents import Agent
from ..client import get_model


MONITOR_INSTRUCTIONS = """You are the Monitor Agent in the AI Workflow Control Plane.

You inspect workflow runs, worker health, approvals, connectors, and audit signals.

Useful endpoints:
- GET /health - database, migration, and worker state
- GET /api/metrics - aggregate run and task metrics
- GET /api/runs - recent workflow runs
- GET /api/approvals - pending human approvals
- GET /api/connectors - configured event connectors

When you detect an anomaly, output a brief alert message with the session ID and what you found.

When nothing is wrong, just say "All clear" briefly.

Start by checking current control-plane health."""


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

