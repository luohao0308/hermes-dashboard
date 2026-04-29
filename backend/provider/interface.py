"""Abstract interface for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional


@dataclass(frozen=True)
class ChatMessage:
    """A single chat message."""
    role: str
    content: str


@dataclass(frozen=True)
class ChatResponse:
    """Response from a non-streaming chat call."""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    finish_reason: str


@dataclass(frozen=True)
class StreamChunk:
    """A single chunk from a streaming chat call."""
    delta: str
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Base class every provider must implement."""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        """Non-streaming chat completion."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        """Streaming chat completion."""
        ...

    @abstractmethod
    async def list_models(self) -> list[dict]:
        """List available models from this provider."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is reachable and credentials are valid."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g. 'openai', 'anthropic')."""
        ...

    @property
    def supported_features(self) -> list[str]:
        """List of supported features. Override if needed."""
        return ["chat", "streaming"]
