"""
app/routes/auth.py — Authentication Endpoints with Bot Guards & Rate Limiting
=============================================================================
POST /api/auth/login    — Single-user login (JSON body)
POST /api/auth/token    — OAuth2 form login
GET  /api/auth/me       — Retrieve profile of currently authenticated user
POST /api/auth/register — Disabled (403 Forbidden)
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from app.security import security_guard
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_403_FORBIDDEN,
    summary="Register a new user (disabled)",
)
async def register(
    payload: UserRegisterRequest,
    session: Optional[AsyncSession] = Depends(get_session),
) -> UserResponse:
    return await AuthService.register(session=session, data=payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login for xander (JSON body)",
)
async def login(
    payload: UserLoginRequest,
    request: Request,
    session: Optional[AsyncSession] = Depends(get_session),
) -> TokenResponse:
    # Bot and scanner defense
    security_guard.verify_request_hygiene(request)
    client_ip = security_guard.get_client_ip(request)

    user = await AuthService.authenticate(
        session=session,
        identifier=payload.email,
        password=payload.password,
        client_ip=client_ip,
    )
    return AuthService.create_token(user)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 compatible token endpoint",
    include_in_schema=False,
)
async def login_oauth2(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Optional[AsyncSession] = Depends(get_session),
) -> TokenResponse:
    # Bot and scanner defense
    security_guard.verify_request_hygiene(request)
    client_ip = security_guard.get_client_ip(request)

    user = await AuthService.authenticate(
        session=session,
        identifier=form_data.username,
        password=form_data.password,
        client_ip=client_ip,
    )
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
