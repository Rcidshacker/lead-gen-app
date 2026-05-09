"""Pydantic v2 schemas for User authentication and profile."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration / signup."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public user profile returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class Token(BaseModel):
    """JWT access / refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: str  # user id
    exp: int
    is_superuser: bool = False
