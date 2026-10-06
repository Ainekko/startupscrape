"""
app/services/auth_service.py — Single-User Authentication and Credential Service
=================================================================================
Implements fast, hardened single-user authentication for 'xander'.
Only one authorized account is permitted. Registration is locked down.
Integrated with SecurityGuard for bot detection and brute-force mitigation.
"""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import create_access_token
from app.config import get_settings
from app.models import TokenResponse, User, UserRegisterRequest, UserRole
from app.security import security_guard

logger = logging.getLogger(__name__)


class AuthService:
    # Single authorized user configuration
    SINGLE_USER = "xander"
    SINGLE_PASSWORD = "xander@flowJOY"
    SINGLE_EMAIL = "xander@flowjoy.com"

    @classmethod
    async def ensure_default_user(cls, session: AsyncSession) -> User:
        """Ensure single authorized user 'xander' exists in PostgreSQL database on startup."""
        stmt = select(User).where(User.email == cls.SINGLE_EMAIL)
        user = (await session.exec(stmt)).first()
        if not user:
            user = User(
                id=1,
                email=cls.SINGLE_EMAIL,
                full_name="Xander",
                role=UserRole.ADMIN.value,
                is_active=True,
                # authenticate() never reads this — it uses secrets.compare_digest
                # against the hardcoded SINGLE_PASSWORD constant. No bcrypt needed.
                hashed_password="*",
            )
            session.add(user)
            try:
                await session.commit()
                await session.refresh(user)
                logger.info("Initialized default user '%s' in PostgreSQL database.", cls.SINGLE_USER)
            except Exception as exc:
                await session.rollback()
                logger.warning("Default user initialization note: %s", exc)
        return user

    @classmethod
    async def register(cls, session: Optional[AsyncSession], data: UserRegisterRequest) -> User:
        """Public registration is strictly disabled in single-user mode."""
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled. Single-user mode is active.",
        )

    @classmethod
    async def authenticate(
        cls,
        session: Optional[AsyncSession],
        identifier: str,
        password: str,
        client_ip: str = "127.0.0.1",
    ) -> User:
        """
        Authenticate user 'xander'.
        Guarded against bot brute-force via SecurityGuard rate limiting and constant-time comparison.
        """
        # 1. Enforce rate limit on client IP
        security_guard.check_login_rate_limit(client_ip)

        clean_id = (identifier or "").strip().lower()
        is_user_match = clean_id in (cls.SINGLE_USER, cls.SINGLE_EMAIL, f"{cls.SINGLE_USER}@flowjoy.internal")
        is_pass_match = secrets.compare_digest(password or "", cls.SINGLE_PASSWORD)

        # 2. Reject mismatched credentials
        if not (is_user_match and is_pass_match):
            security_guard.record_login_failure(client_ip)
            logger.warning("Failed login attempt for identifier '%s' from IP %s", identifier, client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Successful match — clear rate limiter failure records
        security_guard.record_login_success(client_ip)
        logger.info("User '%s' successfully authenticated from IP %s", cls.SINGLE_USER, client_ip)

        # 4. Fetch or return user instance
        if session is not None:
            stmt = select(User).where(User.email == cls.SINGLE_EMAIL)
            db_user = (await session.exec(stmt)).first()
            if db_user:
                return db_user

        # Fallback in-memory user instance
        return User(
            id=1,
            email=cls.SINGLE_EMAIL,
            full_name="Xander",
            role=UserRole.ADMIN.value,
            is_active=True,
            hashed_password="*",
        )

    @classmethod
    def create_token(cls, user: User) -> TokenResponse:
        """Generate signed JWT access token for authenticated user."""
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
            user_id=user.id or 1,
            email=user.email,
            role=user.role,
        )
