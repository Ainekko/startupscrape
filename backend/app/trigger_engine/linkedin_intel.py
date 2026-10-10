"""
app/trigger_engine/linkedin_intel.py — LinkedIn Deep Intel for Tracked Accounts
==============================================================================
Gathers as much LinkedIn intel as possible for a Verve account — WITHOUT any LinkedIn
login, cookies or browser of ours. Every fetch goes through treg.to catalog providers,
which scrape on their own infrastructure, so the user's LinkedIn account is never at risk.

Pipeline per account (all spend capped by IntelBudget):
1. Resolve targets: company slug + founder profile URLs (cheap SERP fallback when missing)
2. Company posts + founder posts (parallel)
3. Comments on the most promising recent posts (parallel)
4. Comments the founders left on other people's posts (what they care about)
5. Analysis -> IntelSignal[], EngagedPerson[], topics, urgency, summary
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.trigger_engine.linkedin_normalize import (
    company_url_from_slug,
    extract_company_slug,
    extract_post_urn,
    extract_profile_handle,
    find_rows,
    normalize_comment,
    normalize_post,
    parse_datetime,
    profile_url_from_handle,
)
from app.trigger_engine.models import (
    EngagedPerson,
    FounderActivity,
    IntelSignal,
    LinkedInComment,
    LinkedInIntelReport,
    LinkedInIntelSnapshot,
    LinkedInPost,
)
from app.trigger_engine.treg_client import TregClient

logger = logging.getLogger(__name__)


# ── treg endpoints: (endpoint_id, method, per-call USD cap) ──────────────────
# The cap is sent as X-Treg-Route-Max-Cost and reserved from the account budget
# before the call; the actual charge (X-Treg-Cost-Micro) is settled afterwards.
ENDPOINTS: dict[str, tuple[str, str, float]] = {
    "company_posts": ("harvestapi.linkedin.company.posts", "GET", 0.005),
    "user_posts": ("treg.linkedin.user.posts", "POST", 0.006),
    "post_comments": ("treg.linkedin.post.comments", "POST", 0.006),
    "user_comments": ("harvestapi.linkedin.user.comments", "GET", 0.005),
    "serp": ("treg.google.serp.organic", "POST", 0.002),
}

KIND_TO_TRIGGER: dict[str, str] = {
    "hiring": "gtm_hiring",
    "funding": "funding",
    "launch": "product_launch",
    "gtm_pain": "social_discussion",
    "milestone": "founder_signal",
    "event": "founder_signal",
    "comment_intent": "social_discussion",
    "notable_engager": "founder_signal",
    "founder_engagement": "founder_signal",
}

KIND_LABELS: dict[str, str] = {
    "hiring": "hiring",
    "funding": "funding",
    "launch": "a launch",
    "gtm_pain": "GTM / outbound",
    "milestone": "a milestone",
    "event": "an event",
}

# ── Classification patterns ──────────────────────────────────────────────────

POST_SIGNAL_PATTERNS: dict[str, list[str]] = {
    "hiring": [
        r"\bwe(?:'| a)?re hiring\b", r"\bnow hiring\b", r"\bjoin (?:our|the) team\b", r"#hiring\b",
        r"\bopen roles?\b", r"\bwe(?:'re| are) looking for (?:an?|our)\b",
        r"\bfirst (?:sales|gtm|marketing|sdr|bdr|ae) hire\b", r"\bhiring (?:an?|our|for)\b",
    ],
    "funding": [
        r"\braised\b", r"\bseed round\b", r"\bpre-seed\b", r"\bseries [abc]\b", r"\bfunding round\b",
        r"\bbacked by\b", r"\$\d+(?:\.\d+)?\s?(?:m|mm|million)\b",
    ],
    "launch": [
        r"\blaunch(?:ed|ing)?\b", r"\bintroducing\b", r"\bnow live\b", r"\bjust shipped\b",
        r"\bproduct hunt\b", r"\bannouncing\b", r"\bgenerally available\b", r"\bpublic beta\b",
    ],
    "gtm_pain": [
        r"\boutbound\b", r"\bcold (?:email|outreach)\b", r"\blead gen(?:eration)?\b", r"\bpipeline\b",
        r"\bprospecting\b", r"\bfounder[- ]led sales\b",
        r"\b(?:hubspot|apollo|clay|salesforce|instantly|smartlead|lemlist)\b",
        r"\bsdrs?\b", r"\bgo[- ]to[- ]market\b", r"\bgtm\b",
    ],
    "milestone": [
        r"\b\d+\s?k?\+? (?:customers|users)\b", r"\barr\b", r"\bmilestone\b", r"\bprofitable\b",
        r"\bnew customer\b", r"\bpartnership\b",
    ],
    "event": [
        r"\bwebinar\b", r"\bconference\b", r"\bsummit\b", r"\bdemo day\b", r"\bspeaking at\b",
        r"\bjoin us at\b", r"\bbooth\b",
    ],
}

COMMENT_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("buying_intent", [
        r"\binterested\b", r"\bhow much\b", r"\bpricing\b", r"\bdemo\b", r"\bsign me up\b",
        r"\bwaitlist\b", r"\bearly access\b", r"\bcan i (?:get|try)\b", r"\bwould love to (?:try|test|see)\b",
        r"\bdm(?:ed)? (?:you|me)\b", r"\bsent you a dm\b", r"\bhow do i (?:get|start|sign)\b",
        r"\bwhere can i\b",
    ]),
    ("pain", [
        r"\bstruggl", r"\bpain\b", r"\bfrustrat", r"\bhard to\b", r"\bwe (?:also )?need\b",
        r"\bbroken\b", r"\bmanual(?:ly)?\b", r"\bwast(?:e|ing)\b", r"\bbottleneck\b",
    ]),
    ("question", [r"\?\s*$", r"^(?:how|what|why|does|is|can|will)\b"]),
    ("praise", [
        r"\bcongrat", r"\bamazing\b", r"\bgreat work\b", r"\blove (?:this|it)\b", r"\bawesome\b",
        r"\bwell deserved\b", "\U0001f389", "\U0001f525", "\U0001f44f",
    ]),
]

ROLE_PATTERNS: list[tuple[str, list[str]]] = [
    ("investor", [
        r"\binvestor\b", r"\bventures?\b", r"\bvc\b", r"\bgeneral partner\b", r"\bpartner at\b",
        r"\bangel\b", r"\bprincipal at\b",
    ]),
    ("sales_leader", [
        r"\bhead of (?:sales|growth|revenue|gtm)\b", r"\bvp,? (?:of )?(?:sales|revenue|growth)\b",
        r"\bcro\b", r"\bchief revenue\b", r"\bdirector of sales\b", r"\bsales director\b",
    ]),
    ("founder", [r"\bco-?founder\b", r"\bfounder\b", r"\bceo\b"]),
    ("sales_rep", [
        r"\baccount executive\b", r"\bsdr\b", r"\bbdr\b", r"\bsales development\b",
        r"\baccount manager\b", r"\bbusiness development\b",
    ]),
    ("recruiter", [r"\brecruit", r"\btalent acquisition\b", r"\bpeople ops\b"]),
    ("engineer", [r"\bengineer\b", r"\bdeveloper\b", r"\bcto\b"]),
]

ROLE_PRIORITY = {"investor": 0, "sales_leader": 1, "founder": 2, "sales_rep": 3, "recruiter": 4, "engineer": 5, "other": 6}

_STOPWORDS = set("""
about above after again against because been before being below between could doing during
every further having here hers herself himself itself just more most other ourselves really
should their theirs themselves there these they this those through under until very what when
where which while whom would your yours yourself yourselves with from that have will into than
them then were also only over some such like make made many much need know think thank thanks
today week year years people company team great love excited proud share sharing happy linkedin
https http www work working first last next back time world
""".split())


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def classify_post_text(text: str) -> list[str]:
    """Return the signal kinds a post's text matches (ordered by POST_SIGNAL_PATTERNS)."""
    if not text:
        return []
    return [kind for kind, pats in POST_SIGNAL_PATTERNS.items() if _matches(pats, text)]


