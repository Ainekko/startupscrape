"""
app/trigger_engine/detectors/tech.py — Tech Stack & Tooling Detector
====================================================================
Detects modern GTM and data technologies in the company's stack:
HubSpot, Salesforce, Apollo, Clay, Segment, PostHog, Supabase, Postgres.
Why Now: Flowjoy engineers custom outbound engines directly around their existing stack
(no new $1k/mo data platform, no platform lock-in, 100% code ownership).
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse
from app.trigger_engine.detectors.base import BaseDetector, DetectedSignal
from app.trigger_engine.treg_client import TregClient

logger = logging.getLogger(__name__)

TARGET_TECH = [
    "hubspot", "salesforce", "apollo", "clay", "outreach", "salesloft",
    "segment", "posthog", "supabase", "postgres", "stripe"
]


class TechStackDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "tech_stack"

    def _extract_domain(self, website: str | None) -> str | None:
        if not website:
            return None
        w = str(website).strip().lower()
        if not w.startswith(("http://", "https://")):
            w = "https://" + w
        try:
            netloc = urlparse(w).netloc
            if ":" in netloc:
                netloc = netloc.split(":")[0]
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc if "." in netloc else None
        except Exception:
            return None

    async def detect(
        self,
        account: dict[str, Any],
        treg: TregClient,
    ) -> list[DetectedSignal]:
        signals: list[DetectedSignal] = []
        company_name = account.get("company_name") or account.get("name") or ""
        website = account.get("website")
        domain = self._extract_domain(website)

        if not domain:
            return signals

        # 1. Check tags or metadata from Verve
        tags = account.get("tags") or []
        if isinstance(tags, list):
            found_tags = [t for t in tags if any(tech in str(t).lower() for tech in TARGET_TECH)]
            if found_tags:
                signals.append(
                    DetectedSignal(
                        trigger_type="tech_stack",
                        headline=f"Active GTM Stack identified at {company_name}",
                        snippet=f"Detected tooling in stack: {', '.join(found_tags[:4])}",
                        source="verve:account_tags",
                        confidence=0.80,
                        raw_metadata={"technologies": found_tags},
                    )
                )

        # 2. Enrich via treg company enrichment if no tech signal found
        if not signals:
            try:
                enrich_data = await treg.enrich_company_tech(domain)
                techs = enrich_data.get("technologies") or enrich_data.get("tech_stack") or []
                if isinstance(techs, list):
                    detected_tools = []
                    for t in techs:
                        name = str(t.get("name", t) if isinstance(t, dict) else t).lower()
                        if any(target in name for target in TARGET_TECH):
                            detected_tools.append(name.capitalize())

                    if detected_tools:
                        signals.append(
                            DetectedSignal(
                                trigger_type="tech_stack",
                                headline=f"Stack detected: {', '.join(detected_tools[:3])} at {company_name}",
                                snippet=f"Company stack contains {', '.join(detected_tools[:5])}. Prime candidate for Flowjoy deterministic stack integration.",
                                source="treg:companies.enrich",
                                confidence=0.88,
                                raw_metadata={"detected_tools": detected_tools},
                            )
                        )
            except Exception as exc:
                logger.warning("Error detecting tech stack for %s: %s", domain, exc)

        return signals

