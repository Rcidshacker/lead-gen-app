"""Dashboard statistics endpoint."""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.job_source import JobSource
from app.models.lead import Lead
from app.models.scraping_job import ScrapingJob
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ---------------------------------------------------------------------------
# GET /dashboard/stats
# ---------------------------------------------------------------------------
@router.get("/stats", summary="Dashboard overview statistics")
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return aggregate statistics for the authenticated user's dashboard.

    Includes:
    - total_leads, new_today, avg_score, active_sources
    - leads_by_platform (dict)
    - leads_by_status (dict)
    - recent_scrapes (last 5 scraping jobs)
    """
    user_id = current_user.id

    # ── Total leads ────────────────────────────────────────────────────
    total_leads_q = (
        select(func.count())
        .select_from(
            select(Lead.id)
            .join(JobSource, Lead.source_id == JobSource.id)
            .where(JobSource.user_id == user_id)
            .subquery()
        )
    )
    total_leads: int = (await db.execute(total_leads_q)).scalar_one()

    # ── New today ──────────────────────────────────────────────────────
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    new_today_q = (
        select(func.count())
        .select_from(
            select(Lead.id)
            .join(JobSource, Lead.source_id == JobSource.id)
            .where(JobSource.user_id == user_id, Lead.created_at >= today_start)
            .subquery()
        )
    )
    new_today: int = (await db.execute(new_today_q)).scalar_one()

    # ── Average score ──────────────────────────────────────────────────
    avg_score_q = (
        select(func.avg(Lead.score))
        .join(JobSource, Lead.source_id == JobSource.id)
        .where(JobSource.user_id == user_id)
    )
    avg_score: float | None = (await db.execute(avg_score_q)).scalar_one()
    avg_score = round(avg_score, 1) if avg_score is not None else 0.0

    # ── Active sources ─────────────────────────────────────────────────
    active_sources_q = select(func.count()).where(
        JobSource.user_id == user_id,
        JobSource.is_active.is_(True),
    )
    active_sources: int = (await db.execute(active_sources_q)).scalar_one()

    # ── Leads by platform ──────────────────────────────────────────────
    by_platform_q = (
        select(Lead.platform, func.count().label("cnt"))
        .join(JobSource, Lead.source_id == JobSource.id)
        .where(JobSource.user_id == user_id)
        .group_by(Lead.platform)
    )
    platform_rows = (await db.execute(by_platform_q)).all()
    leads_by_platform = {row.platform: row.cnt for row in platform_rows}

    # ── Leads by status ────────────────────────────────────────────────
    by_status_q = (
        select(Lead.status, func.count().label("cnt"))
        .join(JobSource, Lead.source_id == JobSource.id)
        .where(JobSource.user_id == user_id)
        .group_by(Lead.status)
    )
    status_rows = (await db.execute(by_status_q)).all()
    leads_by_status = {
        (row.status.value if hasattr(row.status, "value") else row.status): row.cnt
        for row in status_rows
    }

    # ── Recent scrapes (last 5) ────────────────────────────────────────
    recent_q = (
        select(ScrapingJob)
        .join(JobSource, ScrapingJob.source_id == JobSource.id)
        .where(JobSource.user_id == user_id)
        .order_by(ScrapingJob.created_at.desc())
        .limit(5)
    )
    recent_rows = (await db.execute(recent_q)).scalars().all()
    recent_scrapes = [
        {
            "id": str(job.id),
            "source_id": str(job.source_id),
            "status": job.status.value if hasattr(job.status, "value") else job.status,
            "leads_found": job.leads_found,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        for job in recent_rows
    ]

    return {
        "total_leads": total_leads,
        "new_today": new_today,
        "avg_score": avg_score,
        "active_sources": active_sources,
        "leads_by_platform": leads_by_platform,
        "leads_by_status": leads_by_status,
        "recent_scrapes": recent_scrapes,
    }
