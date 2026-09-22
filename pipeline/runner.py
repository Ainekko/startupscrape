"""
runner.py — FlowJoy signal-first lead pipeline orchestrator.

Pipeline:
  Tier 0 — Free scrape + pre-filter (stage, team size, B2B signals)
  Enrich — YC HTTP metadata enrichment (founders, company LinkedIn, personal LinkedIn)
  Tier 1 — jev fast score (B2B, funding stage, no GTM hire)
  Tier 2 — treg email find (threaded, batch=10)
  Tier 3 — jev final fit score (0-20) + rank

Outputs: data/run_<ts>.json (or data/run_<ts>_partial.json on interrupt)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from startupscrape.scrapers.yc import YCScraper
from startupscrape.scrapers.waas import WAASScraper
from startupscrape.models import StartupLead, FilterQuery
from startupscrape.signals import SignalDetector
from startupscrape.enrichers import YCEnricher

from .scorer import judge
from .enricher import enrich_batch

logger = logging.getLogger(__name__)

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── scoring weights ───────────────────────────────────────────────────────────
SCORE_FUNDING = 10       # Seed or Series A
SCORE_NO_GTM = 5         # No GTM engineer / Head of Sales in headcount
SCORE_B2B = 5            # B2B SaaS / Product

BONUS_TEAM_SIZE = 1           # 5–50 headcount
BONUS_TECH_FOUNDER = 1        # ex-FAANG / technical background
BONUS_ENG_HIRING_NOSALES = 1  # engineering roles open with no sales postings
BONUS_EMAIL_VERIFIED = 2      # verified email reachable

TIER1_KEEP = 60
TIER2_KEEP = 50
TREG_MAX_RUN_COST_USD = 1.50

_GTM_TITLES = [
    "gtm engineer", "head of sales", "vp sales", "vp of sales",
    "revenue operations", "revops", "sales lead", "director of sales",
    "growth lead", "head of growth", "gtm lead", "growth engineer",
]

_B2B_TAGS = [
    "b2b", "saas", "enterprise", "developer tools", "devtools", "infrastructure",
    "fintech", "proptech", "hrtech", "martech", "sales", "crm", "data", "analytics",
    "api", "workflow", "ai", "artificial intelligence", "automation", "compliance",
]

_CONSUMER_TAGS = ["consumer", "social", "gaming", "dating", "d2c", "e-commerce", "b2c"]

_TECH_SIGNALS = [
    "google", "meta", "apple", "amazon", "microsoft", "palantir", "stripe",
    "openai", "deepmind", "phd", "stanford", "mit", "berkeley", "cmu", "engineer", "cto"
]

RECENT_BATCHES = ["W25", "S24", "W24", "F24", "S23", "W23", "S22", "W22"]


def run(
    max_leads: int = 10,
    max_treg_cost: float = TREG_MAX_RUN_COST_USD,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """
    Execute the full FlowJoy signal pipeline.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{ts}"
    started_at = datetime.now(timezone.utc).isoformat()
    sources = sources or ["yc"]
    status = "complete"
    partial_path = DATA_DIR / f"{run_id}_partial.json"

    funnel: dict[str, int] = {}
    leads_out: list[dict] = []
    treg_spend = 0.0

    try:
        # ── Tier 0: Scrape ────────────────────────────────────────────────────
        logger.info("Tier 0: scraping startup directories (%s)…", sources)
        raw = _scrape(sources, limit=max(max_leads * 5, 40))
        funnel["raw"] = len(raw)
        logger.info("Tier 0: %d raw leads collected", funnel["raw"])

        # ── Tier 0: Pre-filter ────────────────────────────────────────────────
        filtered = _prefilter(raw)
        funnel["prefiltered"] = len(filtered)
        logger.info("Tier 0 pre-filter: %d remain", funnel["prefiltered"])

        # ── Enrichment: YC HTML parse for founders & links ─────────────────────
        pool_size = min(len(filtered), max(max_leads * 2, 20))
        to_enrich = filtered[:pool_size]
        logger.info("Enriching %d companies with founder/LinkedIn profiles…", len(to_enrich))
        enricher = YCEnricher()
        enriched_leads = enricher.enrich_leads(to_enrich, max_workers=5)

        # ── Tier 1: Fast score ────────────────────────────────────────────────
        logger.info("Tier 1: scoring %d companies…", len(enriched_leads))
        tier1_scored = _tier1_score(enriched_leads)
        tier1_scored.sort(key=lambda x: x["tier1_score"], reverse=True)

        tier1_kept = tier1_scored[:max_leads]
        funnel["tier1_kept"] = len(tier1_kept)
        logger.info("Tier 1: kept top %d leads", funnel["tier1_kept"])

        # ── Tier 2: treg email find ───────────────────────────────────────────
        logger.info("Tier 2: treg email enrichment (cap $%.2f)…", max_treg_cost)

        def _checkpoint(leads_so_far):
            _write_json(partial_path, _build_result(
                run_id, started_at, "partial", funnel, leads_so_far, treg_spend
            ))

        enriched = enrich_batch(tier1_kept, max_run_cost_usd=max_treg_cost, checkpoint_cb=_checkpoint)
        for lead in enriched:
            treg_spend += lead.get("email_result", {}).get("cost_usd", 0.0)

        funnel["email_found"] = sum(1 for l in enriched if l.get("email_result", {}).get("email"))
        logger.info("Tier 2: %d emails found (treg spent $%.4f)", funnel["email_found"], treg_spend)

        # ── Tier 3: Final fit score ───────────────────────────────────────────
        logger.info("Tier 3: final scoring and ranking…")
        tier3_scored = _tier3_score(enriched)
        tier3_scored.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        leads_out = tier3_scored[:max_leads]
        funnel["final_leads"] = len(leads_out)
        logger.info("Tier 3 done: %d final leads ready", funnel["final_leads"])

    except Exception:
        logger.error("Pipeline failed:\n%s", traceback.format_exc())
        status = "partial"

    finished_at = datetime.now(timezone.utc).isoformat()
    result = _build_result(run_id, started_at, status, funnel, leads_out, treg_spend, finished_at)

    out_path = DATA_DIR / f"{run_id}.json"
    _write_json(out_path, result)
    if partial_path.exists():
        partial_path.unlink(missing_ok=True)

    logger.info("Run %s completed → %s (status=%s, treg=$%.4f)", run_id, out_path, status, treg_spend)
    return result


