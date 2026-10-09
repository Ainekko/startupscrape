"""
app/trigger_engine/routes.py — FastAPI APIRouter for Trigger Engine
==================================================================
Prefix: /api/triggers
Provides endpoints to trigger scans, inspect why-now timing events,
review AI-qualified outreach briefs, and update workflow status.
"""

from __future__ import annotations

import glob
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import get_current_user, oauth2_scheme, decode_access_token
from app.db import get_session, get_session_context
from app.models import Lead as VerveLead, User
from app.trigger_engine.models import (
    BriefStatusUpdateRequest,
    LinkedInSpyRequest,
    LinkedInSpyResponse,
    OutreachBriefResponse,
    TriggerEventResponse,
    TriggerRunResponse,
    TriggerScanRequest,
    TriggerStatsResponse,
)
from app.trigger_engine.linkedin_spy import LinkedInSpyService
from app.trigger_engine.service import TriggerEngineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])
_service = TriggerEngineService()
_linkedin_spy = LinkedInSpyService()



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
    session: Optional[AsyncSession] = Depends(get_session),
):
    """List detected trigger events with optional company and type filters."""
    if session is None:
        return []
    try:
        return await _service.get_events(
            session=session,
            limit=limit,
            offset=offset,
            company=company,
            trigger_type=trigger_type,
        )
    except Exception as exc:
        logger.warning("Error fetching trigger events: %s", exc)
        return []


@router.get("/briefs", response_model=list[OutreachBriefResponse])
async def list_outreach_briefs(
    status: Optional[str] = Query(None, description="Filter by brief status: draft, approved, sent, rejected"),
    min_urgency: Optional[int] = Query(None, ge=1, le=10, description="Filter by minimum urgency score"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Optional[AsyncSession] = Depends(get_session),
):
    """List generated outreach briefs ranked by urgency and recency."""
    if session is None:
        return []
    try:
        return await _service.get_briefs(
            session=session,
            limit=limit,
            offset=offset,
            status=status,
            min_urgency=min_urgency,
        )
    except Exception as exc:
        logger.warning("Error fetching outreach briefs: %s", exc)
        return []



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


@router.post("/linkedin/spy", response_model=LinkedInSpyResponse)
async def spy_linkedin(req: LinkedInSpyRequest):
    """
    Cheap & reliable LinkedIn intelligence scanner:
    - Primary: queries anyapi.linkedin.search.jobs ($0.0005/hit)
    - Fallback: queries indexed Google SERP for LinkedIn jobs ($0.00015)
    - People: extracts founders and sales leaders via indexed SERP ($0.00015)
    - Total cost per execution: < $0.0008
    """
    company_name = req.company_name.strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="company_name must not be empty")

    try:
        result = await _linkedin_spy.spy(
            company_name=company_name,
            domain=req.domain,
            roles=req.roles,
            include_people=req.include_people,
        )
        return result
    except Exception as exc:
        logger.error("Failed to execute LinkedIn spy for %s: %s", company_name, exc)
        raise HTTPException(status_code=500, detail=f"LinkedIn spy execution error: {exc}")


