"""Job source CRUD and scraping trigger endpoints."""

import logging
import uuid
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.job_source import JobSource, PlatformType
from app.models.lead import Lead
from app.models.user import User
from app.schemas.job_source import JobSourceCreate, JobSourceResponse, JobSourceUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["Job Sources"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _get_user_source(
    source_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> JobSource:
    """Fetch a source owned by *user_id* or raise 404."""
    result = await db.execute(
        select(JobSource).where(JobSource.id == source_id, JobSource.user_id == user_id)
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


# ---------------------------------------------------------------------------
# GET /sources/
# ---------------------------------------------------------------------------
@router.get("/", response_model=dict, summary="List the user's job sources")
async def list_sources(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    """Return paginated list of job sources for the authenticated user."""
    base = select(JobSource).where(JobSource.user_id == current_user.id)
    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    items_q = (
        base.order_by(JobSource.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = (await db.execute(items_q)).scalars().all()

    # Enrich with lead count
    items = []
    for src in rows:
        lc = (await db.execute(
            select(func.count()).select_from(
                select(Lead.id).where(Lead.source_id == src.id).subquery()
            )
        )).scalar_one()

        items.append(
            JobSourceResponse(
                id=str(src.id),
                name=src.name,
                platform=src.platform.value if isinstance(src.platform, PlatformType) else src.platform,
                url=src.url,
                scrape_config=src.scrape_config,
                is_active=src.is_active,
                schedule=src.schedule.value if hasattr(src.schedule, "value") else src.schedule,
                last_scraped_at=src.last_scraped_at,
                leads_count=lc,
                created_at=src.created_at,
            )
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": ceil(total / per_page) if total else 1,
    }


# ---------------------------------------------------------------------------
# POST /sources/
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=JobSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job source",
)
async def create_source(
    payload: JobSourceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobSourceResponse:
    """Register a new job board source for scraping."""
    source = JobSource(
        user_id=current_user.id,
        name=payload.name,
        platform=PlatformType(payload.platform),
        url=str(payload.url),
        scrape_config=payload.scrape_config.model_dump(),
        schedule=payload.schedule,
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)

    logger.info("User %s created source %s", current_user.email, source.id)
    return JobSourceResponse(
        id=str(source.id),
        name=source.name,
        platform=source.platform.value if isinstance(source.platform, PlatformType) else source.platform,
        url=source.url,
        scrape_config=source.scrape_config,
        is_active=source.is_active,
        schedule=source.schedule.value if hasattr(source.schedule, "value") else source.schedule,
        last_scraped_at=source.last_scraped_at,
        leads_count=0,
        created_at=source.created_at,
    )


# ---------------------------------------------------------------------------
# GET /sources/{source_id}
# ---------------------------------------------------------------------------
@router.get("/{source_id}", response_model=JobSourceResponse, summary="Get source detail")
async def get_source(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobSourceResponse:
    """Return full details for a single job source."""
    src = await _get_user_source(source_id, current_user.id, db)

    lc = (await db.execute(
        select(func.count()).select_from(
            select(Lead.id).where(Lead.source_id == src.id).subquery()
        )
    )).scalar_one()

    return JobSourceResponse(
        id=str(src.id),
        name=src.name,
        platform=src.platform.value if isinstance(src.platform, PlatformType) else src.platform,
        url=src.url,
        scrape_config=src.scrape_config,
        is_active=src.is_active,
        schedule=src.schedule.value if hasattr(src.schedule, "value") else src.schedule,
        last_scraped_at=src.last_scraped_at,
        leads_count=lc,
        created_at=src.created_at,
    )


# ---------------------------------------------------------------------------
# PUT /sources/{source_id}
# ---------------------------------------------------------------------------
@router.put("/{source_id}", response_model=JobSourceResponse, summary="Update a source")
async def update_source(
    source_id: uuid.UUID,
    payload: JobSourceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobSourceResponse:
    """Update an existing job source. Only provided fields are modified."""
    src = await _get_user_source(source_id, current_user.id, db)

    update_data = payload.model_dump(exclude_unset=True)

    if "url" in update_data and update_data["url"] is not None:
        update_data["url"] = str(update_data["url"])

    if "scrape_config" in update_data and update_data["scrape_config"] is not None:
        update_data["scrape_config"] = payload.scrape_config.model_dump()

    for field, value in update_data.items():
        setattr(src, field, value)

    await db.flush()
    await db.refresh(src)

    lc = (await db.execute(
        select(func.count()).select_from(
            select(Lead.id).where(Lead.source_id == src.id).subquery()
        )
    )).scalar_one()

    return JobSourceResponse(
        id=str(src.id),
        name=src.name,
        platform=src.platform.value if isinstance(src.platform, PlatformType) else src.platform,
        url=src.url,
        scrape_config=src.scrape_config,
        is_active=src.is_active,
        schedule=src.schedule.value if hasattr(src.schedule, "value") else src.schedule,
        last_scraped_at=src.last_scraped_at,
        leads_count=lc,
        created_at=src.created_at,
    )


# ---------------------------------------------------------------------------
# DELETE /sources/{source_id}  (soft-delete)
# ---------------------------------------------------------------------------
@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete a source")
async def delete_source(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Deactivate a source without removing it from the database."""
    src = await _get_user_source(source_id, current_user.id, db)
    src.is_active = False
    await db.flush()
    logger.info("User %s deactivated source %s", current_user.email, source_id)


# ---------------------------------------------------------------------------
# POST /sources/{source_id}/scrape
# ---------------------------------------------------------------------------
@router.post(
    "/{source_id}/scrape",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a scrape for a source",
)
async def trigger_scrape(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Create a scraping job and dispatch it to Celery.

    Returns 202 Accepted with the new job details.
    """
    from app.models.scraping_job import JobStatus, ScrapingJob

    src = await _get_user_source(source_id, current_user.id, db)

    if not src.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot scrape an inactive source",
        )

    # Create the job record
    job = ScrapingJob(source_id=src.id, status=JobStatus.pending)
    db.add(job)
    await db.flush()
    await db.refresh(job)

    # Dispatch Celery task (non-blocking; import task lazily to avoid circular deps)
    try:
        from app.workers.tasks import scrape_source_task

        celery_task = scrape_source_task.delay(str(source_id), str(job.id))
        job.celery_task_id = celery_task.id
        await db.flush()
    except Exception as exc:
        logger.exception("Failed to dispatch Celery task for source %s", source_id)
        job.status = JobStatus.failed
        job.error_message = f"Celery dispatch error: {exc}"
        await db.flush()

    logger.info("Scrape job %s dispatched for source %s", job.id, source_id)
    return {
        "id": str(job.id),
        "source_id": str(source_id),
        "status": job.status.value,
        "message": "Scraping job created and dispatched",
    }
