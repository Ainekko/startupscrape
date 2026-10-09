"""
app/trigger_engine/detectors/social.py — Social & Forum Discussion Detector
==========================================================================
Detects when a founder or community discusses the company, product pain,
or GTM/outbound challenges on Reddit or forums.
Why Now: Direct social buying signals or publicly expressed pipeline bottlenecks
provide hyper-personalized hooks for outreach.
"""

from __future__ import annotations

import logging
from typing import Any
from app.trigger_engine.detectors.base import BaseDetector, DetectedSignal
from app.trigger_engine.treg_client import TregClient

logger = logging.getLogger(__name__)

GTM_PAIN_KEYWORDS = [
    "outbound", "cold email", "pipeline", "apollo", "clay", "hubspot",
    "lead gen", "sales", "sdr", "gtm", "prospecting", "crm", "growth"
]


class SocialDiscussionDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "social_discussion"

    async def detect(
        self,
        account: dict[str, Any],
        treg: TregClient,
    ) -> list[DetectedSignal]:
        signals: list[DetectedSignal] = []
        company_name = account.get("company_name") or account.get("name") or ""
        founder_name = account.get("founder_name")
        if not founder_name and account.get("founders"):
            f_list = account["founders"]
            if isinstance(f_list, list) and f_list and isinstance(f_list[0], dict):
                founder_name = f_list[0].get("name")

        if not company_name:
            return signals

        try:
            discussions = await treg.search_social_discussions(company_name, founder_name)
            for disc in discussions:
                title = str(disc.get("title", ""))
                snippet = str(disc.get("snippet", ""))
                combined = f"{title} {snippet}".lower()

                # Check if relevant to GTM/growth/sales or specifically mentions the company/founder
                is_gtm_relevant = any(kw in combined for kw in GTM_PAIN_KEYWORDS)
                is_company_relevant = company_name.lower() in combined or (founder_name and founder_name.lower() in combined)

                if is_company_relevant:
                    confidence = 0.85 if is_gtm_relevant else 0.70
                    signals.append(
                        DetectedSignal(
                            trigger_type="social_discussion",
                            headline=title[:120],
                            snippet=snippet[:250],
                            source="treg:reddit_serp",
                            source_url=disc.get("url"),
                            confidence=confidence,
                            raw_metadata=disc,
                        )
                    )
                    break
        except Exception as exc:
            logger.warning("Error scanning social discussions for %s: %s", company_name, exc)

        return signals

