"""
app/routes/leads.py — Lead Intelligence, GTM Search, and Outreach Management
=============================================================================
GET   /api/leads                 — Search, filter, and paginate qualified leads
GET   /api/leads/{lead_id}       — Get full intelligence on a single lead
PATCH /api/leads/{lead_id}/status — Update outreach stage (contacted, replied, etc.)
POST  /api/leads/{lead_id}/outcome — Log an outreach attempt/outcome
GET   /api/leads/export/csv      — Download filtered leads as CSV
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_session
from app.models import (
    LeadFilterParams,
    LeadOutcomeCreateRequest,
    LeadStatusUpdateRequest,
)
from app.services.lead_service import LeadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", summary="Search, filter, and paginate leads")
async def list_leads(
    query: Optional[str] = Query(None, description="Search company, founder, or one-liner"),
    batch: Optional[str] = Query(None, description="YC Batch (e.g. W24, S24)"),
    industry: Optional[str] = Query(None, description="Industry or sector"),
    min_score: Optional[float] = Query(None, description="Minimum fit score (0-24)"),
    max_score: Optional[float] = Query(None, description="Maximum fit score"),
    has_email: Optional[bool] = Query(None, description="Filter leads with valid founder email"),
    outreach_status: Optional[str] = Query(None, description="Outreach status (new, contacted, etc.)"),
    run_id: Optional[str] = Query(None, description="Filter leads from a specific pipeline run"),
    dedupe: bool = Query(True, description="Deduplicate leads across runs"),
    sort_by: str = Query("score_desc", description="Sort: score_desc, score_asc, name_asc, date_desc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Optional[AsyncSession] = Depends(get_session),
) -> dict[str, Any]:
    params = LeadFilterParams(
        query=query,
        batch=batch,
        industry=industry,
        min_score=min_score,
        max_score=max_score,
        has_email=has_email,
        outreach_status=outreach_status,
        run_id=run_id,
        dedupe=dedupe,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return await LeadService.query_leads(session=session, params=params)


@router.get("/export/csv", summary="Export filtered leads to CSV")
async def export_leads(
    query: Optional[str] = None,
    batch: Optional[str] = None,
    industry: Optional[str] = None,
    min_score: Optional[float] = None,
    has_email: Optional[bool] = None,
    outreach_status: Optional[str] = None,
    run_id: Optional[str] = None,
    dedupe: bool = Query(True, description="Deduplicate leads in CSV export"),
    limit: int = Query(500, ge=1, le=2000),
    session: Optional[AsyncSession] = Depends(get_session),
) -> Response:
    params = LeadFilterParams(
        query=query,
        batch=batch,
        industry=industry,
        min_score=min_score,
        has_email=has_email,
        outreach_status=outreach_status,
        run_id=run_id,
        dedupe=dedupe,
        limit=limit,
        offset=0,
    )
    data = await LeadService.query_leads(session=session, params=params)
    leads_list = data.get("items", [])
    csv_content = LeadService.export_leads_csv(leads_list, dedupe=dedupe)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=startupscrape_leads.csv"},
    )


@router.get("/{lead_id}", summary="Get lead details by ID")
async def get_lead(
    lead_id: str,
    session: Optional[AsyncSession] = Depends(get_session),
) -> dict:
    lead = await LeadService.get_lead(lead_id=lead_id, session=session)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{lead_id}' not found",
        )
    return lead


@router.patch("/{lead_id}/status", summary="Update lead outreach status")
async def update_lead_status(
    lead_id: str,
    payload: LeadStatusUpdateRequest,
    session: Optional[AsyncSession] = Depends(get_session),
) -> dict:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is required to update lead status",
        )
    lead = await LeadService.update_status(
        session=session,
        lead_id=lead_id,
        new_status=payload.outreach_status,
        notes=payload.notes,
    )
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{lead_id}' not found in database",
        )
    return lead.model_dump()


@router.post("/{lead_id}/outcome", summary="Record outreach event")
async def record_outcome(
    lead_id: str,
    payload: LeadOutcomeCreateRequest,
    session: Optional[AsyncSession] = Depends(get_session),
) -> dict:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is required to record outcomes",
        )
    outcome = await LeadService.record_outcome(
        session=session,
        lead_id=lead_id,
        channel=payload.channel,
        status=payload.status,
        notes=payload.notes,
    )
    return outcome.model_dump()
