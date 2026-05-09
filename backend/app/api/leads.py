"""Lead listing, detail, update, and semantic search endpoints."""

import logging
import uuid
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pgvector.sqlalchemy import Vector
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.job_source import JobSource
from app.models.lead import Lead, LeadStatus
from app.models.user import User
from app.schemas.lead import LeadResponse, LeadUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["Leads"])

# Valid sort columns (prevent arbitrary column injection)
VALID_SORT_COLUMNS = {"score", "created_at", "company", "title", "salary", "location"}
VALID_SORT_ORDERS = {"asc", "desc"}


# ---------------------------------------------------------------------------
# Helper — enforce that the lead belongs to one of the current user's sources
# ---------------------------------------------------------------------------
async def _get_user_lead(
    lead_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Lead:
    """Fetch a lead whose source is owned by *user_id*, or raise 404."""
    stmt = (
        select(Lead)
        .join(JobSource, Lead.source_id == JobSource.id)
        .where(Lead.id == lead_id, JobSource.user_id == user_id)
    )
    lead = (await db.execute(stmt)).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


# ---------------------------------------------------------------------------
# GET /leads/
# ---------------------------------------------------------------------------
@router.get("/", response_model=dict, summary="List leads with filters & pagination")
async def list_leads(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    min_score: float | None = Query(None, ge=0, le=100),
    max_score: float | None = Query(None, ge=0, le=100),
    status: str | None = Query(None),
    platform: str | None = Query(None),
    search: str | None = Query(None, description="Search in title, company, and description"),
    source_id: uuid.UUID | None = Query(None),
    sort_by: str = Query("created_at", description=f"One of: {', '.join(VALID_SORT_COLUMNS)}"),
    sort_order: str = Query("desc", description="'asc' or 'desc'"),
) -> dict:
    """Return paginated leads filtered by the authenticated user's sources."""
    # Validate sort params
    if sort_by not in VALID_SORT_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort_by. Must be one of: {', '.join(VALID_SORT_COLUMNS)}",
        )
    if sort_order not in VALID_SORT_ORDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sort_order must be 'asc' or 'desc'",
        )

    # Base query — only leads from the user's sources
    base = (
        select(Lead)
        .join(JobSource, Lead.source_id == JobSource.id)
        .where(JobSource.user_id == current_user.id)
    )

    # Apply filters
    if min_score is not None:
        base = base.where(Lead.score >= min_score)
    if max_score is not None:
        base = base.where(Lead.score <= max_score)
    if status is not None:
        try:
            status_enum = LeadStatus(status)
            base = base.where(Lead.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status. Must be one of: {[s.value for s in LeadStatus]}",
            )
    if platform is not None:
        base = base.where(Lead.platform.ilike(f"%{platform}%"))
    if source_id is not None:
        # Ensure the source belongs to the user
        src_check = await db.execute(
            select(JobSource).where(JobSource.id == source_id, JobSource.user_id == current_user.id)
        )
        if src_check.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found",
            )
        base = base.where(Lead.source_id == source_id)
    if search is not None:
        pattern = f"%{search}%"
        base = base.where(
            or_(
                Lead.title.ilike(pattern),
                Lead.company.ilike(pattern),
                Lead.description.ilike(pattern),
            )
        )

    # Sorting
    sort_col = getattr(Lead, sort_by)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    # Count total matching rows
    from sqlalchemy import func as sa_func

    count_q = select(sa_func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    # Paginate
    items_q = base.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(items_q)).scalars().all()

    items = [LeadResponse.model_validate(r, from_attributes=True) for r in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": ceil(total / per_page) if total else 1,
    }


# ---------------------------------------------------------------------------
# GET /leads/{lead_id}
# ---------------------------------------------------------------------------
@router.get("/{lead_id}", response_model=LeadResponse, summary="Get lead detail")
async def get_lead(
    lead_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Lead:
    """Return the full data for a single lead."""
    lead = await _get_user_lead(lead_id, current_user.id, db)
    return lead


# ---------------------------------------------------------------------------
# PATCH /leads/{lead_id}
# ---------------------------------------------------------------------------
@router.patch("/{lead_id}", response_model=LeadResponse, summary="Update lead status or notes")
async def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Lead:
    """Update a lead's status and/or notes."""
    lead = await _get_user_lead(lead_id, current_user.id, db)

    update_data = payload.model_dump(exclude_unset=True)

    if "status" in update_data and update_data["status"] is not None:
        try:
            lead.status = LeadStatus(update_data["status"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status. Must be one of: {[s.value for s in LeadStatus]}",
            )

    # Notes are stored in raw_data JSONB field for flexibility
    if "notes" in update_data and update_data["notes"] is not None:
        lead.raw_data = {**lead.raw_data, "notes": update_data["notes"]}

    await db.flush()
    await db.refresh(lead)
    return lead


# ---------------------------------------------------------------------------
# POST /leads/search/semantic
# ---------------------------------------------------------------------------
@router.post("/search/semantic", summary="Semantic similarity search for leads")
async def semantic_search(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    query: str = Body(..., min_length=2, description="Natural language search query"),
    limit: int = Body(20, ge=1, le=100, description="Max results to return"),
    min_score: float | None = Body(None, ge=0, le=1, description="Minimum cosine similarity (0-1)"),
) -> dict:
    """Find leads semantically similar to a natural language query.

    Generates an embedding for the query using ``text-embedding-3-small``
    and performs a cosine similarity search against lead embeddings via
    pgvector.  Results are scoped to the authenticated user's sources only.

    Returns results ordered by similarity score (most relevant first).
    Each result includes a ``similarity`` field (0-1, higher = more relevant).
    """
    from app.services.lead_scoring import LeadScoringService

    if not settings_is_openai_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search requires OPENAI_API_KEY to be configured",
        )

    # 1. Generate embedding for the query
    scoring_svc = LeadScoringService()
    query_embedding = await scoring_svc.generate_embedding(query)
    if query_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate query embedding",
        )

    # 2. Perform cosine similarity search via pgvector
    #    The <=> operator is the cosine distance operator from pgvector.
    #    We wrap it in 1 - <=> to get cosine *similarity* (higher = better).
    similarity_threshold = min_score if min_score is not None else 0.0

    stmt = (
        select(
            Lead,
            (1 - Lead.embedding.cosine_distance(query_embedding)).label("similarity"),
        )
        .join(JobSource, Lead.source_id == JobSource.id)
        .where(
            JobSource.user_id == current_user.id,
            Lead.embedding.isnot(None),
        )
        .order_by(text("similarity DESC"))
        .limit(limit)
    )

    rows = (await db.execute(stmt)).all()

    results = []
    for lead, similarity in rows:
        if similarity < similarity_threshold:
            continue
        item = LeadResponse.model_validate(lead, from_attributes=True)
        results.append({
            **item.model_dump(),
            "similarity": round(float(similarity), 4),
        })

    return {"items": results, "query": query, "total": len(results)}


def settings_is_openai_configured() -> bool:
    """Check if OpenAI API key is available for embedding generation."""
    from app.config import settings
    return bool(settings.OPENAI_API_KEY)
