from datetime import datetime, timedelta, timezone

from app.trigger_engine.linkedin_normalize import (
    company_url_from_slug,
    extract_company_slug,
    extract_post_urn,
    extract_profile_handle,
    find_rows,
    normalize_comment,
    normalize_post,
    parse_datetime,
    post_id_from_urn,
    profile_url_from_handle,
)
from tests.linkedin_fixtures import COMPANY_POSTS, FOUNDER_COMMENTS, FOUNDER_POSTS, NOW, POST_COMMENTS


# ── URL / URN ────────────────────────────────────────────────────────────────

def test_extract_company_slug_variants():
    assert extract_company_slug("https://www.linkedin.com/company/acme-ai/about/") == "acme-ai"
    assert extract_company_slug("linkedin.com/company/Acme-AI?trk=x") == "acme-ai"
    assert extract_company_slug("acme-ai") == "acme-ai"
    assert extract_company_slug("https://acme.ai") is None
    assert extract_company_slug(None) is None
    assert company_url_from_slug("acme-ai") == "https://www.linkedin.com/company/acme-ai"


def test_extract_profile_handle_variants():
    assert extract_profile_handle("https://www.linkedin.com/in/jane-doe-123/") == "jane-doe-123"
    assert extract_profile_handle("https://linkedin.com/in/j%C3%A9r%C3%B4me?x=1") == "jérôme"
    assert extract_profile_handle("jane-doe") == "jane-doe"
    assert extract_profile_handle("Jane Doe") is None
    assert extract_profile_handle("https://www.linkedin.com/company/acme") is None
    assert profile_url_from_handle("jane-doe") == "https://www.linkedin.com/in/jane-doe"


def test_extract_post_urn_from_all_shapes():
    assert extract_post_urn("urn:li:activity:7508596155145043968") == "urn:li:activity:7508596155145043968"
    assert extract_post_urn("urn:li:ugcPost:7508596155145043968") == "urn:li:ugcPost:7508596155145043968"
    assert (
        extract_post_urn("https://www.linkedin.com/posts/stripe_x-activity-7477791740645564416-tIbZ")
        == "urn:li:activity:7477791740645564416"
    )
    assert (
        extract_post_urn("https://www.linkedin.com/feed/update/urn:li:activity:7381111111111111111/")
        == "urn:li:activity:7381111111111111111"
    )
    assert extract_post_urn("7380000000000000001") == "urn:li:activity:7380000000000000001"
    assert extract_post_urn("https://example.com/blog") is None
    assert extract_post_urn(None) is None
    assert post_id_from_urn("urn:li:activity:7380000000000000001") == "7380000000000000001"


# ── Dates ────────────────────────────────────────────────────────────────────