def classify_comment_intent(text: str) -> Optional[str]:
    if not text:
        return None
    for intent, pats in COMMENT_INTENT_PATTERNS:
        if _matches(pats, text.strip()):
            return intent
    return None


def classify_role(headline: Optional[str]) -> str:
    if not headline:
        return "other"
    for role, pats in ROLE_PATTERNS:
        if _matches(pats, headline):
            return role
    return "other"


def extract_topics(texts: list[str], top: int = 8) -> list[str]:
    """Cheap topic extraction: hashtags (weighted) + frequent non-stopword terms."""
    counter: Counter[str] = Counter()
    for t in texts:
        if not t:
            continue
        for tag in re.findall(r"#(\w{3,40})", t):
            counter[f"#{tag.lower()}"] += 3
        for word in re.findall(r"[A-Za-z][A-Za-z\-]{4,}", t):
            w = word.lower()
            if w not in _STOPWORDS:
                counter[w] += 1
    return [w for w, c in counter.most_common(top * 2) if c >= 2][:top]


def _days_ago(iso: Optional[str], now: datetime) -> Optional[int]:
    dt = parse_datetime(iso, now) if iso else None
    if not dt:
        return None
    return max(0, (now - dt).days)


def _confidence_for_recency(days: Optional[int]) -> float:
    if days is None:
        return 0.6
    if days <= 14:
        return 0.9
    if days <= 45:
        return 0.8
    return 0.65


