"""Root API router — aggregates all sub-routers for /api/v1."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.exports import router as exports_router
from app.api.job_sources import router as sources_router
from app.api.scraping_jobs import router as jobs_router
from app.api.leads import router as leads_router

api_router = APIRouter()

# ── Auth (public) ────────────────────────────────────────────────────
api_router.include_router(auth_router)

# ── Protected resources ──────────────────────────────────────────────
api_router.include_router(sources_router)
api_router.include_router(leads_router)
api_router.include_router(jobs_router)
api_router.include_router(exports_router)
api_router.include_router(dashboard_router)
