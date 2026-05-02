"""PostgreSQL database connection and session management."""

from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)

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
