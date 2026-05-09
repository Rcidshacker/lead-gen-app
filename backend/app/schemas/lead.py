"""Pydantic v2 schemas for Lead CRUD and filtering."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LeadResponse(BaseModel):
    """Full lead representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    platform: str
    title: str
    company: str
    location: str
    salary: str
    description: str
    requirements: str
    contact_info: dict
    url: str
    score: float
    status: str
    created_at: datetime
    updated_at: datetime


class LeadUpdate(BaseModel):
    """Schema for partially updating a lead (status change, notes, etc.)."""

    status: str | None = None
    notes: str | None = None


class LeadFilters(BaseModel):
    """Query parameters for filtering and searching leads."""

    min_score: float | None = None
    max_score: float | None = None
    status: str | None = None
    platform: str | None = None
    search: str | None = None
    source_id: uuid.UUID | None = None


class LeadListResponse(BaseModel):
    """Paginated list of leads."""

    items: list[LeadResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