def test_parse_datetime_formats():
    assert parse_datetime("2026-10-05T10:00:00Z") == datetime(2026, 10, 5, 10, tzinfo=timezone.utc)
    assert parse_datetime("2026-10-05") == datetime(2026, 10, 5, tzinfo=timezone.utc)
    ms = int(datetime(2026, 10, 5, tzinfo=timezone.utc).timestamp() * 1000)
    assert parse_datetime(ms) == datetime(2026, 10, 5, tzinfo=timezone.utc)
    assert parse_datetime(ms // 1000) == datetime(2026, 10, 5, tzinfo=timezone.utc)
    assert parse_datetime(str(ms)) == datetime(2026, 10, 5, tzinfo=timezone.utc)
    assert parse_datetime({"timestamp": ms}) == datetime(2026, 10, 5, tzinfo=timezone.utc)
    assert parse_datetime({"date": "2026-10-05T00:00:00Z"}) == datetime(2026, 10, 5, tzinfo=timezone.utc)


def test_parse_datetime_relative_labels():
    assert parse_datetime("3d", NOW) == NOW - timedelta(days=3)
    assert parse_datetime("2w", NOW) == NOW - timedelta(weeks=2)
    assert parse_datetime("1mo", NOW) == NOW - timedelta(days=30)
    assert parse_datetime("5h", NOW) == NOW - timedelta(hours=5)
    assert parse_datetime("1y", NOW) == NOW - timedelta(days=365)


def test_parse_datetime_garbage():
    assert parse_datetime(None) is None
    assert parse_datetime("") is None
    assert parse_datetime("not a date") is None
    assert parse_datetime(True) is None


# ── Envelopes ────────────────────────────────────────────────────────────────

def test_find_rows_handles_routed_and_native_envelopes():
    assert len(find_rows(FOUNDER_POSTS, preferred=("posts",))) == 1
    assert len(find_rows(COMPANY_POSTS, preferred=("elements",))) == 3
    assert len(find_rows(POST_COMMENTS, preferred=("comments",))) == 3
    assert find_rows({"data": {"items": [{"a": 1}]}}) == [{"a": 1}]
    assert find_rows([{"a": 1}, "junk"]) == [{"a": 1}]
    assert find_rows({"output": {"posts": []}}) == []
    assert find_rows(None) == []


# ── Posts ────────────────────────────────────────────────────────────────────

def test_normalize_harvest_company_post():
    row = COMPANY_POSTS["elements"][0]
    post = normalize_post(row, source="harvest", owner_type="company", owner_name="Acme AI", now=NOW)
    assert post is not None
    assert post.urn == "urn:li:activity:7380000000000000001"
    assert post.url.startswith("https://www.linkedin.com/posts/acme-ai_hiring")
    assert "hiring" in post.text.lower()
    assert post.likes == 40 and post.comments == 12 and post.reposts == 3
    assert post.posted_at.startswith("2026-10-05T10:00:00")
    assert post.author_name == "Acme AI"
    assert post.owner_type == "company"


def test_normalize_fetchin_founder_post():
    row = FOUNDER_POSTS["output"]["posts"][0]
    post = normalize_post(row, source="routed", owner_type="founder", owner_name="Jane Doe", now=NOW)
    assert post.urn == "urn:li:activity:7381111111111111111"
    assert post.author_name == "Jane Doe"
    assert post.author_url == "https://www.linkedin.com/in/jane-doe"
    assert post.likes == 20 and post.comments == 5


def test_normalize_post_alternate_keys_and_counts():
    row = {
        "commentary": {"text": "Announcing our partnership"},
        "shareUrl": "https://www.linkedin.com/feed/update/urn:li:share:7390000000000000000",
        "socialActivityCounts": {"numLikes": "1.2k", "numComments": 7},
        "comments": [{"text": "x"}, {"text": "y"}],
        "postedAgo": "2d",
        "resharedPost": {"text": "orig"},
    }
    post = normalize_post(row, source="x", now=NOW)
    assert post.text == "Announcing our partnership"
    assert post.urn == "urn:li:share:7390000000000000000"
    assert post.likes == 1200
    assert post.comments == 7  # nested counts win over the top-level comment list
    assert post.is_repost is True
    assert post.posted_at.startswith((NOW - timedelta(days=2)).date().isoformat())


def test_normalize_post_rejects_empty_rows():
    assert normalize_post({}, source="x") is None
    assert normalize_post({"likes": 3}, source="x") is None
    assert normalize_post("nope", source="x") is None  # type: ignore[arg-type]


# ── Comments ─────────────────────────────────────────────────────────────────

def test_normalize_post_comment():
    row = POST_COMMENTS["output"]["comments"][0]
    c = normalize_comment(row, source="routed", post_url="https://p", post_urn="urn:li:activity:1234567890123456", now=NOW)
    assert c.text.startswith("Interested")
    assert c.author_name == "Bob Buyer"
    assert c.author_headline == "Head of Sales at BigCo"
    assert c.author_url == "https://www.linkedin.com/in/bob-buyer"
    assert c.post_url == "https://p"
    assert c.post_urn == "urn:li:activity:1234567890123456"
    assert c.posted_at.startswith("2026-10-06T12:00:00")


def test_normalize_member_comment_with_parent_post():
    row = FOUNDER_COMMENTS["elements"][0]
    c = normalize_comment(row, source="harvest", now=NOW)
    assert "outbound" in c.text
    assert c.post_url.endswith("activity-7382222222222222222-qqqq")
    assert c.post_urn == "urn:li:activity:7382222222222222222"
    assert c.post_text.startswith("How do you build an outbound engine")
    assert c.post_author_name == "Sam GTM"


def test_normalize_comment_flat_author_fields():
    row = {"comment": "Pricing?", "authorName": "Ann", "authorHeadline": "VP Sales", "authorProfileUrl": "https://www.linkedin.com/in/ann"}
    c = normalize_comment(row, source="x")
    assert c.author_name == "Ann"
    assert c.author_headline == "VP Sales"
    assert c.author_url == "https://www.linkedin.com/in/ann"


def test_normalize_comment_rejects_empty():
    assert normalize_comment({"author": {"name": "x"}}, source="x") is None

