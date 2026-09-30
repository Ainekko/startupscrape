"""
app/routes/pipeline.py — Pipeline Execution and Run Management Endpoints
========================================================================
GET  /api/runs          — List all pipeline runs (DB or file)
GET  /api/runs/{run_id} — Get details and leads for a run
POST /api/run           — Trigger a new pipeline run (background task)
GET  /api/status        — Current status of active run
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_session
from app.models import PipelineTriggerRequest
from app.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pipeline"])


@router.get("/runs", summary="List all completed runs")
@router.get("/pipeline/runs", summary="List all completed runs (prefixed)", include_in_schema=False)
async def list_runs(session: Optional[AsyncSession] = Depends(get_session)) -> list[dict]:
    return await PipelineService.list_runs(session=session)


@router.get("/runs/{run_id}", summary="Get specific run details")
@router.get("/pipeline/runs/{run_id}", summary="Get specific run details (prefixed)", include_in_schema=False)
async def get_run(run_id: str, session: Optional[AsyncSession] = Depends(get_session)) -> dict:
    data = await PipelineService.get_run(run_id=run_id, session=session)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found",
        )
    return data


@router.post("/run", summary="Trigger a new pipeline run in background")
@router.post("/pipeline/run", summary="Trigger a new pipeline run (prefixed)", include_in_schema=False)
async def trigger_run(
    background_tasks: BackgroundTasks,
    payload: Optional[PipelineTriggerRequest] = None,
) -> dict:
    if PipelineService.is_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pipeline run is already in progress",
        )

    max_leads = payload.max_leads if payload else 20
    max_treg_cost = payload.max_treg_cost if payload else 1.0

    background_tasks.add_task(
        PipelineService.execute_pipeline_background,
        max_leads=max_leads,
        max_treg_cost=max_treg_cost,
    )
    logger.info("Pipeline run scheduled (max_leads=%d, max_cost=%.2f)", max_leads, max_treg_cost)
    return {"status": "started", "max_leads": max_leads, "max_treg_cost": max_treg_cost}


@router.get("/status", summary="Get active run status")
@router.get("/pipeline/status", summary="Get active run status (prefixed)", include_in_schema=False)
async def run_status() -> dict[str, Any]:
    return PipelineService.get_active_status()
