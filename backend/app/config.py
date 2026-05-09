"""Application configuration using Pydantic BaseSettings with .env support."""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application settings loaded from environment variables and .env file."""

    # ── Application ────────────────────────────────────────────────
    APP_NAME: str = "LeadForge"
    APP_ENV: str = "development"
    APP_PORT: int = 8000

    # ── URLs ───────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # ── Database ───────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_SYNC_URL: str

    # ── Redis ──────────────────────────────────────────────────────
    REDIS_URL: str

    # ── Celery ─────────────────────────────────────────────────────
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # ── AI / LLM ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str | None = None
    ANTHROPIC_API_KEY: str = ""

    # ── Email (Resend) ────────────────────────────────────────────
    RESEND_API_KEY: str = ""
    EMAIL_FROM_ADDRESS: str = "LeadForge <noreply@leadforge.dev>"

    # ── JWT Authentication ─────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── SG-AI (Scoring & Generation AI) ───────────────────────────
    SGAI_MODEL: str = "gpt-4o-mini"
    SGAI_TEMPERATURE: float = 0.1
    SGAI_MAX_TOKENS: int = 4096

    # ── Scraper ────────────────────────────────────────────────────
    SCRAPER_DEFAULT_DELAY: int = 2
    SCRAPER_MAX_CONCURRENT: int = 3
    SCRAPER_TIMEOUT: int = 30

    # ── Logging ────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Webhooks ───────────────────────────────────────────────────
    WEBHOOK_URLS: List[str] = []
    WEBHOOK_SECRET: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton instance used throughout the application
settings = Settings()
