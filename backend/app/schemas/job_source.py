"""Pydantic v2 schemas for JobSource CRUD."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


class ScrapeConfig(BaseModel):
    """Configurable parameters that control how a source is scraped."""

    max_pages: int = 5
    delay: int = 2
    extract_fields: list[str] = []
    headless: bool = True


class JobSourceCreate(BaseModel):
    """Schema for creating a new job source."""

    name: str
    platform: str
    url: HttpUrl
    scrape_config: ScrapeConfig = ScrapeConfig()
    schedule: str = "manual"


class JobSourceUpdate(BaseModel):
    """Schema for partially updating an existing job source."""

    name: str | None = None
    url: HttpUrl | None = None
    scrape_config: ScrapeConfig | None = None
    is_active: bool | None = None
    schedule: str | None = None


class JobSourceResponse(BaseModel):
    """Full job-source representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # UUID as string for JSON serialisation
    name: str
    platform: str
    url: str
    scrape_config: dict
    is_active: bool
    schedule: str
    last_scraped_at: datetime | None
    leads_count: int = 0
    created_at: datetime
