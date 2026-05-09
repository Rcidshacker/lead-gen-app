"""Import all ORM models so Alembic (and Base.metadata) can discover them.

This module MUST be imported before any migration or metadata reflection
is performed.  Each model registers itself with ``Base`` at import time.
"""

from app.models.export import Export  # noqa: F401
from app.models.job_source import JobSource  # noqa: F401
from app.models.lead import Lead  # noqa: F401
from app.models.scraping_job import ScrapingJob  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "User",
    "JobSource",
    "Lead",
    "ScrapingJob",
    "Export",
]
