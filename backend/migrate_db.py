"""
migrate_db.py — One-shot PostgreSQL Database Migration & Data Ingestion Script
==============================================================================
1. Connects to PostgreSQL using settings from .env
2. Creates any missing SQLModel tables (startupscrape_*)
3. Ingests all historical backup JSON runs from data/run_*.json into PostgreSQL
   using unique run-scoped lead IDs so all historical runs preserve their leads.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Setup sys.path to locate backend modules
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db import check_db_connection, get_session_context, init_db
from app.models import Lead, PipelineRun
from app.services.pipeline_service import PipelineService
from sqlmodel import func, select

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("migrate_db")


async def main():
    logger.info("Checking PostgreSQL connection...")
    connected = await check_db_connection()
    if not connected:
        logger.error("Failed to connect to PostgreSQL database. Check DATABASE_URL in .env.")
        sys.exit(1)

    logger.info("Initializing SQLModel tables (create_all)...")
    tables_created = await init_db()
    if not tables_created:
        logger.error("Failed to initialize database tables.")
        sys.exit(1)

    logger.info("Syncing historical backup runs into PostgreSQL...")
    async with get_session_context() as session:
        if session is None:
            logger.error("Could not obtain session context.")
            sys.exit(1)

        synced = await PipelineService.sync_all_backup_runs(session)
        logger.info("Synced %d runs into PostgreSQL.", synced)

        runs_count = (await session.exec(select(func.count(PipelineRun.id)))).one()
        leads_count = (await session.exec(select(func.count(Lead.id)))).one()
        logger.info("Database migration complete: %d runs, %d leads in PostgreSQL.", runs_count, leads_count)


if __name__ == "__main__":
    asyncio.run(main())
