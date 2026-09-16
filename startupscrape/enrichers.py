import html
import json
import re
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

from .models import StartupLead, Founder, JobPosting
from .config import DEFAULT_TIMEOUT


class YCEnricher:
    """Enriches YC startup leads with company website, company LinkedIn/Twitter, founder intelligence, and jobs from YC company pages."""

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

    def fetch_company_enrichment(self, slug_or_url: str) -> Dict[str, Any]:
        """Fetch YC company page and extract website, company LinkedIn/Twitter, and founders."""
        url = self.normalize_company_url(slug_or_url)
        try:
            resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            if resp.status_code != 200:
                return {"website": None, "linkedin_url": None, "twitter_url": None, "founders": [], "jobs": []}
            return self.parse_html(resp.text)
        except Exception:
            return {"website": None, "linkedin_url": None, "twitter_url": None, "founders": [], "jobs": []}

    def parse_html(self, html_text: str) -> Dict[str, Any]:
        """Extract company website, LinkedIn, Twitter, and full founder profiles using Inertia data-page with regex fallback."""
        data: Dict[str, Any] = {
            "website": None,
            "linkedin_url": None,
            "twitter_url": None,
            "founders": [],
            "jobs": [],
            "tags": [],
            "long_description": None,
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
                    data["tags"] = company.get("tags") or []
                    data["long_description"] = company.get("long_description") or None

                    # Extract rich founder intelligence
                    founders_list = []
                    for f in company.get("founders", []):
                        fname = f.get("full_name") or f.get("name")
                        if fname:
                            founder_obj = Founder(
                                name=fname.strip(),
                                title=f.get("title") or "Founder",
                                avatar_thumb=f.get("avatar_thumb_url"),
                                twitter_url=f.get("twitter_url") or None,
                                linkedin_url=f.get("linkedin_url") or None,
                                bio=f.get("founder_bio") or None,
                                has_email=f.get("has_email"),
                                projects=f.get("latest_yc_company", {}).get("name") if isinstance(f.get("latest_yc_company"), dict) else None
                            )
                            founders_list.append(founder_obj)
                    data["founders"] = founders_list

                    # Extract jobs listed on company page
                    jobs_list = []
                    for j in company.get("jobs", []):
                        title = j.get("title")
                        if title:
                            jobs_list.append(JobPosting(
                                id=str(j.get("id") or ""),
                                title=title,
                                role_type=j.get("role_type"),
                                location=j.get("location"),
                                url=j.get("apply_url") or j.get("url")
                            ))
                    data["jobs"] = jobs_list

                    return data
            except Exception:
                pass

        # 2. Fallback regex extraction from HTML
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

        li_match = re.search(r'href=["\'](https?://(?:www\.)?linkedin\.com/company/[^"\'\s]+)["\']', html_text)
        if li_match:
            data["linkedin_url"] = li_match.group(1).rstrip("/")

        tw_matches = re.findall(r'href=["\'](https?://(?:www\.)?(?:twitter\.com|x\.com)/[A-Za-z0-9_]+)["\']', html_text)
        for tw in tw_matches:
            if "ycombinator" not in tw.lower():
                data["twitter_url"] = tw
                break

        return data

    def enrich_lead(self, lead: StartupLead) -> StartupLead:
        """Enrich a single StartupLead with company website, LinkedIn, Twitter, founders, and jobs."""
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
        if extracted.get("tags") and not lead.tags:
            lead.tags = extracted["tags"]
        if extracted.get("long_description") and not lead.long_description:
            lead.long_description = extracted["long_description"]

        # Attach founders
        if extracted.get("founders"):
            lead.founders = extracted["founders"]

        # Attach jobs
        if extracted.get("jobs"):
            if not lead.jobs:
                lead.jobs = extracted["jobs"]
                lead.open_jobs_count = len(lead.jobs)
                lead.is_hiring = True

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
