"""
enricher.py — treg-powered email enrichment for the FlowJoy lead-finder pipeline.

Uses treg.people.email.find:
  POST https://treg.to/call/treg.people.email.find
  Headers:
    X-Treg-Token: $TREG_TOKEN
    X-Treg-Route-Max-Cost: $0.05
  Body:
    {"full_name": "...", "company_name": "...", "domain": "..."}

Extracts verified business email for founders.
Handles concurrency, cost tracking, checkpoints, and budget ceiling.
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_TREG_TOKEN = os.getenv("TREG_TOKEN", "").strip()
_TREG_BASE = "https://treg.to"
_EMAIL_ENDPOINT = "treg.people.email.find"
_PER_CALL_CAP_USD = float(os.getenv("TREG_PER_CALL_CAP_USD", "0.05"))
_BATCH_SIZE = 10
_MAX_WORKERS = 6


def _extract_domain(website: str | None) -> str | None:
    if not website:
        return None
    w = str(website).strip().lower()
    if not w.startswith(("http://", "https://")):
        w = "https://" + w
    try:
        netloc = urlparse(w).netloc
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc if "." in netloc else None
    except Exception:
        return None


def find_email(full_name: str, company_name: str, domain: str | None = None) -> dict[str, Any] | None:
    """
    Call treg.people.email.find for one person.

    Returns dict with keys:
        email, verified, provider, cost_usd, call_id
    """
    if not _TREG_TOKEN:
        logger.warning("TREG_TOKEN not set — skipping email find")
        return None

    clean_domain = _extract_domain(domain)
    payload: dict[str, Any] = {
        "full_name": full_name.strip(),
        "company_name": company_name.strip(),
    }
    if clean_domain:
        payload["domain"] = clean_domain

    headers = {
        "X-Treg-Token": _TREG_TOKEN,
        "X-Treg-Route-Max-Cost": str(_PER_CALL_CAP_USD),
        "Content-Type": "application/json",
    }

    url = f"{_TREG_BASE}/call/{_EMAIL_ENDPOINT}"
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        call_id = r.headers.get("X-Treg-Call-Id", "")
        cost_micro = int(r.headers.get("X-Treg-Cost-Micro", "0"))
        cost_usd = cost_micro / 1_000_000
        served_by = r.headers.get("X-Treg-Served-By", "")

        if r.status_code == 402:
            detail = r.json() if r.content else {}
            logger.warning(
                "treg 402 for %s @ %s — %s (call_id=%s)",
                full_name, company_name, detail.get("error", "budget limit"), call_id
            )
            return {"email": None, "error": "budget_limit", "cost_usd": 0.0, "call_id": call_id}

        if r.status_code == 404:
            return {"email": None, "error": "miss", "cost_usd": cost_usd, "call_id": call_id, "provider": served_by}

        if r.status_code != 200:
            logger.warning("treg call error %d: %s", r.status_code, r.text[:200])
            return {"email": None, "error": f"http_{r.status_code}", "cost_usd": cost_usd, "call_id": call_id}

        data = r.json()
        email = data.get("email") or data.get("output", {}).get("email")
        verified = data.get("output", {}).get("verified", False) or data.get("verified", False)

        return {
            "email": email,
            "verified": bool(verified),
            "provider": served_by or data.get("_treg", {}).get("served_by", ""),
            "cost_usd": cost_usd,
            "call_id": call_id,
            "raw": data,
        }

    except requests.exceptions.Timeout:
        logger.warning("Timeout finding email for %s @ %s", full_name, company_name)
        return {"email": None, "error": "timeout", "cost_usd": 0.0}
    except Exception as exc:
        logger.error("Email find error for %s @ %s: %s", full_name, company_name, exc)
        return {"email": None, "error": str(exc), "cost_usd": 0.0}


def enrich_batch(
    leads: list[dict[str, Any]],
    max_run_cost_usd: float = 2.0,
    checkpoint_cb=None,
) -> list[dict[str, Any]]:
    """
    Enrich a list of leads with emails using treg.
    Mutates each dict in-place: adds email_result dict.
    """
    run_cost = 0.0
    results = list(leads)

    for batch_start in range(0, len(results), _BATCH_SIZE):
        if run_cost >= max_run_cost_usd:
            logger.warning("Stopping email enrichment — run cost $%.4f reached cap $%.2f", run_cost, max_run_cost_usd)
            break

        batch = results[batch_start: batch_start + _BATCH_SIZE]
        futures = {}

        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(batch))) as pool:
            for lead in batch:
                name = lead.get("founder_name", "")
                company = lead.get("company_name", "")
                domain = lead.get("website", "")
                if not name or not company:
                    lead["email_result"] = {"email": None, "error": "missing_name_or_company", "cost_usd": 0.0}
                    continue
                fut = pool.submit(find_email, name, company, domain)
                futures[fut] = lead

            for fut in as_completed(futures):
                lead = futures[fut]
                res = fut.result()
                lead["email_result"] = res or {"email": None, "error": "no_result", "cost_usd": 0.0}
                if res:
                    run_cost += res.get("cost_usd", 0.0)
                    if res.get("error") == "budget_limit":
                        logger.error("treg budget exhausted — stopping")
                        for remaining in batch:
                            if "email_result" not in remaining:
                                remaining["email_result"] = {"email": None, "error": "budget_exhausted", "cost_usd": 0.0}
                        if checkpoint_cb:
                            checkpoint_cb(results)
                        return results

        if checkpoint_cb:
            checkpoint_cb(results)

        time.sleep(0.3)

    return results
