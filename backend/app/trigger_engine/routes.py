"""
app/trigger_engine/routes.py — FastAPI APIRouter for Trigger Engine
==================================================================
Prefix: /api/triggers
Provides endpoints to trigger scans, inspect why-now timing events,
review AI-qualified outreach briefs, and update workflow status.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import get_current_user
from app.db import get_session
from app.models import Lead as VerveLead, User
from app.trigger_engine.models import (
    BriefStatusUpdateRequest,
    OutreachBriefResponse,
    TriggerEventResponse,
    TriggerRunResponse,
    TriggerScanRequest,
    TriggerStatsResponse,
)
from app.trigger_engine.service import TriggerEngineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])
_service = TriggerEngineService()


@router.post("/scan", response_model=TriggerRunResponse)
async def scan_leads(
    req: TriggerScanRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Scan Verve accounts for 'Why Now?' timing triggers, qualify with AI,
    and generate personalized outreach briefs.
    """
    if session is None:
        raise HTTPException(status_code=503, detail="Database session not available")

    # Select target leads from Verve
    query = select(VerveLead)
    if req.lead_ids:
        query = query.where(VerveLead.id.in_(req.lead_ids))
    else:
        # Default to top scored leads
        query = query.order_by(VerveLead.final_score.desc()).limit(req.limit)

    result = await session.execute(query)
    verve_leads = list(result.scalars().all())

    if not verve_leads:
        raise HTTPException(status_code=404, detail="No matching Verve leads found for trigger scanning")

    lead_dicts = []
    for l in verve_leads:
        raw_founders = []
        if l.founders_json:
            try:
                raw_founders = json.loads(l.founders_json)
            except Exception:
                raw_founders = []

        lead_dicts.append({
            "id": l.id,
            "company_name": l.company_name,
            "website": l.website,
            "one_liner": l.one_liner,
            "batch": l.batch,
            "industry": l.industry,
            "team_size": l.team_size,
            "tags": l.tags.split(",") if l.tags else [],
            "founder_name": l.founder_name,
            "founder_title": l.founder_title,
            "founder_linkedin": l.founder_linkedin,
            "email": l.email,
            "founders": raw_founders,
            "yc_url": l.yc_url,
            "linkedin_url": l.linkedin_url,
        })

    run_record = await _service.scan_leads_batch(
        leads=lead_dicts,
        trigger_types=req.trigger_types,
        min_urgency=req.min_urgency,
        session=session,
    )

    return run_record


@router.get("/events", response_model=list[TriggerEventResponse])
async def list_trigger_events(
    company: Optional[str] = Query(None, description="Filter by company name"),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List detected trigger events with optional company and type filters."""
    if session is None:
        raise HTTPException(status_code=503, detail="Database session not available")
    return await _service.get_events(
        session=session,
        limit=limit,
        offset=offset,
        company=company,
        trigger_type=trigger_type,
    )


@router.get("/briefs", response_model=list[OutreachBriefResponse])
async def list_outreach_briefs(
    status: Optional[str] = Query(None, description="Filter by brief status: draft, approved, sent, rejected"),
    min_urgency: Optional[int] = Query(None, ge=1, le=10, description="Filter by minimum urgency score"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List generated outreach briefs ranked by urgency and recency."""
    if session is None:
        raise HTTPException(status_code=503, detail="Database session not available")
    return await _service.get_briefs(
        session=session,
        limit=limit,
        offset=offset,
        status=status,
        min_urgency=min_urgency,
    )


@router.get("/briefs/{brief_id}", response_model=OutreachBriefResponse)
async def get_outreach_brief(
    brief_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full details of a specific outreach brief."""
    if session is None:
        raise HTTPException(status_code=503, detail="Database session not available")
    brief = await _service.get_brief_by_id(session, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail=f"Brief {brief_id} not found")
    return brief


@router.patch("/briefs/{brief_id}", response_model=OutreachBriefResponse)
async def update_outreach_brief_status(
    brief_id: str,
    req: BriefStatusUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update outreach status (draft, approved, sent, rejected) and add review notes."""
    if session is None:
        raise HTTPException(status_code=503, detail="Database session not available")
    brief = await _service.update_brief_status(
        session=session,
        brief_id=brief_id,
        status=req.status,
        notes=req.notes,
    )
    if not brief:
        raise HTTPException(status_code=404, detail=f"Brief {brief_id} not found")
    return brief


@router.get("/stats", response_model=TriggerStatsResponse)
async def get_trigger_stats(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get aggregate performance and event metrics for the Trigger Engine."""
    if session is None:
        raise HTTPException(status_code=503, detail="Database session not available")
    return await _service.get_stats(session=session)

