"""Export ORM model with format enumeration."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExportFormat(str, enum.Enum):
    """Supported export file formats."""

    csv = "csv"
    json = "json"


class Export(Base):
    __tablename__ = "exports"

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
    format: Mapped[ExportFormat] = mapped_column(
        Enum(ExportFormat, name="export_format"),
        nullable=False,
    )
    filters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    file_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
