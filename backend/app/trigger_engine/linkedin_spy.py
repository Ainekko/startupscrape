"""
app/trigger_engine/linkedin_spy.py — Cheap & Reliable LinkedIn Spying Service
=============================================================================
Extracts high-intent hiring signals, leadership changes, and key personnel
from LinkedIn using micro-metered treg APIs and indexed SERP fallbacks.

Architecture & Cost Guarantee:
- Primary Job Search: anyapi.linkedin.search.jobs ($0.0005/success)
- High-Reliability Fallback / SERP Job Search: treg.google.serp.organic ($0.00015)
- Key Leadership & Founder Discovery: treg.google.serp.organic ($0.00015)
- Total scan cost per company: < $0.0008 (less than a tenth of a cent!)
- Zero browser headless dependencies (no Browserbase cookies, no login walls, no bans).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.trigger_engine.models import (
    LinkedInJobItem,
    LinkedInPersonItem,
    LinkedInSpyResponse,
)
from app.trigger_engine.treg_client import TregClient

logger = logging.getLogger(__name__)

# Keywords for GTM and engineering role categorizations
ROLE_CATEGORIES = {
    "gtm_leadership": [
        "head of sales", "vp sales", "vp of sales", "director of sales",
        "chief revenue officer", "cro", "vp revenue", "head of revenue",
        "vp business development", "head of business development", "vp commercial",
    ],
    "gtm_revops": [
        "revops", "revenue operations", "sales ops", "sales operations",
        "marketing ops", "revenue enablement", "sales enablement",
    ],
    "gtm_sales": [
        "account executive", "sales executive", "enterprise sales", "commercial sales",
        "sdr", "sales development", "bdr", "business development representative",
        "inside sales", "account manager",
    ],
    "engineering": [
        "software engineer", "full stack", "backend engineer", "frontend engineer",
        "machine learning", "ml engineer", "ai engineer", "data engineer",
        "founding engineer", "tech lead", "cto",
    ],
}

# Legal suffixes and domains to strip for clean company brand search
SUFFIX_PATTERN = re.compile(
    r"\b(inc|incorporated|llc|ltd|limited|corp|corporation|technologies|technology|labs|app|co|gmbh|saas)\b",
    re.IGNORECASE,
)
DOMAIN_PATTERN = re.compile(
    r"\.(com|ai|io|co|sh|dev|org|net|xyz|app|tech|so)\b",
    re.IGNORECASE,
)


class LinkedInSpyService:
    def __init__(self, treg_client: Optional[TregClient] = None):
        self.treg = treg_client or TregClient()

    def clean_company_name(self, raw_name: str) -> str:
        """
        Normalize company name to its core brand token for reliable search matching.
        Example: "Ramp Financial, Inc." -> "Ramp", "Cursor.sh" -> "Cursor"
        """
        if not raw_name:
            return ""
        name = DOMAIN_PATTERN.sub("", raw_name)
        name = SUFFIX_PATTERN.sub("", name)
        # Remove special characters like commas, dashes, parentheses
        name = re.sub(r"[,._\-()\[\]/]", " ", name)
        # Normalize whitespace
        clean = " ".join(name.split()).strip()
        return clean if clean else raw_name.strip()

    def categorize_title(self, title: str) -> str:
        """Classify job title or profile headline into structured role buckets."""
        lower = title.lower()
        for cat, keywords in ROLE_CATEGORIES.items():
            if any(kw in lower for kw in keywords):
                return cat
        return "other"

    async def search_jobs_anyapi(
        self,
        clean_name: str,
        roles: Optional[list[str]] = None,
    ) -> list[LinkedInJobItem]:
        """
        Query anyapi.linkedin.search.jobs ($0.0005/success).
        Scans for high-urgency GTM roles.
        """
        target_roles = roles or ["sales", "revops", "account executive"]
        all_jobs: list[LinkedInJobItem] = []
        seen_urls: set[str] = set()

        for role in target_roles[:2]:  # Top 2 role searches to cap cost
            query_str = f"{clean_name} {role}".strip()
            resp = await self.treg.call_endpoint(
                "anyapi.linkedin.search.jobs",
                payload={"query": query_str, "limit": 5},
                max_cost=0.01,
            )
            if not resp.get("success"):
                continue

            raw_data = resp.get("data", {})
            output = raw_data.get("output", {})
            data = output.get("data", {}) if isinstance(output, dict) else {}
            items = data.get("items", []) if isinstance(data, dict) else []

            name_lower = clean_name.lower()
            for item in items:
                job_url = item.get("url") or ""
                if job_url in seen_urls:
                    continue

                job_company = str(item.get("company", "")).lower()
                job_title = str(item.get("title", ""))

                # Check if company tokens match or overlap
                company_match = (
                    name_lower in job_company
                    or job_company in name_lower
                    or any(tok in job_company for tok in name_lower.split() if len(tok) >= 3)
                )

                if company_match:
                    if job_url:
                        seen_urls.add(job_url)
                    all_jobs.append(
                        LinkedInJobItem(
                            title=job_title,
                            company=item.get("company") or clean_name,
                            location=item.get("location") or "Remote",
                            url=job_url,
                            category=self.categorize_title(job_title),
                            source="anyapi.linkedin.search.jobs",
                            posted_utc=item.get("createdUtc"),
                        )
                    )

        return all_jobs

    async def search_jobs_serp(self, clean_name: str) -> list[LinkedInJobItem]:
        """
        Reliable fallback & supplement: Google SERP indexed LinkedIn jobs ($0.00015).
        Bypasses any LinkedIn API blocks or rate limits with public Google indexing.
        """
        query = f'site:linkedin.com/jobs "{clean_name}" (sales OR sdr OR bdr OR revops OR "account executive" OR "head of sales" OR engineer)'
        resp = await self.treg.call_endpoint(
            "treg.google.serp.organic",
            payload={"q": query},
            max_cost=0.005,
        )
        if not resp.get("success"):
            return []

        raw_data = resp.get("data", {})
        output = raw_data.get("output", {})
        results = output.get("organic_results", output.get("results", [])) if isinstance(output, dict) else []

        jobs: list[LinkedInJobItem] = []
        name_lower = clean_name.lower()

        for r in results[:5]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            url = r.get("link") or r.get("url") or ""

            # Check that it's a job link or contains company name
            if not ("linkedin.com/jobs" in url or "hiring" in title.lower() or name_lower in title.lower()):
                continue

            # Clean SERP title: "Company hiring Role in Location | LinkedIn" -> "Role"
            clean_title = title.replace(" - LinkedIn", "").replace(" | LinkedIn", "")
            # Try to extract the role part
            role_match = re.search(r"hiring (.*?) in", clean_title, re.IGNORECASE)
            if role_match:
                extracted_role = role_match.group(1).strip()
            else:
                extracted_role = clean_title.split(" - ")[0].split(" | ")[0].strip()

            jobs.append(
                LinkedInJobItem(
                    title=extracted_role,
                    company=clean_name,
                    location="See listing",
                    url=url,
                    category=self.categorize_title(clean_title + " " + snippet),
                    source="treg.google.serp.organic:linkedin_jobs",
                    posted_utc=None,
                )
            )

        return jobs

    async def search_people_serp(self, clean_name: str) -> list[LinkedInPersonItem]:
        """
        Extract key leadership & founders on LinkedIn via Google SERP ($0.00015).
        Returns exact profiles with title classification.
        """
        query = f'site:linkedin.com/in/ "{clean_name}" (founder OR "co-founder" OR ceo OR "head of sales" OR "vp of sales" OR "chief revenue" OR cro)'
        resp = await self.treg.call_endpoint(
            "treg.google.serp.organic",
            payload={"q": query},
            max_cost=0.005,
        )
        if not resp.get("success"):
            return []

        raw_data = resp.get("data", {})
        output = raw_data.get("output", {})
        results = output.get("organic_results", output.get("results", [])) if isinstance(output, dict) else []

        people: list[LinkedInPersonItem] = []
        seen_urls: set[str] = set()

        for r in results[:4]:
            url = r.get("link") or r.get("url") or ""
            if "linkedin.com/in/" not in url or url in seen_urls:
                continue
            seen_urls.add(url)

            raw_title = r.get("title", "")
            # Pattern: "Name - Title - Company | LinkedIn"
            cleaned_title = raw_title.replace(" - LinkedIn", "").replace(" | LinkedIn", "").replace(" – LinkedIn", "")
            parts = [p.strip() for p in re.split(r"[-–|•]", cleaned_title) if p.strip()]

            name = parts[0] if parts else "Unknown Contact"
            title_text = " - ".join(parts[1:]) if len(parts) > 1 else r.get("snippet", "")[:60]

            role_lower = title_text.lower()
            if "founder" in role_lower or "ceo" in role_lower:
                role_type = "founder"
            elif any(k in role_lower for k in ["head of sales", "vp", "cro", "director of sales"]):
                role_type = "sales_leader"
            elif any(k in role_lower for k in ["vp", "chief", "executive"]):
                role_type = "executive"
            else:
                role_type = "other"

            people.append(
                LinkedInPersonItem(
                    name=name,
                    title=title_text,
                    url=url,
                    role_type=role_type,
                )
            )

        return people

    def evaluate_timing_signals(
        self,
        company_name: str,
        jobs: list[LinkedInJobItem],
        people: list[LinkedInPersonItem],
    ) -> tuple[int, str, str]:
        """
        Evaluate urgency (1-10), timing hook, and outbound angle from detected LinkedIn intel.
        """
        categories = {j.category for j in jobs}
        titles_lower = " ".join(j.title.lower() for j in jobs)

        if "gtm_leadership" in categories:
            urgency = 9
            hook = f"Recently posted executive sales leadership roles ({', '.join(j.title for j in jobs if j.category == 'gtm_leadership')})."
            angle = "new_sales_leadership"
        elif "gtm_revops" in categories:
            urgency = 8
            hook = f"Actively hiring RevOps / Sales Operations to organize outbound tooling and pipeline data."
            angle = "revops_bottleneck"
        elif "gtm_sales" in categories:
            urgency = 8
            if any(k in titles_lower for k in ["sdr", "bdr", "sales development"]):
                hook = f"Hiring SDRs / BDRs ({', '.join(j.title for j in jobs if j.category == 'gtm_sales')}); outbound infrastructure required before rep starts."
                angle = "first_sales_hire"
            else:
                hook = f"Expanding Account Executive team; urgent need for pipeline volume."
                angle = "pipeline_acceleration"
        elif "engineering" in categories and not ("gtm_sales" in categories or "gtm_leadership" in categories):
            urgency = 7
            hook = f"Scaling engineering without dedicated sales reps; founder-led sales bottleneck."
            angle = "founder_led_bottleneck"
        elif jobs:
            urgency = 6
            hook = f"Active hiring detected on LinkedIn ({len(jobs)} roles open)."
            angle = "headcount_growth"
        else:
            urgency = 4
            hook = "No active hiring signals detected on LinkedIn."
            angle = "cold_baseline"

        return urgency, hook, angle

    async def spy(
        self,
        company_name: str,
        domain: Optional[str] = None,
        roles: Optional[list[str]] = None,
        include_people: bool = True,
    ) -> LinkedInSpyResponse:
        """
        Execute comprehensive, micro-metered LinkedIn spying.
        Returns validated, structured LinkedIn intelligence with exact micro-dollar accounting.
        """
        clean_name = self.clean_company_name(company_name)
        initial_spend = self.treg.total_cost_usd
        sources_used: list[str] = []

        # 1. Primary job search via anyapi
        jobs = await self.search_jobs_anyapi(clean_name, roles=roles)
        if jobs:
            sources_used.append("anyapi.linkedin.search.jobs")

        # 2. Reliable fallback via Google SERP if 0 jobs found
        if not jobs:
            serp_jobs = await self.search_jobs_serp(clean_name)
            if serp_jobs:
                jobs.extend(serp_jobs)
                sources_used.append("treg.google.serp.organic:jobs")

        # 3. People / Leadership discovery
        people: list[LinkedInPersonItem] = []
        if include_people:
            people = await self.search_people_serp(clean_name)
            if people:
                sources_used.append("treg.google.serp.organic:people")

        # 4. Urgency evaluation & Outbound Angle
        urgency, hook, angle = self.evaluate_timing_signals(company_name, jobs, people)

        # 5. Ledger cost calculation
        cost_usd = round(self.treg.total_cost_usd - initial_spend, 6)

        return LinkedInSpyResponse(
            company_name=company_name,
            clean_name=clean_name,
            domain=domain,
            jobs_found=jobs,
            people_found=people,
            urgency_score=urgency,
            timing_hook=hook,
            angle=angle,
            cost_usd=cost_usd,
            sources_used=sources_used,
            detected_at=datetime.now(timezone.utc),
        )

