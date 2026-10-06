"""
app/services/pipeline_service.py — Pipeline Run and Persistence Service
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_session_context
from app.models import Lead, PipelineRun

logger = logging.getLogger(__name__)

_run_lock = threading.Lock()
_active_run: dict[str, Any] | None = None


class PipelineService:
    @staticmethod
    def get_active_status() -> dict[str, Any]:
        """Return the current running status."""
        global _active_run
        with _run_lock:
            if not _active_run:
                return {"status": "idle"}

            status = _active_run.get("status")

            if status == "running":
                return {"status": "running"}

            # For complete/error states, hold the result visible for 10s then clear
            finished = _active_run.get("finished_at") or _active_run.get("failed_at")
            try:
                fdt = datetime.fromisoformat(finished) if finished else datetime.now(timezone.utc)
            except Exception:
                fdt = datetime.now(timezone.utc)

            if (datetime.now(timezone.utc) - fdt).total_seconds() < 10:
                if status == "complete":
                    return {"status": "done", "run_id": _active_run.get("run_id")}
                if status == "error":
                    return {"status": "error", "error": _active_run.get("error")}

            _active_run = None
            return {"status": "idle"}

    @staticmethod
    def is_running() -> bool:
        with _run_lock:
            return bool(_active_run and _active_run.get("status") == "running")

    @classmethod
    async def list_runs(cls, session: AsyncSession | None = None) -> list[dict]:
        if session is None:
            return []
        stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc())
        db_runs = (await session.exec(stmt)).all()
        return [
            {
                "run_id": r.id,
                "started_at": r.started_at.isoformat() if r.started_at else "",
                "finished_at": r.finished_at.isoformat() if r.finished_at else "",
                "status": r.status,
                "funnel": _parse_funnel(r.funnel_data),
                "spend": _parse_spend(r.spend_data),
                "lead_count": r.lead_count,
            }
            for r in db_runs
        ]

    @classmethod
    async def get_run(cls, run_id: str, session: AsyncSession | None = None) -> dict | None:
        if session is None:
            return None
        run_stmt = select(PipelineRun).where(PipelineRun.id == run_id)
        db_run = (await session.exec(run_stmt)).first()
        if not db_run:
            return None

        lead_stmt = select(Lead).where(Lead.run_id == run_id).order_by(Lead.final_score.desc())
        db_leads = (await session.exec(lead_stmt)).all()

        return {
            "run_id": db_run.id,
            "started_at": db_run.started_at.isoformat() if db_run.started_at else "",
            "finished_at": db_run.finished_at.isoformat() if db_run.finished_at else "",
            "status": db_run.status,
            "funnel": _parse_funnel(db_run.funnel_data),
            "spend": _parse_spend(db_run.spend_data),
            "lead_count": len(db_leads),
            "leads": [_format_lead(lead) for lead in db_leads],
        }

    @classmethod
    async def execute_pipeline_background(
        cls,
        max_leads: int = 20,
        max_treg_cost: float = 1.0,
        batches: list[str] | None = None,
        sources: list[str] | None = None,
    ) -> None:
        global _active_run
        with _run_lock:
            _active_run = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}

        try:
            from pipeline.runner import run as pipeline_run
            result = await asyncio.to_thread(
                pipeline_run,
                max_leads=max_leads,
                max_treg_cost=max_treg_cost,
                batches=batches,
                sources=sources or ["yc"],
            )
            run_id = result.get("run_id", f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")

            try:
                await cls._save_run_to_db(result)
            except Exception as db_err:
                logger.error("Failed to persist run '%s' to database: %s", run_id, db_err)

            with _run_lock:
                _active_run = {
                    "status": "complete",
                    "run_id": run_id,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                }
            logger.info("Pipeline run '%s' completed and persisted.", run_id)

        except BaseException as exc:
            logger.critical("Pipeline run crashed — full traceback:", exc_info=True, stack_info=True)
            with _run_lock:
                _active_run = {
                    "status": "error",
                    "error": str(exc),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                }
            raise

    @classmethod
    async def save_run_data(cls, session: AsyncSession, run_data: dict) -> None:
        run_id = run_data.get("run_id", f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
        funnel = _parse_funnel(json.dumps(run_data.get("funnel", {})))
        spend = _parse_spend(json.dumps(run_data.get("spend", {})))
        leads_data = run_data.get("leads", [])

        existing_run = (await session.exec(select(PipelineRun).where(PipelineRun.id == run_id))).first()
        if not existing_run:
            session.add(PipelineRun(
                id=run_id,
                status=run_data.get("status", "complete"),
                funnel_data=json.dumps(funnel),
                spend_data=json.dumps(spend),
                lead_count=len(leads_data),
                finished_at=datetime.now(timezone.utc),
            ))
        else:
            existing_run.status = run_data.get("status", "complete")
            existing_run.funnel_data = json.dumps(funnel)
            existing_run.spend_data = json.dumps(spend)
            existing_run.lead_count = len(leads_data)
            existing_run.finished_at = datetime.now(timezone.utc)

        for item in leads_data:
            item_raw_id = str(item.get("id") or item.get("company_name", "").lower().replace(" ", "-"))
            if not item_raw_id:
                continue
            lead_id = f"{run_id}_{item_raw_id}" if not item_raw_id.startswith(f"{run_id}_") else item_raw_id

            email_res = item.get("email_result") or {}
            raw_email = email_res.get("email") or item.get("email")
            email_val = _sanitize_email(raw_email)
            email_status = email_res.get("status") or item.get("email_status")
            clean_company = (item.get("company_name") or item_raw_id).strip()
            clean_website = (item.get("website") or "").strip() or None
            clean_founder = (item.get("founder_name") or "").strip() or None

            # Preserve existing outreach progress across re-scrapes
            prior_status = "new"
            prior_notes = None
            prior_lead = (await session.exec(
                select(Lead).where(
                    or_(
                        Lead.company_name == clean_company,
                        Lead.email == email_val if email_val else False,
                    )
                ).where(Lead.outreach_status != "new")
            )).first()
            if prior_lead:
                prior_status = prior_lead.outreach_status
                prior_notes = prior_lead.notes

            existing_lead = (await session.exec(select(Lead).where(Lead.id == lead_id))).first()
            if not existing_lead:
                session.add(Lead(
                    id=lead_id,
                    run_id=run_id,
                    company_name=clean_company,
                    website=clean_website,
                    one_liner=item.get("one_liner"),
                    batch=item.get("batch"),
                    industry=item.get("industry"),
                    team_size=str(item.get("team_size") or ""),
                    tags=json.dumps(item.get("tags", [])),
                    yc_url=item.get("yc_url"),
                    waas_url=item.get("waas_url"),
                    linkedin_url=item.get("linkedin_url"),
                    founder_name=clean_founder,
                    founder_title=item.get("founder_title"),
                    founder_linkedin=item.get("founder_linkedin"),
                    email=email_val,
                    email_status=email_status,
                    tier1_score=float(item.get("tier1_score", 0.0)),
                    final_score=float(item.get("final_score", 0.0)),
                    is_competitor=bool(item.get("is_competitor", False)),
                    is_vertical_product=bool(item.get("is_vertical_product", False)),
                    outreach_status=prior_status,
                    notes=prior_notes,
                    founders_json=json.dumps(item.get("founders", [])),
                    signals_json=json.dumps(item.get("signals", [])),
                    raw_json=json.dumps(item),
                ))
            else:
                existing_lead.run_id = run_id
                existing_lead.final_score = float(item.get("final_score", existing_lead.final_score))
                existing_lead.tier1_score = float(item.get("tier1_score", existing_lead.tier1_score))
                if email_val:
                    existing_lead.email = email_val
                    existing_lead.email_status = email_status
                if clean_company:
                    existing_lead.company_name = clean_company
                if clean_website:
                    existing_lead.website = clean_website
                if clean_founder:
                    existing_lead.founder_name = clean_founder
                if prior_status != "new":
                    existing_lead.outreach_status = prior_status
                    if prior_notes:
                        existing_lead.notes = prior_notes
                existing_lead.raw_json = json.dumps(item)
                existing_lead.updated_at = datetime.now(timezone.utc)

        await session.commit()
        logger.info("Successfully persisted run '%s' with %d leads to PostgreSQL", run_id, len(leads_data))

    @classmethod
    async def _save_run_to_db(cls, run_data: dict) -> None:
        async with get_session_context() as session:
            if session is None:
                logger.warning("No DB session available; skipping persist.")
                return
            await cls.save_run_data(session=session, run_data=run_data)


# ---------------------------------------------------------------------------
# Module-level helpers (not class methods — they don't need self/cls)
# ---------------------------------------------------------------------------

def _parse_funnel(raw: str | None) -> dict[str, int]:
    data = {}
    if raw:
        try:
            data = json.loads(raw)
        except Exception:
            pass
    scraped = int(data.get("raw", data.get("scraped", 0)) or 0)
    prefiltered = int(data.get("prefiltered", 0) or 0)
    tier1 = int(data.get("tier1_kept", data.get("scored", 0)) or 0)
    email = int(data.get("email_found", data.get("enriched", 0)) or 0)
    final = int(data.get("final_leads", data.get("qualified", 0)) or 0)
    return {
        "raw": scraped, "prefiltered": prefiltered, "tier1_kept": tier1,
        "email_found": email, "final_leads": final,
        "scraped": scraped, "enriched": email, "qualified": final,
    }


def _parse_spend(raw: str | None) -> dict[str, Any]:
    data = {}
    if raw:
        try:
            data = json.loads(raw)
        except Exception:
            pass
    treg = float(data.get("treg_usd", data.get("total_usd", 0.0)) or 0.0)
    return {"treg_usd": treg, "total_usd": treg, "jev_judge": data.get("jev_judge", "heuristic")}


def _sanitize_email(email: str | None) -> str | None:
    if not email:
        return None
    import re
    cleaned = email.strip().lower()
    return cleaned if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned) else None


def _format_lead(lead: Lead) -> dict[str, Any]:
    email_res = None
    if lead.email:
        email_res = {
            "email": lead.email,
            "verified": lead.email_status in ("valid", "verified"),
            "status": lead.email_status or "valid",
        }

    if lead.raw_json:
        try:
            data = json.loads(lead.raw_json)
            data["id"] = lead.id
            data["run_id"] = lead.run_id
            data["company_name"] = lead.company_name
            data["outreach_status"] = lead.outreach_status
            data["notes"] = lead.notes
            data["final_score"] = lead.final_score
            data["tier1_score"] = lead.tier1_score
            if email_res and not data.get("email_result"):
                data["email_result"] = email_res
            return data
        except Exception:
            pass

    return {
        "id": lead.id,
        "run_id": lead.run_id,
        "company_name": lead.company_name,
        "website": lead.website,
        "one_liner": lead.one_liner,
        "batch": lead.batch,
        "industry": lead.industry,
        "yc_url": lead.yc_url,
        "waas_url": lead.waas_url,
        "linkedin_url": lead.linkedin_url,
        "founder_name": lead.founder_name,
        "founder_title": lead.founder_title,
        "founder_linkedin": lead.founder_linkedin,
        "founders": json.loads(lead.founders_json) if lead.founders_json else [],
        "signals": json.loads(lead.signals_json) if lead.signals_json else [],
        "tier1_score": lead.tier1_score,
        "final_score": lead.final_score,
        "is_competitor": lead.is_competitor,
        "is_vertical_product": lead.is_vertical_product,
        "email_result": email_res,
        "email": lead.email,
        "email_status": lead.email_status,
        "outreach_status": lead.outreach_status,
        "notes": lead.notes,
    }
