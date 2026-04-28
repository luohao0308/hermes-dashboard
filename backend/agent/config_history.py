"""Local Agent config change history."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from agent.config_evaluator import evaluate_agent_config


class ConfigHistory:
    def __init__(self, path: Optional[str] = None):
        self._path = path
        if self._path:
            directory = os.path.dirname(self._path)
            if directory:
                os.makedirs(directory, exist_ok=True)

    def record(
        self,
        action: str,
        before: dict[str, Any],
        after: dict[str, Any],
        actor: str = "dashboard",
        target: Optional[str] = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": str(uuid.uuid4()),
            "action": action,
            "target": target,
            "actor": actor,
            "created_at": datetime.now().isoformat(),
            "before": _summarize_config(before),
            "after": _summarize_config(after),
        }
        if self._path:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def list_events(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self._path or not os.path.exists(self._path):
            return []
        events: list[dict[str, Any]] = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
        return list(reversed(events))[:limit]


def _summarize_config(config: dict[str, Any]) -> dict[str, Any]:
    agents = config.get("agents") or {}
    custom_agents = config.get("custom_agents") or []
    enabled_agents = [
        (agent.get("name") or key)
        for key, agent in agents.items()
        if agent.get("enabled", True)
    ]
    enabled_custom = [
        agent.get("name")
        for agent in custom_agents
        if agent.get("enabled", True)
    ]
    evaluation = evaluate_agent_config(config)
    return {
        "main_agent": config.get("main_agent"),
        "agent_count": len(agents) + len(custom_agents),
        "enabled_count": len(enabled_agents) + len(enabled_custom),
        "enabled_agents": enabled_agents + enabled_custom,
        "score": evaluation.get("score"),
        "grade": evaluation.get("grade"),
        "finding_count": len(evaluation.get("findings", [])),
    }


_default_history_path = os.environ.get(
    "AGENT_CONFIG_HISTORY_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "agent_config_history.jsonl")),
)
config_history = ConfigHistory(path=_default_history_path)
