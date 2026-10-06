"""
app/routes/analytics.py — Analytics & Performance Reporting Endpoints
All endpoints require authentication.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import get_current_user
from app.db import get_session
from app.models import AnalyticsOverviewResponse, User
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse, summary="Pipeline overview & conversion KPIs")
async def get_overview(
    session: Optional[AsyncSession] = Depends(get_session),
    _: User = Depends(get_current_user),
) -> AnalyticsOverviewResponse:
    return await AnalyticsService.get_overview(session=session)
