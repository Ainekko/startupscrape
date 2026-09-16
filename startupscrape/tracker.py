import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .config import DATA_DIR
from .models import StartupLead


class OutcomeRecord(BaseModel):
    lead_id: str
    company_name: str
    score: int
    signals: List[str] = Field(default_factory=list)
    status: str = "sent"  # sent, opened, replied, meeting_booked, not_interested, bounced
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    suggested_angle: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class OutcomeTracker:
    """Tracks outreach outcomes and computes conversion metrics to create a self-improving loop."""

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or os.path.join(DATA_DIR, "outreach_outcomes.jsonl")
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def _read_records(self) -> List[OutcomeRecord]:
        if not os.path.exists(self.filepath):
            return []
        records = []
        with open(self.filepath, mode="r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(OutcomeRecord.model_validate_json(line))
                    except Exception:
                        pass
        return records

    def _write_records(self, records: List[OutcomeRecord]) -> None:
        with open(self.filepath, mode="w", encoding="utf-8") as f:
            for rec in records:
                f.write(rec.model_dump_json() + "\n")

    def record_lead_sent(
        self,
        lead: StartupLead,
        notes: Optional[str] = None,
        status: str = "sent"
    ) -> OutcomeRecord:
        """Record an outreach attempt for a lead."""
        records = self._read_records()
        gtm = lead.gtm_analysis

        record = OutcomeRecord(
            lead_id=lead.id,
            company_name=lead.name,
            score=gtm.score if gtm else 5,
            signals=gtm.key_signals if gtm else [],
            status=status,
            contact_name=gtm.best_contact_name if gtm else None,
            contact_role=gtm.best_contact_role if gtm else None,
            suggested_angle=gtm.suggested_angle if gtm else None,
            notes=notes
        )

        # Replace existing record for same lead_id or append
        updated = False
        for i, existing in enumerate(records):
            if existing.lead_id == lead.id:
                records[i] = record
                updated = True
                break
        if not updated:
            records.append(record)

        self._write_records(records)
        return record

    def update_outcome(
        self,
        lead_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[OutcomeRecord]:
        """Update status (e.g. replied, meeting_booked, not_interested) for a given lead."""
        records = self._read_records()
        target: Optional[OutcomeRecord] = None

        for rec in records:
            if rec.lead_id == lead_id:
                rec.status = status
                rec.updated_at = datetime.utcnow().isoformat()
                if notes:
                    rec.notes = f"{rec.notes}; {notes}" if rec.notes else notes
                target = rec
                break

        if target:
            self._write_records(records)
        return target

    def get_metrics(self) -> Dict[str, Any]:
        """Calculate reply and conversion rates by status, score bucket, and signals."""
        records = self._read_records()
        total = len(records)
        if total == 0:
            return {
                "total_leads": 0,
                "status_breakdown": {},
                "reply_rate": 0.0,
                "meeting_rate": 0.0,
                "signal_performance": {},
                "score_performance": {}
            }

        status_counts: Dict[str, int] = {}
        for r in records:
            status_counts[r.status] = status_counts.get(r.status, 0) + 1

        replies = status_counts.get("replied", 0) + status_counts.get("meeting_booked", 0)
        meetings = status_counts.get("meeting_booked", 0)

        # Signal-level conversion
        signal_stats: Dict[str, Dict[str, int]] = {}
        for r in records:
            is_reply = r.status in ("replied", "meeting_booked")
            is_meeting = r.status == "meeting_booked"
            for sig in r.signals:
                if sig not in signal_stats:
                    signal_stats[sig] = {"sent": 0, "replies": 0, "meetings": 0}
                signal_stats[sig]["sent"] += 1
                if is_reply:
                    signal_stats[sig]["replies"] += 1
                if is_meeting:
                    signal_stats[sig]["meetings"] += 1

        # Score bucket performance
        score_stats: Dict[str, Dict[str, int]] = {
            "high (8-10)": {"sent": 0, "replies": 0, "meetings": 0},
            "medium (6-7)": {"sent": 0, "replies": 0, "meetings": 0},
            "low (1-5)": {"sent": 0, "replies": 0, "meetings": 0},
        }
        for r in records:
            bucket = "high (8-10)" if r.score >= 8 else ("medium (6-7)" if r.score >= 6 else "low (1-5)")
            score_stats[bucket]["sent"] += 1
            if r.status in ("replied", "meeting_booked"):
                score_stats[bucket]["replies"] += 1
            if r.status == "meeting_booked":
                score_stats[bucket]["meetings"] += 1

        return {
            "total_leads": total,
            "status_breakdown": status_counts,
            "reply_rate": round(replies / total, 3),
            "meeting_rate": round(meetings / total, 3),
            "signal_performance": signal_stats,
            "score_performance": score_stats
        }

    def generate_calibration_insights(self) -> Dict[str, Any]:
        """Recommend adjustments to scoring prompts or signal weights based on real data."""
        metrics = self.get_metrics()
        signal_perf = metrics.get("signal_performance", {})

        top_signals = []
        underperforming_signals = []

        for sig, data in signal_perf.items():
            sent = data["sent"]
            if sent >= 2:  # Min sample size
                reply_rate = data["replies"] / sent
                meeting_rate = data["meetings"] / sent
                if meeting_rate > 0 or reply_rate >= 0.3:
                    top_signals.append({"signal": sig, "reply_rate": reply_rate, "meeting_rate": meeting_rate})
                elif reply_rate == 0:
                    underperforming_signals.append({"signal": sig, "sent": sent})

        return {
            "recommended_boost": [s["signal"] for s in top_signals],
            "recommended_deprioritize": [s["signal"] for s in underperforming_signals],
            "total_tracked": metrics["total_leads"],
            "overall_reply_rate": metrics["reply_rate"]
        }
