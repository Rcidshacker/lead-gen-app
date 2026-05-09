"""Tests for the lead scoring service (fully mocked — no API calls)."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_score_lead_returns_valid_range(mock_openai):
    """Score should be clamped between 0 and 100."""
    from app.services.lead_scoring import LeadScoringService

    svc = LeadScoringService()

    # Mock the OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"score": 85, "reason": "Good match"}'))
    ]

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_openai.return_value = mock_client

    result = await svc.score_lead({
        "title": "Senior Python Developer",
        "company": "Google",
        "location": "Remote",
        "salary": "$200k",
        "description": "Build amazing things",
        "requirements": "Python, FastAPI",
        "platform": "linkedin",
    })

    assert isinstance(result, float)
    assert 0 <= result <= 100
    assert result == 85.0


@pytest.mark.asyncio
async def test_score_lead_defaults_on_parse_error(mock_openai):
    """Should default to 50 when the LLM returns invalid JSON."""
    from app.services.lead_scoring import LeadScoringService

    svc = LeadScoringService()

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="NOT VALID JSON"))
    ]

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_openai.return_value = mock_client

    result = await svc.score_lead({
        "title": "Test",
        "company": "TestCo",
        "location": "NYC",
        "salary": "$100k",
        "description": "Test job",
        "requirements": "Python",
        "platform": "indeed",
    })

    assert result == 50.0


@pytest.mark.asyncio
async def test_score_lead_defaults_on_api_error(mock_openai):
    """Should default to 50 when the API raises an exception."""
    from app.services.lead_scoring import LeadScoringService

    svc = LeadScoringService()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API rate limit"))
    mock_openai.return_value = mock_client

    result = await svc.score_lead({
        "title": "Test",
        "company": "TestCo",
        "location": "NYC",
        "salary": "$100k",
        "description": "Test job",
        "requirements": "Python",
        "platform": "indeed",
    })

    assert result == 50.0


@pytest.mark.asyncio
async def test_generate_embedding(mock_openai):
    """Should return a 1536-dimensional vector."""
    from app.services.lead_scoring import LeadScoringService

    svc = LeadScoringService()

    # Mock embedding response
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

    mock_client = AsyncMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_openai.return_value = mock_client

    result = await svc.generate_embedding("Senior Python Developer at Google")

    assert result is not None
    assert len(result) == 1536


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(mock_openai):
    """Should return None for empty text."""
    from app.services.lead_scoring import LeadScoringService

    svc = LeadScoringService()

    result = await svc.generate_embedding("")
    assert result is None

    result = await svc.generate_embedding(None)
    assert result is None
