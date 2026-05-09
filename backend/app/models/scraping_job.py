"""ScrapingJob ORM model with status enumeration."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobStatus(str, enum.Enum):
    """Lifecycle stages for a scraping job."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ScrapingJob(Base):
    __tablename__ = "scraping_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.pending,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    leads_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
