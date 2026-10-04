"""
app/services/lead_service.py — Lead Management, Filtering, Outcomes & Exports
=============================================================================
Provides query filtering, status updates, outcome tracking, and CSV exports.
PostgreSQL database is the primary source of truth and query engine.
Includes data sanitization and prospect deduplication for sequencer safety.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import aliased
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import (
    Lead,
    LeadFilterParams,
    OutreachOutcome,
    OutreachStatus,
)

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT        = BACKEND_DIR.parent
DATA_DIR    = ROOT / "data"


def sanitize_email(email: str | None) -> str | None:
    """Normalize and validate an email address."""
    if not email:
        return None
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


class LeadService:
    @classmethod
    async def query_leads(
        cls,
        session: AsyncSession | None,
        params: LeadFilterParams,
    ) -> dict[str, Any]:
        """
        Query leads from the primary database engine with filtering, sorting, and pagination.
        When querying across all runs (run_id is None) and dedupe is True, leads are deduplicated
        by email / company name so sequencers and lead lists never contain duplicate prospects.
        Falls back to local file parsing only if the database is disconnected.
        """
        if session is not None:
            try:
                conditions = []

                if params.query:
                    search = f"%{params.query.strip().lower()}%"
                    conditions.append(
                        or_(
                            func.lower(Lead.company_name).like(search),
                            func.lower(Lead.one_liner).like(search),
                            func.lower(Lead.founder_name).like(search),
                        )
                    )

                if params.batch:
                    conditions.append(Lead.batch == params.batch.strip())

                if params.industry:
                    conditions.append(func.lower(Lead.industry).like(f"%{params.industry.strip().lower()}%"))

                if params.min_score is not None:
                    conditions.append(Lead.final_score >= params.min_score)

                if params.max_score is not None:
                    conditions.append(Lead.final_score <= params.max_score)

                if params.has_email is True:
                    conditions.append(Lead.email.isnot(None))
                elif params.has_email is False:
                    conditions.append(Lead.email.is_(None))

                if params.outreach_status:
                    conditions.append(Lead.outreach_status == params.outreach_status)

                if params.run_id:
                    conditions.append(Lead.run_id == params.run_id)

                # Deduplication expression (email if present, else normalized company name)
                dedupe_key = func.coalesce(
                    func.nullif(func.lower(func.trim(Lead.email)), ""),
                    func.lower(func.trim(Lead.company_name)),
                )

                if params.dedupe and not params.run_id:
                    # Window function to pick top-scoring / newest record per unique entity
                    row_num = func.row_number().over(
                        partition_by=dedupe_key,
                        order_by=(Lead.final_score.desc(), Lead.created_at.desc()),
                    ).label("rn")

                    subq_stmt = select(Lead, row_num)
                    for cond in conditions:
                        subq_stmt = subq_stmt.where(cond)
                    subq = subq_stmt.subquery()

                    lead_alias = aliased(Lead, subq)
                    statement = select(lead_alias).where(subq.c.rn == 1)

                    count_statement = select(func.count(func.distinct(dedupe_key)))
                    for cond in conditions:
                        count_statement = count_statement.where(cond)

                    # Sorting
                    if params.sort_by == "score_asc":
                        statement = statement.order_by(lead_alias.final_score.asc())
                    elif params.sort_by == "name_asc":
                        statement = statement.order_by(lead_alias.company_name.asc())
                    elif params.sort_by == "date_desc":
                        statement = statement.order_by(lead_alias.created_at.desc())
                    else:  # default: score_desc
                        statement = statement.order_by(lead_alias.final_score.desc())
                else:
                    statement = select(Lead)
                    count_statement = select(func.count(Lead.id))
                    for cond in conditions:
                        statement = statement.where(cond)
                        count_statement = count_statement.where(cond)

                    # Sorting
                    if params.sort_by == "score_asc":
                        statement = statement.order_by(Lead.final_score.asc())
                    elif params.sort_by == "name_asc":
                        statement = statement.order_by(Lead.company_name.asc())
                    elif params.sort_by == "date_desc":
                        statement = statement.order_by(Lead.created_at.desc())
                    else:  # default: score_desc
                        statement = statement.order_by(Lead.final_score.desc())

                total = (await session.exec(count_statement)).one() or 0
                statement = statement.offset(params.offset).limit(params.limit)
                items = (await session.exec(statement)).all()

                return {
                    "total": total,
                    "limit": params.limit,
                    "offset": params.offset,
                    "items": [cls.format_lead_for_frontend(lead) for lead in items],
                    "source": "database",
                }
            except Exception as exc:
                logger.error("Database query failed in query_leads: %s", exc)
                return cls._query_from_files(params)

        return cls._query_from_files(params)

    @staticmethod
    def format_lead_for_frontend(lead: Lead) -> dict[str, Any]:
        """Format a Lead database record into the exact schema expected by the Svelte frontend."""
        email_clean = sanitize_email(lead.email)
        email_res = None
        if email_clean:
            email_res = {
                "email": email_clean,
                "verified": lead.email_status in ("valid", "verified"),
                "status": lead.email_status or "valid",
            }

        if lead.raw_json:
            try:
                data = json.loads(lead.raw_json)
                data["id"] = lead.id
                data["run_id"] = lead.run_id
                data["company_name"] = sanitize_text(lead.company_name) or lead.company_name
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
            "company_name": sanitize_text(lead.company_name) or lead.company_name,
            "website": sanitize_text(lead.website),
            "one_liner": lead.one_liner,
            "batch": lead.batch,
            "industry": lead.industry,
            "yc_url": lead.yc_url,
            "waas_url": lead.waas_url,
            "linkedin_url": lead.linkedin_url,
            "founder_name": sanitize_text(lead.founder_name),
            "founder_title": lead.founder_title,
            "founder_linkedin": lead.founder_linkedin,
            "founders": json.loads(lead.founders_json) if lead.founders_json else [],
            "signals": json.loads(lead.signals_json) if lead.signals_json else [],
            "tier1_score": lead.tier1_score,
            "final_score": lead.final_score,
            "is_competitor": lead.is_competitor,
            "is_vertical_product": lead.is_vertical_product,
            "email_result": email_res,
            "email": email_clean,
            "email_status": lead.email_status,
            "outreach_status": lead.outreach_status,
            "notes": lead.notes,
        }

    @classmethod
    async def get_lead(cls, lead_id: str, session: AsyncSession | None = None) -> dict | None:
        """Retrieve a single lead by ID from the primary database."""
        if session is not None:
            try:
                stmt = select(Lead).where(Lead.id == lead_id)
                lead = (await session.exec(stmt)).first()
                if not lead:
                    alt_stmt = select(Lead).where(
                        or_(Lead.id.endswith(f"_{lead_id}"), Lead.company_name == lead_id)
                    )
                    lead = (await session.exec(alt_stmt)).first()

                if lead:
                    data = cls.format_lead_for_frontend(lead)
                    data["source"] = "database"
                    return data
                return None
            except Exception as exc:
                logger.error("Error fetching lead '%s' from DB: %s", lead_id, exc)
                return cls._get_from_files(lead_id)

        return cls._get_from_files(lead_id)

    @staticmethod
    def _get_from_files(lead_id: str) -> dict | None:
        for p in sorted(DATA_DIR.glob("run_*.json"), reverse=True):
            try:
                content = json.loads(p.read_text(encoding="utf-8"))
                for l in content.get("leads", []):
                    if l.get("id") == lead_id or l.get("company_name", "").lower().replace(" ", "-") == lead_id:
                        l["source"] = "file"
                        return l
            except Exception:
                continue
        return None

    @classmethod
    async def update_status(
        cls,
        session: AsyncSession,
        lead_id: str,
        new_status: str,
        notes: Optional[str] = None,
    ) -> Lead | None:
        """
        Update outreach status for the lead and sync across identical company/email records.
        Prevents double-outreach across runs in cold-email sequencers.
        """
        stmt = select(Lead).where(Lead.id == lead_id)
        lead = (await session.exec(stmt)).first()
        if not lead:
            alt_stmt = select(Lead).where(
                or_(Lead.id.endswith(f"_{lead_id}"), Lead.company_name == lead_id)
            )
            lead = (await session.exec(alt_stmt)).first()

        if not lead:
            return None

        # Synchronize status across all runs for this company/email so outreach state is globally updated
        conditions = [Lead.company_name == lead.company_name]
        clean_email = sanitize_email(lead.email)
        if clean_email:
            conditions.append(func.lower(Lead.email) == clean_email)

        company_stmt = select(Lead).where(or_(*conditions))
        same_company_leads = (await session.exec(company_stmt)).all()
        for cl in same_company_leads:
            cl.outreach_status = new_status
            if notes:
                cl.notes = notes
            cl.updated_at = datetime.now(timezone.utc)

        outcome = OutreachOutcome(
            lead_id=lead_id,
            company_name=lead.company_name,
            channel="manual",
            status=new_status,
            notes=notes,
        )
        session.add(outcome)
        await session.commit()
        await session.refresh(lead)
        return lead

    @classmethod
    async def record_outcome(
        cls,
        session: AsyncSession,
        lead_id: str,
        channel: str,
        status: str,
        notes: Optional[str] = None,
    ) -> OutreachOutcome:
        """Record an outreach interaction/outcome."""
        lead = (await session.exec(select(Lead).where(Lead.id == lead_id))).first()
        company = lead.company_name if lead else None

        outcome = OutreachOutcome(
            lead_id=lead_id,
            company_name=company,
            channel=channel,
            status=status,
            notes=notes,
        )
        session.add(outcome)

        if lead and status in [s.value for s in OutreachStatus]:
            lead.outreach_status = status
            lead.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(outcome)
        return outcome

    @classmethod
    def export_leads_csv(cls, leads: list[dict], dedupe: bool = True) -> str:
        """
        Generate a CSV string from lead records with sanitization and sequencer deduplication.
        Ensures cold email sequencers never receive duplicate leads or emails.
        """
        output = io.StringIO()
        fieldnames = [
            "Company Name",
            "Final Score",
            "Founder Name",
            "Founder Title",
            "Founder LinkedIn",
            "Email",
            "Email Status",
            "Batch",
            "Industry",
            "Website",
            "One Liner",
            "Outreach Status",
            "YC URL",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        seen_emails: set[str] = set()
        seen_companies: set[str] = set()

        for lead in leads:
            email_val = lead.get("email")
            if not email_val and isinstance(lead.get("email_result"), dict):
                email_val = lead.get("email_result", {}).get("email")

            clean_email = sanitize_email(email_val) or ""
            clean_company = (lead.get("company_name", "") or "").strip().lower()

            if dedupe:
                if clean_email:
                    if clean_email in seen_emails:
                        continue
                    seen_emails.add(clean_email)
                elif clean_company:
                    if clean_company in seen_companies:
                        continue
                    seen_companies.add(clean_company)

            writer.writerow({
                "Company Name": (lead.get("company_name") or "").strip(),
                "Final Score": lead.get("final_score", 0.0),
                "Founder Name": (lead.get("founder_name") or "").strip(),
                "Founder Title": (lead.get("founder_title") or "").strip(),
                "Founder LinkedIn": (lead.get("founder_linkedin") or "").strip(),
                "Email": clean_email,
                "Email Status": lead.get("email_status", ""),
                "Batch": lead.get("batch", ""),
                "Industry": lead.get("industry", ""),
                "Website": (lead.get("website") or "").strip(),
                "One Liner": lead.get("one_liner", ""),
                "Outreach Status": lead.get("outreach_status", "new"),
                "YC URL": lead.get("yc_url", ""),
            })

        return output.getvalue()

    @classmethod
    def _query_from_files(cls, params: LeadFilterParams) -> dict[str, Any]:
        """In-memory filtering across existing local JSON run artifacts (backup fallback only)."""
        all_leads = []
        seen_ids = set()

        for p in sorted(DATA_DIR.glob("run_*.json"), reverse=True):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for lead in data.get("leads", []):
                    lid = lead.get("id") or lead.get("company_name", "")
                    if lid and lid not in seen_ids:
                        seen_ids.add(lid)
                        email_res = lead.get("email_result", {}) or {}
                        lead_copy = dict(lead)
                        raw_email = email_res.get("email") or lead.get("email")
                        lead_copy["email"] = sanitize_email(raw_email)
                        lead_copy["email_status"] = email_res.get("status")
                        lead_copy["outreach_status"] = lead.get("outreach_status", "new")
                        all_leads.append(lead_copy)
            except Exception:
                continue

        filtered = all_leads

        if params.query:
            q = params.query.lower()
            filtered = [
                l for l in filtered
                if q in (l.get("company_name") or "").lower()
                or q in (l.get("one_liner") or "").lower()
                or q in (l.get("founder_name") or "").lower()
            ]

        if params.batch:
            filtered = [l for l in filtered if l.get("batch") == params.batch]

        if params.industry:
            q_ind = params.industry.lower()
            filtered = [l for l in filtered if q_ind in (l.get("industry") or "").lower()]

        if params.min_score is not None:
            filtered = [l for l in filtered if float(l.get("final_score", 0)) >= params.min_score]

        if params.max_score is not None:
            filtered = [l for l in filtered if float(l.get("final_score", 0)) <= params.max_score]

        if params.has_email is True:
            filtered = [l for l in filtered if bool(l.get("email"))]
        elif params.has_email is False:
            filtered = [l for l in filtered if not bool(l.get("email"))]

        # Deduplicate prospects across runs if requested
        if params.dedupe and not params.run_id:
            deduped: dict[str, dict] = {}
            for l in filtered:
                clean_email = sanitize_email(l.get("email"))
                clean_comp = (l.get("company_name") or "").strip().lower()
                key = clean_email if clean_email else clean_comp
                if not key:
                    continue
                if key not in deduped or float(l.get("final_score", 0)) > float(deduped[key].get("final_score", 0)):
                    deduped[key] = l
            filtered = list(deduped.values())

        if params.sort_by == "score_asc":
            filtered.sort(key=lambda x: float(x.get("final_score", 0)))
        elif params.sort_by == "name_asc":
            filtered.sort(key=lambda x: (x.get("company_name") or "").lower())
        else:
            filtered.sort(key=lambda x: float(x.get("final_score", 0)), reverse=True)

        total = len(filtered)
        paginated = filtered[params.offset : params.offset + params.limit]

        return {
            "total": total,
            "limit": params.limit,
            "offset": params.offset,
            "items": paginated,
            "source": "file",
        }
