"""
app/trigger_engine/detectors/product.py — Product Launch & Milestone Detector
=============================================================================
Detects major product launches, version releases, ProductHunt features, or GA announcements.
Why Now: Fresh product availability requires immediate customer acquisition and GTM outbound
to drive trial signups, active pilots, and initial revenue.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from app.trigger_engine.detectors.base import BaseDetector, DetectedSignal
from app.trigger_engine.treg_client import TregClient

logger = logging.getLogger(__name__)

PRODUCT_LAUNCH_REGEX = re.compile(
    r"(launches|announces|unveils|introduces|releases|rolls out|v2|version 2|general availability|\bga\b|product hunt)",
    re.IGNORECASE,
)


class ProductLaunchDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "product_launch"

    async def detect(
        self,
        account: dict[str, Any],
        treg: TregClient,
    ) -> list[DetectedSignal]:
        signals: list[DetectedSignal] = []
        company_name = account.get("company_name") or account.get("name") or ""
        if not company_name:
            return signals

        try:
            articles = await treg.search_company_news(company_name, query_type="product")
            for art in articles:
                title = art.get("title", "")
                snippet = art.get("snippet", "")
                combined = f"{title} {snippet}"

                match = PRODUCT_LAUNCH_REGEX.search(combined)
                if match and (company_name.lower() in combined.lower()):
                    signals.append(
                        DetectedSignal(
                            trigger_type="product_launch",
                            headline=title,
                            snippet=snippet,
                            source=f"treg:product_news ({art.get('source', 'News')})",
                            source_url=art.get("url"),
                            confidence=0.82,
                            raw_metadata=art,
                        )
                    )
                    break
        except Exception as exc:
            logger.warning("Error scanning product news for %s: %s", company_name, exc)

        return signals

