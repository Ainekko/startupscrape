"""
app/services/analytics_service.py — Aggregate Statistics and Funnel Analytics
=============================================================================
Computes pipeline velocity, fit score distribution, and outreach conversion KPIs.
PostgreSQL database is the primary source of truth.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import AnalyticsOverviewResponse, Lead, PipelineRun

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT        = BACKEND_DIR.parent
DATA_DIR    = ROOT / "data"


class AnalyticsService:
    @classmethod
    async def get_overview(cls, session: AsyncSession | None = None) -> AnalyticsOverviewResponse:
        """
        Compute aggregated pipeline KPIs from the primary PostgreSQL database.
        Falls back to file backups only if the database is disconnected.
        """
        if session is not None:
            try:
                runs_count = (await session.exec(select(func.count(PipelineRun.id)))).one() or 0
                leads_count = (await session.exec(select(func.count(Lead.id)))).one() or 0

                avg_score_res = 0.0
                email_count_res = 0
                status_breakdown = {"new": 0}
                top_batches = []

                if leads_count > 0:
                    avg_score_res = (await session.exec(select(func.avg(Lead.final_score)))).one() or 0.0
                    email_count_res = (
                        await session.exec(
                            select(func.count(Lead.id)).where(Lead.email.isnot(None))
                        )
                    ).one() or 0

                    leads_stmt = select(Lead.outreach_status, func.count(Lead.id)).group_by(Lead.outreach_status)
                    status_rows = (await session.exec(leads_stmt)).all()
                    if status_rows:
                        status_breakdown = {row[0]: row[1] for row in status_rows}

                    batch_stmt = (
                        select(Lead.batch, func.count(Lead.id), func.avg(Lead.final_score))
                        .where(Lead.batch.isnot(None))
                        .group_by(Lead.batch)
                        .order_by(func.count(Lead.id).desc())
                        .limit(6)
                    )
                    batch_rows = (await session.exec(batch_stmt)).all()
                    top_batches = [
                        {"batch": row[0], "count": row[1], "avg_score": round(float(row[2] or 0.0), 1)}
                        for row in batch_rows
                    ]

                return AnalyticsOverviewResponse(
                    total_leads=leads_count,
                    total_runs=runs_count,
                    avg_score=round(float(avg_score_res), 1),
                    leads_with_email=email_count_res,
                    status_breakdown=status_breakdown,
                    top_batches=top_batches,
                )
            except Exception as exc:
                logger.error("Could not calculate analytics from DB: %s", exc)
                return cls._calc_from_files()

        return cls._calc_from_files()

    @staticmethod
    def _calc_from_files() -> AnalyticsOverviewResponse:
        total_runs = 0
        all_leads = []
        seen = set()

        for p in sorted(DATA_DIR.glob("run_*.json")):
            if "_partial" in p.name:
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                total_runs += 1
                for lead in data.get("leads", []):
                    lid = lead.get("id") or lead.get("company_name", "")
                    if lid and lid not in seen:
                        seen.add(lid)
                        all_leads.append(lead)
            except Exception:
                continue

        if not all_leads:
            return AnalyticsOverviewResponse(
                total_leads=0,
                total_runs=total_runs,
                avg_score=0.0,
                leads_with_email=0,
                status_breakdown={"new": 0},
                top_batches=[],
            )

        total_leads = len(all_leads)
        scores = [float(l.get("final_score", 0.0)) for l in all_leads]
        avg_score = round(sum(scores) / total_leads, 1) if total_leads else 0.0

        with_email = sum(
            1 for l in all_leads
            if l.get("email") or (l.get("email_result") and l.get("email_result", {}).get("email"))
        )

        status_counts = Counter(l.get("outreach_status", "new") for l in all_leads)
        batch_counts = Counter(l.get("batch") for l in all_leads if l.get("batch"))

        top_batches = [
            {"batch": b, "count": cnt, "avg_score": avg_score}
            for b, cnt in batch_counts.most_common(6)
        ]

        return AnalyticsOverviewResponse(
            total_leads=total_leads,
            total_runs=total_runs,
            avg_score=avg_score,
            leads_with_email=with_email,
            status_breakdown=dict(status_counts),
            top_batches=top_batches,
        )
