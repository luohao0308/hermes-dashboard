"""SDK-ready Hermès read-only tool specs and executors."""

from typing import Any, Awaitable, Callable, Optional

HermesGet = Callable[[str, Optional[dict[str, Any]]], Awaitable[dict[str, Any]]]


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
}


def list_tool_specs() -> list[dict[str, Any]]:
    return list(TOOL_SPECS.values())


async def execute_tool(
    name: str,
    params: dict[str, Any],
    hermes_get: HermesGet,
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
