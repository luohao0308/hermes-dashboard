"""Repository factory — creates PG-backed repositories from a session factory.

Usage:
    from repositories.factory import configure_pg_repositories
    configure_pg_repositories()  # uses default DATABASE_URL

Or with a custom session factory:
    from repositories.factory import create_all_repositories
    repos = create_all_repositories(session_factory)
"""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from database import SessionLocal
from repositories.trace_repository import PgTraceRepository
from repositories.approval_repository import PgApprovalRepository
from repositories.review_repository import PgReviewRepository
from repositories.cost_repository import PgCostRepository
from repositories.chat_repository import PgChatRepository


def create_all_repositories(session_factory: Callable[[], Session]) -> dict[str, Any]:
    """Create all PG repository instances from a session factory callable.

    Args:
        session_factory: A callable that returns a new Session each time it's called.
                         Typically the SessionLocal class from database.py.
    """
    return {
        "trace": PgTraceRepository(session_factory),
        "approval": PgApprovalRepository(session_factory),
        "review": PgReviewRepository(session_factory),
        "cost": PgCostRepository(session_factory),
        "chat": PgChatRepository(session_factory),
    }


def configure_pg_repositories() -> None:
    """Wire PG repositories into existing store modules.

    Call this once at startup (e.g., in main.py lifespan) to enable
    dual-write mode: new writes go to PG, reads try PG then SQLite.

    Passes SessionLocal (the class/factory) rather than SessionLocal()
    (an instance) so each repository operation creates its own session.
    """
    from agent import tracing_store
    from agent import guardrails
    from agent import chat_manager
    from review import review_store
    import cost_tracker

    repos = create_all_repositories(SessionLocal)

    tracing_store.configure_repository(repos["trace"])
    guardrails.configure_approval_repository(repos["approval"])
    chat_manager.configure_chat_repository(repos["chat"])
    review_store.configure_review_repository(repos["review"])
    cost_tracker.configure_cost_repository(repos["cost"])
