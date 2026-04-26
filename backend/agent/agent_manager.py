"""Agent manager — dynamically loads agents from config and wires up handoffs."""

from typing import Optional

from agents import Agent, handoff

from .client import get_model
from .config_loader import load_config, save_config, get_default_config


def _build_agent(key: str, cfg: dict, handoffs: list[Agent] | None = None) -> Agent:
    """Build a single Agent from config dict."""
    return Agent(
        name=cfg.get("name", key),
        model=get_model(),
        instructions=cfg.get("instructions", f"You are {cfg.get('name', key)}."),
        handoffs=handoffs or [],
    )


class _AgentRegistry:
    """Singleton registry — reloads agents from YAML config on demand."""

    _agents: dict[str, Agent] = {}
    _main_key: str = "dispatcher"
    _loaded: bool = False

    def load(self) -> None:
        """Load all agents from config YAML.

        Two-pass build:
        1. Create all agent instances (no handoffs yet — need all names first).
        2. Wire up handoffs by reading each agent's `handoffs` config list.
        """
        cfg = load_config()
        self._main_key = cfg.get("main_agent", "dispatcher")
        self._agents = {}

        # Pass 1: create bare agents
        for key, agent_cfg in cfg.get("agents", {}).items():
            if agent_cfg.get("enabled", True):
                self._agents[key] = _build_agent(key, agent_cfg)

        for custom in cfg.get("custom_agents", []):
            if custom.get("enabled", True):
                self._agents[f"custom_{custom['name']}"] = _build_agent(
                    custom["name"], custom
                )

        # Pass 2: wire up handoffs using agent names
        self._wire_handoffs(cfg)

        self._loaded = True

    def _wire_handoffs(self, cfg) -> None:
        """Resolve `handoffs` name lists to actual Agent objects."""
        for key, agent_cfg in cfg.get("agents", {}).items():
            if not agent_cfg.get("enabled", True):
                continue
            handoff_names = agent_cfg.get("handoffs", [])
            if not handoff_names:
                continue
            agent = self._agents.get(key)
            if not agent:
                continue

            wired = []
            for name in handoff_names:
                # Find target agent by name (not key)
                target = self._find_agent_by_name(name)
                if target:
                    wired.append(handoff(target))
                # else: name not in config — skip silently (custom agents etc.)

            # Replace the bare agent with a new one that has handoffs
            self._agents[key] = _build_agent(
                key,
                agent_cfg,
                handoffs=wired,
            )

        # Also wire custom agents
        for custom in cfg.get("custom_agents", []):
            if not custom.get("enabled", True):
                continue
            handoff_names = custom.get("handoffs", [])
            if not handoff_names:
                continue
            key = f"custom_{custom['name']}"
            agent = self._agents.get(key)
            if not agent:
                continue
            wired = []
            for name in handoff_names:
                target = self._find_agent_by_name(name)
                if target:
                    wired.append(handoff(target))
            self._agents[key] = _build_agent(key, custom, handoffs=wired)

    def _find_agent_by_name(self, name: str) -> Agent | None:
        """Find an agent by its `name` field (not its config key)."""
        for agent in self._agents.values():
            if agent.name == name:
                return agent
        return None

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
