import asyncio

from app.trigger_engine.linkedin_intel import (
    ENDPOINTS,
    IntelBudget,
    IntelOptions,
    LinkedInIntelService,
    classify_comment_intent,
    classify_post_text,
    classify_role,
    extract_topics,
    report_from_snapshot,
    snapshot_from_report,
)
from tests.linkedin_fixtures import (
    COMPANY_POSTS_EP,
    NOW,
    POST_COMMENTS_EP,
    SERP_EP,
    USER_COMMENTS_EP,
    USER_POSTS_EP,
    FakeTreg,
    acme_account,
)


def _gather(fake: FakeTreg, account: dict, **opts):
    service = LinkedInIntelService(treg_client=fake)  # type: ignore[arg-type]
    return asyncio.run(service.gather(account, options=IntelOptions(**opts), now=NOW))


# ── Classifiers ──────────────────────────────────────────────────────────────

def test_classify_post_text():
    assert classify_post_text("We're hiring our first SDR!") == ["hiring", "gtm_pain"]
    assert "funding" in classify_post_text("Thrilled to share we raised a $4M seed round led by X")
    assert "launch" in classify_post_text("Introducing our new API, now live")
    assert "event" in classify_post_text("Join us at the SaaStr summit booth 12")
    assert classify_post_text("Happy Friday everyone") == []
    assert classify_post_text("") == []


def test_classify_comment_intent():
    assert classify_comment_intent("Interested, how much is it?") == "buying_intent"
    assert classify_comment_intent("Can I get early access?") == "buying_intent"
    assert classify_comment_intent("We struggle with this every week") == "pain"
    assert classify_comment_intent("Does it integrate with Salesforce?") == "question"
    assert classify_comment_intent("Congrats on the launch!") == "praise"
    assert classify_comment_intent("ok") is None


def test_classify_role():
    assert classify_role("General Partner at Seed Ventures") == "investor"
    assert classify_role("Head of Sales @ BigCo") == "sales_leader"
    assert classify_role("Co-founder & CEO at Acme") == "founder"
    assert classify_role("Account Executive") == "sales_rep"
    assert classify_role("Technical Recruiter") == "recruiter"
    assert classify_role("Senior Software Engineer") == "engineer"
    assert classify_role(None) == "other"


def test_extract_topics_prefers_hashtags_and_repeats():
    topics = extract_topics(["#outbound is hard", "outbound pipeline pipeline", "#outbound again"])
    assert topics[0] == "#outbound"
    assert "pipeline" in topics


def test_budget_reserve_and_settle():
    b = IntelBudget(0.01)
    assert b.reserve(0.006)
    assert not b.reserve(0.006)
    assert b.exhausted
    b.settle(0.006, 0.002)
    assert b.spent == 0.002 and b.reserved == 0.0
    assert b.reserve(0.006)


# ── Full gather ──────────────────────────────────────────────────────────────

def test_gather_full_account_produces_rich_intel():
    fake = FakeTreg()
    report = _gather(fake, acme_account())

    # Targets
    assert report.lead_id == "lead_acme"
    assert report.company_linkedin_url == "https://www.linkedin.com/company/acme-ai"
    assert [f.name for f in report.founders] == ["Jane Doe", "John Roe"]

    # Company posts: old (2025) post dropped by the 90-day lookback
    assert len(report.company_posts) == 2
    assert all("2025" not in (p.posted_at or "") for p in report.company_posts)
    # Founder posts deduped across founders (same urn returned twice)
    assert len(report.founder_posts) == 1
    assert report.founders[0].posts_found == 1
    assert report.founders[0].comments_made_found == 1
    assert report.founders[0].last_active_at.startswith("2026-10-08")

    # Comments fetched for top 3 posts, founder comments for both founders
    assert len(fake.calls_to(POST_COMMENTS_EP)) == 3
    assert len(fake.calls_to(USER_COMMENTS_EP)) == 2
    assert len(report.post_comments) == 9
    assert len(report.founder_comments) == 2

    kinds = {s.kind for s in report.signals}
    assert {"hiring", "launch", "gtm_pain", "comment_intent", "notable_engager", "founder_engagement"} <= kinds
    trigger_types = {s.trigger_type for s in report.signals}
    assert {"gtm_hiring", "product_launch", "social_discussion", "founder_signal"} <= trigger_types

    intent = next(s for s in report.signals if s.kind == "comment_intent")
    assert intent.headline.startswith("1 commenter(s) asked about pricing")
    assert "Bob Buyer" in intent.evidence

    engagement = next(s for s in report.signals if s.kind == "founder_engagement")
    assert "Sam GTM" in engagement.headline

    # Engaged people: founder excluded, investor ranked first, buyer intent tracked
    names = [p.name for p in report.engaged_people]
    assert "Jane Doe" not in names
    assert names[0] == "Vera VC"
    bob = next(p for p in report.engaged_people if p.name == "Bob Buyer")
    assert bob.role == "sales_leader" and "buying_intent" in bob.intents and bob.comment_count == 3

    assert report.urgency_score == 10
    assert "#outbound" in report.topics or "outbound" in report.topics
    assert report.summary.startswith("Acme AI:")
    assert "buying-intent" in report.summary

    # Spend + audit
    assert report.calls_made == 8
    assert abs(report.cost_usd - 0.016) < 1e-9
    assert report.budget_exhausted is False
    assert set(report.sources_used) == {COMPANY_POSTS_EP, USER_POSTS_EP, POST_COMMENTS_EP, USER_COMMENTS_EP}
    assert report.errors == []


