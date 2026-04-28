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
    assert "create_alert_summary" in names
    assert "terminal_session_list" in names


def test_guardrail_allows_read_tools():
    spec = next(tool for tool in list_tool_specs() if tool["name"] == "get_status")
    decision = evaluate_tool_call(spec)
    policies = list_tool_policies()

    assert decision["risk"] == "read"
    assert decision["decision"] == "allow"
    assert any(policy["risk"] == "destructive" for policy in policies)


def test_guardrail_confirms_dangerous_shell_params():
    decision = evaluate_tool_call(
        {"name": "shell_command", "risk": "read"},
        {"command": "rm -rf tmp/cache"},
    )

    assert decision["decision"] == "confirm"
    assert decision["risk"] == "execute"
    assert decision["dynamic_signal"] == "dangerous_shell"


def test_guardrail_confirms_dangerous_file_params():
    decision = evaluate_tool_call(
        {"name": "file_operation", "risk": "read"},
        {"action": "delete", "path": "backend/data/agent_traces.sqlite3"},
    )

    assert decision["decision"] == "confirm"
    assert decision["risk"] == "execute"
    assert decision["dynamic_signal"] == "dangerous_file"


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


@pytest.mark.asyncio
async def test_execute_create_alert_summary_uses_dashboard_api():
    async def fake_hermes_get(endpoint, params=None):
        return {}

    async def fake_dashboard_get(endpoint, params=None):
        assert endpoint == "/api/alerts"
        assert params == {"limit": 2}
        return {
            "generated_at": "2026-04-29T00:00:00",
            "total": 2,
            "alerts": [
                {"id": "a1", "severity": "critical", "title": "Gateway down", "source": "status"},
                {"id": "a2", "severity": "warning", "title": "Idle session", "source": "session"},
            ],
        }

    result = await execute_tool(
        "create_alert_summary",
        {"limit": 2},
        fake_hermes_get,
        fake_dashboard_get,
    )

    assert result["severity_counts"]["critical"] == 1
    assert result["severity_counts"]["warning"] == 1
    assert result["summary"] == "1 critical, 1 warning, 0 info alerts"


@pytest.mark.asyncio
async def test_execute_terminal_session_list_summarizes_state():
    async def fake_hermes_get(endpoint, params=None):
        return {}

    async def fake_dashboard_get(endpoint, params=None):
        assert endpoint == "/api/terminal/sessions"
        return {
            "total": 2,
            "sessions": [
                {
                    "session_id": "term-1",
                    "pid": 123,
                    "alive": True,
                    "is_attached": True,
                    "attach_count": 2,
                    "pending_dangerous_command": "rm -rf tmp",
                },
                {
                    "session_id": "term-2",
                    "pid": 456,
                    "alive": False,
                    "is_attached": False,
                    "attach_count": 0,
                    "pending_dangerous_command": None,
                },
            ],
        }

    result = await execute_tool(
        "terminal_session_list",
        {},
        fake_hermes_get,
        fake_dashboard_get,
    )

    assert result["total"] == 2
    assert result["alive_count"] == 1
    assert result["attached_count"] == 1
    assert result["pending_dangerous_count"] == 1
    assert result["sessions"][0]["has_pending_dangerous_command"] is True
