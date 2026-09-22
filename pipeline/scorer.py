"""
scorer.py — jev scoring wrapper for FlowJoy lead-finder pipeline.

Public interface:
    judge(state, questions) -> answers dict

If AI_GATEWAY_API_KEY is configured and active, calls jev via Vercel AI Gateway:
    POST https://ai-gateway.vercel.sh/v4/ai/evaluation-model

Evaluates:
  - B2B vs Consumer
  - Absence of in-house GTM/Sales leadership
  - Funding stage (2023-2027 Seed/Series A cohorts)
  - Competitor / Agency Overlap (penalizes automated GTM / AI SDR / agency tools)
  - Vertical Core R&D (boosts DevTools, APIs, tax, firmware, simulation, hardware)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_JEV_URL = "https://ai-gateway.vercel.sh/v4/ai/evaluation-model"
_API_KEY = os.getenv("AI_GATEWAY_API_KEY", "").strip()
_JEV_DISABLED = False

COMPETITOR_TERMS = [
    "automated gtm", "autonomous gtm", "gtm automation", "ai sdr", "autonomous sdr",
    "sales automation", "lead generation", "lead gen", "cold email", "cold outreach",
    "outbound automation", "automate your business processes", "automate business processes",
    "ai agency", "gtm studio", "revenue automation", "sales prospecting", "prospecting tool",
    "pipeline automation", "ai sales agent", "ai sales team", "gtm for small business",
    "outbound pipeline", "automate outbound", "ai for sales", "sales pipeline",
    "the ai team for the businesses that don't have one", "the ai team for businesses",
]

VERTICAL_TERMS = [
    "developer tools", "devtools", "api", "infrastructure", "firmware", "hardware",
    "robotics", "cybersecurity", "security", "database", "tax", "accounting", "fintech",
    "logistics", "trucking", "simulation", "deeptech", "manufacturing", "healthcare",
    "biotech", "compliance", "voice ai", "model", "training data", "embedded", "sensors",
    "crypto", "documents",
]


def judge(state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    global _JEV_DISABLED

    if _API_KEY and not _JEV_DISABLED:
        try:
            return _call_jev(state, questions)
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 403:
                _JEV_DISABLED = True
                try:
                    err_detail = exc.response.json().get("error", {}).get("message", "")
                except Exception:
                    err_detail = exc.response.text[:200]
                logger.warning(
                    "Vercel AI Gateway 403 Forbidden: %s. Using heuristic judge for this run.",
                    err_detail or "Credit card verification required on Vercel account",
                )
            else:
                logger.warning("jev call failed (%s); using heuristic judge", exc)
        except Exception as exc:
            logger.warning("jev evaluation unavailable (%s); using heuristic judge", exc)

    return _heuristic_judge(state, questions)


def _call_jev(state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {_API_KEY}",
        "ai-model-id": "typesafe-ai/jev",
        "ai-evaluation-model-specification-version": "4",
        "ai-gateway-protocol-version": "0.0.1",
        "Content-Type": "application/json",
    }
    body = {"state": state, "questions": questions}

    r = requests.post(_JEV_URL, headers=headers, json=body, timeout=25)
    r.raise_for_status()
    data = r.json()

    for k in data:
        if isinstance(data[k], dict):
            data[k].setdefault("judge", "jev")
    return data


def _heuristic_judge(state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}

    tags = [str(t).lower() for t in state.get("tags", [])]
    one_liner = str(state.get("one_liner", "")).lower()
    batch = str(state.get("batch", "")).lower()
    industry = str(state.get("industry", "")).lower()
    job_titles = [str(t).lower() for t in state.get("job_titles", [])]
    has_gtm_posting = bool(state.get("has_gtm_job_posting", False))

    text_corpus = f"{one_liner} {' '.join(tags)} {industry}".lower()

    # 1. Competitor / Direct Agency Overlap Check
    is_competitor = any(term in text_corpus for term in COMPETITOR_TERMS)

    # 2. Vertical Product Core R&D Check
    is_vertical = any(term in text_corpus for term in VERTICAL_TERMS) and not is_competitor

    b2b_keywords = [
        "b2b", "saas", "enterprise", "developer tools", "devtools", "infrastructure",
        "fintech", "proptech", "hrtech", "martech", "sales", "crm", "data", "analytics",
        "api", "workflow", "ai", "artificial intelligence", "automation", "compliance", "cybersecurity"
    ]
    consumer_keywords = ["consumer", "social", "gaming", "dating", "d2c", "e-commerce", "b2c"]

    is_b2b_signal = ("b2b" in industry) or any(k in tags or k in one_liner for k in b2b_keywords)
    is_consumer_signal = any(k in tags or k in one_liner for k in consumer_keywords) and not ("b2b" in industry)

    gtm_keywords = [
        "gtm engineer", "head of sales", "vp sales", "vp of sales",
        "revenue operations", "revops", "sales lead", "director of sales",
        "growth lead", "head of growth", "gtm lead", "growth engineer"
    ]
    has_gtm_hire = has_gtm_posting or any(any(k in t for k in gtm_keywords) for t in job_titles)

    # Cohorts from 2023 to 2027 count as actively funded Seed/Series A
    is_target_funding_stage = any(yr in batch for yr in ["2023", "2024", "2025", "2026", "2027"])

    for key, q in questions.items():
        qtype = q.get("type", "boolean")

        if "competitor" in key.lower() or "overlap" in key.lower():
            ans = is_competitor
            probs = {"true": 0.95, "false": 0.05} if is_competitor else {"true": 0.05, "false": 0.95}
            results[key] = {"answer": ans, "probabilities": probs, "judge": "heuristic"}

        elif "vertical" in key.lower():
            ans = is_vertical
            probs = {"true": 0.90, "false": 0.10} if is_vertical else {"true": 0.20, "false": 0.80}
            results[key] = {"answer": ans, "probabilities": probs, "judge": "heuristic"}

        elif key == "is_b2b" or ("b2b" in key.lower()):
            if is_b2b_signal and not is_consumer_signal:
                ans, probs = True, {"true": 0.95, "false": 0.05}
            elif is_consumer_signal and not is_b2b_signal:
                ans, probs = False, {"true": 0.10, "false": 0.90}
            else:
                ans, probs = True, {"true": 0.65, "false": 0.35}
            results[key] = {"answer": ans, "probabilities": probs, "judge": "heuristic"}

        elif key == "has_gtm_hire" or ("gtm" in key.lower() and qtype == "boolean"):
            if has_gtm_hire:
                ans, probs = True, {"true": 0.90, "false": 0.10}
            else:
                ans, probs = False, {"true": 0.15, "false": 0.85}
            results[key] = {"answer": ans, "probabilities": probs, "judge": "heuristic"}

        elif key == "funding_stage" or (qtype == "choice" and "stage" in key.lower()):
            options = list(q.get("criteria", {}).keys()) if isinstance(q.get("criteria"), dict) else ["seed", "series_a", "pre_seed", "series_b_plus", "unknown"]
            if is_target_funding_stage:
                probs = {"seed": 0.65, "series_a": 0.30, "pre_seed": 0.03, "series_b_plus": 0.01, "unknown": 0.01}
                ans = "seed"
            else:
                probs = {"seed": 0.05, "series_a": 0.10, "series_b_plus": 0.80, "pre_seed": 0.02, "unknown": 0.03}
                ans = "series_b_plus"
            active_probs = {opt: probs.get(opt, 1.0 / len(options)) for opt in options}
            total = sum(active_probs.values()) or 1.0
            active_probs = {k: round(v / total, 3) for k, v in active_probs.items()}
            results[key] = {"answer": ans if ans in options else options[0], "probabilities": active_probs, "judge": "heuristic"}

        elif key == "fit" or qtype == "score":
            pts = 0.0
            if is_target_funding_stage:
                pts += 10.0
            if not has_gtm_hire:
                pts += 5.0
            if is_b2b_signal:
                pts += 5.0

            # Vertical bonus / Competitor penalty
            if is_vertical:
                pts += 3.0
            if is_competitor:
                pts = max(0.0, pts - 12.0)

            pts = min(24.0, max(0.0, pts))

            results[key] = {
                "answer": pts,
                "probabilities": {
                    "not_a_lead": 0.85 if is_competitor else (0.01 if pts >= 10 else 0.8),
                    "weak": 0.10 if is_competitor else (0.04 if pts >= 15 else 0.2),
                    "moderate": 0.04 if is_competitor else (0.15 if pts >= 15 else 0.5),
                    "strong": 0.01 if is_competitor else (0.40 if pts >= 15 else 0.1),
                    "ideal": 0.00 if is_competitor else (0.40 if pts >= 18 else 0.05),
                },
                "judge": "heuristic",
            }

        else:
            if qtype == "boolean":
                results[key] = {"answer": True, "probabilities": {"true": 0.5, "false": 0.5}, "judge": "heuristic"}
            elif qtype == "score":
                results[key] = {"answer": 10.0, "probabilities": {}, "judge": "heuristic"}
            else:
                opts = list(q.get("criteria", {}).keys()) if isinstance(q.get("criteria"), dict) else ["unknown"]
                results[key] = {"answer": opts[0], "probabilities": {o: 1.0 / len(opts) for o in opts}, "judge": "heuristic"}

    return results
