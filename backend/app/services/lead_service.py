"""
app/services/lead_service.py — Lead Management, Filtering, Outcomes & Exports
=============================================================================
Provides query filtering, status updates, outcome tracking, and CSV exports.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

from sqlalchemy import func, or_
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


class LeadService:
    @classmethod
    async def query_leads(
        cls,
        session: AsyncSession | None,
        params: LeadFilterParams,
    ) -> dict[str, Any]:
        """Query leads with filtering, sorting, and pagination."""
        if session is not None:
            try:
                # Build base query
                statement = select(Lead)
                count_statement = select(func.count(Lead.id))

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

                # Pagination
                total = (await session.exec(count_statement)).one()
                statement = statement.offset(params.offset).limit(params.limit)
                items = (await session.exec(statement)).all()

                if items or total > 0:
                    return {
                        "total": total,
                        "limit": params.limit,
                        "offset": params.offset,
                        "items": [cls.format_lead_for_frontend(lead) for lead in items],
                        "source": "database",
                    }
            except Exception as exc:
                logger.warning("Database query failed, falling back to file leads: %s", exc)

        # Fallback to local files
        return cls._query_from_files(params)

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
    async def get_lead(cls, lead_id: str, session: AsyncSession | None = None) -> dict | None:
        """Retrieve a single lead by ID."""
        if session is not None:
            try:
                stmt = select(Lead).where(Lead.id == lead_id)
                lead = (await session.exec(stmt)).first()
                if lead:
                    data = cls.format_lead_for_frontend(lead)
                    data["source"] = "database"
                    return data
            except Exception as exc:
                logger.warning("Error fetching lead '%s' from DB: %s", lead_id, exc)

        # File fallback
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
        """Update the outreach status of a lead and record an outcome event."""
        stmt = select(Lead).where(Lead.id == lead_id)
        lead = (await session.exec(stmt)).first()
        if not lead:
            return None

        lead.outreach_status = new_status
        if notes:
            lead.notes = notes
        lead.updated_at = datetime.now(timezone.utc)

        # Also log outcome record
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
        # Find lead company name
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

        # Update lead's main status if applicable
        if lead and status in [s.value for s in OutreachStatus]:
            lead.outreach_status = status
            lead.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(outcome)
        return outcome

    @classmethod
    def export_leads_csv(cls, leads: list[dict]) -> str:
        """Generate a CSV string from lead records."""
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

        for lead in leads:
            email_val = lead.get("email")
            if not email_val and isinstance(lead.get("email_result"), dict):
                email_val = lead.get("email_result", {}).get("email")

            writer.writerow({
                "Company Name": lead.get("company_name", ""),
                "Final Score": lead.get("final_score", 0.0),
                "Founder Name": lead.get("founder_name", ""),
                "Founder Title": lead.get("founder_title", ""),
                "Founder LinkedIn": lead.get("founder_linkedin", ""),
                "Email": email_val or "",
                "Email Status": lead.get("email_status", ""),
                "Batch": lead.get("batch", ""),
                "Industry": lead.get("industry", ""),
                "Website": lead.get("website", ""),
                "One Liner": lead.get("one_liner", ""),
                "Outreach Status": lead.get("outreach_status", "new"),
                "YC URL": lead.get("yc_url", ""),
            })

        return output.getvalue()

    @classmethod
    def _query_from_files(cls, params: LeadFilterParams) -> dict[str, Any]:
        """In-memory filtering across existing local JSON run artifacts."""
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
                        lead_copy["email"] = email_res.get("email") or lead.get("email")
                        lead_copy["email_status"] = email_res.get("status")
                        lead_copy["outreach_status"] = lead.get("outreach_status", "new")
                        all_leads.append(lead_copy)
            except Exception:
                continue

        # Filter
        filtered = all_leads
        if params.query:
            q = params.query.lower()
            filtered = [
                l for l in filtered
                if q in l.get("company_name", "").lower()
                or q in l.get("one_liner", "").lower()
                or q in l.get("founder_name", "").lower()
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

        # Sort
        if params.sort_by == "score_asc":
            filtered.sort(key=lambda x: float(x.get("final_score", 0)))
        elif params.sort_by == "name_asc":
            filtered.sort(key=lambda x: x.get("company_name", "").lower())
        else:  # default score_desc
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
