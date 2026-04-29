"""Unit tests for the Provider abstraction layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from provider.interface import ChatMessage, ChatResponse, StreamChunk, LLMProvider
from provider.registry import ProviderRegistry, _get_api_key


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class TestChatMessage:
    def test_create(self):
        msg = ChatMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_immutable(self):
        msg = ChatMessage(role="user", content="hello")
        with pytest.raises(AttributeError):
            msg.role = "assistant"


class TestChatResponse:
    def test_create(self):
        resp = ChatResponse(
            content="hi", model="gpt-4o", provider="openai",
            input_tokens=10, output_tokens=5, finish_reason="stop",
        )
        assert resp.model == "gpt-4o"
        assert resp.input_tokens == 10


class TestStreamChunk:
    def test_delta_only(self):
        chunk = StreamChunk(delta="hello")
        assert chunk.delta == "hello"
        assert chunk.finish_reason is None

    def test_finish(self):
        chunk = StreamChunk(delta="", finish_reason="stop")
        assert chunk.finish_reason == "stop"


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    def test_load_config(self, tmp_path):
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(
            'providers:\n  openai:\n    enabled: true\ndefault_provider: "openai"\n'
        )
        with patch("provider.registry._CONFIG_PATH", config_file):
            registry = ProviderRegistry()
        assert registry._config["default_provider"] == "openai"

    def test_register_and_get(self):
        registry = ProviderRegistry()
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "test"
        registry.register(mock_provider)
        assert registry.get("test") is mock_provider
        assert registry.get("nonexistent") is None

    def test_get_default(self):
        registry = ProviderRegistry()
        registry._config = {"default_provider": "openai"}
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "openai"
        registry.register(mock_provider)
        assert registry.get_default() is mock_provider

    def test_list_providers(self):
        registry = ProviderRegistry()
        registry._config = {
            "providers": {"openai": {"enabled": True, "default_model": "gpt-4o", "models": []}},
        }
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "openai"
        mock_provider.supported_features = ["chat", "streaming"]
        registry.register(mock_provider)
        result = registry.list_providers()
        assert len(result) == 1
        assert result[0]["name"] == "openai"

    def test_get_fallback_chain(self):
        registry = ProviderRegistry()
        registry._config = {"fallback_chain": ["openai", "anthropic"]}
        assert registry.get_fallback_chain() == ["openai", "anthropic"]

    def test_get_provider_config(self):
        registry = ProviderRegistry()
        registry._config = {"providers": {"openai": {"enabled": True}}}
        assert registry.get_provider_config("openai") == {"enabled": True}
        assert registry.get_provider_config("missing") == {}

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        registry = ProviderRegistry()
        p1 = AsyncMock(spec=LLMProvider)
        p1.name = "p1"
        p1.health_check.return_value = True
        p2 = AsyncMock(spec=LLMProvider)
        p2.name = "p2"
        p2.health_check.return_value = False
        registry.register(p1)
        registry.register(p2)
        results = await registry.health_check_all()
        assert results == {"p1": True, "p2": False}


# ---------------------------------------------------------------------------
# _get_api_key helper
# ---------------------------------------------------------------------------


class TestGetApiKey:
    def test_from_env(self):
        with patch.dict("os.environ", {"TEST_KEY": "sk-abc"}):
            assert _get_api_key("TEST_KEY") == "sk-abc"

    def test_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("os.path.exists", return_value=False):
                assert _get_api_key("NO_KEY") is None


# ---------------------------------------------------------------------------
# Adapter factories (unit-level, no real API calls)
# ---------------------------------------------------------------------------


class TestAdapterFactory:
    def test_openai_factory_no_key(self):
        from provider.adapters.openai_provider import create_openai_provider
        with patch("provider.adapters.openai_provider._get_api_key", return_value=None):
            assert create_openai_provider({}) is None

    def test_openai_factory_with_key(self):
        from provider.adapters.openai_provider import create_openai_provider
        with patch("provider.adapters.openai_provider._get_api_key", return_value="sk-test"):
            provider = create_openai_provider({"default_model": "gpt-4o"})
        assert provider is not None
        assert provider.name == "openai"

    def test_anthropic_factory_no_key(self):
        from provider.adapters.anthropic_provider import create_anthropic_provider
        with patch("provider.adapters.anthropic_provider._get_api_key", return_value=None):
            assert create_anthropic_provider({}) is None

    def test_anthropic_factory_with_key(self):
        from provider.adapters.anthropic_provider import create_anthropic_provider
        with patch("provider.adapters.anthropic_provider._get_api_key", return_value="sk-ant-test"):
            provider = create_anthropic_provider({})
        assert provider is not None
        assert provider.name == "anthropic"

    def test_ollama_factory(self):
        from provider.adapters.ollama_provider import create_ollama_provider
        provider = create_ollama_provider({"base_url": "http://localhost:11434"})
        assert provider is not None
        assert provider.name == "ollama"

    def test_openai_compat_factory_no_key(self):
        from provider.adapters.openai_compat import create_openai_compat_provider
        with patch("provider.adapters.openai_compat._get_api_key", return_value=None):
            assert create_openai_compat_provider("minimax", {}) is None

    def test_openai_compat_factory_with_key(self):
        from provider.adapters.openai_compat import create_openai_compat_provider
        with patch("provider.adapters.openai_compat._get_api_key", return_value="sk-test"):
            provider = create_openai_compat_provider("deepseek", {"base_url": "https://api.deepseek.com/v1"})
        assert provider is not None
        assert provider.name == "deepseek"


# ---------------------------------------------------------------------------
# Anthropic _split_system helper
# ---------------------------------------------------------------------------


class TestAnthropicSplitSystem:
    def test_split_system(self):
        from provider.adapters.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(MagicMock(), "claude-sonnet-4-20250514")
        messages = [
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="Hello"),
        ]
        system, chat_msgs = provider._split_system(messages)
        assert system == "You are helpful"
        assert len(chat_msgs) == 1
        assert chat_msgs[0]["role"] == "user"

    def test_no_system(self):
        from provider.adapters.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(MagicMock(), "claude-sonnet-4-20250514")
        messages = [ChatMessage(role="user", content="Hello")]
        system, chat_msgs = provider._split_system(messages)
        assert system == ""
        assert len(chat_msgs) == 1
