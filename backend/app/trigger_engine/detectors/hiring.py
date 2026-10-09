"""
app/trigger_engine/detectors/hiring.py — GTM & Sales Hiring Signal Detector
==========================================================================
Detects when a company is:
1. Hiring their first SDR / BDR / Account Executive (urgency: outbound must be ready before start date)
2. Hiring RevOps / Sales Operations (urgency: existing stack is chaotic/broken)
3. Hiring Head of Sales / VP Sales (urgency: new leadership evaluating tooling & workflow)
4. Rapidly scaling engineering with ZERO sales headcount (urgency: founder-led sales bottleneck)
"""

from __future__ import annotations

import logging
from typing import Any
from app.trigger_engine.detectors.base import BaseDetector, DetectedSignal
from app.trigger_engine.treg_client import TregClient

logger = logging.getLogger(__name__)

GTM_KEYWORDS = {
    "sdr": ["sdr", "sales development", "bdr", "business development representative"],
    "revops": ["revops", "revenue operations", "sales ops", "sales operations"],
    "leadership": ["head of sales", "vp of sales", "vp sales", "chief revenue officer", "cro", "director of sales"],
    "ae": ["account executive", "sales executive", "enterprise sales", "commercial sales"],
}


class GTMHiringDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "gtm_hiring"

    async def detect(
        self,
        account: dict[str, Any],
        treg: TregClient,
    ) -> list[DetectedSignal]:
        signals: list[DetectedSignal] = []
        company_name = account.get("company_name") or account.get("name") or ""
        if not company_name:
            return signals

        # 1. Inspect existing open jobs in Verve metadata if present
        existing_jobs = account.get("jobs", [])
        if isinstance(existing_jobs, list) and existing_jobs:
            for job in existing_jobs:
                title = str(job.get("title", "")).lower() if isinstance(job, dict) else str(job).lower()
                for cat, keywords in GTM_KEYWORDS.items():
                    if any(kw in title for kw in keywords):
                        signals.append(
                            DetectedSignal(
                                trigger_type="gtm_hiring" if cat != "leadership" else "gtm_leadership",
                                headline=f"Hiring {job.get('title', title)} at {company_name}",
                                snippet=f"Open role detected from startup directory: {job.get('title', title)}",
                                source="verve:directory_jobs",
                                source_url=job.get("url") if isinstance(job, dict) else None,
                                confidence=0.85,
                                raw_metadata=job if isinstance(job, dict) else {"title": title},
                            )
                        )

        # 2. Query live LinkedIn jobs via LinkedInSpyService (anyapi + SERP fallback)
        if not signals:
            try:
                from app.trigger_engine.linkedin_spy import LinkedInSpyService
                spy_service = LinkedInSpyService(treg_client=treg)
                spy_result = await spy_service.spy(
                    company_name=company_name,
                    domain=account.get("website"),
                    include_people=False,
                )

                for job in spy_result.jobs_found[:4]:
                    signal_type = "gtm_leadership" if job.category == "gtm_leadership" else "gtm_hiring"
                    signals.append(
                        DetectedSignal(
                            trigger_type=signal_type,
                            headline=f"Hiring {job.title} at {company_name}",
                            snippet=f"Active job posting detected on LinkedIn: {job.title} in {job.location}",
                            source=job.source,
                            source_url=job.url,
                            confidence=0.92,
                            raw_metadata={
                                "title": job.title,
                                "company": job.company,
                                "location": job.location,
                                "url": job.url,
                                "category": job.category,
                                "source": job.source,
                                "posted_utc": job.posted_utc,
                            },
                        )
                    )
            except Exception as exc:
                logger.warning("Error scanning jobs for %s: %s", company_name, exc)

        return signals


