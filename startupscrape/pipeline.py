import re
import logging
from typing import List, Dict, Optional, Union
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import StartupLead, FilterQuery, GTMAnalysis
from .scrapers.yc import YCScraper
from .scrapers.waas import WAASScraper
from .enrichers import YCEnricher
from .gtm_scorer import GTMScorer
from .browserbase_client import BrowserbaseClient

logger = logging.getLogger(__name__)


class StartupScrapePipeline:
    """Unified pipeline for scraping, deduplicating, enriching, and AI GTM scoring."""

    def __init__(
        self,
        yc_scraper: Optional[YCScraper] = None,
        waas_scraper: Optional[WAASScraper] = None,
        yc_enricher: Optional[YCEnricher] = None,
        gtm_scorer: Optional[GTMScorer] = None,
        browserbase_client: Optional[BrowserbaseClient] = None
    ):
        self.yc = yc_scraper or YCScraper()
        self.waas = waas_scraper or WAASScraper()
        self.enricher = yc_enricher or YCEnricher(session=self.yc.session)
        self.scorer = gtm_scorer or GTMScorer()
        self.browserbase = browserbase_client or BrowserbaseClient()

    def _normalize_domain(self, website: Optional[str]) -> Optional[str]:
        if not website:
            return None
        url = website.strip().lower()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            domain = urlparse(url).netloc
            domain = re.sub(r"^www\.", "", domain)
            return domain if domain else None
        except Exception:
            return None

    def _normalize_name(self, name: str) -> str:
        cleaned = re.sub(r"[^\w\s]", "", name.lower())
        return " ".join(cleaned.split())

    def enrich_lead(self, lead: StartupLead) -> StartupLead:
        """Enrich a single lead with website, company LinkedIn, and Twitter."""
        return self.enricher.enrich_lead(lead)

    def enrich_leads(self, leads: List[StartupLead], max_workers: int = 5) -> List[StartupLead]:
        """Enrich a list of leads with company website, LinkedIn, and Twitter."""
        return self.enricher.enrich_leads(leads, max_workers=max_workers)

    def score_lead(self, lead: StartupLead, use_browserbase: bool = False) -> StartupLead:
        """Score account for GTM readiness, optionally using Browserbase to scrape site/careers."""
        extra_text = ""
        if use_browserbase and lead.website:
            try:
                res = self.browserbase.scrape_url(lead.website)
                extra_text = res.get("text", "")[:3000]
            except Exception as e:
                logger.warning(f"Browserbase scrape failed for {lead.website}: {e}")

        lead.gtm_analysis = self.scorer.analyze_account(lead, extra_site_text=extra_text)
        return lead

    def score_leads(
        self,
        leads: List[StartupLead],
        use_browserbase: bool = False,
        max_workers: int = 4
    ) -> List[StartupLead]:
        """Run AI GTM scoring across multiple leads concurrently."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_lead = {
                executor.submit(self.score_lead, lead, use_browserbase): lead
                for lead in leads
            }
            for future in as_completed(future_to_lead):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"GTM scoring failed: {e}")
        return leads

    def scrape_from_urls(
        self,
        urls: List[str],
        max_per_source: int = 50,
        enrich: bool = True,
        score_gtm: bool = False
    ) -> List[StartupLead]:
        """Scrape leads from directory URLs or individual company pages."""
        all_leads: List[StartupLead] = []

        for url in urls:
            if "ycombinator.com" in url:
                leads = self.yc.scrape_url(url, max_results=max_per_source, enrich=enrich)
                all_leads.extend(leads)
            elif "workatastartup.com" in url:
                leads = self.waas.scrape_url(url, max_results=max_per_source)
                all_leads.extend(leads)

        deduped = self.deduplicate_and_merge(all_leads)

        if score_gtm and deduped:
            self.score_leads(deduped)

        return deduped

    def pull_early_stage_gtm_leads(
        self,
        batches: Optional[List[str]] = None,
        limit: int = 20,
        min_score: int = 6,
        use_browserbase: bool = False
    ) -> List[StartupLead]:
        """
        Pull early-stage startups (Seed / Series A / recent batches) hiring GTM roles,
        enrich them with company website, LinkedIn, Twitter, and score with AI.
        """
        target_batches = batches or [
            "Winter 2026", "Fall 2025", "Summer 2025", "Winter 2025", "Summer 2024"
        ]

        query = FilterQuery(
            batches=target_batches,
            is_hiring=True,
            team_size_min=2,
            team_size_max=60,
            limit=limit
        )

        leads = self.yc.scrape(query, max_results=limit, enrich=True)
        leads = self.deduplicate_and_merge(leads)
        self.score_leads(leads, use_browserbase=use_browserbase)

        # Filter by minimum score
        qualified = [l for l in leads if (l.gtm_analysis.score if l.gtm_analysis else 0) >= min_score]
        qualified.sort(key=lambda l: (l.gtm_analysis.score if l.gtm_analysis else 0), reverse=True)
        return qualified

    def deduplicate_and_merge(self, leads: List[StartupLead]) -> List[StartupLead]:
        """Deduplicate by normalized website domain or company name, merging fields."""
        domain_map: Dict[str, StartupLead] = {}
        name_map: Dict[str, StartupLead] = {}
        unique_leads: List[StartupLead] = []

        for lead in leads:
            domain = self._normalize_domain(lead.website)
            norm_name = self._normalize_name(lead.name)

            existing: Optional[StartupLead] = None
            if domain and domain in domain_map:
                existing = domain_map[domain]
            elif norm_name in name_map:
                existing = name_map[norm_name]

            if existing:
                if not existing.website and lead.website:
                    existing.website = lead.website
                if not existing.linkedin_url and lead.linkedin_url:
                    existing.linkedin_url = lead.linkedin_url
                if not existing.twitter_url and lead.twitter_url:
                    existing.twitter_url = lead.twitter_url
                if not existing.one_liner and lead.one_liner:
                    existing.one_liner = lead.one_liner
                if not existing.long_description and lead.long_description:
                    existing.long_description = lead.long_description
                if not existing.batch and lead.batch:
                    existing.batch = lead.batch
                if not existing.team_size and lead.team_size:
                    existing.team_size = lead.team_size
                if not existing.yc_url and lead.yc_url:
                    existing.yc_url = lead.yc_url
                if not existing.waas_url and lead.waas_url:
                    existing.waas_url = lead.waas_url
                if not existing.jobs and lead.jobs:
                    existing.jobs = lead.jobs
                    existing.open_jobs_count = len(lead.jobs)
                    existing.is_hiring = True
                if not existing.locations and lead.locations:
                    existing.locations = lead.locations
            else:
                unique_leads.append(lead)
                if domain:
                    domain_map[domain] = lead
                name_map[norm_name] = lead

        return unique_leads
