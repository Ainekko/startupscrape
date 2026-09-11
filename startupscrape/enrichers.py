import html
import json
import re
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

from .models import StartupLead
from .config import DEFAULT_TIMEOUT


class YCEnricher:
    """Enriches YC startup leads with company website, company LinkedIn, and company Twitter from YC company pages."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.ycombinator.com/companies",
        })

    def normalize_company_url(self, slug_or_url: str) -> str:
        """Convert slug or URL to standard YC company page URL."""
        slug_or_url = slug_or_url.strip()
        if slug_or_url.startswith("http://") or slug_or_url.startswith("https://"):
            return slug_or_url.split("?")[0].rstrip("/")
        slug = slug_or_url.strip("/")
        return f"https://www.ycombinator.com/companies/{slug}"

    def extract_slug(self, slug_or_url: str) -> str:
        """Extract slug from company URL or slug."""
        clean = slug_or_url.strip().split("?")[0].rstrip("/")
        if "/companies/" in clean:
            return clean.split("/companies/")[-1].strip("/")
        return clean

    def fetch_company_enrichment(self, slug_or_url: str) -> Dict[str, Optional[str]]:
        """Fetch YC company page and extract website, company LinkedIn, and company Twitter."""
        url = self.normalize_company_url(slug_or_url)
        try:
            resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            if resp.status_code != 200:
                return {"website": None, "linkedin_url": None, "twitter_url": None}
            return self.parse_html(resp.text)
        except Exception:
            return {"website": None, "linkedin_url": None, "twitter_url": None}

    def parse_html(self, html_text: str) -> Dict[str, Optional[str]]:
        """Extract company website, LinkedIn, and Twitter using Inertia data-page with regex fallback."""
        data: Dict[str, Optional[str]] = {
            "website": None,
            "linkedin_url": None,
            "twitter_url": None,
        }

        # 1. Primary extraction via Inertia data-page JSON
        m = re.search(r'data-page=[\x22\x27](.+?)[\x22\x27]', html_text)
        if m:
            try:
                raw_json = html.unescape(m.group(1))
                page_data = json.loads(raw_json)
                company = page_data.get("props", {}).get("company", {})
                if company:
                    data["website"] = company.get("website") or None
                    data["linkedin_url"] = company.get("linkedin_url") or None
                    data["twitter_url"] = company.get("twitter_url") or None
                    return data
            except Exception:
                pass

        # 2. Fallback regex extraction from HTML
        # Company website
        ws_match = re.search(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*class="[^"]*inline-block[^"]*">', html_text)
        if ws_match:
            data["website"] = ws_match.group(1)
        else:
            links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html_text)
            for link in links:
                if not any(blocked in link for blocked in [
                    "ycombinator.com", "utilitydive.com", "cnbc.com", "axios.com",
                    "twitter.com", "x.com", "linkedin.com", "facebook.com",
                    "startupschool.org", "instagram.com", "youtube.com"
                ]):
                    data["website"] = link
                    break

        # Company LinkedIn (/company/)
        li_match = re.search(r'href=["\'](https?://(?:www\.)?linkedin\.com/company/[^"\'\s]+)["\']', html_text)
        if li_match:
            data["linkedin_url"] = li_match.group(1).rstrip("/")

        # Company Twitter / X (excluding YC's account)
        tw_matches = re.findall(r'href=["\'](https?://(?:www\.)?(?:twitter\.com|x\.com)/[A-Za-z0-9_]+)["\']', html_text)
        for tw in tw_matches:
            if "ycombinator" not in tw.lower():
                data["twitter_url"] = tw
                break

        return data

    def enrich_lead(self, lead: StartupLead) -> StartupLead:
        """Enrich a single StartupLead with company website, LinkedIn, and Twitter."""
        target = lead.yc_url or lead.slug or (lead.id if lead.source == "yc" else None)
        if not target:
            return lead

        extracted = self.fetch_company_enrichment(target)
        if extracted.get("website"):
            lead.website = extracted["website"]
        if extracted.get("linkedin_url"):
            lead.linkedin_url = extracted["linkedin_url"]
        if extracted.get("twitter_url"):
            lead.twitter_url = extracted["twitter_url"]

        return lead

    def enrich_leads(self, leads: List[StartupLead], max_workers: int = 5) -> List[StartupLead]:
        """Enrich multiple leads concurrently."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_lead = {executor.submit(self.enrich_lead, lead): lead for lead in leads}
            for future in as_completed(future_to_lead):
                try:
                    future.result()
                except Exception:
                    pass
        return leads
