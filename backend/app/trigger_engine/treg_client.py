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
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.token = (token or os.getenv("TREG_TOKEN", "")).strip()
        self.base_url = base_url.rstrip("/")
        self.per_call_cap = per_call_cap
        self.total_cost_usd = 0.0
        self.calls_made = 0
        # Injectable transport (httpx.MockTransport in tests)
        self._transport = transport

    def _headers(self, max_cost: Optional[float] = None, with_body: bool = True) -> dict[str, str]:
        cap = max_cost if max_cost is not None else self.per_call_cap
        headers = {"X-Treg-Route-Max-Cost": f"{cap:.4f}"}
        if with_body:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["X-Treg-Token"] = self.token
        return headers

    @staticmethod
    def _extract_cost(response_json: Any, headers: Any) -> float:
        """
        Real charge is the X-Treg-Cost-Micro response header (integer micro-USD).
        Falls back to legacy header / body fields when the header is absent.
        """
        if hasattr(headers, "get"):
            micro = headers.get("x-treg-cost-micro")
            if micro not in (None, ""):
                try:
                    return int(micro) / 1_000_000
                except (ValueError, TypeError):
                    pass
            legacy = headers.get("x-treg-cost-usd")
            if legacy not in (None, ""):
                try:
                    return float(legacy)
                except (ValueError, TypeError):
                    pass

        if isinstance(response_json, dict):
            treg_meta = response_json.get("_treg")
            if isinstance(treg_meta, dict):
                if treg_meta.get("charged_micro") is not None:
                    try:
                        return int(treg_meta["charged_micro"]) / 1_000_000
                    except (ValueError, TypeError):
                        pass
                if treg_meta.get("cost_usd") is not None:
                    try:
                        return float(treg_meta["cost_usd"])
                    except (ValueError, TypeError):
                        pass
            for key in ("costUsd", "cost_usd"):
                if response_json.get(key) is not None:
                    try:
                        return float(response_json[key])
                    except (ValueError, TypeError):
                        pass
        return 0.0

    def _track_cost(self, response_json: Any, headers: Any) -> float:
        cost = self._extract_cost(response_json, headers)
        self.total_cost_usd += cost
        return cost

    async def call(
        self,
        endpoint_id: str,
        *,
        method: str = "POST",
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        max_cost: Optional[float] = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        """
        Call any treg catalog endpoint: {method} https://treg.to/call/{endpoint_id}

        - POST endpoints take a JSON body (`json`).
        - Strict-query GET endpoints (e.g. HarvestAPI, Fetchin) take only `params`, no body.

        Returns: {success, data, cost_usd, status_code, call_id, served_by, error?, pending?}
        """
        method = method.upper()
        url = f"{self.base_url}/call/{endpoint_id}"
        has_body = method != "GET" and json is not None
        headers = self._headers(max_cost=max_cost, with_body=has_body)
        clean_params = {k: v for k, v in (params or {}).items() if v is not None} or None

        self.calls_made += 1
        try:
            client_kwargs: dict[str, Any] = {"timeout": timeout}
            if self._transport is not None:
                client_kwargs["transport"] = self._transport
            async with httpx.AsyncClient(**client_kwargs) as client:
                res = await client.request(
                    method,
                    url,
                    headers=headers,
                    params=clean_params,
                    json=json if has_body else None,
                )

            call_id = res.headers.get("x-treg-call-id")
            served_by = res.headers.get("x-treg-served-by")

            if res.status_code == 200:
                try:
                    data = res.json()
                except ValueError:
                    data = {"text": res.text}
                cost = self._track_cost(data, res.headers)
                logger.debug("treg call %s succeeded (cost=$%.6f, call_id=%s)", endpoint_id, cost, call_id)
                return {
                    "success": True,
                    "data": data,
                    "cost_usd": cost,
                    "status_code": 200,
                    "call_id": call_id,
                    "served_by": served_by,
                }

            if res.status_code == 202:
                # Routed async child still running — do NOT retry (it may still charge).
                logger.info("treg call %s pending (202), call_id=%s", endpoint_id, call_id)
                return {
                    "success": False,
                    "pending": True,
                    "error": "pending",
                    "status_code": 202,
                    "cost_usd": 0.0,
                    "call_id": call_id,
                    "served_by": served_by,
                }

            logger.warning("treg call %s returned %d: %s", endpoint_id, res.status_code, res.text[:200])
            return {
                "success": False,
                "error": res.text[:500],
                "status_code": res.status_code,
                "cost_usd": 0.0,
                "call_id": call_id,
                "served_by": served_by,
            }
        except Exception as exc:
            logger.error("treg call %s failed with exception: %s", endpoint_id, exc)
            return {"success": False, "error": str(exc), "status_code": None, "cost_usd": 0.0}

    async def call_endpoint(
        self,
        endpoint_id: str,
        payload: dict[str, Any],
        max_cost: Optional[float] = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        """
        Backward-compatible caller: POST https://treg.to/call/{endpoint_id} with a JSON body.
        """
        return await self.call(
            endpoint_id,
            method="POST",
            json=payload,
            max_cost=max_cost,
            timeout=timeout,
        )

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

