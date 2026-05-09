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
