"""Shared test configuration — sets env vars before any module imports."""

from __future__ import annotations

import os

# Must be set before any import that triggers Settings instantiation
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SERVICE_TOKENS", "test-token-abc,test-token-xyz")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-do-not-use-in-prod")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB = os.environ.get("TEST_DATABASE_URL")


def _make_client(engine_obj, role: str = "operator"):
    """Create a TestClient with the given X-User-Role header."""
    from database import get_db
    from main import app

    connection = engine_obj.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    def _override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app, headers={"X-User-Role": role})
    client._test_transaction = transaction  # type: ignore[attr-defined]
    client._test_connection = connection  # type: ignore[attr-defined]
    client._test_app = app  # type: ignore[attr-defined]
    client._test_session = session  # type: ignore[attr-defined]
    return client


def _cleanup_client(c):
    """Rollback and close a test client's DB resources."""
    c._test_transaction.rollback()  # type: ignore[attr-defined]
    c._test_connection.close()  # type: ignore[attr-defined]
    c._test_app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.fixture(scope="module")
def engine():
    """Create test database engine. Skips if TEST_DATABASE_URL not set."""
    if not TEST_DB:
        pytest.skip("TEST_DATABASE_URL not set")
    eng = create_engine(TEST_DB, pool_pre_ping=True)
    from database import Base
    Base.metadata.create_all(eng)
    yield eng
    # Truncate all tables to prevent cross-module data pollution.
    with eng.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    # Reset global repository singletons set by configure_pg_repositories().
    # Some test files create TestClient(app) which triggers lifespan and sets these.
    _reset_global_repos()
    eng.dispose()


@pytest.fixture(autouse=True, scope="module")
def _reset_repos_per_module():
    """Reset global repository singletons at the start of each test module.

    Some test files create TestClient(app) which triggers lifespan and sets
    global singletons via configure_pg_repositories(). Without resetting,
    subsequent modules that expect local stores (SQLite) would use PG repos.
    """
    _reset_global_repos()
    yield
    _reset_global_repos()


def _reset_global_repos():
    """Reset module-level repository singletons to prevent cross-module pollution."""
    try:
        from review import review_store
        review_store._review_repo = None
    except ImportError:
        pass
    try:
        from agent import tracing_store
        tracing_store._trace_repo = None
    except ImportError:
        pass
    try:
        from agent import guardrails
        guardrails._approval_repo = None
    except ImportError:
        pass
    try:
        from agent import chat_manager
        chat_manager._chat_repo = None
    except ImportError:
        pass
    try:
        import cost_tracker
        cost_tracker._cost_repo = None
    except ImportError:
        pass


@pytest.fixture()
def client(engine):
    """TestClient with operator role (default for write-operation tests)."""
    c = _make_client(engine, role="operator")
    yield c
    _cleanup_client(c)


@pytest.fixture()
def viewer_client(engine):
    """TestClient with viewer role (read-only)."""
    c = _make_client(engine, role="viewer")
    yield c
    _cleanup_client(c)


@pytest.fixture()
def admin_client(engine):
    """TestClient with admin role."""
    c = _make_client(engine, role="admin")
    yield c
    _cleanup_client(c)


@pytest.fixture()
def db(engine):
    """Raw SQLAlchemy session for repository-level tests (no HTTP, no RBAC)."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
