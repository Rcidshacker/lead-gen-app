"""Alembic environment configuration — async-aware migration runner.

Reads ``DATABASE_URL`` from ``app.config`` at runtime so that migrations
always use the same connection string as the application.  Both offline
(generate SQL script) and online (apply to DB) modes are supported.
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ── Ensure the project root is on sys.path ───────────────────────────────
# This allows ``alembic`` CLI to find ``app.config`` and ``app.models``
# regardless of the working directory from which it is invoked.
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ── Alembic Config object ────────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging (if configured)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import all ORM models so Base.metadata discovers every table ─────────
from app.database import Base  # noqa: E402
import app.models  # noqa: F401, E402  (side-effect: registers all models)

target_metadata = Base.metadata

# ── Read the database URL from the application config ─────────────────────
from app.config import settings  # noqa: E402

# Alembic's ``sqlalchemy.url`` is overridden here so the .ini placeholder
# is never actually used at runtime.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


# ---------------------------------------------------------------------------
# Async helpers
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates a SQL script rather than connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Execute migrations against a live connection (sync wrapper)."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the async engine."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        pool_pre_ping=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
