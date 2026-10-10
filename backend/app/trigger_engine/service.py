"""
app/trigger_engine/service.py — Trigger Engine Orchestration Service
===================================================================
Coordinates signal detectors, AI qualification, and outreach brief generation.
Handles database persistence in 'trigengine_' tables, cost governance, and batch runs.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import desc, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.trigger_engine.detectors.base import BaseDetector, DetectedSignal
from app.trigger_engine.detectors.funding import FundingDetector
from app.trigger_engine.detectors.hiring import GTMHiringDetector
from app.trigger_engine.detectors.linkedin_activity import LinkedInActivityDetector
from app.trigger_engine.detectors.product import ProductLaunchDetector
from app.trigger_engine.detectors.social import SocialDiscussionDetector
from app.trigger_engine.detectors.tech import TechStackDetector
from app.trigger_engine.linkedin_intel import snapshot_from_report
from app.trigger_engine.models import (
    BriefStatus,
    OutreachBrief,
    TriggerEvent,
    TriggerEvaluation,
    TriggerRun,
    TriggerRunStatus,
)
from app.trigger_engine.outreach import OutreachEngine
from app.trigger_engine.qualifier import AIQualifier
from app.trigger_engine.treg_client import TregClient

logger = logging.getLogger(__name__)


class TriggerEngineService:
    def __init__(self, treg_client: Optional[TregClient] = None):
        self.treg = treg_client or TregClient()
        self.qualifier = AIQualifier()
        self.outreach = OutreachEngine()

        self.detectors: dict[str, BaseDetector] = {
            "gtm_hiring": GTMHiringDetector(),
            "funding": FundingDetector(),
            "product_launch": ProductLaunchDetector(),
            "social_discussion": SocialDiscussionDetector(),
            "tech_stack": TechStackDetector(),
            "linkedin_activity": LinkedInActivityDetector(),
        }

    async def scan_account(
        self,
        account: dict[str, Any],
        trigger_types: Optional[list[str]] = None,
        min_urgency: int = 6,
        session: Optional[AsyncSession] = None,
    ) -> dict[str, Any]:
        """
        Scan a single Verve account across specified trigger detectors,
        qualify findings with AI, and generate outreach briefs.
        """
        company_name = account.get("company_name") or account.get("name") or "Unknown"
        lead_id = str(account.get("id") or account.get("slug") or str(uuid.uuid4()))
        domain = account.get("website")

        active_detectors = [
            d for name, d in self.detectors.items()
            if not trigger_types or name in trigger_types
        ]

        found_signals: list[DetectedSignal] = []
        evaluations: list[dict[str, Any]] = []
        briefs: list[dict[str, Any]] = []

        for detector in active_detectors:
            try:
                if isinstance(detector, LinkedInActivityDetector):
                    signals, intel_report = await detector.detect_with_report(account, self.treg)
                    if intel_report is not None and session:
                        intel_report.lead_id = lead_id
                        session.add(snapshot_from_report(intel_report))
                else:
                    signals = await detector.detect(account, self.treg)
                for sig in signals:
                    found_signals.append(sig)

                    # Persist event
                    event_id = f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
                    event_record = TriggerEvent(
                        id=event_id,
                        lead_id=lead_id,
                        company_name=company_name,
                        company_domain=domain,
                        trigger_type=sig.trigger_type,
                        headline=sig.headline,
                        snippet=sig.snippet,
                        source=sig.source,
                        source_url=sig.source_url,
                        confidence=sig.confidence,
                        raw_metadata=json.dumps(sig.raw_metadata or {}),
                    )
                    if session:
                        session.add(event_record)

                    # AI Qualification
                    eval_data = await self.qualifier.qualify(account, sig)
                    eval_id = f"eval_{uuid.uuid4().hex[:8]}"
                    is_qualified = bool(eval_data.get("is_qualified", False))
                    urgency = int(eval_data.get("urgency_score", 5))

                    eval_record = TriggerEvaluation(
                        id=eval_id,
                        event_id=event_id,
                        lead_id=lead_id,
                        company_name=company_name,
                        is_qualified=is_qualified,
                        urgency_score=urgency,
                        relevance_score=int(eval_data.get("relevance_score", 5)),
                        why_now_rationale=eval_data.get("why_now_rationale", ""),
                        target_decision_maker=eval_data.get("target_decision_maker", "Founder"),
                        suggested_angle=eval_data.get("suggested_angle", "first_sales_hire"),
                    )
                    if session:
                        session.add(eval_record)
                    evaluations.append(eval_data)

                    # Generate brief if qualified and meets min urgency
                    if is_qualified and urgency >= min_urgency:
                        brief_dict = self.outreach.generate_brief(account, sig, eval_data)
                        brief_id = f"brief_{uuid.uuid4().hex[:8]}"

                        brief_record = OutreachBrief(
                            id=brief_id,
                            lead_id=lead_id,
                            company_name=company_name,
                            founder_name=brief_dict.get("founder_name"),
                            founder_email=brief_dict.get("founder_email"),
                            founder_title=brief_dict.get("founder_title"),
                            founder_linkedin=brief_dict.get("founder_linkedin"),
                            trigger_event_id=event_id,
                            evaluation_id=eval_id,
                            trigger_type=sig.trigger_type,
                            urgency_score=urgency,
                            angle=brief_dict.get("angle", "first_sales_hire"),
                            why_now_hook=brief_dict.get("why_now_hook", ""),
                            email_subject=brief_dict.get("email_subject", ""),
                            email_body=brief_dict.get("email_body", ""),
                            linkedin_note=brief_dict.get("linkedin_note", ""),
                            slack_preview=brief_dict.get("slack_preview", ""),
                            status=BriefStatus.DRAFT.value,
                        )
                        if session:
                            session.add(brief_record)
                        briefs.append(brief_dict)

            except Exception as exc:
                logger.error("Error executing detector %s on %s: %s", detector.name, company_name, exc)

        if session:
            await session.commit()

        return {
            "lead_id": lead_id,
            "company_name": company_name,
            "signals_found": len(found_signals),
            "evaluations": evaluations,
            "briefs_generated": len(briefs),
            "briefs": briefs,
        }

    async def scan_leads_batch(
        self,
        leads: list[dict[str, Any]],
        trigger_types: Optional[list[str]] = None,
        min_urgency: int = 6,
        session: Optional[AsyncSession] = None,
    ) -> TriggerRun:
        """
        Scan a batch of leads, record run telemetry, and commit all changes.
        """
        run_id = f"trigrun_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        run_record = TriggerRun(
            id=run_id,
            status=TriggerRunStatus.RUNNING.value,
            accounts_scanned=0,
            triggers_found=0,
            qualified_count=0,
            briefs_generated=0,
            treg_cost_usd=0.0,
            started_at=datetime.now(timezone.utc),
        )
        if session:
            session.add(run_record)
            await session.commit()

        initial_cost = self.treg.total_cost_usd

        try:
            for lead in leads:
                res = await self.scan_account(
                    account=lead,
                    trigger_types=trigger_types,
                    min_urgency=min_urgency,
                    session=session,
                )
                run_record.accounts_scanned += 1
                run_record.triggers_found += res["signals_found"]
                run_record.briefs_generated += res["briefs_generated"]
                if res["briefs_generated"] > 0:
                    run_record.qualified_count += 1

            run_record.status = TriggerRunStatus.COMPLETE.value
        except Exception as exc:
            logger.error("TriggerRun %s failed: %s", run_id, exc)
            run_record.status = TriggerRunStatus.ERROR.value
            run_record.error_message = str(exc)
        finally:
            run_record.finished_at = datetime.now(timezone.utc)
            run_record.treg_cost_usd = round(self.treg.total_cost_usd - initial_cost, 6)
            if session:
                session.add(run_record)
                await session.commit()

        return run_record

    # ── Database Queries ─────────────────────────────────────────────────────

    async def get_events(
        self,
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        company: Optional[str] = None,
        trigger_type: Optional[str] = None,
    ) -> list[TriggerEvent]:
        query = select(TriggerEvent).order_by(desc(TriggerEvent.detected_at))
        if company:
            query = query.where(TriggerEvent.company_name.ilike(f"%{company}%"))
        if trigger_type:
            query = query.where(TriggerEvent.trigger_type == trigger_type)
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_briefs(
        self,
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        min_urgency: Optional[int] = None,
    ) -> list[OutreachBrief]:
        query = select(OutreachBrief).order_by(desc(OutreachBrief.urgency_score), desc(OutreachBrief.created_at))
        if status:
            query = query.where(OutreachBrief.status == status)
        if min_urgency:
            query = query.where(OutreachBrief.urgency_score >= min_urgency)
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_brief_by_id(self, session: AsyncSession, brief_id: str) -> Optional[OutreachBrief]:
        query = select(OutreachBrief).where(OutreachBrief.id == brief_id)
        result = await session.execute(query)
        return result.scalars().first()

    async def update_brief_status(
        self,
        session: AsyncSession,
        brief_id: str,
        status: BriefStatus,
        notes: Optional[str] = None,
    ) -> Optional[OutreachBrief]:
        brief = await self.get_brief_by_id(session, brief_id)
        if not brief:
            return None
        brief.status = status.value
        if notes:
            brief.notes = notes
        brief.updated_at = datetime.now(timezone.utc)
        session.add(brief)
        await session.commit()
        await session.refresh(brief)
        return brief

    async def get_stats(self, session: AsyncSession) -> dict[str, Any]:
        total_events = (await session.execute(select(func.count(TriggerEvent.id)))).scalar() or 0
        total_briefs = (await session.execute(select(func.count(OutreachBrief.id)))).scalar() or 0
        approved_briefs = (await session.execute(
            select(func.count(OutreachBrief.id)).where(OutreachBrief.status == BriefStatus.APPROVED.value)
        )).scalar() or 0

        # Type distribution
        events = (await session.execute(select(TriggerEvent.trigger_type))).scalars().all()
        by_type: dict[str, int] = {}
        for t in events:
            by_type[t] = by_type.get(t, 0) + 1

        # Angle distribution
        brief_angles = (await session.execute(select(OutreachBrief.angle))).scalars().all()
        by_angle: dict[str, int] = {}
        for a in brief_angles:
            by_angle[a] = by_angle.get(a, 0) + 1

        avg_urgency = (await session.execute(select(func.avg(OutreachBrief.urgency_score)))).scalar() or 0.0

        # Total spend across runs
        total_spend = (await session.execute(select(func.sum(TriggerRun.treg_cost_usd)))).scalar() or 0.0

        return {
            "total_events": total_events,
            "total_briefs": total_briefs,
            "approved_briefs": approved_briefs,
            "by_trigger_type": by_type,
            "by_angle": by_angle,
            "avg_urgency": round(float(avg_urgency), 1),
            "total_spend_usd": round(float(total_spend), 4),
        }

