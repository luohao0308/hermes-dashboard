"""Ollama provider adapter for local models."""

from typing import AsyncIterator, Optional

import httpx

from ..interface import ChatMessage, ChatResponse, StreamChunk, LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider using the REST API."""

    def __init__(self, base_url: str, default_model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=120.0)

    @property
    def name(self) -> str:
        return "ollama"

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
        response = await self._client.post(
            "/api/chat",
            json={
                "model": model or self._default_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
        )
        response.raise_for_status()
        data = response.json()
        msg = data.get("message", {})
        return ChatResponse(
            content=msg.get("content", ""),
            model=data.get("model", model or self._default_model),
            provider="ollama",
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        async with self._client.stream(
            "POST",
            "/api/chat",
            json={
                "model": model or self._default_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": True,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                import json

                data = json.loads(line)
                msg = data.get("message", {})
                content = msg.get("content", "")
                if content:
                    yield StreamChunk(delta=content)
                if data.get("done"):
                    yield StreamChunk(delta="", finish_reason="stop")

    async def list_models(self) -> list[dict]:
        response = await self._client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return [
            {"id": m["name"], "owned_by": "ollama"}
            for m in data.get("models", [])
        ]

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False


def create_ollama_provider(config: dict) -> Optional[OllamaProvider]:
    """Factory: create an Ollama provider from config."""
    base_url = config.get("base_url", "http://localhost:11434")
    default_model = config.get("default_model", "llama3.1")
    return OllamaProvider(base_url, default_model)
