"""
app/trigger_engine/detectors/linkedin_activity.py — LinkedIn Posts & Comments Detector
=====================================================================================
Turns a LinkedInIntelReport (company posts, founder posts, comments on them, and the
founders' own comments elsewhere) into Trigger Engine DetectedSignals.
Why Now: a founder posting about hiring/outbound, buyers asking for demos in the
comments, or investors engaging are the freshest public timing hooks available.

Data comes exclusively from treg providers — no LinkedIn login, no ban risk.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.trigger_engine.detectors.base import BaseDetector, DetectedSignal
from app.trigger_engine.linkedin_intel import IntelOptions, LinkedInIntelService
from app.trigger_engine.models import LinkedInIntelReport
from app.trigger_engine.treg_client import TregClient

logger = logging.getLogger(__name__)

MAX_SIGNALS_PER_ACCOUNT = 4


def report_to_signals(report: LinkedInIntelReport, limit: int = MAX_SIGNALS_PER_ACCOUNT) -> list[DetectedSignal]:
    """Map the strongest intel signals to DetectedSignals (one per kind, strongest first)."""
    out: list[DetectedSignal] = []
    seen_kinds: set[str] = set()
    for s in report.signals:
        if s.kind in seen_kinds:
            continue
        seen_kinds.add(s.kind)
        out.append(
            DetectedSignal(
                trigger_type=s.trigger_type,
                headline=s.headline[:120],
                snippet=s.evidence[:250],
                source=f"treg:linkedin:{s.kind}",
                source_url=s.source_url,
                confidence=s.confidence,
                raw_metadata={
                    "intel_kind": s.kind,
                    "actor": s.actor,
                    "posted_at": s.posted_at,
                    "recency_days": s.recency_days,
                    "account_urgency": report.urgency_score,
                    "summary": report.summary,
                },
            )
        )
        if len(out) >= limit:
            break
    return out


class LinkedInActivityDetector(BaseDetector):
    def __init__(self, options: Optional[IntelOptions] = None):
        self.options = options or IntelOptions()

    @property
    def name(self) -> str:
        return "linkedin_activity"

    async def detect_with_report(
        self,
        account: dict[str, Any],
        treg: TregClient,
    ) -> tuple[list[DetectedSignal], Optional[LinkedInIntelReport]]:
        company_name = account.get("company_name") or account.get("name")
        if not company_name:
            return [], None
        try:
            service = LinkedInIntelService(treg_client=treg)
            report = await service.gather(account, options=self.options)
            return report_to_signals(report), report
        except Exception as exc:
            logger.warning("LinkedIn activity scan failed for %s: %s", company_name, exc)
            return [], None

    async def detect(
        self,
        account: dict[str, Any],
        treg: TregClient,
    ) -> list[DetectedSignal]:
        signals, _ = await self.detect_with_report(account, treg)
        return signals

