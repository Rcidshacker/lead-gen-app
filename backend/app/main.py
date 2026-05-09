"""LeadForge FastAPI application entry point.

Creates the FastAPI instance, configures middleware, registers exception
handlers, and wires up the API router.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialise resources on startup, clean up on shutdown."""
    # ── Startup ─────────────────────────────────────────────────────────
    logger.info("Starting %s (%s env)", settings.APP_NAME, settings.APP_ENV)

    # Enable pgvector extension so the `vector` column type works
    try:
        from app.database import async_engine
        from sqlalchemy import text

        async with async_engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("pgvector extension enabled")
    except Exception as exc:
        logger.warning("Could not enable pgvector extension: %s", exc)

    # Verify database connectivity
    try:
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1"))
            result.scalar()
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)

    yield  # application is running

    # ── Shutdown ────────────────────────────────────────────────────────
    logger.info("Shutting down %s", settings.APP_NAME)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LeadForge API",
    version="0.1.0",
    description="AI-powered lead generation and enrichment platform",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------

if settings.APP_ENV == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.FRONTEND_URL,
            settings.BACKEND_URL,
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ---------------------------------------------------------------------------
# API router
# ---------------------------------------------------------------------------

# Lazy import so the router module can depend on `app`-level objects if needed.
from app.api.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Health & readiness endpoints
# ---------------------------------------------------------------------------


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Lightweight liveness probe — always returns 200 if the process is up."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/ready", tags=["system"])
async def readiness_check() -> JSONResponse:
    """Readiness probe — verifies DB and Redis connectivity."""
    checks: dict[str, bool] = {}

    # Database
    try:
        from app.database import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Redis
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    all_ok = all(checks.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return 422 with a human-friendly error envelope."""
    errors = [
        {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
    """Return a consistent 404 JSON response."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "The requested resource was not found."},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Any) -> JSONResponse:
    """Return a consistent 500 JSON response (hides internals in production)."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    detail = "Internal server error" if settings.APP_ENV != "development" else str(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail},
    )


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
