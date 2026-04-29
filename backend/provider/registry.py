"""Provider registry: registration, lookup, lifecycle."""

import os
import yaml
from pathlib import Path
from typing import Optional

from .interface import LLMProvider


_CONFIG_PATH = Path(__file__).parent / "providers.yaml"


class ProviderRegistry:
    """Manages LLM provider instances."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._config: dict = {}
        self._load_config()

    def _load_config(self) -> None:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH) as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {"providers": {}, "default_provider": "openai"}

    def register(self, provider: LLMProvider) -> None:
        """Register a provider instance."""
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[LLMProvider]:
        """Get a provider by name."""
        return self._providers.get(name)

    def get_default(self) -> Optional[LLMProvider]:
        """Get the default provider."""
        default_name = self._config.get("default_provider", "openai")
        return self._providers.get(default_name)

    def list_providers(self) -> list[dict]:
        """List all registered providers with their status."""
        result = []
        for name, provider in self._providers.items():
            provider_config = self._config.get("providers", {}).get(name, {})
            result.append({
                "name": name,
                "enabled": provider_config.get("enabled", True),
                "default_model": provider_config.get("default_model", ""),
                "base_url": provider_config.get("base_url", ""),
                "models": provider_config.get("models", []),
                "supported_features": provider.supported_features,
            })
        return result

    def get_fallback_chain(self) -> list[str]:
        """Get the fallback chain from config."""
        return self._config.get("fallback_chain", [])

    def get_provider_config(self, name: str) -> dict:
        """Get raw config for a provider."""
        return self._config.get("providers", {}).get(name, {})

    def update_provider_config(self, name: str, updates: dict) -> None:
        """Update provider config in memory and persist to YAML."""
        if "providers" not in self._config:
            self._config["providers"] = {}
        if name not in self._config["providers"]:
            self._config["providers"][name] = {}
        self._config["providers"][name].update(updates)
        self._save_config()

    def _save_config(self) -> None:
        with open(_CONFIG_PATH, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

    async def health_check_all(self) -> dict[str, bool]:
        """Run health check on all registered providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results


def _get_api_key(env_var: str) -> Optional[str]:
    """Resolve API key from environment variable."""
    key = os.environ.get(env_var)
    if key:
        return key
    hermes_env = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(hermes_env):
        with open(hermes_env) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{env_var}="):
                    key = line.split("=", 1)[1].strip()
                    if key and key != "***":
                        return key
    return None
