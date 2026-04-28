"""SDK-ready Hermès read-only tool specs and executors."""

from typing import Any, Awaitable, Callable, Optional

HermesGet = Callable[[str, Optional[dict[str, Any]]], Awaitable[dict[str, Any]]]
DashboardGet = Callable[[str, Optional[dict[str, Any]]], Awaitable[dict[str, Any]]]


TOOL_SPECS: dict[str, dict[str, Any]] = {
    "get_status": {
        "name": "get_status",
        "description": "Read Hermès gateway and runtime status.",
        "risk": "read",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    "search_sessions": {
        "name": "search_sessions",
        "description": "Search Hermès sessions by text query.",
        "risk": "read",
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "minLength": 1, "maxLength": 200},
            },
            "required": ["q"],
            "additionalProperties": False,
        },
    },
    "get_session_messages": {
        "name": "get_session_messages",
        "description": "Read messages for a Hermès session.",
        "risk": "read",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "minLength": 1, "maxLength": 200},
            },
            "required": ["session_id"],
            "additionalProperties": False,
        },
    },
    "get_logs": {
        "name": "get_logs",
        "description": "Read recent Hermès logs.",
        "risk": "read",
        "input_schema": {
            "type": "object",
            "properties": {
                "lines": {"type": "integer", "minimum": 1, "maximum": 500},
                "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                "component": {"type": "string", "maxLength": 100},
            },
            "additionalProperties": False,
        },
    },
    "get_model_info": {
        "name": "get_model_info",
        "description": "Read current model metadata.",
        "risk": "read",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    "create_alert_summary": {
        "name": "create_alert_summary",
        "description": "Create a compact summary of current Hermès alerts for Monitor Agent triage.",
        "risk": "read",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "additionalProperties": False,
        },
    },
    "terminal_session_list": {
        "name": "terminal_session_list",
        "description": "List browser terminal sessions and summarize attachment and pending command state.",
        "risk": "read",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}


def list_tool_specs() -> list[dict[str, Any]]:
    return list(TOOL_SPECS.values())


async def execute_tool(
    name: str,
    params: dict[str, Any],
    hermes_get: HermesGet,
    dashboard_get: Optional[DashboardGet] = None,
) -> dict[str, Any]:
    if name not in TOOL_SPECS:
        raise ValueError(f"Unknown tool: {name}")
    _validate_params(name, params)

    if name == "get_status":
        return await hermes_get("/api/status", None)
    if name == "search_sessions":
        return await hermes_get("/api/sessions/search", {"q": params["q"]})
    if name == "get_session_messages":
        return await hermes_get(f"/api/sessions/{params['session_id']}/messages", None)
    if name == "get_logs":
        query = {
            "lines": params.get("lines", 100),
            "level": params.get("level", "INFO"),
        }
        if params.get("component"):
            query["component"] = params["component"]
        return await hermes_get("/api/logs", query)
    if name == "get_model_info":
        return await hermes_get("/api/model/info", None)
    if name == "create_alert_summary":
        if dashboard_get is None:
            raise ValueError("Dashboard API access is required for create_alert_summary")
        data = await dashboard_get("/api/alerts", {"limit": params.get("limit", 10)})
        return _summarize_alerts(data)
    if name == "terminal_session_list":
        if dashboard_get is None:
            raise ValueError("Dashboard API access is required for terminal_session_list")
        data = await dashboard_get("/api/terminal/sessions", None)
        return _summarize_terminal_sessions(data)

    raise ValueError(f"Unhandled tool: {name}")


def _validate_params(name: str, params: dict[str, Any]) -> None:
    if not isinstance(params, dict):
        raise ValueError("Tool params must be an object")
    schema = TOOL_SPECS[name]["input_schema"]
    required = schema.get("required", [])
    for key in required:
        if key not in params:
            raise ValueError(f"Missing required param: {key}")
    allowed = set(schema.get("properties", {}).keys())
    unknown = set(params.keys()) - allowed
    if unknown:
        raise ValueError(f"Unknown params: {', '.join(sorted(unknown))}")

    if name == "get_logs":
        lines = params.get("lines", 100)
        if not isinstance(lines, int) or lines < 1 or lines > 500:
            raise ValueError("lines must be an integer between 1 and 500")
        level = params.get("level", "INFO")
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValueError("level must be DEBUG, INFO, WARNING, or ERROR")
    if name == "create_alert_summary":
        limit = params.get("limit", 10)
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            raise ValueError("limit must be an integer between 1 and 50")


def _summarize_alerts(data: dict[str, Any]) -> dict[str, Any]:
    alerts = data.get("alerts", [])
    if not isinstance(alerts, list):
        alerts = []
    counts = {"critical": 0, "warning": 0, "info": 0}
    compact_alerts = []
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        severity = str(alert.get("severity") or "info")
        counts[severity] = counts.get(severity, 0) + 1
        compact_alerts.append({
            "id": alert.get("id"),
            "severity": severity,
            "title": alert.get("title"),
            "source": alert.get("source"),
            "session_id": alert.get("session_id"),
            "action_nav": alert.get("action_nav"),
        })
    summary = (
        f"{counts.get('critical', 0)} critical, "
        f"{counts.get('warning', 0)} warning, "
        f"{counts.get('info', 0)} info alerts"
    )
    return {
        "summary": summary,
        "severity_counts": counts,
        "alerts": compact_alerts,
        "total": data.get("total", len(compact_alerts)),
        "generated_at": data.get("generated_at"),
    }


def _summarize_terminal_sessions(data: dict[str, Any]) -> dict[str, Any]:
    sessions = data.get("sessions", [])
    if not isinstance(sessions, list):
        sessions = []
    alive_count = 0
    attached_count = 0
    pending_dangerous_count = 0
    compact_sessions = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        alive = bool(session.get("alive"))
        attached = bool(session.get("is_attached"))
        pending = session.get("pending_dangerous_command")
        alive_count += int(alive)
        attached_count += int(attached)
        pending_dangerous_count += int(bool(pending))
        compact_sessions.append({
            "session_id": session.get("session_id"),
            "pid": session.get("pid"),
            "alive": alive,
            "is_attached": attached,
            "attach_count": session.get("attach_count", 0),
            "has_pending_dangerous_command": bool(pending),
        })
    return {
        "total": data.get("total", len(compact_sessions)),
        "alive_count": alive_count,
        "attached_count": attached_count,
        "pending_dangerous_count": pending_dangerous_count,
        "sessions": compact_sessions,
    }
