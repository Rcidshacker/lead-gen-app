"""Pydantic v2 schemas for Export CRUD."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExportCreate(BaseModel):
    """Schema for requesting a new data export."""

    format: str = "csv"
    filters: dict = {}


class ExportResponse(BaseModel):
    """Export record representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # UUID as string
    format: str
    filters: dict
    file_url: str
    created_at: datetime
