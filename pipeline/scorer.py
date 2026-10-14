"""
scorer.py — Laya scoring wrapper for FlowJoy lead-finder pipeline.

Public interface:
    judge(state, questions) -> answers dict

Calls convaiinnovations/laya via Vercel AI Gateway:
    POST https://ai-gateway.vercel.sh/v4/ai/evaluation-model
"""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

_EVAL_URL = "https://ai-gateway.vercel.sh/v4/ai/evaluation-model"
_MODEL_ID = "convaiinnovations/laya"


def judge(state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    return _call_laya(state, questions)


def _call_laya(state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("AI_GATEWAY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AI_GATEWAY_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "ai-model-id": _MODEL_ID,
        "ai-evaluation-model-specification-version": "4",
        "ai-gateway-protocol-version": "0.0.1",
        "Content-Type": "application/json",
    }
    body = {"state": state, "questions": questions}

    r = requests.post(_EVAL_URL, headers=headers, json=body, timeout=25)
    r.raise_for_status()
    data = r.json()

    for k in data:
        if isinstance(data[k], dict):
            data[k].setdefault("judge", "laya")
    return data