def _snippet(text: str, n: int = 90) -> str:
    clean = " ".join((text or "").split())
    return clean if len(clean) <= n else clean[: n - 1].rstrip() + "…"


def _lookback_to_harvest_window(days: int, allowed: tuple[str, ...]) -> str:
    table = [(1, "24h"), (7, "week"), (30, "month"), (90, "3months"), (180, "6months"), (365, "year")]
    for limit, label in table:
        if days <= limit and label in allowed:
            return label
    return allowed[-1]


# ── Budget ───────────────────────────────────────────────────────────────────

class IntelBudget:
    """Reserve-then-settle budget so parallel calls can never overshoot the cap."""

    def __init__(self, max_usd: float):
        self.max_usd = max_usd
        self.spent = 0.0
        self.reserved = 0.0
        self.exhausted = False

    def reserve(self, amount: float) -> bool:
        if self.spent + self.reserved + amount > self.max_usd + 1e-9:
            self.exhausted = True
            return False
        self.reserved += amount
        return True

    def settle(self, reserved: float, actual: float) -> None:
        self.reserved = max(0.0, self.reserved - reserved)
        self.spent += max(0.0, actual)


@dataclass
class IntelOptions:
    max_cost_usd: float = 0.06
    lookback_days: int = 90
    max_posts_for_comments: int = 3
    comments_per_post: int = 25
    max_founders: int = 2
    include_founder_comments: bool = True


@dataclass
class _Ctx:
    budget: IntelBudget
    now: datetime
    calls: int = 0
    sources: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)


@dataclass
class FounderTarget:
    name: Optional[str]
    profile_url: str
    handle: str


# ── Service ──────────────────────────────────────────────────────────────────

