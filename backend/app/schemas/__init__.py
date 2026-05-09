"""Re-export key Pydantic schemas from every sub-module.

Import this package when you need any schema — it collects all public
symbols in one place for convenience.
"""

from app.schemas.export import ExportCreate, ExportResponse  # noqa: F401
from app.schemas.job_source import (  # noqa: F401
    JobSourceCreate,
    JobSourceResponse,
    JobSourceUpdate,
    ScrapeConfig,
)
from app.schemas.lead import (  # noqa: F401
    LeadFilters,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
)
from app.schemas.scraping_job import (  # noqa: F401
    ScrapingJobListResponse,
    ScrapingJobResponse,
)
from app.schemas.user import (  # noqa: F401
    Token,
    TokenPayload,
    UserCreate,
    UserLogin,
    UserResponse,
)

__all__ = [
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "TokenPayload",
    # JobSource
    "ScrapeConfig",
    "JobSourceCreate",
    "JobSourceUpdate",
    "JobSourceResponse",
    # Lead
    "LeadResponse",
    "LeadUpdate",
    "LeadFilters",
    "LeadListResponse",
    # ScrapingJob
    "ScrapingJobResponse",
    "ScrapingJobListResponse",
    # Export
    "ExportCreate",
    "ExportResponse",
]
