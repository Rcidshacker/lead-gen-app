"""LeadForge backend test configuration and shared fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure app models are imported before any test that touches the DB
import app.models  # noqa: F401
from app.database import Base, get_db
from app.main import app

# ---------------------------------------------------------------------------
# Test database — uses a separate database to avoid touching dev data
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://leadforge:leadforge@localhost:5432/leadforge_test",
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests requiring external services")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test with auto-rollback."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client with dependency overrides.

    Overrides the database dependency to use the test session.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_openai(mocker: Any) -> Any:
    """Mock OpenAI API calls to prevent burning credits.

    Usage in tests::

        def test_scoring(mock_openai):
            mock_openai.chat.completions.create.return_value = ...
    """
    return mocker.patch("app.services.lead_scoring.AsyncOpenAI")


@pytest.fixture
def mock_resend(mocker: Any) -> Any:
    """Mock Resend email API calls."""
    return mocker.patch("app.services.email_service.resend")
