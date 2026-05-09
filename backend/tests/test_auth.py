"""Tests for the authentication API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """GET /health should return 200 with healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_register_user(client):
    """POST /api/v1/auth/register should create a new user."""
    payload = {
        "email": "testuser@leadforge.dev",
        "password": "SecureTest123!",
        "full_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@leadforge.dev"
    assert data["full_name"] == "Test User"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Registering the same email twice should return 409."""
    payload = {
        "email": "dup@leadforge.dev",
        "password": "SecureTest123!",
        "full_name": "First User",
    }
    response1 = await client.post("/api/v1/auth/register", json=payload)
    assert response1.status_code == 201

    response2 = await client.post("/api/v1/auth/register", json={**payload, "full_name": "Second User"})
    assert response2.status_code == 409


@pytest.mark.asyncio
async def test_login_and_access_token(client):
    """POST /api/v1/auth/login should return a JWT access token."""
    # Register first
    register_payload = {
        "email": "login@leadforge.dev",
        "password": "LoginTest123!",
        "full_name": "Login User",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    # Login
    login_payload = {
        "username": "login@leadforge.dev",
        "password": "LoginTest123!",
    }
    response = await client.post(
        "/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Login with wrong password should return 401."""
    register_payload = {
        "email": "wrongpw@leadforge.dev",
        "password": "CorrectPw123!",
        "full_name": "Pw User",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    login_payload = {
        "username": "wrongpw@leadforge.dev",
        "password": "WrongPassword!",
    }
    response = await client.post(
        "/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client):
    """Accessing a protected endpoint without a token should return 401."""
    response = await client.get("/api/v1/sources/")
    assert response.status_code == 401
