import pytest

from agent.tools.hermes_tools import execute_tool, list_tool_specs
from agent.guardrails import evaluate_tool_call, list_tool_policies


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
