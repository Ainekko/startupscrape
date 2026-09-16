import pytest
from startupscrape.models import StartupLead, JobPosting, Founder
from startupscrape.signals import (
    SignalDetector,
    should_enrich_with_browser,
    SIGNAL_FOUNDING_AE,
    SIGNAL_SALES_LEAD,
    SIGNAL_REVOPS,
    SIGNAL_RECENT_BATCH,
    SIGNAL_OPTIMAL_TEAM,
    SIGNAL_FOUNDER_BOTTLENECK
)


def test_signal_detector_job_titles():
    lead = StartupLead(
        id="test-saas",
        source="workatastartup",
        name="TestSaaS",
        batch="Winter 2025",
        team_size=15,
        is_hiring=True,
        jobs=[
            JobPosting(title="Founding Account Executive"),
            JobPosting(title="RevOps Lead")
        ]
    )

    signals = SignalDetector.detect_signals(lead)
    assert SIGNAL_FOUNDING_AE in signals
    assert SIGNAL_REVOPS in signals
    assert SIGNAL_RECENT_BATCH in signals
    assert SIGNAL_OPTIMAL_TEAM in signals


def test_signal_detector_pain_language():
    lead = StartupLead(
        id="pain-lead",
        source="yc",
        name="PainLead",
        one_liner="Replacing founder-led sales with AI workflows"
    )
    signals = SignalDetector.detect_signals(lead)
    assert SIGNAL_FOUNDER_BOTTLENECK in signals


def test_compute_pre_score_high_fit():
    lead = StartupLead(
        id="fit-lead",
        source="workatastartup",
        name="ScaleNow",
        batch="Winter 2026",
        team_size=20,
        is_hiring=True,
        jobs=[
            JobPosting(title="Head of Sales")
        ]
    )
    score = SignalDetector.compute_pre_score(lead)
    # base 4 + hiring 1 + sales lead 2 + recent batch 1 + team size 1 = 9
    assert score >= 8


def test_should_enrich_with_browser_low_score():
    lead = StartupLead(
        id="low-fit",
        source="yc",
        name="Dormant Tech",
        batch="Winter 2012",
        team_size=1,
        is_hiring=False
    )
    should_run, reason = should_enrich_with_browser(lead, min_score=7)
    assert should_run is False
    assert "threshold" in reason.lower()


def test_should_enrich_with_browser_already_complete():
    lead = StartupLead(
        id="complete-lead",
        source="yc",
        name="Complete Tech",
        website="https://completetech.io",
        linkedin_url="https://linkedin.com/company/completetech",
        batch="Winter 2025",
        team_size=25,
        is_hiring=True,
        founders=[Founder(name="Jane Doe", title="CEO")],
        jobs=[JobPosting(title="Founding AE")]
    )
    # Has high score, but already has website, linkedin, founder, and jobs
    should_run, reason = should_enrich_with_browser(lead, min_score=7)
    assert should_run is False
    assert "already has full founder" in reason.lower()


def test_should_enrich_with_browser_high_score_missing_founder():
    lead = StartupLead(
        id="missing-founder-lead",
        source="workatastartup",
        name="Secret Stealth",
        website="https://stealth.ai",
        batch="Winter 2025",
        team_size=18,
        is_hiring=True,
        founders=[],  # Missing founder
        jobs=[JobPosting(title="Head of Sales")]
    )
    should_run, reason = should_enrich_with_browser(lead, min_score=7)
    assert should_run is True
    assert "missing: founder/leadership contact" in reason.lower()
