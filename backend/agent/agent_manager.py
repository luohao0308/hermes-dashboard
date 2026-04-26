"""Agent manager — dynamically loads agents from config and wires up handoffs."""

from typing import Optional

from agents import Agent, handoff

from .client import get_model
from .config_loader import load_config, save_config, get_default_config


def _build_agent(key: str, cfg: dict) -> Agent:
    """Build a single Agent from config dict."""
    return Agent(
        name=cfg.get("name", key),
        model=get_model(),
        instructions=cfg.get("instructions", f"You are {cfg.get('name', key)}."),
    )


class _AgentRegistry:
    """Singleton registry — reloads agents from YAML config on demand."""

    _agents: dict[str, Agent] = {}
    _main_key: str = "dispatcher"
    _loaded: bool = False

    def load(self) -> None:
        """Load all agents from config YAML."""
        cfg = load_config()
        self._main_key = cfg.get("main_agent", "dispatcher")
        self._agents = {}

        for key, agent_cfg in cfg.get("agents", {}).items():
            if agent_cfg.get("enabled", True):
                self._agents[key] = _build_agent(key, agent_cfg)

        for custom in cfg.get("custom_agents", []):
            if custom.get("enabled", True):
                self._agents[f"custom_{custom['name']}"] = _build_agent(
                    custom["name"], custom
                )

        self._loaded = True

    def get_main_agent(self) -> Agent:
        if not self._loaded:
            self.load()
        return self._agents.get(self._main_key, self._agents.get("dispatcher"))

    def get_all_agents(self) -> dict[str, Agent]:
        if not self._loaded:
            self.load()
        return self._agents

    def get_configured_main_key(self) -> str:
        if not self._loaded:
            self.load()
        return self._main_key

    def reload(self) -> None:
        """Hot-reload from config."""
        self._loaded = False
        self.load()


_agent_registry = _AgentRegistry()
_agent_registry.load()


def get_main_agent() -> Agent:
    return _agent_registry.get_main_agent()


def get_all_agents() -> dict[str, Agent]:
    return _agent_registry.get_all_agents()


def get_configured_main_key() -> str:
    return _agent_registry.get_configured_main_key()


def reload_agents() -> None:
    _agent_registry.reload()
