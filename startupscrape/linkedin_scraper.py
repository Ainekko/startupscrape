import json
import logging
import re
import time
from typing import Optional, Dict, Any, List
import requests

from .config import GEMINI_API_KEY, GEMINI_MODEL, DEFAULT_TIMEOUT
from .browserbase_client import BrowserbaseClient

logger = logging.getLogger(__name__)

# Titles we consider as GTM-relevant contacts
GTM_TITLE_KEYWORDS = [
    "founder", "ceo", "co-founder", "chief executive",
    "head of sales", "vp sales", "vp of sales", "director of sales",
    "account executive", "revops", "revenue operations",
    "head of growth", "growth", "head of marketing", "cmo",
    "chief revenue", "cro", "business development"
]


class LinkedInScraper:
    """Scrapes LinkedIn company pages and people profiles using a persistent Browserbase context."""

    def __init__(
        self,
        browserbase: Optional[BrowserbaseClient] = None,
        context_id: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        gemini_model: Optional[str] = None
    ):
        self.bb = browserbase or BrowserbaseClient()
        self.context_id = context_id
        self.gemini_api_key = gemini_api_key or GEMINI_API_KEY
        self.gemini_model = gemini_model or GEMINI_MODEL
        self.gemini_endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        )

    def _extract_slug_from_url(self, url: str) -> Optional[str]:
        """Extract LinkedIn company slug from URL."""
        m = re.search(r'linkedin\.com/company/([^/?#]+)', url)
        return m.group(1).rstrip('/') if m else None

    def _gemini_parse(self, page_text: str, prompt: str) -> Dict[str, Any]:
        """Use Gemini to parse unstructured page text into structured data."""
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"text": f"Page content:\n{page_text[:4000]}"}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }
        for attempt in range(3):
            try:
                resp = requests.post(self.gemini_endpoint, json=payload, timeout=45)
                if resp.status_code == 200:
                    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)
                elif resp.status_code in (503, 429):
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"Gemini parse error: {e}")
                time.sleep(2 ** attempt)
        return {}

    def scrape_company_page(self, linkedin_url: str) -> Dict[str, Any]:
        """
        Scrape a LinkedIn company page for headcount, recent posts, and hiring signals.
        Returns structured dict with company intel.
        """
        slug = self._extract_slug_from_url(linkedin_url)
        if not slug:
            return {}

        company_url = f"https://www.linkedin.com/company/{slug}/"
        logger.info(f"[LinkedIn] Scraping company page: {company_url}")

        try:
            result = self.bb.scrape_url(
                company_url,
                context_id=self.context_id,
                wait_ms=4000,
                timeout_ms=35000
            )
            page_text = result.get("text", "")
        except Exception as e:
            logger.warning(f"[LinkedIn] Company page scrape failed for {slug}: {e}")
            return {}

        if not page_text or len(page_text) < 100:
            logger.warning(f"[LinkedIn] Got empty/short page for {slug} — likely not logged in")
            return {"error": "not_authenticated"}

        prompt = """Extract the following from this LinkedIn company page text and return valid JSON:
{
  "headcount": <integer or null>,
  "headcount_range": "<string like '1-10' or null>",
  "recent_posts_summary": "<2-3 sentence summary of recent company posts/activity or null>",
  "gtm_hiring_signals": ["<list of GTM/sales/growth job titles mentioned>"],
  "company_description": "<brief description from About section or null>",
  "industries": ["<list of industries>"],
  "notable_signal": "<any standout signal: funding, launch, product milestone, pain language>"
}
Return only valid JSON, no explanation."""

        parsed = self._gemini_parse(page_text, prompt)
        parsed["_raw_text_sample"] = page_text[:500]
        return parsed

    def scrape_company_people(self, linkedin_url: str, max_contacts: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape the LinkedIn company People tab for GTM-relevant contacts
        (Founders, VP Sales, Head of Growth, RevOps).
        Returns a list of contact dicts.
        """
        slug = self._extract_slug_from_url(linkedin_url)
        if not slug:
            return []

        people_url = f"https://www.linkedin.com/company/{slug}/people/"
        logger.info(f"[LinkedIn] Scraping people: {people_url}")

        try:
            result = self.bb.scrape_url(
                people_url,
                context_id=self.context_id,
                wait_ms=4000,
                timeout_ms=35000
            )
            page_text = result.get("text", "")
        except Exception as e:
            logger.warning(f"[LinkedIn] People page scrape failed for {slug}: {e}")
            return []

        if not page_text or len(page_text) < 100:
            return []

        prompt = f"""From this LinkedIn company People page, extract up to {max_contacts} GTM-relevant contacts.
Focus on: Founder, CEO, Co-Founder, Head of Sales, VP Sales, RevOps, Head of Growth, CRO, CMO, AE.
Return valid JSON array:
[
  {{
    "name": "<full name>",
    "title": "<exact title>",
    "linkedin_url": "<profile URL if found or null>",
    "is_founder": <true/false>
  }}
]
Return only the JSON array, no explanation."""

        parsed = self._gemini_parse(page_text, prompt)
        if isinstance(parsed, list):
            return parsed[:max_contacts]
        return []

    def enrich_lead_with_linkedin(self, lead_name: str, linkedin_url: str) -> Dict[str, Any]:
        """
        Full LinkedIn enrichment for a lead: company page intel + GTM contacts.
        Returns combined dict ready to feed into GTM scorer.
        """
        enrichment: Dict[str, Any] = {
            "company_intel": {},
            "gtm_contacts": []
        }

        company_data = self.scrape_company_page(linkedin_url)
        if company_data.get("error") == "not_authenticated":
            logger.warning(f"[LinkedIn] Not authenticated — run setup_linkedin_context.py first")
            return enrichment

        enrichment["company_intel"] = company_data

        # Small delay between pages to avoid rate limiting
        time.sleep(2)

        contacts = self.scrape_company_people(linkedin_url)
        enrichment["gtm_contacts"] = contacts

        logger.info(
            f"[LinkedIn] {lead_name} → headcount: {company_data.get('headcount')}, "
            f"contacts: {len(contacts)}"
        )
        return enrichment
