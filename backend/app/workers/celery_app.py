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
# periodic scrape task for each one using its ``schedule`` enum column.
# The ``ScrapeSchedule`` enum values are mapped to crontab expressions:
#   hourly  -> "0 * * * *"
#   daily   -> "0 0 * * *"
#   weekly  -> "0 0 * * 0"
#   manual  -> skipped (no automatic schedule)
#
# New sources added via the API will be picked up on the next worker restart
# or after a SIGHUP. For fully dynamic scheduling without restarts,
# consider migrating to django-celery-beat in a future iteration.
# ---------------------------------------------------------------------------

# Map ScrapeSchedule enum values -> Celery crontab() kwargs
_SCHEDULE_TO_CRON = {
    "hourly": {"minute": "0", "hour": "*"},
    "daily": {"minute": "0", "hour": "0"},
    "weekly": {"minute": "0", "hour": "0", "day_of_week": "0"},
    # "manual" is intentionally omitted - no periodic schedule
}


@celery_app.on_after_finalize.connect
def setup_source_schedules(sender, **kwargs):
    """Register a periodic scrape task for every active JobSource.

    Queries the ``schedule`` enum column (not a non-existent ``schedule_cron``
    text column) and maps each value to a Celery crontab schedule.  Sources
    with ``schedule = 'manual'`` are skipped entirely.
    """
    try:
        import logging
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        sync_url = os.environ.get("DATABASE_SYNC_URL", "")
        if not sync_url:
            logging.getLogger(__name__).warning(
                "DATABASE_SYNC_URL not set - skipping dynamic source scheduling"
            )
            return

        engine = create_engine(sync_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            # Query the `schedule` column (enum: hourly/daily/weekly/manual)
            # and skip sources with schedule='manual' - they have no cron.
            rows = session.execute(
                text(
                    "SELECT id, name, schedule FROM job_sources "
                    "WHERE is_active = true AND schedule IS NOT NULL "
                    "AND schedule != 'manual'"
                )
            ).fetchall()

        for row in rows:
            source_id, name, schedule_value = row

            cron_kwargs = _SCHEDULE_TO_CRON.get(schedule_value)
            if cron_kwargs is None:
                continue  # unknown or manual schedule - skip

            sender.add_periodic_task(
                crontab(**cron_kwargs),
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
        # Don't raise - beat must start even if DB is temporarily unavailable
