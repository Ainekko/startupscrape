"""LinkedInActivityDetector + TriggerEngineService integration (offline, FakeTreg)."""

from __future__ import annotations

import asyncio

import pytest

from app.trigger_engine.detectors.linkedin_activity import (
    MAX_SIGNALS_PER_ACCOUNT,
    LinkedInActivityDetector,
    report_to_signals,
)
from app.trigger_engine.linkedin_intel import LinkedInIntelService
from app.trigger_engine.service import TriggerEngineService
from tests.linkedin_fixtures import NOW, FakeTreg, acme_account


@pytest.fixture(autouse=True)
def pin_now(monkeypatch):
    """Pin gather() to the fixture clock so the lookback filter is deterministic."""
    original = LinkedInIntelService.gather

    async def pinned(self, account, options=None, extra_founder_urls=None, now=None):
        return await original(self, account, options=options, extra_founder_urls=extra_founder_urls, now=NOW)

    monkeypatch.setattr(LinkedInIntelService, "gather", pinned)


def _report():
    service = LinkedInIntelService(treg_client=FakeTreg())
    return asyncio.run(service.gather(acme_account()))


def test_report_to_signals_one_per_kind_and_capped():
    report = _report()
    assert report.signals, "fixture should produce intel signals"
    signals = report_to_signals(report)
    assert 1 <= len(signals) <= MAX_SIGNALS_PER_ACCOUNT
    kinds = [s.raw_metadata["intel_kind"] for s in signals]
    assert len(kinds) == len(set(kinds))
    for s in signals:
        assert s.source.startswith("treg:linkedin:")
        assert len(s.headline) <= 120
        assert len(s.snippet) <= 250
        assert s.raw_metadata["account_urgency"] == report.urgency_score


def test_report_to_signals_respects_limit():
    report = _report()
    assert len(report_to_signals(report, limit=1)) == 1


def test_detector_detect_returns_signals():
    signals = asyncio.run(LinkedInActivityDetector().detect(acme_account(), FakeTreg()))
    assert signals
    assert all(s.source.startswith("treg:linkedin:") for s in signals)


def test_detector_without_company_name_is_noop():
    treg = FakeTreg()
    signals, report = asyncio.run(LinkedInActivityDetector().detect_with_report({"id": "x"}, treg))
    assert signals == [] and report is None
    assert treg.calls == []


def test_detector_swallows_provider_failures():
    treg = FakeTreg(responses={})  # every call 404s
    signals, report = asyncio.run(LinkedInActivityDetector().detect_with_report(acme_account(), treg))
    assert signals == []
    assert report is not None and report.errors


def test_scan_account_with_linkedin_activity_generates_briefs():
    service = TriggerEngineService(treg_client=FakeTreg())
    service.qualifier.api_key = ""  # force deterministic heuristic qualifier
    result = asyncio.run(
        service.scan_account(acme_account(), trigger_types=["linkedin_activity"], session=None)
    )
    assert result["lead_id"] == "lead_acme"
    assert result["signals_found"] >= 1
    assert result["briefs_generated"] >= 1

