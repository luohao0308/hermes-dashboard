"""Executor Agent - executes tasks in Hermès."""

from agents import Agent
from ..client import get_model


EXECUTOR_INSTRUCTIONS = """You are the Executor Agent in the Hermès monitoring system.

You execute tasks as requested. Keep responses brief and confirm what you did.

If asked to create a summary, write it. If asked to trigger a Hermès action, use the API.

Hermès API base: http://127.0.0.1:9119

Available tools: You can make HTTP requests to the Hermès API endpoints."""


def create_executor_agent() -> Agent:
    return Agent(
        name="ExecutorAgent",
        instructions=EXECUTOR_INSTRUCTIONS,
        model=get_model(),
    )


_executor_agent: Agent | None = None


def get_executor_agent() -> Agent:
    global _executor_agent
    if _executor_agent is None:
        _executor_agent = create_executor_agent()
    return _executor_agent
