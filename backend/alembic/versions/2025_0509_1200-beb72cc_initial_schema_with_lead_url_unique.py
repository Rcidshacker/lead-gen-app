"""initial_schema_with_lead_url_unique

Revision ID: beb72cc_initial
Revises: None
Create Date: 2025-05-09 12:00:00.000000

Initial migration capturing the full LeadForge schema:
  - users
  - job_sources
  - leads (with unique constraint + index on url)
  - scraping_jobs
  - exports
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "beb72cc_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create ENUM types ────────────────────────────────────────────────
    platform_type = postgresql.ENUM(
        "linkedin", "naukri", "upwork", "indeed", "custom",
        name="platform_type",
        create_type=False,
    )
    platform_type.create(op.get_bind(), checkfirst=True)

    scrape_schedule = postgresql.ENUM(
        "hourly", "daily", "weekly", "manual",
        name="scrape_schedule",
        create_type=False,
    )
    scrape_schedule.create(op.get_bind(), checkfirst=True)

    lead_status = postgresql.ENUM(
        "new", "contacted", "interested", "rejected", "hired",
        name="lead_status",
        create_type=False,
    )
    lead_status.create(op.get_bind(), checkfirst=True)

    job_status = postgresql.ENUM(
        "pending", "running", "completed", "failed",
        name="job_status",
        create_type=False,
    )
    job_status.create(op.get_bind(), checkfirst=True)

    export_format = postgresql.ENUM(
        "csv", "json",
        name="export_format",
        create_type=False,
    )
    export_format.create(op.get_bind(), checkfirst=True)

    # ── Table: users ─────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── Table: job_sources ───────────────────────────────────────────────
    op.create_table(
        "job_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("platform", platform_type, nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "scrape_config",
            postgresql.JSONB(),
            server_default=sa.text("'{}'"),
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "schedule",
            scrape_schedule,
            nullable=False,
            server_default="manual",
        ),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── Table: leads ─────────────────────────────────────────────────────
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_sources.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("salary", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements", sa.Text(), nullable=False),
        sa.Column(
            "contact_info",
            postgresql.JSONB(),
            server_default=sa.text("'{}'"),
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "raw_data",
            postgresql.JSONB(),
            server_default=sa.text("'{}'"),
        ),
        sa.Column("score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column(
            "status",
            lead_status,
            nullable=False,
            server_default="new",
        ),
        sa.Column("embedding", sa.Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        # Unique constraint on url to prevent duplicate leads
        sa.UniqueConstraint("url", name="uq_leads_url"),
    )
    # Index on url for fast lookups (in addition to unique constraint)
    op.create_index("ix_leads_url", "leads", ["url"], unique=False)

    # ── Table: scraping_jobs ─────────────────────────────────────────────
    op.create_table(
        "scraping_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_sources.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            job_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "leads_found",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── Table: exports ───────────────────────────────────────────────────
    op.create_table(
        "exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("format", export_format, nullable=False),
        sa.Column(
            "filters",
            postgresql.JSONB(),
            server_default=sa.text("'{}'"),
        ),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("exports")
    op.drop_table("scraping_jobs")
    op.drop_index("ix_leads_url", table_name="leads")
    op.drop_table("leads")
    op.drop_table("job_sources")
    op.drop_table("users")

    postgresql.ENUM(name="export_format").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="job_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="lead_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="scrape_schedule").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="platform_type").drop(op.get_bind(), checkfirst=True)
