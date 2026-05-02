"""Abstract base classes for repository interfaces.

Each repository defines the contract that both SQLite (legacy) and
PostgreSQL implementations must satisfy. Methods return plain dicts
to keep callers storage-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class TraceRepository(ABC):
    """Runs, spans, RCA reports, runbooks, and knowledge search."""

    @abstractmethod
    def create_run(
        self,
        session_id: str,
        agent_id: str,
        input_summary: str,
        linked_session_id: Optional[str] = None,
    ) -> str: ...

    @abstractmethod
    def complete_run(self, run_id: str, status: str = "completed") -> None: ...

    @abstractmethod
    def add_span(
        self,
        run_id: str,
        span_type: str,
        title: str,
        summary: str = "",
        agent_name: Optional[str] = None,
        status: str = "completed",
        metadata: Optional[dict[str, Any]] = None,
    ) -> str: ...

    @abstractmethod
    def get_run(self, run_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def find_latest_run(
        self,
        session_id: Optional[str] = None,
        linked_session_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def list_spans(self, run_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_eval_summary(self) -> dict[str, Any]: ...

    @abstractmethod
    def save_rca_report(
        self,
        session_id: str,
        report: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    def get_latest_rca_report(self, session_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def save_runbook(
        self,
        session_id: str,
        runbook: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    def get_latest_runbook(self, session_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def update_latest_runbook(
        self, session_id: str, runbook: dict[str, Any]
    ) -> dict[str, Any]: ...

    @abstractmethod
    def search_knowledge(
        self, query: str, limit: int = 20
    ) -> list[dict[str, Any]]: ...


class ApprovalRepository(ABC):
    """Guardrail approval events."""

    @abstractmethod
    def create(self, event: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def list(self, status: Optional[str] = None) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get(self, event_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def update(
        self, event_id: str, updates: dict[str, Any]
    ) -> Optional[dict[str, Any]]: ...


class ReviewRepository(ABC):
    """PR code review results."""

    @abstractmethod
    def save(self, review: Any) -> None: ...

    @abstractmethod
    def get(self, review_id: str) -> Optional[Any]: ...

    @abstractmethod
    def list_reviews(
        self,
        repo: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]: ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]: ...


class CostRepository(ABC):
    """API usage cost tracking and budget alerts."""

    @abstractmethod
    def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_per_1k_input: float,
        cost_per_1k_output: float,
        review_id: Optional[str] = None,
        latency_ms: Optional[int] = None,
        status: str = "success",
    ) -> str: ...

    @abstractmethod
    def get_summary(self, period: str = "daily") -> dict[str, Any]: ...

    @abstractmethod
    def get_breakdown(self, days: int = 30) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_trend(self, days: int = 30) -> list[dict[str, Any]]: ...

    @abstractmethod
    def set_budget(
        self,
        scope: str,
        limit_usd: float,
        provider: Optional[str] = None,
        alert_threshold: float = 0.8,
    ) -> None: ...

    @abstractmethod
    def check_alerts(self) -> list[dict[str, Any]]: ...


class ChatRepository(ABC):
    """Chat sessions and messages."""

    @abstractmethod
    def create_session(
        self,
        agent_id: str = "main",
        linked_session_id: Optional[str] = None,
        terminal_session_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def close_session(self, session_id: str) -> bool: ...

    @abstractmethod
    def update_session_agent(self, session_id: str, agent_id: str) -> bool: ...

    @abstractmethod
    def update_session_context(
        self,
        session_id: str,
        title: Optional[str] = None,
        linked_session_id: Optional[str] = None,
        terminal_session_id: Optional[str] = None,
    ) -> bool: ...

    @abstractmethod
    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def list_sessions(self) -> list[dict[str, Any]]: ...
