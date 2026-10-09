"""
app/trigger_engine/qualifier.py — AI Trigger Evaluation & Opportunity Scorer
===========================================================================
Evaluates detected "Why Now?" triggers against Flowjoy's ICP and value proposition:
- Seed & Series A B2B startups ($1M-$6M raised, 5-50 people)
- Evaluates urgency (1-10) and relevance (1-10)
- Answers: "Is this actually worth contacting today and why?"
- Determines target decision-maker and best GTM hook
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional
import httpx

from app.trigger_engine.detectors.base import DetectedSignal

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the AI Qualifier for Flowjoy (https://flowjoy.online).
Flowjoy is a GTM Engineering Studio for Seed and Series A B2B startups.
We build production-grade revenue pipelines and outbound automations in 2-4 week sprints directly into the client's GitHub repo.

Evaluate the detected 'Why Now?' trigger for this account:
1. Urgency score (1-10): How urgently does this trigger create an outbound or pipeline problem?
   (9-10 = First SDR hiring, recent funding round with investor growth mandate, rapid team expansion with 0 sales)
2. Relevance score (1-10): How closely does this match Flowjoy's engineering sprint offer?
3. Is Qualified: True if urgency >= 6 and relevance >= 6.
4. Why Now Rationale: Exactly 1-2 punchy sentences explaining why contacting this founder today is high leverage.
5. Target Angle: Choose one of:
   - 'first_sales_hire' (hiring SDR/sales, need pipeline ready before start date)
   - 'post_funding_ramp' (just raised, investor growth targets, dev team busy on product)
   - 'founder_led_bottleneck' (growing engineering with 0 sales, founder wasting weekends on manual prospecting)
   - 'product_launch_pipeline' (new product launched, need customer acquisition fast)
   - 'stack_friction' (using Hubspot/Clay/Apollo, dealing with manual CSV workflows)
6. Target Decision Maker: (e.g. CEO, Co-founder, Head of Sales)

Respond strictly in valid JSON format:
{
  "is_qualified": bool,
  "urgency_score": int,
  "relevance_score": int,
  "why_now_rationale": str,
  "target_decision_maker": str,
  "suggested_angle": str
}"""


class AIQualifier:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.8-flash"):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.model = os.getenv("GEMINI_MODEL", model).strip() or "gemini-3.8-flash"

    async def qualify(
        self,
        account: dict[str, Any],
        signal: DetectedSignal,
    ) -> dict[str, Any]:
        """
        Evaluate a detected signal for an account using Gemini or calibrated heuristic fallback.
        """
        company_name = account.get("company_name") or account.get("name") or "Unknown Company"
        founder_name = account.get("founder_name") or "Founder"
        stage = account.get("batch") or account.get("gtm_analysis", {}).get("stage", "Seed/Series A")
        team_size = account.get("team_size") or "Early Stage"
        one_liner = account.get("one_liner") or account.get("long_description") or ""

        if self.api_key:
            try:
                result = await self._call_gemini(
                    company_name=company_name,
                    founder_name=founder_name,
                    stage=stage,
                    team_size=team_size,
                    one_liner=one_liner,
                    signal=signal,
                )
                if result:
                    return result
            except Exception as exc:
                logger.warning("Gemini AI evaluation failed (%s), using heuristic fallback.", exc)

        return self._heuristic_fallback(account, signal)

    async def _call_gemini(
        self,
        company_name: str,
        founder_name: str,
        stage: str,
        team_size: Any,
        one_liner: str,
        signal: DetectedSignal,
    ) -> Optional[dict[str, Any]]:
        prompt = f"""Evaluate this trigger for Flowjoy GTM Engineering Studio:
Company: {company_name} ({stage}, Team Size: {team_size})
Description: {one_liner}
Founder: {founder_name}
Trigger Type: {signal.trigger_type}
Headline: {signal.headline}
Context/Snippet: {signal.snippet}
Source: {signal.source}
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            else:
                logger.warning("Gemini API returned status %d: %s", res.status_code, res.text[:200])
                return None

    def _heuristic_fallback(self, account: dict[str, Any], signal: DetectedSignal) -> dict[str, Any]:
        """Deterministic calibration when AI is unavailable."""
        ttype = signal.trigger_type
        company_name = account.get("company_name") or account.get("name") or "the company"

        if ttype in ("gtm_hiring", "gtm_leadership"):
            return {
                "is_qualified": True,
                "urgency_score": 9,
                "relevance_score": 10,
                "why_now_rationale": f"{company_name} is actively hiring for GTM roles. They need automated outbound infrastructure operating before new sales headcount starts.",
                "target_decision_maker": "Founder / CEO",
                "suggested_angle": "first_sales_hire",
            }
        elif ttype == "funding":
            return {
                "is_qualified": True,
                "urgency_score": 8,
                "relevance_score": 9,
                "why_now_rationale": f"Recent capital injection at {company_name} accelerates growth mandates while engineering is 100% focused on core product.",
                "target_decision_maker": "Founder / CEO",
                "suggested_angle": "post_funding_ramp",
            }
        elif ttype == "product_launch":
            return {
                "is_qualified": True,
                "urgency_score": 7,
                "relevance_score": 8,
                "why_now_rationale": f"Recent product launch requires immediate pipeline to convert trials and initial pilots into enterprise contracts.",
                "target_decision_maker": "Founder / CEO",
                "suggested_angle": "product_launch_pipeline",
            }
        elif ttype == "social_discussion":
            return {
                "is_qualified": True,
                "urgency_score": 7,
                "relevance_score": 8,
                "why_now_rationale": f"Public discussions indicate active pain or exploration around outbound sales and tooling.",
                "target_decision_maker": "Founder",
                "suggested_angle": "stack_friction",
            }
        else:
            return {
                "is_qualified": True,
                "urgency_score": 6,
                "relevance_score": 7,
                "why_now_rationale": f"Stack detection confirms {company_name} has existing GTM tooling that can be tied together into an automated pipeline.",
                "target_decision_maker": "Founder / CEO",
                "suggested_angle": "stack_friction",
            }

