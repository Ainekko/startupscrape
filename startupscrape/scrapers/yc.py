import json
import urllib.parse
import logging
from typing import List, Dict, Any, Optional
import requests

from ..config import (
    YC_ALGOLIA_APP_ID,
    YC_ALGOLIA_API_KEY,
    YC_PRIMARY_INDEX,
    ALGOLIA_API_BASE,
    DEFAULT_TIMEOUT,
    fetch_live_algolia_opts
)
from ..models import StartupLead, Founder, FilterQuery

logger = logging.getLogger(__name__)


class YCScraper:
    """Scraper client for Y Combinator company directory and company detail pages."""

    def __init__(self, app_id: Optional[str] = None, api_key: Optional[str] = None):
        self.app_id = app_id or YC_ALGOLIA_APP_ID
        self.api_key = api_key or YC_ALGOLIA_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.ycombinator.com/",
            "Origin": "https://www.ycombinator.com",
            "Content-Type": "application/json"
        })

    def _refresh_key(self) -> bool:
        """Dynamically refresh Algolia credentials from live YC companies page."""
        opts = fetch_live_algolia_opts("https://www.ycombinator.com/companies", self.session)
        if opts.get("key") and opts.get("app"):
            self.app_id = opts["app"]
            self.api_key = opts["key"]
            logger.info("Auto-refreshed YC Algolia credentials successfully.")
            return True
        return False

    def parse_url(self, url: str) -> FilterQuery:
        """Parse YC directory search URL with query parameters into FilterQuery."""
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        batches = params.get("batch", [])
        industries = params.get("industry", [])
        regions = params.get("regions", [])
        is_hiring = params.get("isHiring", [None])[0]
        nonprofit = params.get("nonprofit", [None])[0]
        query_text = params.get("q", [""])[0]

        team_size_min = None
        team_size_max = None
        team_size_raw = params.get("team_size", [None])[0]
        if team_size_raw:
            try:
                ts_list = json.loads(team_size_raw)
                if len(ts_list) == 2:
                    team_size_min = int(ts_list[0]) if ts_list[0] else None
                    team_size_max = int(ts_list[1]) if ts_list[1] else None
            except Exception:
                pass

        return FilterQuery(
            query_text=query_text,
            batches=batches,
            industries=industries,
            regions=regions,
            is_hiring=True if is_hiring in ("true", "True", "1") else (False if is_hiring in ("false", "False", "0") else None),
            nonprofit=True if nonprofit in ("true", "True", "1") else None,
            team_size_min=team_size_min,
            team_size_max=team_size_max,
        )

    def _build_algolia_params(self, filters: FilterQuery, page: int = 0, hits_per_page: int = 50) -> str:
        """Construct Algolia URL-encoded query parameters."""
        facet_filters = []

        if filters.batches:
            facet_filters.append([f"batch:{b}" for b in filters.batches])
        if filters.industries:
            facet_filters.append([f"industry:{ind}" for ind in filters.industries])
        if filters.regions:
            facet_filters.append([f"regions:{r}" for r in filters.regions])
        if filters.is_hiring is True:
            facet_filters.append(["isHiring:true"])
        elif filters.is_hiring is False:
            facet_filters.append(["isHiring:false"])
        if filters.nonprofit is True:
            facet_filters.append(["nonprofit:true"])

        query_parts = [
            f"query={urllib.parse.quote(filters.query_text or '')}",
            f"page={page}",
            f"hitsPerPage={hits_per_page}"
        ]

        if facet_filters:
            query_parts.append(f"facetFilters={urllib.parse.quote(json.dumps(facet_filters))}")

        numeric_filters = []
        if filters.team_size_min is not None:
            numeric_filters.append(f"team_size>={filters.team_size_min}")
        if filters.team_size_max is not None:
            numeric_filters.append(f"team_size<={filters.team_size_max}")

        if numeric_filters:
            query_parts.append(f"numericFilters={urllib.parse.quote(json.dumps(numeric_filters))}")

        return "&".join(query_parts)

    def scrape(self, filters: FilterQuery, max_results: int = 50, enrich: bool = False) -> List[StartupLead]:
        """Query Algolia endpoint and return parsed StartupLead records with auto-refresh on 403."""
        leads: List[StartupLead] = []
        page = 0
        hits_per_page = min(max_results, 50)

        while len(leads) < max_results:
            endpoint = (
                f"{ALGOLIA_API_BASE}"
                f"?x-algolia-agent=Algolia%20for%20JavaScript%20(4.14.3)"
                f"&x-algolia-api-key={self.api_key}"
                f"&x-algolia-application-id={self.app_id}"
            )
            params_str = self._build_algolia_params(filters, page=page, hits_per_page=hits_per_page)
            payload = {
                "requests": [
                    {
                        "indexName": YC_PRIMARY_INDEX,
                        "params": params_str
                    }
                ]
            }

            resp = self.session.post(endpoint, json=payload, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 403:
                # Key expired, attempt auto-refresh
                if self._refresh_key():
                    endpoint = (
                        f"{ALGOLIA_API_BASE}"
                        f"?x-algolia-agent=Algolia%20for%20JavaScript%20(4.14.3)"
                        f"&x-algolia-api-key={self.api_key}"
                        f"&x-algolia-application-id={self.app_id}"
                    )
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

        if enrich and leads:
            from ..enrichers import YCEnricher
            enricher = YCEnricher(session=self.session)
            enricher.enrich_leads(leads)

        return leads

    def is_company_detail_url(self, url: str) -> bool:
        """Check if URL points directly to a single company page."""
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.strip("/")
        parts = path.split("/")
        return len(parts) == 2 and parts[0] == "companies" and parts[1] != ""

    def scrape_company_page(self, slug_or_url: str) -> Optional[StartupLead]:
        """Scrape and enrich a single company page directly."""
        clean = slug_or_url.strip().split("?")[0].rstrip("/")
        slug = clean.split("/companies/")[-1].strip("/") if "/companies/" in clean else clean
        url = f"https://www.ycombinator.com/companies/{slug}"

        from ..enrichers import YCEnricher
        enricher = YCEnricher(session=self.session)
        data = enricher.fetch_company_enrichment(url)

        lead = StartupLead(
            id=slug,
            source="yc",
            name=data.get("name") or slug.title(),
            slug=slug,
            website=data.get("website"),
            one_liner=data.get("one_liner"),
            long_description=data.get("long_description"),
            batch=data.get("batch"),
            team_size=data.get("team_size"),
            locations=[data["location"]] if data.get("location") else [],
            city=data.get("city"),
            country=data.get("country"),
            tags=data.get("tags") or [],
            founders=data.get("founders") or [],
            jobs=data.get("jobs") or [],
            yc_url=url,
            linkedin_url=data.get("linkedin_url"),
            twitter_url=data.get("twitter_url"),
        )
        return lead

    def scrape_url(self, url: str, max_results: int = 50, enrich: bool = True) -> List[StartupLead]:
        """Scrape leads from either a single company URL or a directory search URL."""
        if self.is_company_detail_url(url):
            lead = self.scrape_company_page(url)
            return [lead] if lead else []

        filters = self.parse_url(url)
        return self.scrape(filters, max_results=max_results, enrich=enrich)

    def _parse_hit(self, hit: Dict[str, Any]) -> StartupLead:
        """Map raw Algolia hit to StartupLead model."""
        slug = hit.get("slug") or hit.get("objectID", "")
        yc_url = f"https://www.ycombinator.com/companies/{slug}" if slug else None

        locations = []
        if hit.get("all_locations"):
            locations = [loc.strip() for loc in hit.get("all_locations", "").split(";") if loc.strip()]
        elif hit.get("location"):
            locations = [hit.get("location")]

        return StartupLead(
            id=str(hit.get("objectID") or slug),
            source="yc",
            name=hit.get("name", "Unknown"),
            slug=slug,
            website=hit.get("website"),
            one_liner=hit.get("one_liner"),
            long_description=hit.get("long_description"),
            batch=hit.get("batch_name") or hit.get("batch"),
            status=hit.get("status", "Active"),
            industry=hit.get("industry"),
            subindustry=hit.get("subindustry"),
            tags=hit.get("tags", []),
            team_size=hit.get("team_size"),
            locations=locations,
            country=hit.get("country"),
            city=hit.get("city"),
            is_hiring=bool(hit.get("isHiring")),
            open_jobs_count=hit.get("job_count", 0) or len(hit.get("jobs", [])),
            yc_url=yc_url,
            linkedin_url=hit.get("linkedin_url"),
            twitter_url=hit.get("twitter_url"),
            github_url=hit.get("github_url"),
            raw_data=hit
        )
