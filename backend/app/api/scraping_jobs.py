"""Scraping job listing, detail, and retry endpoints."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.job_source import JobSource
from app.models.scraping_job import JobStatus, ScrapingJob
from app.models.user import User
from app.schemas.scraping_job import ScrapingJobResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Scraping Jobs"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
async def _get_user_job(
    job_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> ScrapingJob:
    """Fetch a scraping job whose source is owned by *user_id*, or raise 404."""
    stmt = (
        select(ScrapingJob)
        .join(JobSource, ScrapingJob.source_id == JobSource.id)
        .where(ScrapingJob.id == job_id, JobSource.user_id == user_id)
    )
    job = (await db.execute(stmt)).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scraping job not found")
    return job


def _job_to_response(job: ScrapingJob) -> dict:
    """Serialise a ScrapingJob ORM object to a plain dict."""
    return {
        "id": str(job.id),
        "source_id": str(job.source_id),
        "status": job.status.value if isinstance(job.status, JobStatus) else job.status,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message,
        "leads_found": job.leads_found,
        "created_at": job.created_at,
    }


# ---------------------------------------------------------------------------
# GET /jobs/
# ---------------------------------------------------------------------------
@router.get("/", summary="List scraping jobs with pagination")
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
) -> dict:
    """Return paginated scraping jobs for the authenticated user."""
    base = (
        select(ScrapingJob)
        .join(JobSource, ScrapingJob.source_id == JobSource.id)
        .where(JobSource.user_id == current_user.id)
    )

    if status_filter is not None:
        try:
            status_enum = JobStatus(status_filter)
            base = base.where(ScrapingJob.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status. Must be one of: {[s.value for s in JobStatus]}",
            )

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    # Paginate
    items_q = (
        base.order_by(ScrapingJob.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = (await db.execute(items_q)).scalars().all()

    return {
        "items": [_job_to_response(j) for j in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}
# ---------------------------------------------------------------------------
@router.get("/{job_id}", summary="Get scraping job detail")
async def get_job(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return full details for a single scraping job."""
    job = await _get_user_job(job_id, current_user.id, db)
    return _job_to_response(job)


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/retry
# ---------------------------------------------------------------------------
@router.post(
    "/{job_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed scraping job",
)
async def retry_job(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Create a new scraping job for the same source and dispatch to Celery.

    Only failed or completed jobs may be retried.
    """
    existing_job = await _get_user_job(job_id, current_user.id, db)

    if existing_job.status not in (JobStatus.failed, JobStatus.completed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or completed jobs can be retried",
        )

    # Verify the source is still active
    src_result = await db.execute(
        select(JobSource).where(
            JobSource.id == existing_job.source_id,
            JobSource.user_id == current_user.id,
        )
    )
    source = src_result.scalar_one_or_none()
    if source is None or not source.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source is no longer available or active",
        )

    # Create a fresh job
    new_job = ScrapingJob(source_id=source.id, status=JobStatus.pending)
    db.add(new_job)
    await db.flush()
    await db.refresh(new_job)

    # Dispatch Celery
    try:
        from app.tasks.scrape_tasks import scrape_source_task

        celery_task = scrape_source_task.delay(str(source.id), str(new_job.id))
        new_job.celery_task_id = celery_task.id
        await db.flush()
    except Exception as exc:
        logger.exception("Failed to dispatch retry Celery task")
        new_job.status = JobStatus.failed
        new_job.error_message = f"Celery dispatch error: {exc}"
        await db.flush()

    logger.info("Retry job %s dispatched for source %s", new_job.id, source.id)
    return {
        "id": str(new_job.id),
        "source_id": str(source.id),
        "status": new_job.status.value,
        "message": "Retry job created and dispatched",
    }
