"""Database engine, session factories, and FastAPI dependency.

Provides both async (for FastAPI) and sync (for Celery workers) session
factories so the entire application shares a single source of truth for
DB connectivity.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# ── Async engine & session (FastAPI / async code) ─────────────────
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Sync engine & session (Celery workers / migration scripts) ────
sync_engine = create_engine(
    settings.DATABASE_SYNC_URL,
    echo=settings.APP_ENV == "development",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)


# ── Declarative base ──────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


# ── FastAPI dependency ────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and guarantee it is closed."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
