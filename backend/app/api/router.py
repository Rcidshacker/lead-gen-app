"""Root API router — aggregates all sub-routers for /api/v1."""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/", tags=["root"])
async def api_root() -> dict[str, str]:
    """Root of the v1 API — confirms the router is mounted."""
    return {"message": "LeadForge API v1 is live"}
