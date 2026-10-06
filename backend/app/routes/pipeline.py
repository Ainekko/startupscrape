"""
app/routes/pipeline.py — Pipeline Execution and Run Management Endpoints
GET  /api/runs          — List all pipeline runs
GET  /api/runs/{run_id} — Get details and leads for a run
POST /api/run           — Trigger a new pipeline run (requires auth)
GET  /api/status        — Current status of active run
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import get_current_user
from app.db import get_session
from app.models import PipelineTriggerRequest, User
from app.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pipeline"])


@router.get("/runs", summary="List all completed runs")
async def list_runs(session: Optional[AsyncSession] = Depends(get_session)) -> list[dict]:
    return await PipelineService.list_runs(session=session)


@router.get("/runs/{run_id}", summary="Get specific run details")
async def get_run(run_id: str, session: Optional[AsyncSession] = Depends(get_session)) -> dict:
    data = await PipelineService.get_run(run_id=run_id, session=session)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found")
    return data


@router.post("/run", summary="Trigger a new pipeline run (auth required)")
async def trigger_run(
    background_tasks: BackgroundTasks,
    payload: Optional[PipelineTriggerRequest] = None,
    _: User = Depends(get_current_user),
) -> dict:
    if PipelineService.is_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A pipeline run is already in progress")

    p = payload or PipelineTriggerRequest()
    background_tasks.add_task(
        PipelineService.execute_pipeline_background,
        max_leads=p.max_leads,
        max_treg_cost=p.max_treg_cost,
        batches=p.batches,
        sources=p.sources,
    )
    logger.info("Pipeline run scheduled (max_leads=%d, max_cost=%.2f, batches=%s, sources=%s)",
                p.max_leads, p.max_treg_cost, p.batches, p.sources)
    return {"status": "started", "max_leads": p.max_leads, "max_treg_cost": p.max_treg_cost}


@router.get("/status", summary="Get active run status")
async def run_status() -> dict[str, Any]:
    return PipelineService.get_active_status()
