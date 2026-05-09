"""PostgreSQL Row-Level Security (RLS) middleware.

Sets the ``app.current_user_id`` PostgreSQL local variable on every
database connection, enabling RLS policies to enforce tenant isolation
at the database level.  This acts as a safety net — even if application-
layer filtering has a bug, the database will refuse to return or modify
cross-tenant data.

Usage with SQLAlchemy::

    from app.rls import set_rls_context, clear_rls_context

    # In a FastAPI dependency:
    async def get_db():
        async with AsyncSessionLocal() as session:
            await set_rls_context(session, user_id=current_user.id)
            yield session
            await clear_rls_context(session)
"""

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# The PostgreSQL local variable name used by RLS policies
_RLS_USER_VAR = "app.current_user_id"


async def set_rls_context(session: AsyncSession, user_id: UUID) -> None:
    """Set the RLS user context for the current database connection.

    Parameters
    ----------
    session:
        An async SQLAlchemy session.
    user_id:
        The UUID of the currently authenticated user.
    """
    await session.execute(
        text(f"SET LOCAL {_RLS_USER_VAR} = :user_id"),
        {"user_id": str(user_id)},
    )
    logger.debug("RLS context set: user_id=%s", user_id)


async def clear_rls_context(session: AsyncSession) -> None:
    """Clear the RLS user context (reset to unrestricted)."""
    await session.execute(
        text(f"SET LOCAL {_RLS_USER_VAR} = ''"),
    )


def set_rls_context_sync(session: Session, user_id: UUID) -> None:
    """Synchronous version for Celery workers / non-async code."""
    session.execute(
        text(f"SET LOCAL {_RLS_USER_VAR} = :user_id"),
        {"user_id": str(user_id)},
    )


def clear_rls_context_sync(session: Session) -> None:
    """Synchronous version for Celery workers / non-async code."""
    session.execute(
        text(f"SET LOCAL {_RLS_USER_VAR} = ''"),
    )
