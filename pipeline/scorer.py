"""
scorer.py — jev scoring wrapper for FlowJoy lead-finder pipeline.

Public interface:
    judge(state, questions) -> answers dict

If AI_GATEWAY_API_KEY is configured and active, calls jev via Vercel AI Gateway:
    POST https://ai-gateway.vercel.sh/v4/ai/evaluation-model
    Headers:
        Authorization: Bearer $AI_GATEWAY_API_KEY
        ai-model-id: typesafe-ai/jev
        ai-evaluation-model-specification-version: 4
        ai-gateway-protocol-version: 0.0.1
    Body:
        {"state": {...}, "questions": {...}}

Question Schema:
    boolean: {"type": "boolean", "instructions": "<str>"}
    choice:  {"type": "choice", "instructions": "<str>", "criteria": {"<option>": "<desc>", ...}}
    score:   {"type": "score", "instructions": "<str>", "criteria": [{"level": <int>, "description": "<desc>"}, ...]}

Fallback:
    If jev is unreachable, unverified (e.g. 403 customer_verification_required),
    or throws an error, scores deterministically via calibrated heuristics based on signals in state.
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


def judge(state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    """
    Score a lead using jev, falling back to calibrated heuristics if unavailable.
    """
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
    """
    Deterministic calibrated evaluator.
    Directly extracts signal evidence from state to evaluate fit.
    """
    results: dict[str, Any] = {}

    tags = [str(t).lower() for t in state.get("tags", [])]
    one_liner = str(state.get("one_liner", "")).lower()
    batch = str(state.get("batch", "")).lower()
    job_titles = [str(t).lower() for t in state.get("job_titles", [])]
    has_gtm_posting = bool(state.get("has_gtm_job_posting", False))

    b2b_keywords = [
        "b2b", "saas", "enterprise", "developer tools", "devtools", "infrastructure",
        "fintech", "proptech", "hrtech", "martech", "sales", "crm", "data", "analytics",
        "api", "workflow", "ai agent", "automation", "compliance", "cybersecurity"
    ]
    consumer_keywords = ["consumer", "social", "gaming", "dating", "d2c", "e-commerce", "b2c"]

    is_b2b_signal = any(k in tags or k in one_liner for k in b2b_keywords)
    is_consumer_signal = any(k in tags or k in one_liner for k in consumer_keywords)

    gtm_keywords = [
        "gtm engineer", "head of sales", "vp sales", "vp of sales",
        "revenue operations", "revops", "sales lead", "director of sales",
        "growth lead", "head of growth", "gtm lead", "growth engineer"
    ]
    has_gtm_hire = has_gtm_posting or any(any(k in t for k in gtm_keywords) for t in job_titles)

    recent_batches = ["w25", "s24", "w24", "f24", "s23", "w23", "2024", "2025", "2026"]
    is_recent = any(b in batch for b in recent_batches) or bool(batch and not any(y in batch for y in ["2015", "2016", "2017", "2018", "2019", "2020", "2021"]))

    for key, q in questions.items():
        qtype = q.get("type", "boolean")

        if key == "is_b2b" or ("b2b" in key.lower()):
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
            if is_recent:
                probs = {"seed": 0.65, "series_a": 0.25, "pre_seed": 0.05, "series_b_plus": 0.03, "unknown": 0.02}
                ans = "seed"
            else:
                probs = {"seed": 0.20, "series_a": 0.30, "series_b_plus": 0.40, "pre_seed": 0.05, "unknown": 0.05}
                ans = "series_a"
            active_probs = {opt: probs.get(opt, 1.0 / len(options)) for opt in options}
            total = sum(active_probs.values()) or 1.0
            active_probs = {k: round(v / total, 3) for k, v in active_probs.items()}
            results[key] = {"answer": ans if ans in options else options[0], "probabilities": active_probs, "judge": "heuristic"}

        elif key == "fit" or qtype == "score":
            pts = 0.0
            if is_recent:
                pts += 10.0
            if not has_gtm_hire:
                pts += 5.0
            if is_b2b_signal:
                pts += 5.0
            pts = min(20.0, max(0.0, pts))

            results[key] = {
                "answer": pts,
                "probabilities": {
                    "not_a_lead": 0.02 if pts >= 10 else 0.8,
                    "weak": 0.05 if pts >= 15 else 0.2,
                    "moderate": 0.15 if pts >= 15 else 0.5,
                    "strong": 0.40 if pts >= 15 else 0.1,
                    "ideal": 0.38 if pts >= 18 else 0.05,
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