def test_gather_sends_correct_provider_inputs():
    fake = FakeTreg()
    _gather(fake, acme_account(), lookback_days=90, comments_per_post=10)

    company_call = fake.calls_to(COMPANY_POSTS_EP)[0]
    assert company_call["method"] == "GET"
    assert company_call["params"]["companyUniversalName"] == "acme-ai"
    assert company_call["params"]["scrapePostedLimit"] == "3months"
    assert company_call["max_cost"] == ENDPOINTS["company_posts"][2]

    user_posts_urls = sorted(c["json"]["linkedin_url"] for c in fake.calls_to(USER_POSTS_EP))
    assert user_posts_urls == ["https://www.linkedin.com/in/jane-doe", "https://www.linkedin.com/in/john-roe"]

    comment_calls = fake.calls_to(POST_COMMENTS_EP)
    assert all(c["json"]["post_urn"].startswith("urn:li:activity:") and c["json"]["limit"] == 10 for c in comment_calls)
    # Highest-engagement post (launch, 30 comments) is fetched first
    assert comment_calls[0]["json"]["post_urn"] == "urn:li:activity:7370000000000000002"

    member_comment_call = fake.calls_to(USER_COMMENTS_EP)[0]
    assert member_comment_call["method"] == "GET"
    assert member_comment_call["params"]["postedLimit"] == "month"


def test_gather_resolves_targets_via_serp_when_missing():
    fake = FakeTreg()
    report = _gather(fake, {"company_name": "Acme AI"})

    assert len(fake.calls_to(SERP_EP)) == 2
    assert report.company_linkedin_url == "https://www.linkedin.com/company/acme-ai"
    assert [f.name for f in report.founders] == ["Jane Doe"]  # engineer result filtered out
    assert fake.calls_to(COMPANY_POSTS_EP)[0]["params"]["companyUniversalName"] == "acme-ai"
    assert report.lead_id == "acc_acme_ai"


def test_gather_respects_budget_cap():
    fake = FakeTreg()
    report = _gather(fake, acme_account(), max_cost_usd=0.008)

    assert report.budget_exhausted is True
    assert report.cost_usd <= 0.008
    assert any("budget" in e for e in report.errors)
    assert "partial (budget cap hit)" in report.summary


def test_gather_handles_total_provider_failure():
    fake = FakeTreg(responses={})
    report = _gather(fake, acme_account())

    assert report.signals == []
    assert report.company_posts == [] and report.founder_posts == []
    assert report.urgency_score == 1
    assert report.cost_usd == 0.0
    assert any(e.startswith("company_posts: 404") for e in report.errors)
    assert "No timing signals" in report.summary


def test_gather_can_skip_comments_and_founders():
    fake = FakeTreg()
    report = _gather(fake, acme_account(), max_posts_for_comments=0, include_founder_comments=False, max_founders=0)

    assert fake.calls_to(POST_COMMENTS_EP) == []
    assert fake.calls_to(USER_COMMENTS_EP) == []
    assert fake.calls_to(USER_POSTS_EP) == []
    assert fake.calls_to(SERP_EP) == []
    assert len(report.company_posts) == 2


def test_founder_targets_dedupe_and_extra_urls():
    targets = LinkedInIntelService.founder_targets_from_account(
        acme_account(),
        extra_urls=["https://www.linkedin.com/in/new-person", "https://www.linkedin.com/in/jane-doe"],
    )
    handles = [t.handle for t in targets]
    assert handles == ["new-person", "jane-doe", "john-roe"]
    jane = next(t for t in targets if t.handle == "jane-doe")
    assert jane.name == "Jane Doe"  # name filled from later duplicate


def test_snapshot_roundtrip():
    report = _gather(FakeTreg(), acme_account())
    snap = snapshot_from_report(report)
    assert snap.lead_id == "lead_acme"
    assert snap.signals_count == len(report.signals)
    assert snap.posts_count == 3
    assert snap.comments_count == 11

    restored = report_from_snapshot(snap)
    assert restored.cached is True
    assert restored.signals == report.signals
    assert restored.engaged_people == report.engaged_people

