"""Database connection and session management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text, types
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


DATA_DIR = Path(__file__).resolve().parent / "data"
FALLBACK_SQLITE_PATH = DATA_DIR / "runtime.sqlite3"
FALLBACK_ALEMBIC_VERSION = "009"


def _create_primary_engine():
    return create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )


def _create_sqlite_engine():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{FALLBACK_SQLITE_PATH}",
        connect_args={"check_same_thread": False},
    )


def _patch_metadata_for_sqlite() -> None:
    """Coerce PostgreSQL-only column types so SQLite can build the schema."""
    from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    import models  # noqa: F401  - register ORM tables before create_all()

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, PG_JSONB):
                column.type = types.JSON()
            elif isinstance(column.type, PG_UUID):
                column.type = types.Uuid(as_uuid=True)
            if column.server_default is not None and "now()" in str(column.server_default):
                column.server_default = None


def _seed_sqlite_metadata() -> None:
    """Create the minimal migration bookkeeping expected by /health."""
    from sqlalchemy import text as sql_text

    with engine.begin() as conn:
        conn.execute(
            sql_text(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "version_num VARCHAR(32) NOT NULL"
                ")"
            )
        )
        conn.execute(sql_text("DELETE FROM alembic_version"))
        conn.execute(
            sql_text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
            {"version_num": FALLBACK_ALEMBIC_VERSION},
        )


def _probe_engine(engine) -> None:
    with engine.connect() as db:
        db.execute(text("SELECT 1"))


engine = _create_primary_engine()
try:
    _probe_engine(engine)
except SQLAlchemyError as exc:
    engine.dispose()
    if not settings.enable_sqlite_fallback:
        raise RuntimeError(
            "Database unavailable. Start PostgreSQL, set DATABASE_URL, or enable "
            "ENABLE_SQLITE_FALLBACK=true for local development only."
        ) from exc
    logger.warning(
        "Primary database unavailable; using local SQLite fallback at %s. "
        "This mode is intended for local development only.",
        FALLBACK_SQLITE_PATH,
    )
    engine = _create_sqlite_engine()
    _patch_metadata_for_sqlite()
    Base.metadata.create_all(engine)
    _seed_sqlite_metadata()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        # Force connection to verify DB is reachable (SQLAlchemy uses lazy connections)
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db.close()
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {type(exc).__name__}. Check PostgreSQL and run 'alembic upgrade head'.",
        )
    try:
        yield db
    finally:
        db.close()
