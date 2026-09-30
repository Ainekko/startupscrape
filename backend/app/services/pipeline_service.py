"""
app/services/pipeline_service.py — Pipeline Run and Persistence Service
========================================================================
Manages pipeline runs, background execution, database persistence, and JSON fallbacks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_session_context
from app.models import Lead, PipelineRun

logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = Path(__file__).resolve().parents[2]   # backend/
ROOT        = BACKEND_DIR.parent                    # startupscrape/
DATA_DIR    = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Ensure root is importable for pipeline package
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_run_lock = threading.Lock()
_active_run: dict[str, Any] | None = None


class PipelineService:
    @staticmethod
    def get_active_status() -> dict[str, Any]:
        """Return the current running status or idle."""
        with _run_lock:
            return _active_run or {"status": "idle"}

    @staticmethod
    def is_running() -> bool:
        """Check if a pipeline run is currently in progress."""
        with _run_lock:
            return bool(_active_run and _active_run.get("status") == "running")

    @staticmethod
    def format_lead_for_frontend(lead: Lead) -> dict[str, Any]:
        """Format a Lead database record into the exact schema expected by the Svelte frontend."""
        if lead.raw_json:
            try:
                data = json.loads(lead.raw_json)
                data["outreach_status"] = lead.outreach_status
                data["notes"] = lead.notes
                data["final_score"] = lead.final_score
                data["tier1_score"] = lead.tier1_score
                return data
            except Exception:
                pass

        email_res = None
        if lead.email:
            email_res = {"email": lead.email, "verified": lead.email_status == "valid"}

        return {
            "id": lead.id,
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
            "outreach_status": lead.outreach_status,
            "notes": lead.notes,
        }

    @classmethod
    async def list_runs(cls, session: AsyncSession | None = None) -> list[dict]:
        """
        List all completed runs. Queries the PostgreSQL database first;
        falls back to data/run_*.json if DB is empty or unavailable.
        """
        if session is not None:
            try:
                stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc())
                db_runs = (await session.exec(stmt)).all()
                if db_runs:
                    result = []
                    for r in db_runs:
                        funnel = json.loads(r.funnel_data) if r.funnel_data else {}
                        spend = json.loads(r.spend_data) if r.spend_data else {}
                        result.append({
                            "run_id": r.id,
                            "started_at": r.started_at.isoformat() if r.started_at else "",
                            "finished_at": r.finished_at.isoformat() if r.finished_at else "",
                            "status": r.status,
                            "funnel": funnel,
                            "spend": spend,
                            "lead_count": r.lead_count,
                            "source": "database",
                        })
                    return result
            except Exception as exc:
                logger.warning("Could not read runs from DB, falling back to files: %s", exc)

        # Fallback: scan DATA_DIR
        return cls._list_runs_from_files()

    @classmethod
    async def get_run(cls, run_id: str, session: AsyncSession | None = None) -> dict | None:
        """
        Get run details and lead list. Tries database first, then JSON file.
        """
        if session is not None:
            try:
                run_stmt = select(PipelineRun).where(PipelineRun.id == run_id)
                db_run = (await session.exec(run_stmt)).first()
                if db_run:
                    lead_stmt = select(Lead).where(Lead.run_id == run_id).order_by(Lead.final_score.desc())
                    db_leads = (await session.exec(lead_stmt)).all()

                    funnel = json.loads(db_run.funnel_data) if db_run.funnel_data else {}
                    spend = json.loads(db_run.spend_data) if db_run.spend_data else {}

                    return {
                        "run_id": db_run.id,
                        "started_at": db_run.started_at.isoformat() if db_run.started_at else "",
                        "finished_at": db_run.finished_at.isoformat() if db_run.finished_at else "",
                        "status": db_run.status,
                        "funnel": funnel,
                        "spend": spend,
                        "lead_count": len(db_leads),
                        "leads": [cls.format_lead_for_frontend(l) for l in db_leads],
                        "source": "database",
                    }
            except Exception as exc:
                logger.warning("Could not load run '%s' from DB: %s", run_id, exc)

        # Fallback to file
        return cls._load_run_from_file(run_id)

    @classmethod
    def execute_pipeline_background(cls, max_leads: int = 20, max_treg_cost: float = 1.0) -> None:
        """Background worker function executing the full pipeline and persisting results."""
        global _active_run
        with _run_lock:
            _active_run = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}

        try:
            from pipeline.runner import run as pipeline_run
            result = pipeline_run(max_leads=max_leads, max_treg_cost=max_treg_cost)
            run_id = result.get("run_id", f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")

            # Persist to database asynchronously via event loop
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(cls._save_run_to_db(result))
                loop.close()
            except Exception as db_err:
                logger.error("Failed to sync run '%s' to database: %s", run_id, db_err)

            with _run_lock:
                _active_run = {
                    "status": "complete",
                    "run_id": run_id,
                    "lead_count": len(result.get("leads", [])),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                }
            logger.info("Pipeline run '%s' completed successfully.", run_id)

        except Exception as exc:
            logger.error("Pipeline run execution failed: %s", exc)
            with _run_lock:
                _active_run = {
                    "status": "error",
                    "error": str(exc),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                }

    @classmethod
    async def persist_json_run_file(cls, path: Path | str, session: AsyncSession) -> dict:
        """Load a JSON run file from disk and persist it into PostgreSQL."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Run file {path} not found")
        data = json.loads(p.read_text(encoding="utf-8"))
        await cls.save_run_data(session=session, run_data=data)
        return data

    @classmethod
    async def save_run_data(cls, session: AsyncSession, run_data: dict) -> None:
        """Persist a run dictionary into the given active AsyncSession."""
        run_id = run_data.get("run_id", f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
        funnel = run_data.get("funnel", {})
        spend = run_data.get("spend", {})
        leads_data = run_data.get("leads", [])

        # Check if run record exists
        existing_run = (await session.exec(select(PipelineRun).where(PipelineRun.id == run_id))).first()
        if not existing_run:
            run_obj = PipelineRun(
                id=run_id,
                status=run_data.get("status", "complete"),
                funnel_data=json.dumps(funnel),
                spend_data=json.dumps(spend),
                lead_count=len(leads_data),
                finished_at=datetime.now(timezone.utc),
            )
            session.add(run_obj)
        else:
            existing_run.status = run_data.get("status", "complete")
            existing_run.funnel_data = json.dumps(funnel)
            existing_run.spend_data = json.dumps(spend)
            existing_run.lead_count = len(leads_data)
            existing_run.finished_at = datetime.now(timezone.utc)

        # Persist each lead
        for item in leads_data:
            lead_id = str(item.get("id") or item.get("company_name", "").lower().replace(" ", "-"))
            if not lead_id:
                continue

            existing_lead = (await session.exec(select(Lead).where(Lead.id == lead_id))).first()
            email_res = item.get("email_result", {}) or {}
            email_val = email_res.get("email") or item.get("email")
            email_status = email_res.get("status")

            if not existing_lead:
                new_lead = Lead(
                    id=lead_id,
                    run_id=run_id,
                    company_name=item.get("company_name", lead_id),
                    website=item.get("website"),
                    one_liner=item.get("one_liner"),
                    batch=item.get("batch"),
                    industry=item.get("industry"),
                    team_size=str(item.get("team_size") or ""),
                    tags=json.dumps(item.get("tags", [])),
                    yc_url=item.get("yc_url"),
                    waas_url=item.get("waas_url"),
                    linkedin_url=item.get("linkedin_url"),
                    founder_name=item.get("founder_name"),
                    founder_title=item.get("founder_title"),
                    founder_linkedin=item.get("founder_linkedin"),
                    email=email_val,
                    email_status=email_status,
                    tier1_score=float(item.get("tier1_score", 0.0)),
                    final_score=float(item.get("final_score", 0.0)),
                    is_competitor=bool(item.get("is_competitor", False)),
                    is_vertical_product=bool(item.get("is_vertical_product", False)),
                    founders_json=json.dumps(item.get("founders", [])),
                    signals_json=json.dumps(item.get("signals", [])),
                    raw_json=json.dumps(item),
                )
                session.add(new_lead)
            else:
                existing_lead.run_id = run_id
                existing_lead.final_score = float(item.get("final_score", existing_lead.final_score))
                existing_lead.tier1_score = float(item.get("tier1_score", existing_lead.tier1_score))
                if email_val:
                    existing_lead.email = email_val
                    existing_lead.email_status = email_status
                existing_lead.raw_json = json.dumps(item)
                existing_lead.updated_at = datetime.now(timezone.utc)

        await session.commit()
        logger.info("Successfully persisted run '%s' with %d leads to PostgreSQL", run_id, len(leads_data))

    @classmethod
    async def _save_run_to_db(cls, run_data: dict) -> None:
        """Persist pipeline run summary and generated leads into PostgreSQL using session context."""
        async with get_session_context() as session:
            if session is None:
                logger.warning("Database session context unavailable; skipping DB persist.")
                return
            await cls.save_run_data(session=session, run_data=run_data)

    @staticmethod
    def _list_runs_from_files() -> list[dict]:
        runs = []
        for p in sorted(DATA_DIR.glob("run_*.json"), reverse=True):
            if "_partial" in p.name:
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                runs.append({
                    "run_id": data.get("run_id", p.stem),
                    "started_at": data.get("started_at", ""),
                    "finished_at": data.get("finished_at", ""),
                    "status": data.get("status", "complete"),
                    "funnel": data.get("funnel", {}),
                    "spend": data.get("spend", {}),
                    "lead_count": len(data.get("leads", [])),
                    "source": "file",
                })
            except Exception:
                pass
        return runs

    @staticmethod
    def _load_run_from_file(run_id: str) -> dict | None:
        candidates = list(DATA_DIR.glob(f"{run_id}*.json"))
        if not candidates:
            return None
        path = sorted(candidates)[-1]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["source"] = "file"
            return data
        except Exception:
            return None