def _scrape(sources: list[str], limit: int = 50) -> list[StartupLead]:
    results: list[StartupLead] = []
    # Seed/Series A query targeting recent batches
    fq = FilterQuery(batches=RECENT_BATCHES, limit=limit)

    def _yc():
        try:
            return YCScraper().scrape(fq, max_results=limit, enrich=False)
        except Exception as e:
            logger.warning("YC scrape failed: %s", e)
            return []

    def _waas():
        try:
            return WAAScraper().scrape(fq, max_results=limit)
        except Exception as e:
            logger.warning("WAAS scrape failed: %s", e)
            return []

    tasks = []
    if "yc" in sources:
        tasks.append(_yc)
    if "waas" in sources:
        tasks.append(_waas)

    with ThreadPoolExecutor(max_workers=max(1, len(tasks))) as pool:
        for fut in as_completed([pool.submit(t) for t in tasks]):
            results.extend(fut.result())

    # Fallback to broader scrape if recent batch query returned too few
    if len(results) < 15:
        logger.info("Expanding scrape query to general batches...")
        broader_fq = FilterQuery(limit=limit)
        results.extend(YCScraper().scrape(broader_fq, max_results=limit, enrich=False))

    # Deduplicate by slug / name
    seen: set[str] = set()
    deduped: list[StartupLead] = []
    for lead in results:
        key = (lead.slug or lead.name).lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(lead)
    return deduped


