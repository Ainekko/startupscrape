import json
import logging
from typing import Optional, Dict, Any, List
import requests

from .config import GEMINI_API_KEY, GEMINI_MODEL, DEFAULT_TIMEOUT
from .models import StartupLead, GTMAnalysis

logger = logging.getLogger(__name__)

GTM_SYSTEM_PROMPT = """You are an expert B2B Go-To-Market (GTM) analyst and sales strategist.
Your task is to evaluate early-stage startups (Seed / Series A) to determine if they are primed for scaling their GTM operations (sales, outbound, RevOps, pipeline generation).

Evaluate based on:
1. Stage & Growth: Are they early-stage (Seed, Series A, recent funding, team size 2-50)?
2. Hiring Signals: Are they hiring GTM roles (Founding Account Executive, SDR, Head of Sales, RevOps, Growth)?
3. GTM Pain Language: Does their company description, job postings, or website indicate pains like founder-led sales bottlenecks, moving upmarket, building repeatable outbound, or pipeline predictability?

Output strictly valid JSON with this schema:
{
  "score": <integer from 1 to 10, where 8-10 is high urgency/fit>,
  "stage": "<Seed | Series A | Early | Growth | Other>",
  "key_signals": [
    "<Signal 1: e.g. Recently raised Seed / Summer 2024 batch>",
    "<Signal 2: e.g. Hiring first Founding Account Executive>",
    "<Signal 3: e.g. Founder-led sales transitioning to dedicated outbound>"
  ],
  "best_contact_role": "<Founder / CEO | Head of Sales | VP Sales | RevOps Lead>",
  "best_contact_name": "<Name of founder/executive if known, or null>",
  "suggested_angle": "<Concise 1-sentence sales hook focused on their specific pain>",
  "first_message": "<Punchy, personalized 2-3 sentence outreach message tailored to the company and role>"
}
"""


class GTMScorer:
    """Uses Gemini to evaluate early-stage startups on GTM scaling readiness and generate outreach angles."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def analyze_account(self, lead: StartupLead, extra_site_text: Optional[str] = None) -> GTMAnalysis:
        """Run GTM scoring and signal extraction on a startup lead."""
        if not self.api_key:
            return GTMAnalysis(
                score=5,
                stage="Early",
                key_signals=["API key not configured"],
                best_contact_role="Founder / CEO",
                suggested_angle="Scaling early sales operations",
                first_message="Hi, noticed your recent growth and wanted to connect regarding scaling your GTM pipeline."
            )

        # Build context from lead data
        founders_str = ", ".join([f"{f.name} ({f.title or 'Founder'})" for f in lead.founders]) or "N/A"
        jobs_str = "\n".join([f"- {j.title} ({j.location or 'Remote'})" for j in lead.jobs]) or "None listed"

        user_content = f"""Company Name: {lead.name}
Website: {lead.website or 'N/A'}
Batch / Stage: {lead.batch or 'N/A'}
Team Size: {lead.team_size or 'N/A'}
One-Liner: {lead.one_liner or 'N/A'}
Description: {lead.long_description or 'N/A'}
Is Hiring: {lead.is_hiring} (Open jobs: {lead.open_jobs_count})
Open Roles:
{jobs_str}
Founders / Leadership:
{founders_str}
"""
        if extra_site_text:
            user_content += f"\nScraped Website Context:\n{extra_site_text[:2000]}\n"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": GTM_SYSTEM_PROMPT},
                        {"text": user_content}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 200:
                result = resp.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(text)
                return GTMAnalysis(
                    score=int(data.get("score", 5)),
                    stage=data.get("stage", "Early"),
                    key_signals=data.get("key_signals", []),
                    best_contact_role=data.get("best_contact_role", "Founder / CEO"),
                    best_contact_name=data.get("best_contact_name") or (lead.founders[0].name if lead.founders else None),
                    suggested_angle=data.get("suggested_angle", ""),
                    first_message=data.get("first_message", "")
                )
            else:
                logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Error during GTM scoring for {lead.name}: {e}")

        # Fallback heuristic
        score = 6 if lead.is_hiring else 4
        return GTMAnalysis(
            score=score,
            stage="Seed",
            key_signals=["Early-stage startup", "Active hiring" if lead.is_hiring else "Early development"],
            best_contact_role="Founder / CEO",
            best_contact_name=lead.founders[0].name if lead.founders else None,
            suggested_angle=f"Scaling outbound pipeline for {lead.name}",
            first_message=f"Hi, saw {lead.name}'s recent momentum and wanted to share how similar early-stage teams scale their GTM operations."
        )
