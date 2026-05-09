"""Celery application configuration for LeadForge.

Creates and configures the Celery app instance used by both the worker
processes and the beat scheduler.  Settings are read directly from the
environment (via ``os.environ``) so that we avoid importing the async-aware
``app.config`` module inside the synchronous Celery worker context.
"""

import os
from celery import Celery
from celery.schedules import crontab

# ---------------------------------------------------------------------------
# Build Celery instance
# ---------------------------------------------------------------------------
# We read broker / backend URLs straight from the environment so that no
# async machinery (asyncpg, etc.) is triggered at import time in the worker.
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    "redis://localhost:6379/0",
)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    "redis://localhost:6379/1",
)

celery_app = Celery(
    "leadforge",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# ---------------------------------------------------------------------------
# Serialisation & timezone
# ---------------------------------------------------------------------------
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    result_extended=True,
)

# ---------------------------------------------------------------------------
# Periodic task schedule (Celery Beat)
# ---------------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    "cleanup-old-exports": {
        "task": "app.workers.tasks.cleanup_old_exports_task",
        "schedule": crontab(hour=3, minute=0),  # every day at 03:00 UTC
        "args": (),
    },
}

# ---------------------------------------------------------------------------
# Auto-discover tasks so that ``celery -A app.workers.celery_app`` picks them
# up without extra imports.
# ---------------------------------------------------------------------------
celery_app.autodiscover_tasks(["app.workers"])

# ---------------------------------------------------------------------------
# Dynamic per-source periodic scheduling
# ---------------------------------------------------------------------------
# On worker startup, read active JobSource rows from DB and register a
# periodic scrape task for each one using its schedule_cron field.
# New sources added via the API will be picked up on the next worker restart
# or after a SIGHUP. For fully dynamic scheduling without restarts,
# consider migrating to django-celery-beat in a future iteration.
# ---------------------------------------------------------------------------

@celery_app.on_after_finalize.connect
def setup_source_schedules(sender, **kwargs):
    """Register a periodic scrape task for every active JobSource."""
    try:
        import logging
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        sync_url = os.environ.get("DATABASE_SYNC_URL", "")
        if not sync_url:
            logging.getLogger(__name__).warning(
                "DATABASE_SYNC_URL not set — skipping dynamic source scheduling"
            )
            return

        engine = create_engine(sync_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            # Raw query to avoid importing ORM models at celery startup
            # (which can trigger async engine initialisation prematurely)
            rows = session.execute(
                text(
                    "SELECT id, name, schedule_cron FROM job_sources "
                    "WHERE is_active = true AND schedule_cron IS NOT NULL"
                )
            ).fetchall()

        for row in rows:
            source_id, name, cron_str = row

            # Parse "minute hour day month weekday" cron string
            parts = cron_str.strip().split()
            if len(parts) != 5:
                continue  # skip malformed cron strings

            minute, hour, day_of_month, month, day_of_week = parts

            sender.add_periodic_task(
                crontab(
                    minute=minute,
                    hour=hour,
                    day_of_month=day_of_month,
                    month_of_year=month,
                    day_of_week=day_of_week,
                ),
                sender.signature(
                    "app.workers.tasks.scrape_source_task",
                    args=[str(source_id)],
                ),
                name=f"auto-scrape-{name}-{source_id}",
            )

        engine.dispose()

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "Failed to set up dynamic source schedules: %s", exc
        )
        # Don't raise — beat must start even if DB is temporarily unavailable
