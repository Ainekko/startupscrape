import json
import logging
import time
from typing import Optional, Dict, Any, List
import requests

from .config import GEMINI_API_KEY, GEMINI_MODEL, DEFAULT_TIMEOUT
from .models import StartupLead, GTMAnalysis
from .flowjoy_wiki import FLOWJOY_WIKI

logger = logging.getLogger(__name__)

GTM_SYSTEM_PROMPT = f"""You are the Lead GTM Strategist for FlowJoy (flowjoy.online), a specialized GTM Engineering Studio partnering with Seed to Series A B2B startups.

{FLOWJOY_WIKI}

Your mission:
Evaluate the target startup account to determine how well they fit FlowJoy's GTM Engineering services, and craft a hyper-personalized outreach hook.

Scoring Rules (1 to 10):
- Base score: 5
- Seed to Series A / recent YC batch (W24, S24, W25, S25, W26): +2
- Actively hiring sales / GTM / RevOps roles: +2
- Team size 5-50 (sweet spot): +1
- Data Completeness Bonus (CRITICAL):
  - Verified Founder Name + Title: +1
  - Verified Founder Personal LinkedIn: +1
  - Founder Has Email flag is True: +1
  - Founder Bio / Past Projects available: +1
- Deduct 2-3 points if company is massive (>100 employees), enterprise, B2C, or inactive.
Cap max score at 10.

Output strictly valid JSON with this exact schema:
{{
  "score": <integer from 1 to 10>,
  "stage": "<Seed | Series A | Early | Growth>",
  "key_signals": [
    "<Signal 1: e.g. Seed-stage / W25 batch with 7-person team>",
    "<Signal 2: e.g. Founder LinkedIn & Bio verified (Repeated founder, ML researcher)>",
    "<Signal 3: e.g. Direct Founder Email available>",
    "<Signal 4: e.g. Core devs busy on product, ideal for FlowJoy 2-4 week sprint>"
  ],
  "best_contact_role": "<Founder / CEO | Co-Founder | Head of Sales>",
  "best_contact_name": "<Full name of the target founder/exec>",
  "best_contact_linkedin": "<Personal LinkedIn URL of the target contact or null>",
  "suggested_angle": "<Punchy 1-sentence value hook specifically pitching FlowJoy GTM Engineering>",
  "first_message": "<Hyper-personalized 2-3 sentence outreach message mentioning their founder background/projects and offering a free GTM stack teardown>"
}}
"""


class GTMScorer:
    """Uses Gemini to evaluate early-stage startups on FlowJoy GTM readiness and craft targeted pitches."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def analyze_account(self, lead: StartupLead, extra_site_text: Optional[str] = None) -> GTMAnalysis:
        """Run FlowJoy GTM scoring and signal extraction on a startup lead with retry on transient failures."""
        primary_founder = lead.founders[0] if lead.founders else None

        if not self.api_key:
            return GTMAnalysis(
                score=7 if (lead.is_hiring and primary_founder) else 5,
                stage="Seed",
                key_signals=["Early-stage startup", "Founder identified" if primary_founder else "Stealth team"],
                best_contact_role=primary_founder.title if primary_founder else "Founder / CEO",
                best_contact_name=primary_founder.name if primary_founder else None,
                best_contact_linkedin=primary_founder.linkedin_url if primary_founder else None,
                suggested_angle="Engineering autonomous Clay + Apollo + HubSpot outbound pipelines in 2-4 weeks",
                first_message=f"Hi {primary_founder.name.split()[0] if primary_founder else 'there'}, saw {lead.name}'s momentum. Instead of pulling core engineers off product to build internal CRM syncs, Flowjoy ships production GTM pipelines directly to your GitHub in 2-4 weeks. Open for a free 15-minute stack teardown?"
            )

        # Build rich context from lead data
        founders_info = []
        for f in lead.founders:
            f_str = f"- {f.name} ({f.title or 'Founder'})"
            if f.linkedin_url:
                f_str += f" | LinkedIn: {f.linkedin_url}"
            if f.twitter_url:
                f_str += f" | Twitter: {f.twitter_url}"
            if f.has_email:
                f_str += " | Email: Available"
            if f.bio:
                f_str += f" | Bio/Projects: {f.bio}"
            founders_info.append(f_str)
        founders_text = "\n".join(founders_info) if founders_info else "None listed"

        jobs_str = "\n".join([f"- {j.title} ({j.role_type or 'General'}, {j.location or 'Remote'})" for j in lead.jobs]) or "None listed"

        user_content = f"""Company Name: {lead.name}
Website: {lead.website or 'N/A'}
Company LinkedIn: {lead.linkedin_url or 'N/A'}
Batch / Stage: {lead.batch or 'N/A'}
Team Size: {lead.team_size or 'N/A'}
Industry / Tags: {lead.industry or 'N/A'} ({', '.join(lead.tags)})
One-Liner: {lead.one_liner or 'N/A'}
Description: {lead.long_description or 'N/A'}
Is Hiring: {lead.is_hiring} (Open jobs: {lead.open_jobs_count})
Open Roles:
{jobs_str}

Founders & Leadership Profiles:
{founders_text}
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

        # Retry up to 3 times on 503 or timeout
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(self.endpoint, json=payload, timeout=45)
                if resp.status_code == 200:
                    result = resp.json()
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(text)
                    return GTMAnalysis(
                        score=int(data.get("score", 6)),
                        stage=data.get("stage", "Seed"),
                        key_signals=data.get("key_signals", []),
                        best_contact_role=data.get("best_contact_role", (primary_founder.title if primary_founder else "Founder / CEO")),
                        best_contact_name=data.get("best_contact_name") or (primary_founder.name if primary_founder else None),
                        best_contact_linkedin=data.get("best_contact_linkedin") or (primary_founder.linkedin_url if primary_founder else None),
                        suggested_angle=data.get("suggested_angle", ""),
                        first_message=data.get("first_message", "")
                    )
                elif resp.status_code in (503, 429):
                    wait = 2 ** attempt
                    logger.warning(f"Gemini {resp.status_code} for {lead.name}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text}")
                    break
            except requests.exceptions.Timeout:
                wait = 2 ** attempt
                logger.warning(f"Gemini timeout for {lead.name}, retrying in {wait}s...")
                time.sleep(wait)
            except Exception as e:
                logger.error(f"Error during GTM scoring for {lead.name}: {e}")
                break

        # Fallback heuristic if API unavailable
        fallback_score = 5
        if lead.is_hiring:
            fallback_score += 2
        if primary_founder and primary_founder.linkedin_url:
            fallback_score += 1
        if primary_founder and primary_founder.has_email:
            fallback_score += 1

        fname = primary_founder.name if primary_founder else None
        first_name = fname.split()[0] if fname else "there"
        return GTMAnalysis(
            score=min(10, fallback_score),
            stage="Seed",
            key_signals=[
                "Early-stage Seed startup",
                "Hiring active" if lead.is_hiring else "Core team scaling",
                "Founder LinkedIn verified" if (primary_founder and primary_founder.linkedin_url) else "Founder identified"
            ],
            best_contact_role=primary_founder.title if primary_founder else "Founder / CEO",
            best_contact_name=fname,
            best_contact_linkedin=primary_founder.linkedin_url if primary_founder else None,
            suggested_angle=f"Building automated GTM revenue systems for {lead.name}",
            first_message=f"Hi {first_name}, saw what you're building at {lead.name}. Instead of pulling your core devs off product to build internal CRM syncs and lead lists, FlowJoy ships production GTM pipelines directly to your GitHub in 2-4 weeks. Open for a free 15-min teardown?"
        )
