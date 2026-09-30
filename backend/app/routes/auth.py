"""
app/routes/auth.py — Authentication Endpoints
==============================================
POST /api/auth/register — Create a new user account
POST /api/auth/login    — Obtain JWT bearer access token
GET  /api/auth/me       — Retrieve profile of currently authenticated user
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import get_current_user
from app.db import get_session
from app.models import (
    TokenResponse,
    User,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserRegisterRequest,
    session: Optional[AsyncSession] = Depends(get_session),
) -> UserResponse:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not configured",
        )
    user = await AuthService.register(session=session, data=payload)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login (JSON body)",
)
async def login(
    payload: UserLoginRequest,
    session: Optional[AsyncSession] = Depends(get_session),
) -> TokenResponse:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not configured",
        )
    user = await AuthService.authenticate(session, payload.email, payload.password)
    return AuthService.create_token(user)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 compatible token endpoint",
    include_in_schema=False,
)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Optional[AsyncSession] = Depends(get_session),
) -> TokenResponse:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not configured",
        )
    user = await AuthService.authenticate(session, form_data.username, form_data.password)
    return AuthService.create_token(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
