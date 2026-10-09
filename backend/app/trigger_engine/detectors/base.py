"""
app/trigger_engine/detectors/base.py — Base Detector Interface & Signal Dataclass
================================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.trigger_engine.treg_client import TregClient


@dataclass
class DetectedSignal:
    trigger_type: str
    headline: str
    snippet: str
    source: str
    source_url: Optional[str] = None
    confidence: float = 0.8
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseDetector(ABC):
    """Abstract base class for all signal detectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the detector (e.g. 'gtm_hiring')."""
        pass

    @abstractmethod
    async def detect(
        self,
        account: dict[str, Any],
        treg: TregClient,
    ) -> list[DetectedSignal]:
        """
        Scan an account dictionary (from Verve/Startupscrape) and return any detected signals.
        """
        pass

