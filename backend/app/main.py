"""
StartupScrape Backend — FastAPI Application
============================================
Lead intelligence, scoring, and automated GTM pipeline engine.

Run locally:
    uv run uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import check_db_connection, init_db
from app.routes import analytics, auth, leads, pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database tables safely on startup."""
    logger.info("Starting StartupScrape API server...")
    if settings.database_url:
        db_ok = await init_db()
        if db_ok:
            logger.info("StartupScrape PostgreSQL database connection and tables verified.")
        else:
            logger.warning("Database initialization could not be completed; running with fallback storage.")
    else:
        logger.info("Running in file-only mode (DATABASE_URL not configured).")

    yield

    logger.info("Shutting down StartupScrape API server...")


app = FastAPI(
    title="StartupScrape API",
    description="Lead generation and GTM intelligence engine — YC & WAAS startup scoring",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(pipeline.router, prefix=settings.api_prefix)
app.include_router(leads.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)


@app.get("/health", tags=["meta"])
async def health():
    db_connected = await check_db_connection() if settings.database_url else False
    return {
        "status": "ok",
        "version": "1.1.0",
        "database_connected": db_connected,
        "database_configured": bool(settings.database_url),
    }
