import json
import urllib.parse
from typing import List, Dict, Any, Optional
import requests

from ..config import (
    WAAS_ALGOLIA_APP_ID,
    WAAS_ALGOLIA_API_KEY,
    WAAS_COMPANY_INDEX,
    ALGOLIA_API_BASE,
    DEFAULT_TIMEOUT
)
from ..models import StartupLead, JobPosting, FilterQuery


class WAASScraper:
    """Scraper client for Work at a Startup directory via official Algolia endpoints."""

    def __init__(self, app_id: Optional[str] = None, api_key: Optional[str] = None):
        self.app_id = app_id or WAAS_ALGOLIA_APP_ID
        self.api_key = api_key or WAAS_ALGOLIA_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.workatastartup.com/",
            "Origin": "https://www.workatastartup.com",
            "Content-Type": "application/json"
        })

    def parse_url(self, url: str) -> FilterQuery:
        """Parse WAAS URL parameters into FilterQuery."""
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        locations = params.get("locations", [])
        industry = params.get("industry", [])
        industries = [i for i in industry if i.lower() != "any"]
        job_types = [j for j in params.get("jobType", []) if j.lower() != "any"]
        has_equity = params.get("hasEquity", [None])[0]
        has_salary = params.get("hasSalary", [None])[0]
        us_visa_not_req = params.get("usVisaNotRequired", [None])[0]
        sort_by = params.get("sortBy", ["created_desc"])[0]

        return FilterQuery(
            locations=locations,
            industries=industries,
            job_types=job_types,
            has_equity=True if has_equity in ("true", "True", "1") else None,
            has_salary=True if has_salary in ("true", "True", "1") else None,
            visa_not_required=True if us_visa_not_req in ("true", "True", "1") else None,
            sort_by=sort_by
        )

    def _build_algolia_params(self, filters: FilterQuery, page: int = 0, hits_per_page: int = 50) -> str:
        """Construct Algolia query parameters for WAAS."""
        facet_filters = []

        if filters.locations:
            facet_filters.append([f"locations:{loc}" for loc in filters.locations if loc.lower() != "any"])

        if filters.industries:
            facet_filters.append([f"industry:{ind}" for ind in filters.industries if ind.lower() != "any"])

        if filters.has_equity is True:
            facet_filters.append(["has_equity:true"])

        if filters.has_salary is True:
            facet_filters.append(["has_salary:true"])

        if filters.visa_not_required is True:
            facet_filters.append(["us_visa_not_required:true"])

        query_parts = [
            f"query={urllib.parse.quote(filters.query_text or '')}",
            f"page={page}",
            f"hitsPerPage={hits_per_page}"
        ]

        if facet_filters:
            query_parts.append(f"facetFilters={urllib.parse.quote(json.dumps(facet_filters))}")

        return "&".join(query_parts)

    def scrape(self, filters: FilterQuery, max_results: int = 50) -> List[StartupLead]:
        """Query WAAS Algolia endpoint and return StartupLead records."""
        endpoint = (
            f"{ALGOLIA_API_BASE}"
            f"?x-algolia-agent=Algolia%20for%20JavaScript%20(4.14.3)"
            f"&x-algolia-api-key={self.api_key}"
            f"&x-algolia-application-id={self.app_id}"
        )

        leads: List[StartupLead] = []
        page = 0
        hits_per_page = min(max_results, 50)

        while len(leads) < max_results:
            params_str = self._build_algolia_params(filters, page=page, hits_per_page=hits_per_page)
            payload = {
                "requests": [
                    {
                        "indexName": WAAS_COMPANY_INDEX,
                        "params": params_str
                    }
                ]
            }

            resp = self.session.post(endpoint, json=payload, timeout=DEFAULT_TIMEOUT)
            if resp.status_code != 200:
                break

            data = resp.json()
            results = data.get("results", [{}])[0]
            hits = results.get("hits", [])
            if not hits:
                break

            for hit in hits:
                lead = self._parse_hit(hit)
                leads.append(lead)
                if len(leads) >= max_results:
                    break

            nb_pages = results.get("nbPages", 1)
            page += 1
            if page >= nb_pages:
                break

        return leads

    def scrape_url(self, url: str, max_results: int = 50) -> List[StartupLead]:
        """Convenience method to parse WAAS URL and scrape in one call."""
        filters = self.parse_url(url)
        return self.scrape(filters, max_results=max_results)

    def _parse_hit(self, hit: Dict[str, Any]) -> StartupLead:
        """Map raw WAAS Algolia hit to StartupLead model."""
        slug = hit.get("slug") or hit.get("objectID", "")
        waas_url = f"https://www.workatastartup.com/companies/{slug}" if slug else None

        # Extract job postings
        jobs: List[JobPosting] = []
        for job_data in hit.get("jobs", []):
            if isinstance(job_data, dict):
                jobs.append(JobPosting(
                    id=str(job_data.get("id", "")),
                    title=job_data.get("title", ""),
                    role_type=job_data.get("role_type"),
                    location=job_data.get("location"),
                    has_salary=job_data.get("has_salary"),
                    has_equity=job_data.get("has_equity"),
                    visa_sponsored=job_data.get("visa_sponsored"),
                    url=job_data.get("url") or (f"{waas_url}/jobs/{job_data.get('id')}" if waas_url and job_data.get('id') else None)
                ))

        # Extract locations
        locations = hit.get("locations", [])
        if isinstance(locations, str):
            locations = [locations]

        return StartupLead(
            id=str(hit.get("objectID") or slug),
            source="workatastartup",
            name=hit.get("name", "Unknown"),
            slug=slug,
            website=hit.get("website"),
            one_liner=hit.get("one_liner"),
            long_description=hit.get("description"),
            batch=hit.get("batch"),
            industry=hit.get("industry"),
            subindustry=hit.get("subindustry"),
            tags=hit.get("tags", []),
            team_size=hit.get("team_size") or hit.get("headcount"),
            locations=locations,
            is_hiring=True if len(jobs) > 0 or hit.get("is_hiring") else False,
            open_jobs_count=len(jobs) or hit.get("job_count", 0),
            jobs=jobs,
            waas_url=waas_url,
            raw_data=hit
        )