class LinkedInIntelService:
    def __init__(self, treg_client: Optional[TregClient] = None):
        self.treg = treg_client or TregClient()

    # -- low-level budgeted call ------------------------------------------------
    async def _call(
        self,
        ctx: _Ctx,
        kind: str,
        *,
        json_body: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> Optional[Any]:
        endpoint_id, method, cap = ENDPOINTS[kind]
        if not ctx.budget.reserve(cap):
            ctx.errors.append(f"{kind}: skipped (budget exhausted)")
            return None
        try:
            resp = await self.treg.call(
                endpoint_id,
                method=method,
                json=json_body,
                params=params,
                max_cost=cap,
            )
        except Exception as exc:  # defensive: client already catches, fakes may not
            resp = {"success": False, "error": str(exc), "cost_usd": 0.0}
        ctx.budget.settle(cap, float(resp.get("cost_usd") or 0.0))
        ctx.calls += 1
        if resp.get("success"):
            ctx.sources.add(endpoint_id)
            return resp.get("data")
        status = resp.get("status_code")
        ctx.errors.append(f"{kind}: {status if status is not None else 'error'} {str(resp.get('error', ''))[:120]}".strip())
        return None

    # -- target resolution ------------------------------------------------------
    @staticmethod
    def founder_targets_from_account(account: dict[str, Any], extra_urls: Optional[list[str]] = None) -> list[FounderTarget]:
        candidates: list[tuple[Optional[str], Optional[str]]] = []
        for url in extra_urls or []:
            candidates.append((None, url))
        candidates.append((account.get("founder_name"), account.get("founder_linkedin")))
        founders = account.get("founders") or []
        if isinstance(founders, list):
            for f in founders:
                if isinstance(f, dict):
                    url = f.get("linkedin_url") or f.get("linkedin") or f.get("linkedinUrl") or f.get("url")
                    candidates.append((f.get("name") or f.get("full_name"), url))

        targets: list[FounderTarget] = []
        seen: set[str] = set()
        for name, url in candidates:
            handle = extract_profile_handle(url) if url else None
            if not handle:
                continue
            key = handle.lower()
            if key in seen:
                # Fill a missing name on an earlier duplicate
                for t in targets:
                    if t.handle.lower() == key and not t.name and name:
                        t.name = name
                continue
            seen.add(key)
            targets.append(FounderTarget(name=name, profile_url=profile_url_from_handle(handle) or url, handle=handle))
        return targets

    @staticmethod
    def _serp_rows(data: Any) -> list[dict[str, Any]]:
        return find_rows(data, preferred=("organic_results", "results", "organic"))

    async def _resolve_company_slug(self, ctx: _Ctx, company_name: str) -> Optional[str]:
        q = f'site:linkedin.com/company "{company_name}"'
        data = await self._call(ctx, "serp", json_body={"q": q})
        if not data:
            return None
        tokens = [t for t in re.findall(r"[a-z0-9]+", company_name.lower()) if len(t) >= 3]
        for r in self._serp_rows(data)[:6]:
            url = r.get("link") or r.get("url") or ""
            slug = extract_company_slug(url) if "/company/" in url else None
            if not slug:
                continue
            hay = f"{r.get('title', '')} {slug}".lower()
            if not tokens or any(t in hay for t in tokens):
                return slug
        return None

    async def _resolve_founders_via_serp(self, ctx: _Ctx, company_name: str, limit: int) -> list[FounderTarget]:
        q = f'site:linkedin.com/in/ "{company_name}" (founder OR "co-founder" OR ceo)'
        data = await self._call(ctx, "serp", json_body={"q": q})
        if not data:
            return []
        out: list[FounderTarget] = []
        seen: set[str] = set()
        for r in self._serp_rows(data)[:8]:
            url = r.get("link") or r.get("url") or ""
            handle = extract_profile_handle(url) if "linkedin.com/in/" in url else None
            if not handle or handle.lower() in seen:
                continue
            title = str(r.get("title", ""))
            text = f"{title} {r.get('snippet', '')}".lower()
            if not re.search(r"\b(co-?founder|founder|ceo)\b", text):
                continue
            seen.add(handle.lower())
            name = re.split(r"\s[-–|]\s", title)[0].strip() or None
            out.append(FounderTarget(name=name, profile_url=profile_url_from_handle(handle) or url, handle=handle))
            if len(out) >= limit:
                break
        return out

    # -- fetchers -----------------------------------------------------------------
    async def _fetch_company_posts(self, ctx: _Ctx, slug: str, company_name: str, opts: IntelOptions) -> list[LinkedInPost]:
        params = {
            "companyUniversalName": slug,
            "page": 1,
            "scrapePostedLimit": _lookback_to_harvest_window(
                opts.lookback_days, ("24h", "week", "month", "3months", "6months", "year")
            ),
        }
        data = await self._call(ctx, "company_posts", params=params)
        if data is None:
            return []
        posts = []
        for row in find_rows(data, preferred=("elements", "posts")):
            p = normalize_post(row, source=ENDPOINTS["company_posts"][0], owner_type="company", owner_name=company_name, now=ctx.now)
            if p:
                posts.append(p)
        return posts

    async def _fetch_founder_posts(self, ctx: _Ctx, founder: FounderTarget) -> list[LinkedInPost]:
        data = await self._call(ctx, "user_posts", json_body={"linkedin_url": founder.profile_url, "limit": 10})
        if data is None:
            return []
        posts = []
        owner = founder.name or founder.handle
        for row in find_rows(data, preferred=("posts",)):
            p = normalize_post(row, source=ENDPOINTS["user_posts"][0], owner_type="founder", owner_name=owner, now=ctx.now)
            if p:
                posts.append(p)
        return posts

    async def _fetch_post_comments(self, ctx: _Ctx, post: LinkedInPost, limit: int) -> list[LinkedInComment]:
        urn = post.urn or extract_post_urn(post.url)
        if not urn:
            return []
        data = await self._call(ctx, "post_comments", json_body={"post_urn": urn, "limit": limit})
        if data is None:
            return []
        comments = []
        for row in find_rows(data, preferred=("comments",)):
            c = normalize_comment(row, source=ENDPOINTS["post_comments"][0], post_url=post.url, post_urn=urn, now=ctx.now)
            if c:
                c.post_text = c.post_text or _snippet(post.text, 300)
                c.post_author_name = c.post_author_name or post.author_name or post.owner_name
                comments.append(c)
        return comments[:limit]

    async def _fetch_founder_comments(self, ctx: _Ctx, founder: FounderTarget, opts: IntelOptions) -> list[LinkedInComment]:
        params = {
            "profile": founder.profile_url,
            "postedLimit": _lookback_to_harvest_window(min(opts.lookback_days, 30), ("24h", "week", "month")),
            "page": 1,
        }
        data = await self._call(ctx, "user_comments", params=params)
        if data is None:
            return []
        comments = []
        for row in find_rows(data, preferred=("elements", "comments")):
            c = normalize_comment(row, source=ENDPOINTS["user_comments"][0], now=ctx.now)
            if c:
                c.author_name = c.author_name or founder.name
                c.author_url = founder.profile_url
                comments.append(c)
        return comments

    # -- selection ------------------------------------------------------------------
    @staticmethod
    def _dedupe_posts(posts: list[LinkedInPost]) -> list[LinkedInPost]:
        seen: set[str] = set()
        out = []
        for p in posts:
            key = p.urn or p.url or _snippet(p.text, 60)
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
        return out

    @staticmethod
    def _within_lookback(post: LinkedInPost, now: datetime, lookback_days: int) -> bool:
        days = _days_ago(post.posted_at, now)
        return days is None or days <= lookback_days

    @staticmethod
    def _comment_priority(post: LinkedInPost, now: datetime) -> float:
        days = _days_ago(post.posted_at, now)
        recency = 0.0 if days is None else max(0.0, 30.0 - days)
        signal_bonus = 15.0 if post.signal_kinds else 0.0
        return post.comments * 3.0 + post.likes * 0.5 + recency + signal_bonus

    def _pick_posts_for_comments(self, posts: list[LinkedInPost], now: datetime, n: int) -> list[LinkedInPost]:
        if n <= 0:
            return []
        eligible = [p for p in posts if (p.urn or extract_post_urn(p.url)) and not p.is_repost]
        any_counts = any(p.comments > 0 for p in eligible)
        if any_counts:
            eligible = [p for p in eligible if p.comments > 0]
        eligible.sort(key=lambda p: self._comment_priority(p, now), reverse=True)
        return eligible[:n]

    # -- analysis ---------------------------------------------------------------------
    def analyze(
        self,
        report: LinkedInIntelReport,
        founder_targets: list[FounderTarget],
        now: datetime,
    ) -> LinkedInIntelReport:
        signals: list[IntelSignal] = []
        founder_handles = {t.handle.lower() for t in founder_targets}
        founder_names = {(t.name or "").lower() for t in founder_targets if t.name}

        # 1. Post signals (max 2 per kind, newest first)
        all_posts = sorted(
            report.company_posts + report.founder_posts,
            key=lambda p: parse_datetime(p.posted_at, now) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        per_kind: Counter[str] = Counter()
        for p in all_posts:
            for kind in p.signal_kinds:
                if per_kind[kind] >= 2:
                    continue
                per_kind[kind] += 1
                days = _days_ago(p.posted_at, now)
                who = p.author_name or p.owner_name or report.company_name
                signals.append(IntelSignal(
                    kind=kind,
                    trigger_type=KIND_TO_TRIGGER[kind],
                    headline=f"{who} posted about {KIND_LABELS.get(kind, kind)}: {_snippet(p.text, 70)}",
                    evidence=_snippet(p.text, 280),
                    source_url=p.url,
                    posted_at=p.posted_at,
                    actor=who,
                    confidence=_confidence_for_recency(days),
                    recency_days=days,
                ))

        # 2. Comments on their posts: intent + commenter roles
        for c in report.post_comments:
            c.intent = classify_comment_intent(c.text)
            c.author_role = classify_role(c.author_headline)

        def _is_insider(c: LinkedInComment) -> bool:
            handle = extract_profile_handle(c.author_url) if c.author_url else None
            if handle and handle.lower() in founder_handles:
                return True
            name = (c.author_name or "").lower()
            return bool(name) and (name in founder_names or name == report.company_name.lower())

        outsiders = [c for c in report.post_comments if not _is_insider(c)]

        for intent, label in (("buying_intent", "asked about pricing / demo / access"), ("pain", "described a pain")):
            hits = [c for c in outsiders if c.intent == intent]
            if hits:
                newest = max((c.posted_at for c in hits if c.posted_at), default=None)
                days = _days_ago(newest, now)
                unique_people = len({(c.author_url or c.author_name or c.text).lower() for c in hits})
                signals.append(IntelSignal(
                    kind="comment_intent",
                    trigger_type=KIND_TO_TRIGGER["comment_intent"],
                    headline=f"{unique_people} commenter(s) {label} on {report.company_name}'s LinkedIn posts",
                    evidence=" | ".join(f"{c.author_name or 'Someone'}: {_snippet(c.text, 90)}" for c in hits[:3]),
                    source_url=hits[0].post_url,
                    posted_at=newest,
                    actor=hits[0].author_name,
                    confidence=0.85 if intent == "buying_intent" else 0.75,
                    recency_days=days,
                ))

        notable = [c for c in outsiders if c.author_role in ("investor", "sales_leader")]
        seen_notable: set[str] = set()
        for c in notable:
            key = (c.author_url or c.author_name or "").lower()
            if not key or key in seen_notable or len(seen_notable) >= 3:
                continue
            seen_notable.add(key)
            role_label = "Investor" if c.author_role == "investor" else "Sales leader"
            signals.append(IntelSignal(
                kind="notable_engager",
                trigger_type=KIND_TO_TRIGGER["notable_engager"],
                headline=f"{role_label} {c.author_name or ''} ({_snippet(c.author_headline or '', 60)}) engaged with {report.company_name}'s post".replace("  ", " "),
                evidence=_snippet(c.text, 200),
                source_url=c.post_url,
                posted_at=c.posted_at,
                actor=c.author_name,
                confidence=0.7,
                recency_days=_days_ago(c.posted_at, now),
            ))

        # 3. Founder comments elsewhere -> what they care about right now
        for c in report.founder_comments:
            c.intent = classify_comment_intent(c.text)
            combined = f"{c.text} {c.post_text or ''}"
            kinds = classify_post_text(combined)
            if "gtm_pain" in kinds or "hiring" in kinds:
                days = _days_ago(c.posted_at, now)
                topic = "GTM / outbound" if "gtm_pain" in kinds else "hiring"
                signals.append(IntelSignal(
                    kind="founder_engagement",
                    trigger_type=KIND_TO_TRIGGER["founder_engagement"],
                    headline=f"{c.author_name or 'Founder'} commented on a post about {topic}"
                             + (f" by {c.post_author_name}" if c.post_author_name else ""),
                    evidence=f"Comment: {_snippet(c.text, 160)}" + (f" — Post: {_snippet(c.post_text, 120)}" if c.post_text else ""),
                    source_url=c.comment_url or c.post_url,
                    posted_at=c.posted_at,
                    actor=c.author_name,
                    confidence=_confidence_for_recency(days),
                    recency_days=days,
                ))

        signals.sort(key=lambda s: (s.confidence, -(s.recency_days if s.recency_days is not None else 999)), reverse=True)
        report.signals = signals

        # 4. Engaged people (warm intros + lookalike prospects)
        people: dict[str, EngagedPerson] = {}
        for c in outsiders:
            if not c.author_name:
                continue
            key = (c.author_url or c.author_name).lower()
            person = people.get(key)
            if person is None:
                person = EngagedPerson(
                    name=c.author_name,
                    headline=c.author_headline,
                    url=c.author_url,
                    role=c.author_role or "other",
                    sample_comment=_snippet(c.text, 160),
                )
                people[key] = person
            person.comment_count += 1
            if c.intent and c.intent not in person.intents:
                person.intents.append(c.intent)
        report.engaged_people = sorted(
            people.values(),
            key=lambda p: (ROLE_PRIORITY.get(p.role, 9), -("buying_intent" in p.intents), -p.comment_count),
        )[:25]

        # 5. Founder activity + topics
        founders_out: list[FounderActivity] = []
        for t in founder_targets:
            owner_key = t.name or t.handle
            f_posts = [p for p in report.founder_posts if p.owner_name == owner_key]
            f_comments = [c for c in report.founder_comments if c.author_url and (extract_profile_handle(c.author_url) or "").lower() == t.handle.lower()]
            stamps = [parse_datetime(x.posted_at, now) for x in [*f_posts, *f_comments] if x.posted_at]
            stamps = [s for s in stamps if s]
            founders_out.append(FounderActivity(
                name=t.name,
                profile_url=t.profile_url,
                posts_found=len(f_posts),
                comments_made_found=len(f_comments),
                last_active_at=max(stamps).isoformat() if stamps else None,
                top_topics=extract_topics([p.text for p in f_posts] + [c.text for c in f_comments], top=5),
            ))
        report.founders = founders_out
        report.topics = extract_topics(
            [p.text for p in report.company_posts + report.founder_posts] + [c.text for c in report.founder_comments]
        )
        company_stamps = [parse_datetime(p.posted_at, now) for p in report.company_posts if p.posted_at]
        company_stamps = [s for s in company_stamps if s]
        report.last_company_post_at = max(company_stamps).isoformat() if company_stamps else None

        # 6. Urgency + summary
        report.urgency_score = self._score(report, now)
        report.summary = self._summarize(report, now)
        return report

    @staticmethod
    def _score(report: LinkedInIntelReport, now: datetime) -> int:
        weights = {
            "hiring": 4, "funding": 4, "launch": 3, "gtm_pain": 3, "comment_intent": 2,
            "founder_engagement": 2, "notable_engager": 1, "milestone": 1, "event": 1,
        }
        score = 0
        counted: set[str] = set()
        for s in report.signals:
            if s.kind in counted:
                continue
            counted.add(s.kind)
            w = weights.get(s.kind, 1)
            if s.recency_days is not None and s.recency_days > 60:
                w = max(1, w // 2)
            score += w
        latest = [d for d in (_days_ago(p.posted_at, now) for p in report.company_posts + report.founder_posts) if d is not None]
        if latest and min(latest) <= 14:
            score += 1
        if not report.signals:
            return 3 if (report.company_posts or report.founder_posts) else 1
        return max(1, min(10, score))

    @staticmethod
    def _summarize(report: LinkedInIntelReport, now: datetime) -> str:
        parts: list[str] = []
        kinds = []
        for s in report.signals:
            if s.kind not in kinds:
                kinds.append(s.kind)
        if kinds:
            parts.append(f"{len(report.signals)} LinkedIn signal(s): {', '.join(k.replace('_', ' ') for k in kinds[:4])}")
        else:
            parts.append("No timing signals on LinkedIn")
        for f in report.founders:
            days = _days_ago(f.last_active_at, now)
            if days is not None:
                parts.append(f"{f.name or 'founder'} active {days}d ago")
        buyers = sum(1 for p in report.engaged_people if "buying_intent" in p.intents)
        if buyers:
            parts.append(f"{buyers} buying-intent commenter(s)")
        if report.budget_exhausted:
            parts.append("partial (budget cap hit)")
        return f"{report.company_name}: " + " · ".join(parts)

    # -- main entry -------------------------------------------------------------------
    async def gather(
        self,
        account: dict[str, Any],
        options: Optional[IntelOptions] = None,
        extra_founder_urls: Optional[list[str]] = None,
        now: Optional[datetime] = None,
    ) -> LinkedInIntelReport:
        opts = options or IntelOptions()
        now = now or datetime.now(timezone.utc)
        ctx = _Ctx(budget=IntelBudget(opts.max_cost_usd), now=now)

        company_name = account.get("company_name") or account.get("name") or "Unknown"
        lead_id = str(account.get("id") or f"acc_{re.sub(r'[^a-z0-9]+', '_', company_name.lower()).strip('_')}")
        report = LinkedInIntelReport(lead_id=lead_id, company_name=company_name)

        # 1. Resolve targets
        slug = extract_company_slug(account.get("company_linkedin_url") or account.get("linkedin_url"))
        founder_targets = self.founder_targets_from_account(account, extra_founder_urls)[: opts.max_founders]

        resolvers = []
        if not slug:
            resolvers.append(self._resolve_company_slug(ctx, company_name))
        if not founder_targets and opts.max_founders > 0:
            resolvers.append(self._resolve_founders_via_serp(ctx, company_name, opts.max_founders))
        if resolvers:
            results = await asyncio.gather(*resolvers)
            idx = 0
            if not slug:
                slug = results[idx]
                idx += 1
            if not founder_targets and opts.max_founders > 0:
                founder_targets = results[idx]

        report.company_linkedin_url = company_url_from_slug(slug) if slug else None

        # 2. Posts (parallel)
        post_jobs = []
        if slug:
            post_jobs.append(self._fetch_company_posts(ctx, slug, company_name, opts))
        for f in founder_targets:
            post_jobs.append(self._fetch_founder_posts(ctx, f))
        post_results = await asyncio.gather(*post_jobs) if post_jobs else []

        offset = 0
        if slug:
            report.company_posts = post_results[0]
            offset = 1
        founder_posts: list[LinkedInPost] = []
        for res in post_results[offset:]:
            founder_posts.extend(res)

        report.company_posts = [p for p in self._dedupe_posts(report.company_posts) if self._within_lookback(p, now, opts.lookback_days)]
        report.founder_posts = [p for p in self._dedupe_posts(founder_posts) if self._within_lookback(p, now, opts.lookback_days)]
        for p in report.company_posts + report.founder_posts:
            p.signal_kinds = classify_post_text(p.text)

        # 3. Comments on top posts + 4. founder comments elsewhere (parallel)
        to_comment = self._pick_posts_for_comments(report.company_posts + report.founder_posts, now, opts.max_posts_for_comments)
        comment_jobs = [self._fetch_post_comments(ctx, p, opts.comments_per_post) for p in to_comment]
        founder_comment_jobs = (
            [self._fetch_founder_comments(ctx, f, opts) for f in founder_targets]
            if opts.include_founder_comments else []
        )
        results = await asyncio.gather(*comment_jobs, *founder_comment_jobs) if (comment_jobs or founder_comment_jobs) else []
        for res in results[: len(comment_jobs)]:
            report.post_comments.extend(res)
        for res in results[len(comment_jobs):]:
            report.founder_comments.extend(
                c for c in res
                if (_days_ago(c.posted_at, now) is None or _days_ago(c.posted_at, now) <= opts.lookback_days)
            )

        # 5. Analysis
        report.cost_usd = round(ctx.budget.spent, 6)
        report.calls_made = ctx.calls
        report.budget_exhausted = ctx.budget.exhausted
        report.sources_used = sorted(ctx.sources)
        report.errors = ctx.errors
        self.analyze(report, founder_targets, now)
        return report


# ── Persistence helpers ──────────────────────────────────────────────────────

def snapshot_from_report(report: LinkedInIntelReport) -> LinkedInIntelSnapshot:
    return LinkedInIntelSnapshot(
        id=f"liintel_{uuid.uuid4().hex[:10]}",
        lead_id=report.lead_id,
        company_name=report.company_name,
        signals_count=len(report.signals),
        posts_count=len(report.company_posts) + len(report.founder_posts),
        comments_count=len(report.post_comments) + len(report.founder_comments),
        cost_usd=report.cost_usd,
        report_json=report.model_dump_json(),
        created_at=report.generated_at,
    )


def report_from_snapshot(snapshot: LinkedInIntelSnapshot) -> LinkedInIntelReport:
    report = LinkedInIntelReport.model_validate(json.loads(snapshot.report_json))
    report.cached = True
    return report


async def save_snapshot(session: Any, report: LinkedInIntelReport, commit: bool = True) -> LinkedInIntelSnapshot:
    snap = snapshot_from_report(report)
    session.add(snap)
    if commit:
        await session.commit()
    return snap


async def load_latest_snapshot(
    session: Any,
    lead_id: str,
    max_age_hours: Optional[float] = None,
) -> Optional[LinkedInIntelReport]:
    from sqlalchemy import desc
    from sqlmodel import select

    query = (
        select(LinkedInIntelSnapshot)
        .where(LinkedInIntelSnapshot.lead_id == lead_id)
        .order_by(desc(LinkedInIntelSnapshot.created_at))
        .limit(1)
    )
    result = await session.execute(query)
    snap = result.scalars().first()
    if not snap:
        return None
    if max_age_hours is not None:
        created = snap.created_at if snap.created_at.tzinfo else snap.created_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created > timedelta(hours=max_age_hours):
            return None
    return report_from_snapshot(snap)
