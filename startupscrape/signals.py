import re
from typing import List, Tuple, Dict, Any, Optional
from .models import StartupLead


# Signal definitions
SIGNAL_FOUNDING_AE = "Hiring Founding Account Executive"
SIGNAL_SALES_LEAD = "Hiring Sales Leadership (Head of Sales / VP Sales)"
SIGNAL_REVOPS = "Hiring Revenue Operations (RevOps)"
SIGNAL_SDR_BDR = "Hiring Outbound SDR / BDR"
SIGNAL_GROWTH_LEAD = "Hiring Head of Growth / GTM Lead"
SIGNAL_RECENT_BATCH = "Recent Tier-1 Batch (2024-2026)"
SIGNAL_OPTIMAL_TEAM = "Optimal Early-Stage Scaling Team (5-50 members)"
SIGNAL_FOUNDER_BOTTLENECK = "Founder-Led Sales Bottleneck Language"


class SignalDetector:
    """Analyzes startup metadata, job postings, and company descriptions to extract GTM signals."""

    @staticmethod
    def detect_signals(lead: StartupLead) -> List[str]:
        signals: List[str] = []

        # Combine text for keyword analysis
        job_titles = [j.title.lower() for j in lead.jobs]
        full_text = " ".join([
            lead.name,
            lead.one_liner or "",
            lead.long_description or "",
            " ".join(job_titles)
        ]).lower()

        # 1. Hiring Signals from Job Postings
        for title in job_titles:
            if any(kw in title for kw in ["founding ae", "founding account executive", "first sales"]):
                if SIGNAL_FOUNDING_AE not in signals:
                    signals.append(SIGNAL_FOUNDING_AE)
            if any(kw in title for kw in ["head of sales", "vp sales", "vp of sales", "director of sales"]):
                if SIGNAL_SALES_LEAD not in signals:
                    signals.append(SIGNAL_SALES_LEAD)
            if any(kw in title for kw in ["revops", "revenue operations"]):
                if SIGNAL_REVOPS not in signals:
                    signals.append(SIGNAL_REVOPS)
            if any(kw in title for kw in ["sdr", "bdr", "sales development"]):
                if SIGNAL_SDR_BDR not in signals:
                    signals.append(SIGNAL_SDR_BDR)
            if any(kw in title for kw in ["head of growth", "growth lead", "gtm lead"]):
                if SIGNAL_GROWTH_LEAD not in signals:
                    signals.append(SIGNAL_GROWTH_LEAD)

        # 2. Batch Signals
        if lead.batch:
            b_lower = lead.batch.lower()
            if any(yr in b_lower for yr in ["2024", "2025", "2026", "w24", "s24", "w25", "s25", "w26"]):
                signals.append(SIGNAL_RECENT_BATCH)

        # 3. Team Size Signals
        if lead.team_size and 5 <= lead.team_size <= 50:
            signals.append(SIGNAL_OPTIMAL_TEAM)

        # 4. Pain language signals in description or jobs
        pain_keywords = [
            "founder-led sales", "build our sales engine", "first sales hire",
            "scale outbound", "outbound pipeline", "repeatable sales motion",
            "move upmarket", "pipeline predictability"
        ]
        if any(kw in full_text for kw in pain_keywords):
            signals.append(SIGNAL_FOUNDER_BOTTLENECK)

        return signals

    @classmethod
    def compute_pre_score(cls, lead: StartupLead) -> int:
        """Calculate preliminary heuristic score (1-10) before heavy enrichment."""
        signals = cls.detect_signals(lead)
        score = 4

        if lead.is_hiring:
            score += 1

        if SIGNAL_FOUNDING_AE in signals or SIGNAL_SALES_LEAD in signals:
            score += 2
        if SIGNAL_REVOPS in signals or SIGNAL_SDR_BDR in signals:
            score += 1
        if SIGNAL_GROWTH_LEAD in signals:
            score += 1
        if SIGNAL_RECENT_BATCH in signals:
            score += 1
        if SIGNAL_OPTIMAL_TEAM in signals:
            score += 1
        if SIGNAL_FOUNDER_BOTTLENECK in signals:
            score += 1

        return max(1, min(10, score))


def should_enrich_with_browser(lead: StartupLead, min_score: int = 7) -> Tuple[bool, str]:
    """
    Decide whether to spend heavy Browserbase/LinkedIn resources on a lead.

    Policy:
    1. Score must be >= min_score (high value target).
    2. Must be missing critical contact or company context that cannot be enriched via HTTP.
    """
    pre_score = SignalDetector.compute_pre_score(lead)

    if pre_score < min_score:
        return False, f"Pre-score {pre_score}/10 < threshold {min_score} (low/medium urgency fit)"

    # Check if we already have sufficient data from Algolia & HTTP enrichment
    has_website = bool(lead.website)
    has_linkedin = bool(lead.linkedin_url)
    has_founder = bool(lead.founders and len(lead.founders) > 0)
    has_jobs = bool(lead.jobs and len(lead.jobs) > 0)

    # If lead already has founder, website, LinkedIn, and jobs, browser is redundant
    if has_website and has_linkedin and has_founder and has_jobs:
        return False, "Lead already has full founder, website, LinkedIn, and job listings from HTTP/Algolia"

    # Missing critical intel for a high-value lead
    missing_items = []
    if not has_founder:
        missing_items.append("founder/leadership contact")
    if not has_linkedin:
        missing_items.append("company LinkedIn")
    if not has_website:
        missing_items.append("website")

    reason = f"High-value lead (score {pre_score}/10) missing: {', '.join(missing_items)}"
    return True, reason