def _prefilter(leads: list[StartupLead]) -> list[StartupLead]:
    kept = []
    for lead in leads:
        # Exclude massive mature companies
        if lead.team_size and lead.team_size > 150:
            continue

        # Exclude pure consumer if tagged
        tags_lower = [t.lower() for t in lead.tags]
        if any(t in tags_lower for t in _CONSUMER_TAGS) and not any(t in tags_lower for t in _B2B_TAGS):
            continue

        kept.append(lead)
    return kept


def _tier1_score(leads: list[StartupLead]) -> list[dict]:
    def _score_one(lead: StartupLead) -> dict:
        signals = SignalDetector.detect_signals(lead)
        job_titles = [j.title.lower() for j in lead.jobs]
        has_gtm = any(kw in t for t in job_titles for kw in _GTM_TITLES)
        has_eng_job = any(kw in t for t in job_titles for kw in ["engineer", "developer", "backend", "ml", "ai"])
        tags_lower = [t.lower() for t in lead.tags]
        is_b2b_tag = any(t in tags_lower for t in _B2B_TAGS)

        founder = lead.founders[0] if lead.founders else None
        founder_bios = " ".join((f.bio or "") + " " + (f.title or "") for f in lead.founders).lower()
        is_tech_founder = any(s in founder_bios for s in _TECH_SIGNALS)

        state = {
            "company": lead.name,
            "one_liner": lead.one_liner or "",
            "batch": lead.batch or "",
            "team_size": lead.team_size,
            "tags": lead.tags,
            "job_titles": job_titles,
            "has_gtm_job_posting": has_gtm,
            "has_engineering_hiring": has_eng_job,
            "founder_bios": founder_bios[:400],
            "signals": signals,
            "product": "FlowJoy — GTM Engineering Studio building revenue systems for B2B Seed/Series A startups",
        }

        questions = {
            "is_b2b": {
                "type": "boolean",
                "instructions": "Is this a B2B company (sells products or services to other businesses, developers, or enterprises)?",
            },
            "has_gtm_hire": {
                "type": "boolean",
                "instructions": "Does this company currently have a GTM engineer, Head of Sales, RevOps, or Growth Lead?",
            },
            "funding_stage": {
                "type": "choice",
                "instructions": "What is the most likely funding stage of this company?",
                "criteria": {
                    "seed": "Seed round, pre-product-market-fit",
                    "series_a": "Series A, early revenue scaling",
                    "series_b_plus": "Series B or later scaling",
                    "pre_seed": "Pre-seed or bootstrapped",
                    "unknown": "Cannot determine",
                },
            },
        }

        eval_result = judge(state, questions)

        score = 0
        judge_used = eval_result.get("is_b2b", {}).get("judge", "heuristic")

        # B2B: 5 pts
        b2b_prob = eval_result.get("is_b2b", {}).get("probabilities", {}).get("true", 0.5)
        if b2b_prob >= 0.6 or is_b2b_tag:
            score += SCORE_B2B

        # Funding stage (Seed / Series A): 10 pts
        stage_probs = eval_result.get("funding_stage", {}).get("probabilities", {})
        seed_prob = stage_probs.get("seed", 0) + stage_probs.get("series_a", 0)
        if seed_prob >= 0.5 or (lead.batch and any(b in lead.batch for b in RECENT_BATCHES)):
            score += SCORE_FUNDING

        # No GTM hire: 5 pts
        gtm_prob = eval_result.get("has_gtm_hire", {}).get("probabilities", {}).get("true", 0.5)
        if gtm_prob < 0.4 and not has_gtm:
            score += SCORE_NO_GTM

        # Bonuses
        if lead.team_size and 5 <= lead.team_size <= 50:
            score += BONUS_TEAM_SIZE
        if is_tech_founder:
            score += BONUS_TECH_FOUNDER
        if has_eng_job and not has_gtm:
            score += BONUS_ENG_HIRING_NOSALES

        return {
            "id": lead.id,
            "company_name": lead.name,
            "website": lead.website,
            "one_liner": lead.one_liner,
            "batch": lead.batch,
            "team_size": lead.team_size,
            "tags": lead.tags,
            "industry": lead.industry,
            "yc_url": lead.yc_url,
            "waas_url": lead.waas_url,
            "linkedin_url": lead.linkedin_url,
            "founder_name": (founder.name if founder else ""),
            "founder_title": (founder.title if founder else "Founder"),
            "founder_linkedin": (founder.linkedin_url if founder else ""),
            "founders": [
                {
                    "name": f.name,
                    "title": f.title,
                    "linkedin_url": f.linkedin_url,
                    "twitter_url": f.twitter_url,
                }
                for f in lead.founders
            ],
            "signals": signals,
            "tier1_score": score,
            "jev_probs": {
                "is_b2b": eval_result.get("is_b2b", {}).get("probabilities", {}),
                "has_gtm_hire": eval_result.get("has_gtm_hire", {}).get("probabilities", {}),
                "funding_stage": eval_result.get("funding_stage", {}).get("probabilities", {}),
            },
            "jev_judge": judge_used,
            "email_result": None,
        }

    scored = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_score_one, lead): lead for lead in leads}
        for fut in as_completed(futures):
            try:
                scored.append(fut.result())
            except Exception as e:
                logger.warning("Tier 1 score failed for a lead: %s", e)
    return scored


