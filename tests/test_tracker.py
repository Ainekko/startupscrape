import os
import pytest
from startupscrape.models import StartupLead, GTMAnalysis
from startupscrape.tracker import OutcomeTracker


@pytest.fixture
def tracker(tmp_path):
    ledger_path = str(tmp_path / "outreach_outcomes.jsonl")
    return OutcomeTracker(filepath=ledger_path)


def test_record_lead_sent(tracker):
    lead = StartupLead(
        id="lead-1",
        source="yc",
        name="AlphaCorp",
        gtm_analysis=GTMAnalysis(
            score=9,
            key_signals=["Hiring Founding AE"],
            best_contact_role="CEO",
            best_contact_name="Alice"
        )
    )

    rec = tracker.record_lead_sent(lead, notes="Initial cold email sent")
    assert rec.lead_id == "lead-1"
    assert rec.score == 9
    assert rec.status == "sent"
    assert rec.contact_name == "Alice"
    assert os.path.exists(tracker.filepath)


def test_update_outcome(tracker):
    lead = StartupLead(
        id="lead-2",
        source="yc",
        name="BetaCorp",
        gtm_analysis=GTMAnalysis(score=8, key_signals=["Hiring Head of Sales"])
    )
    tracker.record_lead_sent(lead)

    updated = tracker.update_outcome("lead-2", status="replied", notes="Positive response asking for deck")
    assert updated is not None
    assert updated.status == "replied"
    assert "Positive response" in updated.notes


def test_metrics_and_calibration(tracker):
    # Setup 3 leads:
    # Lead 1: replied (score 9, Signal A)
    # Lead 2: meeting_booked (score 9, Signal A + B)
    # Lead 3: not_interested (score 5, Signal C)
    lead1 = StartupLead(id="1", source="yc", name="L1", gtm_analysis=GTMAnalysis(score=9, key_signals=["Signal A"]))
    lead2 = StartupLead(id="2", source="yc", name="L2", gtm_analysis=GTMAnalysis(score=9, key_signals=["Signal A", "Signal B"]))
    lead3 = StartupLead(id="3", source="yc", name="L3", gtm_analysis=GTMAnalysis(score=5, key_signals=["Signal C"]))

    tracker.record_lead_sent(lead1)
    tracker.record_lead_sent(lead2)
    tracker.record_lead_sent(lead3)

    tracker.update_outcome("1", "replied")
    tracker.update_outcome("2", "meeting_booked")
    tracker.update_outcome("3", "not_interested")

    metrics = tracker.get_metrics()
    assert metrics["total_leads"] == 3
    assert metrics["status_breakdown"]["replied"] == 1
    assert metrics["status_breakdown"]["meeting_booked"] == 1
    assert metrics["status_breakdown"]["not_interested"] == 1
    assert metrics["reply_rate"] == 0.667
    assert metrics["meeting_rate"] == 0.333

    # Signal A has 2 sent, 2 replies, 1 meeting
    assert metrics["signal_performance"]["Signal A"]["sent"] == 2
    assert metrics["signal_performance"]["Signal A"]["replies"] == 2

    # High bucket (8-10) has 2 sent, 2 replies
    assert metrics["score_performance"]["high (8-10)"]["sent"] == 2
    assert metrics["score_performance"]["high (8-10)"]["replies"] == 2

    insights = tracker.generate_calibration_insights()
    assert "Signal A" in insights["recommended_boost"]
