import pytest

from agent.tools.hermes_tools import execute_tool, list_tool_specs
from agent.guardrails import (
    create_approval_event,
    evaluate_tool_call,
    list_approval_events,
    list_tool_policies,
    resolve_approval_event,
    validate_approval_event,
)


def test_list_tool_specs_contains_read_tools():
    names = {tool["name"] for tool in list_tool_specs()}

    assert "get_status" in names
    assert "get_logs" in names
    assert "get_session_messages" in names


def test_guardrail_allows_read_tools():
    spec = next(tool for tool in list_tool_specs() if tool["name"] == "get_status")
    decision = evaluate_tool_call(spec)
    policies = list_tool_policies()

    assert decision["risk"] == "read"
    assert decision["decision"] == "allow"
    assert any(policy["risk"] == "destructive" for policy in policies)


def test_guardrail_approval_event_lifecycle():
    spec = {"name": "write_file", "risk": "write"}
    guardrail = {"tool": "write_file", "risk": "write", "decision": "confirm", "description": "needs approval"}
    params = {"path": "README.md", "content": "ok"}

    event = create_approval_event(spec, params, guardrail)
    assert event["status"] == "pending"
    assert any(item["event_id"] == event["event_id"] for item in list_approval_events("pending"))

    with pytest.raises(PermissionError):
        validate_approval_event(event["event_id"], "write_file", params)

    approved = resolve_approval_event(event["event_id"], approved=True, resolved_by="test")
    assert approved is not None
    assert approved["status"] == "approved"
    assert validate_approval_event(event["event_id"], "write_file", params)["status"] == "approved"

    with pytest.raises(ValueError, match="params mismatch"):
        validate_approval_event(event["event_id"], "write_file", {"path": "README.md"})


@pytest.mark.asyncio
async def test_execute_get_logs_validates_and_calls_hermes_get():
    calls = []

    async def fake_hermes_get(endpoint, params=None):
        calls.append((endpoint, params))
        return {"logs": []}

    result = await execute_tool(
        "get_logs",
        {"lines": 25, "level": "ERROR"},
        fake_hermes_get,
    )

    assert result == {"logs": []}
    assert calls == [("/api/logs", {"lines": 25, "level": "ERROR"})]


@pytest.mark.asyncio
async def test_execute_tool_rejects_unknown_params():
    async def fake_hermes_get(endpoint, params=None):
        return {}

    with pytest.raises(ValueError, match="Unknown params"):
        await execute_tool("get_status", {"extra": "nope"}, fake_hermes_get)
