"""
app/trigger_engine/treg_client.py — treg API Client for Signal Extraction
========================================================================
Lightweight, resilient client for querying treg.to catalog endpoints:
- anyapi.linkedin.search.jobs ($0.0005/success) -> GTM hiring triggers
- treg.google.serp.news ($0.00015/success) -> Funding and product announcements
- treg.google.serp.organic ($0.00015/success) -> Social, forum, and stack mentions
- treg.companies.enrich ($0.0018/success) -> Company tech and growth intel

Handles per-call spending ceilings (X-Treg-Route-Max-Cost), latency timeouts,
error recovery, and exact ledger cost accounting.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://treg.to"


class TregClient:
    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        per_call_cap: float = 0.05,
    ):
        self.token = (token or os.getenv("TREG_TOKEN", "")).strip()
        self.base_url = base_url.rstrip("/")
        self.per_call_cap = per_call_cap
        self.total_cost_usd = 0.0

    def _headers(self, max_cost: Optional[float] = None) -> dict[str, str]:
        cap = max_cost if max_cost is not None else self.per_call_cap
        headers = {
            "Content-Type": "application/json",
            "X-Treg-Route-Max-Cost": f"{cap:.4f}",
        }
        if self.token:
            headers["X-Treg-Token"] = self.token
        return headers

    def _track_cost(self, response_json: dict[str, Any], headers: Any) -> float:
        cost = 0.0
        if "costUsd" in response_json:
            cost = float(response_json.get("costUsd") or 0.0)
        elif "cost_usd" in response_json:
            cost = float(response_json.get("cost_usd") or 0.0)
        elif "_treg" in response_json and isinstance(response_json["_treg"], dict):
            cost = float(response_json["_treg"].get("cost_usd", 0.0))
        elif hasattr(headers, "get") and headers.get("x-treg-cost-usd"):
            try:
                cost = float(headers.get("x-treg-cost-usd", 0.0))
            except (ValueError, TypeError):
                cost = 0.0

        self.total_cost_usd += cost
        return cost

    async def call_endpoint(
        self,
        endpoint_id: str,
        payload: dict[str, Any],
        max_cost: Optional[float] = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        """
        Generic caller for any treg catalog endpoint: POST https://treg.to/call/{endpoint_id}
        """
        url = f"{self.base_url}/call/{endpoint_id}"
        headers = self._headers(max_cost=max_cost)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    cost = self._track_cost(data, res.headers)
                    logger.debug("treg call %s succeeded (cost=$%.6f)", endpoint_id, cost)
                    return {"success": True, "data": data, "cost_usd": cost}
                else:
                    logger.warning("treg call %s returned %d: %s", endpoint_id, res.status_code, res.text[:200])
                    return {"success": False, "error": res.text, "status_code": res.status_code, "cost_usd": 0.0}
        except Exception as exc:
            logger.error("treg call %s failed with exception: %s", endpoint_id, exc)
            return {"success": False, "error": str(exc), "cost_usd": 0.0}

    # ── High-Level Signal Search Methods ─────────────────────────────────────

    async def search_gtm_jobs(self, company_name: str, role_keyword: str = "sales") -> list[dict[str, Any]]:
        """
        Search open job listings on LinkedIn for sales/RevOps/GTM roles via anyapi.linkedin.search.jobs.
        Cost: ~$0.0005 per success.
        """
        query_str = f"{company_name} {role_keyword}".strip()
        resp = await self.call_endpoint(
            "anyapi.linkedin.search.jobs",
            payload={"query": query_str, "limit": 5},
            max_cost=0.01,
        )
        if not resp.get("success"):
            return []

        raw_data = resp.get("data", {})
        output = raw_data.get("output", {})
        data = output.get("data", {}) if isinstance(output, dict) else {}
        items = data.get("items", []) if isinstance(data, dict) else []

        matched_jobs = []
        company_lower = company_name.lower()
        for item in items:
            job_company = str(item.get("company", "")).lower()
            # Verify company name matches or overlaps
            if company_lower in job_company or job_company in company_lower:
                matched_jobs.append({
                    "title": item.get("title"),
                    "company": item.get("company"),
                    "location": item.get("location"),
                    "url": item.get("url"),
                    "created_utc": item.get("createdUtc"),
                    "source": "anyapi.linkedin.search.jobs",
                })
        return matched_jobs

    async def search_company_news(self, company_name: str, query_type: str = "funding") -> list[dict[str, Any]]:
        """
        Search Google News for funding, financing, acquisitions or product releases via treg.google.serp.news.
        Cost: ~$0.00015 per success.
        """
        if query_type == "funding":
            q = f'"{company_name}" (funding OR raised OR "Series A" OR "Series B" OR "Seed round" OR valuation)'
        elif query_type == "product":
            q = f'"{company_name}" (launch OR "new product" OR "announces" OR "GA" OR "v2")'
        else:
            q = f'"{company_name}" {query_type}'

        resp = await self.call_endpoint(
            "treg.google.serp.news",
            payload={"q": q, "limit": 5},
            max_cost=0.01,
        )
        if not resp.get("success"):
            return []

        raw_data = resp.get("data", {})
        output = raw_data.get("output", {})
        results = output.get("results", []) if isinstance(output, dict) else []

        clean_results = []
        for r in results:
            clean_results.append({
                "title": r.get("title"),
                "snippet": r.get("snippet"),
                "source": r.get("source"),
                "url": r.get("url"),
                "created_utc": r.get("createdUtc"),
            })
        return clean_results

    async def search_social_discussions(self, company_name: str, founder_name: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Search Reddit and community discussions via Google Organic SERP.
        Cost: ~$0.00015 per success.
        """
        query_parts = [f'site:reddit.com "{company_name}"']
        if founder_name:
            query_parts.append(f'OR site:reddit.com "{founder_name}"')
        q = " ".join(query_parts)

        resp = await self.call_endpoint(
            "treg.google.serp.organic",
            payload={"q": q},
            max_cost=0.005,
        )
        if not resp.get("success"):
            return []

        raw_data = resp.get("data", {})
        output = raw_data.get("output", {})
        results = output.get("organic_results", output.get("results", [])) if isinstance(output, dict) else []

        discussions = []
        for r in results[:5]:
            discussions.append({
                "title": r.get("title"),
                "snippet": r.get("snippet"),
                "url": r.get("link", r.get("url")),
                "source": "reddit",
            })
        return discussions

    async def enrich_company_tech(self, domain: str) -> dict[str, Any]:
        """
        Enrich company technologies and stack via treg.companies.enrich.
        Cost: ~$0.0018 per success.
        """
        if not domain:
            return {}
        resp = await self.call_endpoint(
            "treg.companies.enrich",
            payload={"domain": domain},
            max_cost=0.02,
        )
        if not resp.get("success"):
            return {}

        raw_data = resp.get("data", {})
        return raw_data.get("output", {})

