"""
app/trigger_engine/detectors/funding.py — Funding & Capital Events Detector
==========================================================================
Detects when a company recently raised capital (Seed, Series A, Series B,
venture round, valuation milestone).
Why Now: Fresh capital creates immediate investor pressure to generate pipeline
and scale outbound, while core engineers are swamped with customer feature requests.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from app.trigger_engine.detectors.base import BaseDetector, DetectedSignal
from app.trigger_engine.treg_client import TregClient

logger = logging.getLogger(__name__)

FUNDING_REGEX = re.compile(
    r"(\$\d+(\.\d+)?\s*(m|million|k|b|billion)|raises|raised|secures|funding round|series\s+[a-c]|seed round|pre-seed)",
    re.IGNORECASE,
)


class FundingDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "funding"

    async def detect(
        self,
        account: dict[str, Any],
        treg: TregClient,
    ) -> list[DetectedSignal]:
        signals: list[DetectedSignal] = []
        company_name = account.get("company_name") or account.get("name") or ""
        if not company_name:
            return signals

        # 1. Search Google News via treg
        try:
            articles = await treg.search_company_news(company_name, query_type="funding")
            for art in articles:
                title = art.get("title", "")
                snippet = art.get("snippet", "")
                combined = f"{title} {snippet}"

                # Match funding patterns
                match = FUNDING_REGEX.search(combined)
                if match and (company_name.lower() in combined.lower()):
                    signals.append(
                        DetectedSignal(
                            trigger_type="funding",
                            headline=title,
                            snippet=snippet,
                            source=f"treg:news ({art.get('source', 'Google News')})",
                            source_url=art.get("url"),
                            confidence=0.88,
                            raw_metadata=art,
                        )
                    )
                    break # Take the most relevant funding news
        except Exception as exc:
            logger.warning("Error scanning funding news for %s: %s", company_name, exc)

        # 2. Fallback: check recent YC cohort / stage in Verve metadata
        if not signals:
            batch = str(account.get("batch") or "")
            if any(term in batch for term in ["2024", "2025", "2026", "W24", "S24", "W25", "S25", "W26"]):
                signals.append(
                    DetectedSignal(
                        trigger_type="funding",
                        headline=f"{company_name} YC Cohort Freshness ({batch})",
                        snippet=f"Recent graduate of Y Combinator {batch}. Under active investor mandate to build repeatable outbound pipeline.",
                        source="verve:yc_batch",
                        source_url=account.get("yc_url"),
                        confidence=0.80,
                        raw_metadata={"batch": batch, "stage": account.get("gtm_analysis", {}).get("stage", "Seed")},
                    )
                )

        return signals

