"""
app/db.py — Asynchronous PostgreSQL Database Connection with SQLModel
=====================================================================
Connects to PostgreSQL using asyncpg. Tables are isolated with the prefix
'startupscrape_' to allow safely sharing a PostgreSQL instance with other apps.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from urllib.parse import parse_qs, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory = None


def get_database_url() -> tuple[str, bool]:
    """
    Format and clean PostgreSQL connection string for asyncpg.
    Returns (clean_url, requires_ssl).
    """
    settings = get_settings()
    db_url = settings.database_url.strip()

    if not db_url:
        return "", False

    parsed = urlparse(db_url)
    query_params = parse_qs(parsed.query)

    # Check for SSL requirement (e.g. Neon, AWS RDS, Supabase)
    ssl_mode = query_params.get("sslmode", [""])[0]
    requires_ssl = ssl_mode in ("require", "verify-ca", "verify-full") or "neon.tech" in (parsed.netloc or "")

    scheme = parsed.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    clean_url = urlunparse((
        scheme,
        parsed.netloc,
        parsed.path,
        "",
        "",
        "",
    ))

    return clean_url, requires_ssl


def get_engine() -> AsyncEngine | None:
    """Get or lazily initialize the singleton async database engine."""
    global _engine
    if _engine is None:
        clean_url, requires_ssl = get_database_url()
        if not clean_url:
            logger.warning("DATABASE_URL not set. Running without PostgreSQL database connection.")
            return None

        # Neon pooler (PgBouncer) requires prepared statement caching disabled
        connect_args: dict[str, Any] = {
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
        }
        if requires_ssl:
            connect_args["ssl"] = "require"

        settings = get_settings()
        _engine = create_async_engine(
            clean_url,
            echo=settings.database_echo,
            poolclass=NullPool,
            connect_args=connect_args,
        )
        logger.info("StartupScrape async database engine initialized (NullPool + Neon PgBouncer safe)")

    return _engine


def get_session_factory():
    """Get or lazily initialize the sessionmaker for AsyncSession."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        if engine is None:
            return None
        _session_factory = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession | None, None]:
    """FastAPI dependency for obtaining an AsyncSession."""
    factory = get_session_factory()
    if factory is None:
        yield None
        return

    async with factory() as session:
        try:
            yield session
        except Exception as exc:
            logger.error("Database session error: %s", exc)
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context():
    """Context manager for obtaining an AsyncSession in background tasks or scripts."""
    factory = get_session_factory()
    if factory is None:
        yield None
        return

    async with factory() as session:
        try:
            yield session
        except Exception as exc:
            logger.error("Database context session error: %s", exc)
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> bool:
    """
    Initialize all database tables defined in SQLModel metadata.
    Safe to run repeatedly; will only create missing tables.
    """
    engine = get_engine()
    if engine is None:
        logger.warning("Skipping DB table initialization: no engine available.")
        return False

    try:
        # Import models so they are registered in SQLModel.metadata
        from app import models  # noqa: F401
        from app.trigger_engine import models as trigger_models  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("StartupScrape and Trigger Engine database tables verified/created successfully.")
        return True
    except Exception as exc:
        logger.error("Failed to initialize database tables: %s", exc)
        return False


async def check_db_connection() -> bool:
    """Ping the database to verify connectivity."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception as exc:
        logger.error("Database connection check failed: %s", exc)
        return False
