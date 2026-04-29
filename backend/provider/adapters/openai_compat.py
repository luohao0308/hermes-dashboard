"""Generic OpenAI-compatible provider adapter.

Works with any API that implements the OpenAI chat completions format:
MiniMax, DeepSeek, Together, Groq, vLLM, etc.
"""

from typing import AsyncIterator, Optional

import openai

from ..interface import ChatMessage, ChatResponse, StreamChunk, LLMProvider
from ..registry import _get_api_key


class OpenAICompatProvider(LLMProvider):
    """Provider for any OpenAI-compatible API."""

    def __init__(
        self, provider_name: str, client: openai.AsyncOpenAI, default_model: str
    ) -> None:
        self._provider_name = provider_name
        self._client = client
        self._default_model = default_model

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def supported_features(self) -> list[str]:
        return ["chat", "streaming"]

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
            provider=self._provider_name,
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
        try:
            models = await self._client.models.list()
            return [{"id": m.id, "owned_by": m.owned_by} for m in models.data]
        except Exception:
            return [{"id": self._default_model, "owned_by": self._provider_name}]

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False


def create_openai_compat_provider(
    name: str, config: dict
) -> Optional[OpenAICompatProvider]:
    """Factory: create an OpenAI-compatible provider from config.

    Args:
        name: Provider name (e.g. "minimax", "deepseek").
        config: Provider config dict with base_url, api_key/api_key_env, default_model.
    """
    # 1. 直接配置的 api_key（自定义 Provider 场景）
    api_key = config.get("api_key")
    # 2. 从环境变量解析
    if not api_key:
        api_key_env = config.get("api_key_env", f"{name.upper()}_API_KEY")
        api_key = _get_api_key(api_key_env)
    if not api_key:
        return None
    base_url = config.get("base_url")
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    default_model = config.get("default_model", "")
    return OpenAICompatProvider(name, client, default_model)
