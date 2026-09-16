# Self-Improving Feedback Loop: Outbound Learning Engine

A static scraper produces static results. To achieve superior conversion rates over time, `startupscrape` includes a closed-loop outcome tracking and calibration system.

---

## 1. How the Loop Works

```
┌────────────────────────────────────────┐
│     1. Scrape, Score & Enrich Leads    │
│        (Signals, Angles, Messages)     │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│     2. Dispatch Cold Outreach          │
│        (Email, LinkedIn, Twitter)      │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│     3. Record Outcomes in Tracker      │
│        • Replied / Meeting Booked      │
│        • Not Interested / Bounced      │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│     4. Performance Analytics           │
│        • Conversion rate by signal     │
│        • Conversion rate by score      │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│     5. Continuous Calibration          │
│        • Boost high-converting signals │
│        • Deprioritize dead signals     │
│        • Refine Gemini prompt hooks    │
└────────────────────────────────────────┘
```

---

## 2. Using the Outcome Tracker

### 2.1 Logging Outreach
When an outbound message is dispatched to a lead:
```python
from startupscrape.tracker import OutcomeTracker

tracker = OutcomeTracker()
# After scoring and exporting leads
for lead in leads:
    tracker.record_lead_sent(lead, notes="Campaign: W25 Founding AE Sequence")
```

### 2.2 Updating Status
When a prospect replies or books a demo:
```python
tracker.update_outcome(
    lead_id="acme_ai",
    status="meeting_booked",
    notes="Booked demo via Calendly link in 2nd email"
)
```

Status options:
- `sent` (Initial email dispatched)
- `opened` (Email opened)
- `replied` (Prospect replied)
- `meeting_booked` (Qualified meeting or demo booked)
- `not_interested` (Rejected / bad timing / not a fit)
- `bounced` (Invalid email address)

---

## 3. Reviewing Conversion Metrics & Insights

To see live performance analytics:
```python
metrics = tracker.get_metrics()
print("Reply Rate:", metrics["reply_rate"])
print("Meeting Rate:", metrics["meeting_rate"])
print("Signal Breakdown:", metrics["signal_performance"])

insights = tracker.generate_calibration_insights()
print("Recommended Signal Boosts:", insights["recommended_boost"])
print("Recommended Deprioritizations:", insights["recommended_deprioritize"])
```

### 3.1 Loop Calibration
If leads with the signal `"Hiring Founding Account Executive"` yield a 40% reply rate while leads with `"Optimal Early-Stage Scaling Team"` yield 5%, the calibration engine flags this disparity so you can:
1. Increase the heuristic weight of `"Hiring Founding Account Executive"`.
2. Filter your outbound lists to strictly target the highest-converting signals.
3. Update the Gemini prompt in `gtm_scorer.py` with the winning value angles.
