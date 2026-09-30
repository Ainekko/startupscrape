"""
app/services/auth_service.py — Authentication and User Management Service
"""

from __future__ import annotations

import logging
from datetime import timedelta
from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import create_access_token, hash_password, verify_password
from app.config import get_settings
from app.models import TokenResponse, User, UserRegisterRequest, UserRole

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    async def register(session: AsyncSession, data: UserRegisterRequest) -> User:
        """Register a new user account."""
        # Check if email is already registered
        stmt = select(User).where(User.email == data.email.strip().lower())
        existing = (await session.exec(stmt)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
            )

        # Check total users count; if first user, grant admin role
        count_stmt = select(User)
        all_users = (await session.exec(count_stmt)).all()
        assigned_role = UserRole.ADMIN.value if len(all_users) == 0 else UserRole.USER.value

        user = User(
            email=data.email.strip().lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=assigned_role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("Registered new user: %s (role: %s)", user.email, user.role)
        return user

    @staticmethod
    async def authenticate(session: AsyncSession, email: str, password: str) -> User:
        """Authenticate user by email and password."""
        stmt = select(User).where(User.email == email.strip().lower())
        user = (await session.exec(stmt)).first()

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        return user

    @staticmethod
    def create_token(user: User) -> TokenResponse:
        """Generate JWT access token for user."""
        settings = get_settings()
        expires = timedelta(minutes=settings.access_token_expire_minutes)
        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=expires,
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=int(expires.total_seconds()),
            user_id=user.id,
            email=user.email,
            role=user.role,
        )
