"""Authentication endpoints — register, login, and profile retrieval."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import create_access_token, create_refresh_token, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Create a new user account.

    Raises 400 if the email is already registered.
    """
    from app.api.deps import hash_password

    # Check uniqueness
    existing = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()  # get the generated id before commit
    await db.refresh(user)
    logger.info("Registered new user %s", user.email)
    return user


# ---------------------------------------------------------------------------
# POST /auth/login  (OAuth2 password flow — form-encoded)
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=Token,
    summary="Obtain access & refresh tokens",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Authenticate with email + password and receive JWT tokens.

    Accepts ``application/x-www-form-urlencoded`` body (OAuth2 spec).
    """
    from app.api.deps import verify_password

    result = await db.execute(
        select(User).where(User.email == form_data.username.lower())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    token_data = {"sub": str(user.id), "is_superuser": user.is_superuser}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.info("User %s logged in", user.email)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the authenticated user's profile",
)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Fetch the profile of the currently authenticated user."""
    return current_user