def _tier3_score(leads: list[dict]) -> list[dict]:
    def _score_one(lead: dict) -> dict:
        email_found = bool(lead.get("email_result", {}) and lead["email_result"].get("email"))
        state = {
            "company": lead["company_name"],
            "one_liner": lead.get("one_liner", ""),
            "team_size": lead.get("team_size"),
            "signals": lead.get("signals", []),
            "tier1_score": lead.get("tier1_score", 0),
            "email_found": email_found,
            "founder_name": lead.get("founder_name", ""),
            "founder_title": lead.get("founder_title", ""),
            "product": "FlowJoy — GTM Engineering Studio building revenue systems for B2B Seed/Series A startups",
        }
        questions = {
            "fit": {
                "type": "score",
                "instructions": "Score this lead's fit as a FlowJoy prospect from 0 to 20.",
                "criteria": [
                    {"level": 0, "description": "Consumer, pre-revenue, or clearly not a match"},
                    {"level": 5, "description": "B2B but large/mature, already has full GTM team"},
                    {"level": 10, "description": "B2B, Seed/SeriesA, may have some sales capacity"},
                    {"level": 15, "description": "B2B, Seed/SeriesA, no GTM hire, technical founder"},
                    {"level": 20, "description": "All signals: seed/A, B2B, no GTM, eng-heavy, email found"},
                ],
            },
        }

        eval_res = judge(state, questions)
        fit_ans = eval_res.get("fit", {}).get("answer", lead.get("tier1_score", 0))

        # Add bonus for verified email
        final_score = float(fit_ans)
        if email_found:
            final_score = min(24.0, final_score + BONUS_EMAIL_VERIFIED)

        lead["final_score"] = round(final_score, 1)
        lead["jev_final_probs"] = eval_res.get("fit", {}).get("probabilities", {})
        lead["jev_final_judge"] = eval_res.get("fit", {}).get("judge", "heuristic")
        return lead

    result = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_score_one, lead): lead for lead in leads}
        for fut in as_completed(futures):
            try:
                result.append(fut.result())
            except Exception as e:
                logger.warning("Tier 3 score failed: %s", e)
    return result


def _build_result(
    run_id: str,
    started_at: str,
    status: str,
    funnel: dict,
    leads: list[dict],
    treg_spend: float,
    finished_at: str | None = None,
) -> dict:
    judge_name = leads[0].get("jev_judge", "heuristic") if leads else "heuristic"
    return {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at or datetime.now(timezone.utc).isoformat(),
        "status": status,
        "funnel": funnel,
        "spend": {
            "treg_usd": round(treg_spend, 6),
            "jev_judge": judge_name,
        },
        "leads": leads,
    }


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)