@router.get("/leads")
async def list_upstream_verve_leads(
    limit: int = Query(10, ge=1, le=50),
    session: Optional[AsyncSession] = Depends(get_session),
):
    """
    Fetch top qualified accounts sourced by Verve (PostgreSQL database or fallback run files).
    These accounts are fed into the Trigger Engine for 'Why Now?' timing event detection.
    """
    leads_out = []

    # 1. Fetch from PostgreSQL database (startupscrape_leads table)
    async def _extract_from_db(sess: AsyncSession):
        query = select(VerveLead).order_by(VerveLead.final_score.desc()).limit(limit)
        result = await sess.execute(query)
        db_leads = list(result.scalars().all())
        for l in db_leads:
            signals = []
            if getattr(l, "signals_json", None):
                try:
                    signals = json.loads(l.signals_json)
                except Exception:
                    pass
            founders = []
            if getattr(l, "founders_json", None):
                try:
                    founders = json.loads(l.founders_json)
                except Exception:
                    pass
            first_f = founders[0] if founders else {}
            leads_out.append({
                "id": str(l.id),
                "company_name": l.company_name,
                "website": l.website,
                "one_liner": l.one_liner,
                "batch": l.batch,
                "industry": l.industry,
                "team_size": l.team_size,
                "founder_name": l.founder_name or first_f.get("name"),
                "founder_title": l.founder_title or first_f.get("title", "Founder"),
                "founder_linkedin": l.founder_linkedin or first_f.get("linkedin_url"),
                "email": l.email,
                "email_status": getattr(l, "email_status", None),
                "final_score": l.final_score or 9.0,
                "key_signals": signals,
                "source": "verve_db",
                "outreach_status": getattr(l, "outreach_status", "new"),
            })

    if session is not None:
        try:
            await _extract_from_db(session)
        except Exception as exc:
            logger.warning("Could not read leads from DB session: %s", exc)

    if not leads_out:
        try:
            async with get_session_context() as ctx_sess:
                if ctx_sess is not None:
                    await _extract_from_db(ctx_sess)
        except Exception as exc:
            logger.warning("Could not read leads from DB context: %s", exc)

    # 2. Fallback to latest Verve data file in data/ if DB is empty or disconnected
    if not leads_out:
        data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
        patterns = [
            str(data_dir / "flowjoy_targeted_leads_*.json"),
            str(data_dir / "run_*.json"),
        ]
        files = []
        for pat in patterns:
            files.extend(glob.glob(pat))
        if files:
            files.sort(key=os.path.getmtime, reverse=True)
            try:
                with open(files[0], "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                file_leads = raw_data if isinstance(raw_data, list) else raw_data.get("leads", [])
                file_leads.sort(
                    key=lambda x: (
                        (x.get("gtm_analysis", {}).get("score", 0) if isinstance(x.get("gtm_analysis"), dict) else 0)
                        or x.get("final_score", 0)
                        or 8.5
                    ),
                    reverse=True,
                )
                for l in file_leads[:limit]:
                    founders = l.get("founders", [])
                    first_f = founders[0] if isinstance(founders, list) and founders else {}
                    gtm = l.get("gtm_analysis", {}) if isinstance(l.get("gtm_analysis"), dict) else {}
                    c_name = l.get("name") or l.get("company_name") or "Unknown"
                    leads_out.append({
                        "id": str(l.get("id") or l.get("slug") or c_name),
                        "company_name": c_name,
                        "website": l.get("website"),
                        "one_liner": l.get("one_liner") or l.get("long_description", ""),
                        "batch": l.get("batch"),
                        "industry": l.get("industry"),
                        "team_size": l.get("team_size"),
                        "founder_name": first_f.get("name") or l.get("founder_name"),
                        "founder_title": first_f.get("title") or l.get("founder_title", "Founder"),
                        "founder_linkedin": first_f.get("linkedin_url") or l.get("founder_linkedin"),
                        "email": l.get("email"),
                        "final_score": gtm.get("score") or l.get("final_score") or 9.5,
                        "key_signals": gtm.get("key_signals", []),
                        "source": "verve_artifact",
                    })
            except Exception as e:
                logger.error("Failed to parse Verve artifact %s: %s", files[0], e)

    return leads_out


class SingleCompanyScanRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    trigger_types: Optional[list[str]] = None
    min_urgency: int = 6


@router.post("/scan-company")
async def scan_single_company(
    req: SingleCompanyScanRequest,
    session: Optional[AsyncSession] = Depends(get_session),
):
    """
    Scan any company on-demand across all timing trigger sources:
    - LinkedIn hiring & leadership (anyapi.linkedin.search.jobs)
    - Funding announcements (treg.google.serp.news)
    - Product launches (treg.google.serp.news)
    - Social discussions / Reddit (treg.google.serp.organic)
    - Tech stack enrichments (treg.companies.enrich)
    """
    c_name = req.company_name.strip()
    if not c_name:
        raise HTTPException(status_code=400, detail="company_name is required")

    account_data = {
        "id": f"acc_{c_name.lower().replace(' ', '_')}",
        "company_name": c_name,
        "website": req.domain,
    }

    try:
        res = await _service.scan_account(
            account=account_data,
            trigger_types=req.trigger_types,
            min_urgency=req.min_urgency,
            session=session,
        )
        return res
    except Exception as exc:
        logger.error("Failed to scan company %s: %s", c_name, exc)
        raise HTTPException(status_code=500, detail=f"Company scan error: {exc}")




