"""Shared offline fixtures for LinkedIn intel tests: canned provider rows + a fake treg client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional, Union

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

COMPANY_POSTS_EP = "harvestapi.linkedin.company.posts"
USER_POSTS_EP = "treg.linkedin.user.posts"
POST_COMMENTS_EP = "treg.linkedin.post.comments"
USER_COMMENTS_EP = "harvestapi.linkedin.user.comments"
SERP_EP = "treg.google.serp.organic"


def _ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


# HarvestAPI-style company posts
COMPANY_POSTS = {
    "status": "ok",
    "elements": [
        {
            "id": "7380000000000000001",
            "linkedinUrl": "https://www.linkedin.com/posts/acme-ai_hiring-activity-7380000000000000001-abcd",
            "content": "We're hiring our first SDR to scale outbound! Join our team.",
            "postedAt": {"timestamp": _ms("2026-10-05T10:00:00Z"), "date": "2026-10-05T10:00:00Z"},
            "engagement": {"likes": 40, "comments": 12, "shares": 3},
            "author": {"name": "Acme AI", "linkedinUrl": "https://www.linkedin.com/company/acme-ai"},
        },
        {
            "id": "7370000000000000002",
            "linkedinUrl": "https://www.linkedin.com/posts/acme-ai_launch-activity-7370000000000000002-efgh",
            "content": "Introducing Acme v2 - now live on Product Hunt",
            "postedAt": {"date": "2026-09-20T10:00:00Z"},
            "engagement": {"likes": 100, "comments": 30, "shares": 10},
            "author": {"name": "Acme AI"},
        },
        {
            "id": "7000000000000000003",
            "linkedinUrl": "https://www.linkedin.com/posts/acme-ai_old-activity-7000000000000000003-zzzz",
            "content": "We raised a $3M seed round",
            "postedAt": {"date": "2025-01-01T00:00:00Z"},
            "engagement": {"likes": 5, "comments": 1},
        },
    ],
}

# treg routed user posts (Fetchin-style rows under output.posts)
FOUNDER_POSTS = {
    "output": {
        "posts": [
            {
                "urn": "urn:li:activity:7381111111111111111",
                "url": "https://www.linkedin.com/feed/update/urn:li:activity:7381111111111111111",
                "text": "Founder-led sales is exhausting. Our pipeline needs work. #gtm #outbound",
                "postedAt": "2026-10-08T09:00:00Z",
                "numLikes": 20,
                "numComments": 5,
                "author": {"firstName": "Jane", "lastName": "Doe", "publicIdentifier": "jane-doe"},
            }
        ],
        "has_more": False,
    },
    "raw": {},
    "_treg": {"served_by": "fetchinio"},
}

# treg routed post comments
POST_COMMENTS = {
    "output": {
        "comments": [
            {
                "text": "Interested! How much does it cost?",
                "author": {
                    "name": "Bob Buyer",
                    "headline": "Head of Sales at BigCo",
                    "linkedinUrl": "https://www.linkedin.com/in/bob-buyer",
                },
                "createdAt": "2026-10-06T12:00:00Z",
            },
            {
                "text": "Congrats team! \U0001f389",
                "author": {
                    "name": "Vera VC",
                    "headline": "Partner at Seed Ventures",
                    "linkedinUrl": "https://www.linkedin.com/in/vera-vc",
                },
                "createdAt": "2026-10-06T13:00:00Z",
            },
            {
                "text": "Thanks all!",
                "author": {
                    "name": "Jane Doe",
                    "headline": "Co-founder & CEO at Acme",
                    "linkedinUrl": "https://www.linkedin.com/in/jane-doe",
                },
                "createdAt": "2026-10-06T14:00:00Z",
            },
        ]
    }
}

# HarvestAPI-style comments a founder made elsewhere
FOUNDER_COMMENTS = {
    "elements": [
        {
            "commentary": "We're struggling with outbound too - Clay + Apollo is a mess.",
            "createdAt": "2026-10-07T08:00:00Z",
            "post": {
                "linkedinUrl": "https://www.linkedin.com/posts/sam-gtm_activity-7382222222222222222-qqqq",
                "content": "How do you build an outbound engine at seed stage?",
                "author": {"name": "Sam GTM"},
            },
        }
    ]
}

SERP_COMPANY = {
    "output": {
        "organic_results": [
            {"title": "Acme AI | LinkedIn", "link": "https://www.linkedin.com/company/acme-ai", "snippet": "Acme AI builds agents"},
        ]
    }
}

SERP_PEOPLE = {
    "output": {
        "organic_results": [
            {"title": "Jane Doe - Co-founder & CEO - Acme AI | LinkedIn", "link": "https://www.linkedin.com/in/jane-doe", "snippet": "Co-founder at Acme AI"},
            {"title": "Random Person - Engineer - Acme AI | LinkedIn", "link": "https://www.linkedin.com/in/random", "snippet": "Engineer"},
        ]
    }
}


def acme_account(**overrides: Any) -> dict[str, Any]:
    account = {
        "id": "lead_acme",
        "company_name": "Acme AI",
        "website": "https://acme.ai",
        "linkedin_url": "https://www.linkedin.com/company/acme-ai",
        "founder_name": "Jane Doe",
        "founder_linkedin": "https://www.linkedin.com/in/jane-doe/",
        "founders": [
            {"name": "Jane Doe", "linkedin_url": "https://linkedin.com/in/jane-doe"},
            {"name": "John Roe", "linkedin_url": "https://www.linkedin.com/in/john-roe"},
        ],
    }
    account.update(overrides)
    return account


def _serp(json: Optional[dict[str, Any]] = None, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    q = (json or {}).get("q", "")
    return SERP_COMPANY if "linkedin.com/company" in q else SERP_PEOPLE


def default_responses() -> dict[str, Any]:
    return {
        COMPANY_POSTS_EP: COMPANY_POSTS,
        USER_POSTS_EP: FOUNDER_POSTS,
        POST_COMMENTS_EP: POST_COMMENTS,
        USER_COMMENTS_EP: FOUNDER_COMMENTS,
        SERP_EP: _serp,
    }


Responder = Union[dict[str, Any], Callable[..., Optional[dict[str, Any]]], None]


class FakeTreg:
    """Drop-in for TregClient.call(); records every call, never touches the network."""

    def __init__(self, responses: Optional[dict[str, Responder]] = None, cost_usd: float = 0.002):
        self.responses = default_responses() if responses is None else responses
        self.cost_usd = cost_usd
        self.calls: list[dict[str, Any]] = []
        self.total_cost_usd = 0.0

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
        self.calls.append({"endpoint_id": endpoint_id, "method": method, "json": json, "params": params, "max_cost": max_cost})
        responder = self.responses.get(endpoint_id)
        data = responder(json=json, params=params) if callable(responder) else responder
        if data is None:
            return {"success": False, "status_code": 404, "error": "not found", "cost_usd": 0.0}
        self.total_cost_usd += self.cost_usd
        return {"success": True, "status_code": 200, "data": data, "cost_usd": self.cost_usd}

    async def call_endpoint(self, endpoint_id: str, payload: dict[str, Any], max_cost: Optional[float] = None, timeout: float = 15.0):
        return await self.call(endpoint_id, method="POST", json=payload, max_cost=max_cost)

    def calls_to(self, endpoint_id: str) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["endpoint_id"] == endpoint_id]

