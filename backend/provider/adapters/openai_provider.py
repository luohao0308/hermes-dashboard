"""OpenAI provider adapter."""

from typing import AsyncIterator, Optional

import openai

from ..interface import ChatMessage, ChatResponse, StreamChunk, LLMProvider
from ..registry import _get_api_key


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider using the official SDK."""

    def __init__(self, client: openai.AsyncOpenAI, default_model: str) -> None:
        self._client = client
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "openai"

    @property
    def supported_features(self) -> list[str]:
        return ["chat", "streaming", "vision", "function_calling"]

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        response = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        usage = response.usage
        return ChatResponse(
            content=choice.message.content or "",
            model=response.model,
            provider="openai",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        response = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield StreamChunk(delta=delta.content)
            if chunk.choices and chunk.choices[0].finish_reason:
                yield StreamChunk(delta="", finish_reason=chunk.choices[0].finish_reason)

    async def list_models(self) -> list[dict]:
        models = await self._client.models.list()
        return [
            {"id": m.id, "owned_by": m.owned_by}
            for m in models.data
            if "gpt" in m.id
        ]

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False


def create_openai_provider(config: dict) -> Optional[OpenAIProvider]:
    """Factory: create an OpenAI provider from config."""
    api_key = _get_api_key(config.get("api_key_env", "OPENAI_API_KEY"))
    if not api_key:
        return None
    client = openai.AsyncOpenAI(api_key=api_key)
    default_model = config.get("default_model", "gpt-4o")
    return OpenAIProvider(client, default_model)
