"""JobSource ORM model with platform and schedule enumerations."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlatformType(str, enum.Enum):
    """Supported job-board platforms."""

    linkedin = "linkedin"
    naukri = "naukri"
    upwork = "upwork"
    indeed = "indeed"
    custom = "custom"


class ScrapeSchedule(str, enum.Enum):
    """Supported scrape frequencies."""

    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"
    manual = "manual"


class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    platform: Mapped[PlatformType] = mapped_column(
        Enum(PlatformType, name="platform_type"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    scrape_config: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    schedule: Mapped[ScrapeSchedule] = mapped_column(
        Enum(ScrapeSchedule, name="scrape_schedule"),
        default=ScrapeSchedule.manual,
        nullable=False,
    )
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
