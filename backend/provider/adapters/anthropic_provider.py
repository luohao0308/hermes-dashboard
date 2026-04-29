"""Anthropic provider adapter."""

from typing import AsyncIterator, Optional

import anthropic

from ..interface import ChatMessage, ChatResponse, StreamChunk, LLMProvider
from ..registry import _get_api_key


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider using the official SDK."""

    def __init__(self, client: anthropic.AsyncAnthropic, default_model: str) -> None:
        self._client = client
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def supported_features(self) -> list[str]:
        return ["chat", "streaming", "vision", "function_calling"]

    def _split_system(
        self, messages: list[ChatMessage]
    ) -> tuple[str, list[dict]]:
        """Extract system message (Anthropic uses a separate system param)."""
        system = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})
        return system, chat_msgs

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        system, chat_msgs = self._split_system(messages)
        kwargs = {
            "model": model or self._default_model,
            "messages": chat_msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        response = await self._client.messages.create(**kwargs)
        content = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return ChatResponse(
            content=content,
            model=response.model,
            provider="anthropic",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason or "end_turn",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        system, chat_msgs = self._split_system(messages)
        kwargs = {
            "model": model or self._default_model,
            "messages": chat_msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(delta=text)
            yield StreamChunk(delta="", finish_reason="end_turn")

    async def list_models(self) -> list[dict]:
        # Anthropic doesn't have a list models endpoint; return configured models
        return [
            {"id": self._default_model, "owned_by": "anthropic"},
        ]

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model=self._default_model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False


def create_anthropic_provider(config: dict) -> Optional[AnthropicProvider]:
    """Factory: create an Anthropic provider from config."""
    api_key = _get_api_key(config.get("api_key_env", "ANTHROPIC_API_KEY"))
    if not api_key:
        return None
    client = anthropic.AsyncAnthropic(api_key=api_key)
    default_model = config.get("default_model", "claude-sonnet-4-20250514")
    return AnthropicProvider(client, default_model)
