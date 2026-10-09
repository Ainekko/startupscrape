"""
app/trigger_engine/outreach.py — Personalized Outreach Brief Generator
======================================================================
Transforms verified Verve accounts + detected "Why Now?" triggers into
hyper-personalized, ready-to-send outreach briefs matching Flowjoy's voice:
- Peer-to-peer, technical, zero corporate fluff
- Directly anchored to the real-time trigger event
- Cold email draft (subject + body)
- LinkedIn connection note (<300 chars)
- Internal Slack alert preview
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from app.trigger_engine.detectors.base import DetectedSignal

logger = logging.getLogger(__name__)


class OutreachEngine:
    """Generates personalized outreach briefs from evaluated triggers."""

    def generate_brief(
        self,
        account: dict[str, Any],
        signal: DetectedSignal,
        evaluation: dict[str, Any],
    ) -> dict[str, Any]:
        company_name = account.get("company_name") or account.get("name") or "your team"
        founder_name = account.get("founder_name")
        if not founder_name and account.get("founders"):
            f_list = account["founders"]
            if isinstance(f_list, list) and f_list and isinstance(f_list[0], dict):
                founder_name = f_list[0].get("name")
        founder_name = founder_name or "there"
        first_name = founder_name.split()[0] if founder_name != "there" else "there"

        founder_email = account.get("email")
        founder_title = account.get("founder_title") or "Founder / CEO"
        founder_linkedin = account.get("founder_linkedin")
        if not founder_linkedin and account.get("founders"):
            f_list = account["founders"]
            if isinstance(f_list, list) and f_list and isinstance(f_list[0], dict):
                founder_linkedin = f_list[0].get("linkedin_url")

        angle = evaluation.get("suggested_angle", "first_sales_hire")
        urgency = evaluation.get("urgency_score", 8)
        headline = signal.headline
        trigger_type = signal.trigger_type

        # 1. Why Now Hook
        why_now_hook = evaluation.get("why_now_rationale") or f"Detected active signal: {headline}"

        # 2. Angle Templates
        if angle == "first_sales_hire" or trigger_type in ("gtm_hiring", "gtm_leadership"):
            email_subject = f"outbound engine for {company_name}"
            email_body = (
                f"Hi {first_name},\n\n"
                f"Saw {company_name} is actively looking to hire for sales. When technical founders bring on "
                f"their first sales reps, they usually spend the first 3 months paying them to manually stitch Apollo "
                f"and Clay spreadsheets instead of having discovery conversations.\n\n"
                f"At Flowjoy, we engineer automated revenue pipelines directly into your GitHub repo in a 2-week sprint "
                f"so your outbound runs on autopilot before they even start.\n\n"
                f"Worth a quick 10-minute architecture review?"
            )
            linkedin_note = (
                f"Hi {first_name}, saw {company_name} is scaling sales. We engineer automated outbound engines "
                f"directly into your GitHub in 2-week sprints so reps spend 100% of their day selling. Worth connecting?"
            )

        elif angle == "post_funding_ramp" or trigger_type == "funding":
            email_subject = f"gtm engineering post-raise // {company_name}"
            email_body = (
                f"Hi {first_name},\n\n"
                f"Saw the news on {company_name} — congrats on the momentum.\n\n"
                f"Most Seed/Series A technical founders we speak with have their core engineering team 100% focused on "
                f"shipping product, leaving outbound pipelines and lead routing under-engineered.\n\n"
                f"Flowjoy acts as your dedicated GTM Engineering team — shipping production revenue pipelines "
                f"directly to your repo in 2–4 weeks (100% code ownership, zero platform lock-in).\n\n"
                f"Mind if I share a 2-minute Loom teardown on how other YC founders set this up?"
            )
            linkedin_note = (
                f"Hi {first_name}, congrats on the {company_name} momentum. We build production revenue pipelines "
                f"for Seed B2B teams so dev teams stay focused on product. Would love to connect."
            )

        elif angle == "product_launch_pipeline" or trigger_type == "product_launch":
            email_subject = f"outbound pipeline for {company_name}"
            email_body = (
                f"Hi {first_name},\n\n"
                f"Loved what you and the team shipped with {headline}.\n\n"
                f"Now that the product is live, the main challenge is spinning up predictable outbound pipeline "
                f"without burning developer time on internal sales plumbing.\n\n"
                f"Flowjoy engineers custom outbound systems in 2–4 weeks with 100% code ownership. "
                f"Worth a 10-minute chat to review the architecture?"
            )
            linkedin_note = (
                f"Hi {first_name}, saw the {headline} launch. We engineer custom outbound engines for early B2B teams "
                f"to accelerate trial acquisition. Would love to connect."
            )

        elif angle == "stack_friction" or trigger_type == "tech_stack":
            email_subject = f"quick question re {company_name} gtm stack"
            email_body = (
                f"Hi {first_name},\n\n"
                f"Noticed {company_name} is scaling your stack. Modern B2B teams spend thousands each month "
                f"on Apollo, Clay, and HubSpot, yet reps and founders are still manually exporting CSVs between tabs.\n\n"
                f"At Flowjoy, we engineer deterministic data pipelines and autonomous outbound agents directly into "
                f"your existing stack in 2–4 weeks.\n\n"
                f"Free for a quick 10-minute intro next week?"
            )
            linkedin_note = (
                f"Hi {first_name}, noticed you're scaling {company_name}. We build automated data pipelines connecting "
                f"Clay/HubSpot/Slack so outbound runs autonomously. Worth connecting?"
            )

        else: # Founder-led bottleneck default
            email_subject = f"quick question re {company_name} outbound"
            email_body = (
                f"Hi {first_name},\n\n"
                f"Noticed {company_name} is scaling engineering while sales remains founder-led. We put together "
                f"5-minute Loom teardowns for technical founders showing where pipeline leaks are happening across "
                f"outbound tooling.\n\n"
                f"Mind if I record one for {company_name}?"
            )
            linkedin_note = (
                f"Hi {first_name}, loved what {company_name} is building. We help technical founders automate "
                f"outbound pipeline without hiring full-time sales headcount. Worth connecting?"
            )

        # 3. Slack preview (formatted for internal Flowjoy team notifications)
        slack_preview = (
            f"🎯 *Why-Now Alert: {company_name}* (Urgency: {urgency}/10)\n"
            f"• *Trigger*: {headline}\n"
            f"• *Why Now*: {why_now_hook}\n"
            f"• *Contact*: {founder_name} ({founder_title}) <{founder_email or 'email pending'}>\n"
            f"• *Angle*: `{angle}` | Brief drafted & ready for review."
        )

        return {
            "company_name": company_name,
            "founder_name": founder_name,
            "founder_email": founder_email,
            "founder_title": founder_title,
            "founder_linkedin": founder_linkedin,
            "trigger_type": trigger_type,
            "urgency_score": urgency,
            "angle": angle,
            "why_now_hook": why_now_hook,
            "email_subject": email_subject,
            "email_body": email_body,
            "linkedin_note": linkedin_note,
            "slack_preview": slack_preview,
            "status": "draft",
        }

