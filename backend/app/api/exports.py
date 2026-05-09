"""Export endpoints — trigger, list, and retrieve data exports."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.export import Export, ExportFormat
from app.models.user import User
from app.schemas.export import ExportCreate, ExportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exports", tags=["Exports"])


def _export_to_response(export: Export) -> dict:
    """Serialise an Export ORM object to a plain dict."""
    return {
        "id": str(export.id),
        "format": export.format.value if isinstance(export.format, ExportFormat) else export.format,
        "filters": export.filters,
        "file_url": export.file_url,
        "created_at": export.created_at,
    }


# ---------------------------------------------------------------------------
# POST /exports/
# ---------------------------------------------------------------------------
@router.post(
    "/",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new export task",
)
async def create_export(
    payload: ExportCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Create an export record and dispatch generation to Celery.

    Returns 202 Accepted with the export id.
    """
    # Validate format
    try:
        fmt = ExportFormat(payload.format)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid format. Must be one of: {[f.value for f in ExportFormat]}",
        )

    # Create placeholder export record
    export = Export(
        user_id=current_user.id,
        format=fmt,
        filters=payload.filters,
        file_url="",  # will be updated by the Celery task
    )
    db.add(export)
    await db.flush()
    await db.refresh(export)

    # Dispatch Celery task
    try:
        from app.workers.tasks import generate_export_task

        generate_export_task.delay(
            str(export.id),
            payload.filters,
            fmt.value,
            str(current_user.id),
        )
    except Exception as exc:
        logger.exception("Failed to dispatch export task")
        # Clean up the record
        await db.delete(export)
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start export: {exc}",
        )

    logger.info("Export %s dispatched for user %s", export.id, current_user.id)
    return {
        "id": str(export.id),
        "format": fmt.value,
        "status": "pending",
        "message": "Export task created and dispatched",
    }


# ---------------------------------------------------------------------------
# GET /exports/
# ---------------------------------------------------------------------------
@router.get("/", summary="List user's exports")
async def list_exports(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return all export records for the authenticated user."""
    result = await db.execute(
        select(Export)
        .where(Export.user_id == current_user.id)
        .order_by(Export.created_at.desc())
    )
    exports = result.scalars().all()
    return {"items": [_export_to_response(e) for e in exports]}


# ---------------------------------------------------------------------------
# GET /exports/{export_id}
# ---------------------------------------------------------------------------
@router.get("/{export_id}", summary="Get export detail")
async def get_export(
    export_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return full details for a single export, including the download URL."""
    result = await db.execute(
        select(Export).where(
            Export.id == export_id,
            Export.user_id == current_user.id,
        )
    )
    export = result.scalar_one_or_none()
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")

    resp = _export_to_response(export)
    # Append download-ready status
    resp["download_ready"] = bool(export.file_url)
    return resp
