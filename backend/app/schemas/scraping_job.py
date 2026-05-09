"""Pydantic v2 schemas for ScrapingJob responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScrapingJobResponse(BaseModel):
    """Single scraping-job representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # UUID as string
    source_id: str  # UUID as string
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    leads_found: int
    created_at: datetime


class ScrapingJobListResponse(BaseModel):
    """Paginated list of scraping jobs."""

    items: list[ScrapingJobResponse]
    total: int
    page: int
    per_page: int
