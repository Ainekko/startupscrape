"""
app/services/pipeline_service.py — Pipeline Run and Persistence Service
========================================================================
Manages pipeline runs, background execution, database persistence, and JSON fallbacks.
The PostgreSQL database is the PRIMARY source of truth and data engine.
JSON files in data/ serve strictly as disaster recovery backup dumps.
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

from sqlalchemy import func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_session_context
from app.models import Lead, PipelineRun

logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = Path(__file__).resolve().parents[2]   # backend/
ROOT        = BACKEND_DIR.parent                    # startupscrape/
import os

DATA_DIR_ENV = os.getenv("DATA_DIR")
if DATA_DIR_ENV:
    DATA_DIR = Path(DATA_DIR_ENV)
elif Path("/opt/render").exists():
    DATA_DIR = Path("/tmp/data")
else:
    DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Ensure root is importable for pipeline package
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_run_lock = threading.Lock()
_active_run: dict[str, Any] | None = None


def _clear_active_run() -> None:
    """Clear the module-level active run state under the run lock."""
    global _active_run
    with _run_lock:
        _active_run = None


def format_funnel(data: dict) -> dict[str, int]:
    """Ensure canonical backend keys and frontend aliases are always populated."""
    raw = int(data.get("raw", data.get("scraped", 0)) or 0)
    prefiltered = int(data.get("prefiltered", 0) or 0)
    tier1 = int(data.get("tier1_kept", data.get("scored", 0)) or 0)
    email = int(data.get("email_found", data.get("enriched", 0)) or 0)
    final = int(data.get("final_leads", data.get("qualified", 0)) or 0)
    return {
        "raw": raw,
        "prefiltered": prefiltered,
        "tier1_kept": tier1,
        "email_found": email,
        "final_leads": final,
        # Standard frontend aliases
        "scraped": raw,
        "enriched": email,
        "qualified": final,
    }


def format_spend(data: dict) -> dict[str, Any]:
    """Ensure canonical backend keys and frontend aliases are always populated."""
    treg = float(data.get("treg_usd", data.get("total_usd", 0.0)) or 0.0)
    judge = data.get("jev_judge", "heuristic")
    return {
        "treg_usd": treg,
        "total_usd": treg,
        "jev_judge": judge,
    }


def sanitize_email(email: str | None) -> str | None:
    """Normalize and validate an email address."""
    if not email:
        return None
    import re
    cleaned = email.strip().lower()
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
        return cleaned
    return None


def sanitize_text(text: str | None) -> str | None:
    """Clean whitespace from strings."""
    if not text:
        return None
    cleaned = text.strip()
    return cleaned if cleaned else None


class PipelineService:
    @staticmethod
    def get_active_status() -> dict[str, Any]:
        """Return the current running status in the shape expected by the frontend."""
        with _run_lock:
            if not _active_run:
                return {"status": "idle"}

            status = _active_run.get("status")

            if status == "running":
                return {"status": "running"}

            if status == "complete":
                finished = _active_run.get("finished_at")
                run_id = _active_run.get("run_id")
                try:
                    if finished:
                        fdt = datetime.fromisoformat(finished)
                    else:
                        fdt = datetime.now(timezone.utc)
                except Exception:
                    fdt = datetime.now(timezone.utc)

                retention = 10
                if (datetime.now(timezone.utc) - fdt).total_seconds() < retention:
                    return {"status": "done", "run_id": run_id}
                else:
                    _clear_active_run()
                    return {"status": "idle"}

            if status == "error":
                err = _active_run.get("error")
                finished = _active_run.get("failed_at") or _active_run.get("finished_at")
                try:
                    if finished:
                        fdt = datetime.fromisoformat(finished)
                    else:
                        fdt = datetime.now(timezone.utc)
                except Exception:
                    fdt = datetime.now(timezone.utc)

                retention = 10
                if (datetime.now(timezone.utc) - fdt).total_seconds() < retention:
                    return {"status": "error", "error": err}
                else:
                    _clear_active_run()
                    return {"status": "idle"}

            return {"status": "idle"}

    @staticmethod
    def is_running() -> bool:
        """Check if a pipeline run is currently in progress."""
        with _run_lock:
            return bool(_active_run and _active_run.get("status") == "running")

    @staticmethod
    def format_lead_for_frontend(lead: Lead) -> dict[str, Any]:
        """Format a Lead database record into the exact schema expected by the Svelte frontend."""
        email_res = None
        if lead.email:
            email_res = {
                "email": lead.email,
                "verified": lead.email_status in ("valid", "verified"),
                "status": lead.email_status or "valid",
            }

        # If raw_json is present, use it as baseline to preserve enriched nested structures
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

    @classmethod
    async def list_runs(cls, session: AsyncSession | None = None) -> list[dict]:
        """
        List all pipeline runs from the primary database engine.
        Falls back to JSON file backups only if the database is disconnected.
        """
        if session is not None:
            try:
                stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc())
                db_runs = (await session.exec(stmt)).all()
                result = []
                for r in db_runs:
                    raw_funnel = json.loads(r.funnel_data) if r.funnel_data else {}
                    raw_spend = json.loads(r.spend_data) if r.spend_data else {}
                    result.append({
                        "run_id": r.id,
                        "started_at": r.started_at.isoformat() if r.started_at else "",
                        "finished_at": r.finished_at.isoformat() if r.finished_at else "",
                        "status": r.status,
                        "funnel": format_funnel(raw_funnel),
                        "spend": format_spend(raw_spend),
                        "lead_count": r.lead_count,
                        "source": "database",
                    })
                return result
            except Exception as exc:
                logger.error("Database query failed in list_runs: %s", exc)
                return cls._list_runs_from_files()

        return cls._list_runs_from_files()

    @classmethod
    async def get_run(cls, run_id: str, session: AsyncSession | None = None) -> dict | None:
        """
        Get run details and lead list from the primary database engine.
        Returns None if not found in database. Falls back to files only if DB is disconnected.
        """
        if session is not None:
            try:
                run_stmt = select(PipelineRun).where(PipelineRun.id == run_id)
                db_run = (await session.exec(run_stmt)).first()
                if not db_run:
                    return None

                lead_stmt = select(Lead).where(Lead.run_id == run_id).order_by(Lead.final_score.desc())
                db_leads = (await session.exec(lead_stmt)).all()

                raw_funnel = json.loads(db_run.funnel_data) if db_run.funnel_data else {}
                raw_spend = json.loads(db_run.spend_data) if db_run.spend_data else {}

                return {
                    "run_id": db_run.id,
                    "started_at": db_run.started_at.isoformat() if db_run.started_at else "",
                    "finished_at": db_run.finished_at.isoformat() if db_run.finished_at else "",
                    "status": db_run.status,
                    "funnel": format_funnel(raw_funnel),
                    "spend": format_spend(raw_spend),
                    "lead_count": len(db_leads) if db_leads else db_run.lead_count,
                    "leads": [cls.format_lead_for_frontend(l) for l in db_leads],
                    "source": "database",
                }
            except Exception as exc:
                logger.error("Database query failed in get_run for '%s': %s", run_id, exc)
                return cls._load_run_from_file(run_id)

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

            # Persist to primary PostgreSQL database
            try:
                app_loop = None
                try:
                    from app.main import app as _app
                    app_loop = getattr(_app.state, "loop", None)
                except Exception:
                    app_loop = None

                if app_loop and app_loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(cls._save_run_to_db(result), app_loop)
                    future.result(timeout=60)
                else:
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(cls._save_run_to_db(result))
                    finally:
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
            logger.info("Pipeline run '%s' completed and persisted.", run_id)

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
        """
        Persist a run dictionary and its leads into PostgreSQL.
        Each lead is given a unique primary key scoped to this run so that historical
        runs never lose their leads when companies are re-scraped in subsequent runs.
        """
        run_id = run_data.get("run_id", f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
        funnel = format_funnel(run_data.get("funnel", {}))
        spend = format_spend(run_data.get("spend", {}))
        leads_data = run_data.get("leads", [])

        # 1. Upsert PipelineRun
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

        # 2. Persist each lead scoped to this run
        for item in leads_data:
            item_raw_id = str(item.get("id") or item.get("company_name", "").lower().replace(" ", "-"))
            if not item_raw_id:
                continue

            # Unique key scoped to this run
            lead_record_id = f"{run_id}_{item_raw_id}" if not item_raw_id.startswith(f"{run_id}_") else item_raw_id

            existing_lead = (await session.exec(select(Lead).where(Lead.id == lead_record_id))).first()

            email_res = item.get("email_result", {}) or {}
            raw_email = email_res.get("email") or item.get("email")
            email_val = sanitize_email(raw_email)
            email_status = email_res.get("status") or item.get("email_status")

            clean_company = sanitize_text(item.get("company_name", item_raw_id)) or item_raw_id
            clean_website = sanitize_text(item.get("website"))
            clean_founder = sanitize_text(item.get("founder_name"))

            # Check if this company/email already has an active outreach status in DB to prevent sequencer reset
            prior_status = "new"
            prior_notes = None
            prior_lead = (await session.exec(
                select(Lead).where(
                    or_(
                        Lead.company_name == clean_company,
                        Lead.email == email_val if email_val else False
                    )
                ).where(Lead.outreach_status != "new")
            )).first()
            if prior_lead:
                prior_status = prior_lead.outreach_status
                prior_notes = prior_lead.notes

            if not existing_lead:
                new_lead = Lead(
                    id=lead_record_id,
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
                )
                session.add(new_lead)
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
    async def sync_all_backup_runs(cls, session: AsyncSession) -> int:
        """
        Sync all backup JSON run files from data directories into PostgreSQL.
        Ensures PostgreSQL is the complete, primary data engine with all runs and leads.
        Safe to call on startup — runs idempotently without duplicating or overwriting.
        """
        synced_count = 0
        search_dirs = [DATA_DIR]
        legacy_dir = ROOT / "data"
        if legacy_dir != DATA_DIR and legacy_dir.exists():
            search_dirs.append(legacy_dir)

        seen_names = set()
        candidates = []
        for d in search_dirs:
            for p in d.glob("run_*.json"):
                if p.name not in seen_names and "_partial" not in p.name:
                    seen_names.add(p.name)
                    candidates.append(p)
        candidates.sort()

        for p in candidates:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                run_id = data.get("run_id", p.stem)

                existing_run = (await session.exec(select(PipelineRun).where(PipelineRun.id == run_id))).first()
                lead_count = 0
                if existing_run:
                    lead_count = (await session.exec(select(func.count(Lead.id)).where(Lead.run_id == run_id))).one()

                expected_leads = len(data.get("leads", []))
                if not existing_run or (expected_leads > 0 and lead_count == 0):
                    await cls.save_run_data(session=session, run_data=data)
                    synced_count += 1
            except Exception as e:
                logger.warning("Could not sync backup run file %s: %s", p.name, e)

        if synced_count > 0:
            logger.info("Synced %d backup run files into PostgreSQL database.", synced_count)
        return synced_count

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
        search_dirs = [DATA_DIR]
        legacy_dir = ROOT / "data"
        if legacy_dir != DATA_DIR and legacy_dir.exists():
            search_dirs.append(legacy_dir)

        seen_names = set()
        candidates = []
        for d in search_dirs:
            for p in d.glob("run_*.json"):
                if p.name not in seen_names and "_partial" not in p.name:
                    seen_names.add(p.name)
                    candidates.append(p)
        candidates.sort(reverse=True)

        for p in candidates:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                funnel = format_funnel(data.get("funnel", {}))
                spend = format_spend(data.get("spend", {}))
                runs.append({
                    "run_id": data.get("run_id", p.stem),
                    "started_at": data.get("started_at", ""),
                    "finished_at": data.get("finished_at", ""),
                    "status": data.get("status", "complete"),
                    "funnel": funnel,
                    "spend": spend,
                    "lead_count": len(data.get("leads", [])),
                    "source": "file",
                })
            except Exception:
                pass
        return runs

    @staticmethod
    def _load_run_from_file(run_id: str) -> dict | None:
        search_dirs = [DATA_DIR]
        legacy_dir = ROOT / "data"
        if legacy_dir != DATA_DIR and legacy_dir.exists():
            search_dirs.append(legacy_dir)

        candidates = []
        for d in search_dirs:
            candidates.extend(d.glob(f"{run_id}*.json"))

        if not candidates:
            return None
        path = sorted(candidates)[-1]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["funnel"] = format_funnel(data.get("funnel", {}))
            data["spend"] = format_spend(data.get("spend", {}))
            data["source"] = "file"
            return data
        except Exception:
            return None
