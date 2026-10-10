"""
app/trigger_engine/linkedin_normalize.py — Provider-agnostic LinkedIn Parsing Helpers
=====================================================================================
treg relays provider-native LinkedIn rows (Fetchin, HarvestAPI, AnyAPI, TikHub, ...).
Their shapes differ, so every row goes through these tolerant, pure functions.

Nothing here performs I/O — everything is unit-testable offline.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from urllib.parse import unquote, urlparse

from app.trigger_engine.models import LinkedInComment, LinkedInPost

# ── URL / URN helpers ────────────────────────────────────────────────────────

_COMPANY_RE = re.compile(r"linkedin\.com/(?:company|school|showcase)/([^/?#]+)", re.IGNORECASE)
_PROFILE_RE = re.compile(r"linkedin\.com/in/([^/?#]+)", re.IGNORECASE)
_URN_RE = re.compile(r"urn:li:(activity|ugcPost|share):(\d{10,25})", re.IGNORECASE)
_ACTIVITY_IN_URL_RE = re.compile(r"(?:activity|ugcPost|share)[-:](\d{10,25})", re.IGNORECASE)
_BARE_ID_RE = re.compile(r"^\d{15,25}$")


def extract_company_slug(url_or_slug: Optional[str]) -> Optional[str]:
    """'https://www.linkedin.com/company/acme-ai/about' -> 'acme-ai'. Bare slugs pass through."""
    if not url_or_slug:
        return None
    raw = str(url_or_slug).strip()
    m = _COMPANY_RE.search(raw)
    if m:
        return unquote(m.group(1)).strip().lower() or None
    if "/" not in raw and "." not in raw and " " not in raw:
        return raw.lower()
    return None


def extract_profile_handle(url_or_handle: Optional[str]) -> Optional[str]:
    """'https://www.linkedin.com/in/jane-doe-123/' -> 'jane-doe-123'. Bare handles pass through."""
    if not url_or_handle:
        return None
    raw = str(url_or_handle).strip()
    m = _PROFILE_RE.search(raw)
    if m:
        return unquote(m.group(1)).strip() or None
    if "/" not in raw and "." not in raw and " " not in raw:
        return raw
    return None


def profile_url_from_handle(handle: Optional[str]) -> Optional[str]:
    h = extract_profile_handle(handle)
    return f"https://www.linkedin.com/in/{h}" if h else None


def company_url_from_slug(slug: Optional[str]) -> Optional[str]:
    s = extract_company_slug(slug)
    return f"https://www.linkedin.com/company/{s}" if s else None


def extract_post_urn(value: Optional[str]) -> Optional[str]:
    """
    Accepts a post URL, an activity/ugcPost/share URN, or a bare numeric id.
    Returns a canonical URN like 'urn:li:activity:7508596155145043968'.
    """
    if not value:
        return None
    raw = str(value).strip()
    m = _URN_RE.search(raw)
    if m:
        kind = m.group(1)
        kind = "ugcPost" if kind.lower() == "ugcpost" else kind.lower()
        return f"urn:li:{kind}:{m.group(2)}"
    m = _ACTIVITY_IN_URL_RE.search(raw)
    if m:
        kind_match = re.search(r"(activity|ugcPost|share)[-:]\d", raw, re.IGNORECASE)
        kind = kind_match.group(1) if kind_match else "activity"
        kind = "ugcPost" if kind.lower() == "ugcpost" else kind.lower()
        return f"urn:li:{kind}:{m.group(1)}"
    if _BARE_ID_RE.match(raw):
        return f"urn:li:activity:{raw}"
    return None


def post_id_from_urn(urn: Optional[str]) -> Optional[str]:
    if not urn:
        return None
    m = _URN_RE.search(urn)
    return m.group(2) if m else None


def is_linkedin_url(url: Optional[str]) -> bool:
    if not url:
        return False
    try:
        host = urlparse(str(url)).netloc.lower()
    except ValueError:
        return False
    return host.endswith("linkedin.com")


# ── Date parsing ─────────────────────────────────────────────────────────────

_RELATIVE_RE = re.compile(r"^\s*(\d+)\s*(mo|m|h|d|w|y|yr|min|s)\b", re.IGNORECASE)


def parse_datetime(value: Any, now: Optional[datetime] = None) -> Optional[datetime]:
    """
    Parse timestamps from provider rows into aware UTC datetimes.
    Handles ISO strings, epoch seconds/ms (int or numeric str), LinkedIn relative
    labels ('3d', '2w', '1mo', '5h', '1y'), and nested dicts ({timestamp|date|time}).
    """
    if value is None or value == "":
        return None
    now = now or datetime.now(timezone.utc)

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, dict):
        for key in ("timestamp", "date", "time", "postedAt", "iso", "value"):
            if key in value:
                parsed = parse_datetime(value.get(key), now)
                if parsed:
                    return parsed
        return None

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        ts = float(value)
        if ts > 1e12:  # milliseconds
            ts /= 1000.0
        if ts <= 0:
            return None
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{9,14}(\.\d+)?", text):
        return parse_datetime(float(text), now)

    rel = _RELATIVE_RE.match(text)
    if rel and len(text) <= 12:
        n = int(rel.group(1))
        unit = rel.group(2).lower()
        delta = {
            "s": timedelta(seconds=n),
            "min": timedelta(minutes=n),
            "m": timedelta(minutes=n),
            "h": timedelta(hours=n),
            "d": timedelta(days=n),
            "w": timedelta(weeks=n),
            "mo": timedelta(days=30 * n),
            "y": timedelta(days=365 * n),
            "yr": timedelta(days=365 * n),
        }.get(unit)
        if delta is not None:
            return now - delta

    iso = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


# ── Envelope unwrapping ──────────────────────────────────────────────────────

_ROW_KEYS = (
    "posts", "comments", "elements", "items", "results", "data", "element",
    "activities", "updates", "feed", "list", "records", "output", "raw", "response",
)


def find_rows(payload: Any, preferred: Iterable[str] = (), max_depth: int = 4) -> list[dict[str, Any]]:
    """
    Locate the first list of dict rows inside an arbitrary provider/treg envelope.
    Tries `preferred` keys first (e.g. 'posts' for routed user posts), then common keys.
    """
    keys = tuple(preferred) + tuple(k for k in _ROW_KEYS if k not in preferred)

    def _walk(node: Any, depth: int) -> Optional[list[dict[str, Any]]]:
        if depth > max_depth or node is None:
            return None
        if isinstance(node, list):
            rows = [r for r in node if isinstance(r, dict)]
            return rows if rows else None
        if isinstance(node, dict):
            for k in keys:
                if k in node:
                    found = _walk(node[k], depth + 1)
                    if found:
                        return found
        return None

    return _walk(payload, 0) or []


# ── Field helpers ────────────────────────────────────────────────────────────

def _first(row: dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in row and row[k] not in (None, "", [], {}):
            return row[k]
    return None


def _to_int(value: Any) -> int:
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for k in ("count", "total", "value", "totalCount"):
            if k in value:
                return _to_int(value[k])
        return 0
    text = str(value).strip().lower().replace(",", "")
    m = re.match(r"^([\d.]+)\s*([km]?)$", text)
    if not m:
        return 0
    num = float(m.group(1))
    mult = {"k": 1_000, "m": 1_000_000}.get(m.group(2), 1)
    return int(num * mult)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for k in ("text", "value", "content", "commentary"):
            if k in value:
                return _text(value[k])
        return ""
    if isinstance(value, list):
        return " ".join(_text(v) for v in value).strip()
    return str(value).strip()


def _person(row: dict[str, Any], container_keys: Iterable[str]) -> dict[str, Optional[str]]:
    """Extract {name, headline, url} from a nested author/actor object or flat fields."""
    node: Any = _first(row, container_keys)
    if isinstance(node, list) and node:
        node = node[0]
    src = node if isinstance(node, dict) else {}

    name = _first(src, ("name", "fullName", "full_name", "authorName", "title"))
    if not name:
        first = _first(src, ("firstName", "first_name"))
        last = _first(src, ("lastName", "last_name"))
        name = " ".join(p for p in (first, last) if p) or None
    if isinstance(name, dict):
        name = _text(name)

    headline = _first(src, ("headline", "info", "occupation", "position", "description", "subtitle", "jobTitle"))
    url = _first(src, ("linkedinUrl", "linkedin_url", "url", "profileUrl", "profile_url", "navigationUrl"))
    if not url:
        handle = _first(src, ("publicIdentifier", "public_identifier", "universalName", "username"))
        if handle:
            url = profile_url_from_handle(str(handle))

    if not name:
        name = _first(row, ("authorName", "author_name", "commenterName", "actorName", "fullName", "name"))
    if not headline:
        headline = _first(row, ("authorHeadline", "author_headline", "commenterHeadline", "headline", "authorTitle"))
    if not url:
        url = _first(row, ("authorProfileUrl", "authorUrl", "author_url", "commenterProfileUrl", "profileUrl", "authorLinkedinUrl"))

    if not name and isinstance(node, str):
        name = node

    return {
        "name": _text(name) or None,
        "headline": _text(headline) or None,
        "url": str(url).strip() if url else None,
    }


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


# ── Row normalizers ──────────────────────────────────────────────────────────

def normalize_post(
    row: dict[str, Any],
    source: str,
    owner_type: str = "company",
    owner_name: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[LinkedInPost]:
    """Normalize one provider-native post row. Returns None if the row has no usable text or url."""
    if not isinstance(row, dict):
        return None

    # Some providers wrap the actual post (e.g. {"post": {...}} or reposts {"resharedPost": {...}})
    inner = row.get("post") if isinstance(row.get("post"), dict) else row

    text = _text(_first(inner, ("text", "content", "commentary", "postText", "post_text", "description", "body", "message")))
    url = _first(inner, ("url", "linkedinUrl", "postUrl", "post_url", "shareUrl", "share_url", "permalink", "link"))
    urn_source = _first(inner, ("urn", "activityUrn", "activity_urn", "postUrn", "post_urn", "shareUrn", "entityUrn", "id", "activityId", "postId"))

    urn = extract_post_urn(str(urn_source)) if urn_source else None
    if not urn and url:
        urn = extract_post_urn(str(url))

    if not text and not url:
        return None

    posted_raw = _first(inner, (
        "postedAt", "posted_at", "postedDate", "posted_date", "postedDateTimestamp", "createdAt",
        "created_at", "publishedAt", "published_at", "date", "time", "timestamp", "postedAgo",
    ))
    posted_at = parse_datetime(posted_raw, now)

    engagement = inner.get("engagement") if isinstance(inner.get("engagement"), dict) else {}
    stats = inner.get("stats") if isinstance(inner.get("stats"), dict) else {}
    social = inner.get("socialActivityCounts") if isinstance(inner.get("socialActivityCounts"), dict) else {}
    merged = {**inner, **social, **stats, **engagement}

    likes = _to_int(_first(merged, (
        "numLikes", "likeCount", "like_count", "totalReactionCount", "reactionCount", "reaction_count",
        "num_likes", "total_reactions", "likes", "reactions",
    )))
    comments = _to_int(_first(merged, (
        "numComments", "commentCount", "comment_count", "commentsCount", "num_comments", "comments",
    )))
    reposts = _to_int(_first(merged, (
        "numShares", "repostCount", "shareCount", "share_count", "num_shares", "shares", "reposts",
    )))

    author = _person(inner, ("author", "actor", "owner", "poster"))
    is_repost = bool(
        inner.get("isRepost") or inner.get("is_repost") or inner.get("resharedPost")
        or inner.get("reshared") or str(inner.get("type", "")).lower() in ("repost", "reshare")
    )

    return LinkedInPost(
        urn=urn,
        url=str(url).strip() if url else None,
        text=text[:4000],
        posted_at=_iso(posted_at),
        author_name=author["name"] or owner_name,
        author_headline=author["headline"],
        author_url=author["url"],
        owner_type=owner_type,
        owner_name=owner_name,
        likes=likes,
        comments=comments,
        reposts=reposts,
        is_repost=is_repost,
        source=source,
    )


def normalize_comment(
    row: dict[str, Any],
    source: str,
    post_url: Optional[str] = None,
    post_urn: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[LinkedInComment]:
    """Normalize one provider-native comment row. Returns None if it has no text."""
    if not isinstance(row, dict):
        return None
    inner = row.get("comment") if isinstance(row.get("comment"), dict) else row

    text = _text(_first(inner, ("text", "commentary", "comment", "content", "commentText", "comment_text", "message", "body")))
    if not text:
        return None

    author = _person(inner, ("author", "actor", "commenter", "user", "owner"))
    posted_raw = _first(inner, ("createdAt", "created_at", "postedAt", "posted_at", "date", "time", "timestamp", "createdAtTimestamp"))
    posted_at = parse_datetime(posted_raw, now)

    engagement = inner.get("engagement") if isinstance(inner.get("engagement"), dict) else {}
    merged = {**inner, **engagement}
    likes = _to_int(_first(merged, ("numLikes", "likeCount", "reactionCount", "totalReactionCount", "likes", "reactions")))
    replies = _to_int(_first(merged, ("numReplies", "replyCount", "repliesCount", "commentCount", "replies")))

    # Comments a member made elsewhere carry the parent post
    parent = inner.get("post") if isinstance(inner.get("post"), dict) else None
    parent_url = post_url or _first(inner, ("postUrl", "post_url", "postLink", "linkedinUrl"))
    parent_text = None
    if parent:
        parent_url = parent_url or _first(parent, ("url", "linkedinUrl", "postUrl"))
        parent_text = _text(_first(parent, ("text", "content", "commentary")))[:500] or None
        parent_author = _person(parent, ("author", "actor"))
    else:
        parent_author = {"name": None, "headline": None, "url": None}

    comment_url = _first(inner, ("commentUrl", "comment_url", "url", "permalink"))

    return LinkedInComment(
        text=text[:2000],
        author_name=author["name"],
        author_headline=author["headline"],
        author_url=author["url"],
        posted_at=_iso(posted_at),
        likes=likes,
        replies=replies,
        post_url=str(parent_url).strip() if parent_url else None,
        post_urn=post_urn or (extract_post_urn(str(parent_url)) if parent_url else None),
        post_text=parent_text,
        post_author_name=parent_author["name"],
        comment_url=str(comment_url).strip() if comment_url and comment_url != parent_url else None,
        source=source,
    )
