"""
app/trigger_engine/models.py — SQLModel Database Entities & Pydantic Schemas
===========================================================================
All database tables in this module are strictly isolated with the prefix
'trigengine_' to ensure clean separation from Verve ('startupscrape_') tables
and enable seamless migration to a standalone database whenever needed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field as PyField
from sqlmodel import Field, SQLModel


# =============================================================================
# Enums
# =============================================================================

class TriggerType(str, Enum):
    FUNDING = "funding"
    GTM_HIRING = "gtm_hiring"
    GTM_LEADERSHIP = "gtm_leadership"
    PRODUCT_LAUNCH = "product_launch"
    HEADCOUNT_GROWTH = "headcount_growth"
    SOCIAL_DISCUSSION = "social_discussion"
    TECH_STACK = "tech_stack"
    FOUNDER_SIGNAL = "founder_signal"


class BriefStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    REPLIED = "replied"
    REJECTED = "rejected"


class TriggerRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


# =============================================================================
# SQLModel Table Models (Prefix: trigengine_)
# =============================================================================

class TriggerEvent(SQLModel, table=True):
    __tablename__ = "trigengine_events"

    id: str = Field(primary_key=True)  # e.g. "evt_20261009_xxxxxx"
    lead_id: str = Field(index=True)   # Soft reference to Verve lead id
    company_name: str = Field(index=True)
    company_domain: Optional[str] = Field(default=None)
    trigger_type: str = Field(index=True)  # TriggerType value
    headline: str
    snippet: str
    source: str = Field(default="treg")    # e.g. "treg:anyapi.linkedin.search.jobs"
    source_url: Optional[str] = Field(default=None)
    confidence: float = Field(default=0.8) # 0.0 to 1.0
    raw_metadata: Optional[str] = Field(default=None) # JSON payload

    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TriggerEvaluation(SQLModel, table=True):
    __tablename__ = "trigengine_evaluations"

    id: str = Field(primary_key=True)  # e.g. "eval_xxxxxx"
    event_id: str = Field(index=True)  # Soft reference to TriggerEvent.id
    lead_id: str = Field(index=True)   # Soft reference to Verve lead id
    company_name: str = Field(index=True)

    is_qualified: bool = Field(default=False, index=True)
    urgency_score: int = Field(default=5)      # 1 to 10
    relevance_score: int = Field(default=5)    # 1 to 10
    why_now_rationale: str
    target_decision_maker: Optional[str] = Field(default="Founder / CEO")
    suggested_angle: str = Field(default="first_sales_hire") # Angle tag

    evaluator: str = Field(default="gemini-2.5-flash")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutreachBrief(SQLModel, table=True):
    __tablename__ = "trigengine_briefs"

    id: str = Field(primary_key=True)  # e.g. "brief_xxxxxx"
    lead_id: str = Field(index=True)   # Soft reference to Verve lead id
    company_name: str = Field(index=True)
    founder_name: Optional[str] = Field(default=None)
    founder_email: Optional[str] = Field(default=None, index=True)
    founder_title: Optional[str] = Field(default=None)
    founder_linkedin: Optional[str] = Field(default=None)

    trigger_event_id: Optional[str] = Field(default=None, index=True)
    evaluation_id: Optional[str] = Field(default=None)
    trigger_type: str = Field(default="gtm_hiring")

    urgency_score: int = Field(default=8)
    angle: str = Field(default="first_sales_hire")
    why_now_hook: str
    email_subject: str
    email_body: str
    linkedin_note: str
    slack_preview: str

    status: str = Field(default=BriefStatus.DRAFT.value, index=True)
    notes: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TriggerRun(SQLModel, table=True):
    __tablename__ = "trigengine_runs"

    id: str = Field(primary_key=True)  # e.g. "trigrun_20261009_120000"
    status: str = Field(default=TriggerRunStatus.RUNNING.value, index=True)
    accounts_scanned: int = Field(default=0)
    triggers_found: int = Field(default=0)
    qualified_count: int = Field(default=0)
    briefs_generated: int = Field(default=0)
    treg_cost_usd: float = Field(default=0.0)
    error_message: Optional[str] = Field(default=None)

    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Pydantic Schemas for API Requests & Responses
# =============================================================================

class TriggerScanRequest(BaseModel):
    lead_ids: Optional[list[str]] = None
    limit: int = PyField(default=10, ge=1, le=100)
    trigger_types: Optional[list[str]] = None # None = all types
    min_urgency: int = PyField(default=6, ge=1, le=10)
    max_treg_cost: float = PyField(default=0.50, ge=0.01, le=5.0)


class BriefStatusUpdateRequest(BaseModel):
    status: BriefStatus
    notes: Optional[str] = None


class TriggerEventResponse(BaseModel):
    id: str
    lead_id: str
    company_name: str
    company_domain: Optional[str] = None
    trigger_type: str
    headline: str
    snippet: str
    source: str
    source_url: Optional[str] = None
    confidence: float
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TriggerEvaluationResponse(BaseModel):
    id: str
    event_id: str
    lead_id: str
    company_name: str
    is_qualified: bool
    urgency_score: int
    relevance_score: int
    why_now_rationale: str
    target_decision_maker: Optional[str] = None
    suggested_angle: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutreachBriefResponse(BaseModel):
    id: str
    lead_id: str
    company_name: str
    founder_name: Optional[str] = None
    founder_email: Optional[str] = None
    founder_title: Optional[str] = None
    founder_linkedin: Optional[str] = None
    trigger_type: str
    urgency_score: int
    angle: str
    why_now_hook: str
    email_subject: str
    email_body: str
    linkedin_note: str
    slack_preview: str
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TriggerRunResponse(BaseModel):
    id: str
    status: str
    accounts_scanned: int
    triggers_found: int
    qualified_count: int
    briefs_generated: int
    treg_cost_usd: float
    error_message: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TriggerStatsResponse(BaseModel):
    total_events: int
    total_briefs: int
    approved_briefs: int
    by_trigger_type: dict[str, int]
    by_angle: dict[str, int]
    avg_urgency: float
    total_spend_usd: float


class LinkedInJobItem(BaseModel):
    title: str
    company: str
    location: Optional[str] = "Remote"
    url: Optional[str] = None
    category: str = "other"  # gtm_sales, gtm_revops, gtm_leadership, engineering, other
    source: str = "anyapi.linkedin.search.jobs"
    posted_utc: Optional[str] = None


class LinkedInPersonItem(BaseModel):
    name: str
    title: str
    url: str
    role_type: str = "other"  # founder, sales_leader, executive, other


class LinkedInSpyRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    roles: Optional[list[str]] = None
    include_people: bool = True


class LinkedInSpyResponse(BaseModel):
    company_name: str
    clean_name: str
    domain: Optional[str] = None
    jobs_found: list[LinkedInJobItem] = []
    people_found: list[LinkedInPersonItem] = []
    urgency_score: int = 5
    timing_hook: str
    angle: str
    cost_usd: float
    sources_used: list[str] = []
    detected_at: datetime = PyField(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# LinkedIn Deep Intel (posts, comments, engaged people) — via treg providers only
# =============================================================================

class LinkedInIntelSnapshot(SQLModel, table=True):
    __tablename__ = "trigengine_linkedin_intel"

    id: str = Field(primary_key=True)  # e.g. "liintel_xxxxxxxx"
    lead_id: str = Field(index=True)   # Soft reference to Verve lead id
    company_name: str = Field(index=True)
    signals_count: int = Field(default=0)
    posts_count: int = Field(default=0)
    comments_count: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    report_json: str  # Full LinkedInIntelReport JSON
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class LinkedInPost(BaseModel):
    urn: Optional[str] = None
    url: Optional[str] = None
    text: str = ""
    posted_at: Optional[str] = None  # ISO 8601 UTC
    author_name: Optional[str] = None
    author_headline: Optional[str] = None
    author_url: Optional[str] = None
    owner_type: str = "company"  # company | founder
    owner_name: Optional[str] = None
    likes: int = 0
    comments: int = 0
    reposts: int = 0
    is_repost: bool = False
    source: str = ""
    signal_kinds: list[str] = []


class LinkedInComment(BaseModel):
    text: str
    author_name: Optional[str] = None
    author_headline: Optional[str] = None
    author_url: Optional[str] = None
    posted_at: Optional[str] = None
    likes: int = 0
    replies: int = 0
    post_url: Optional[str] = None
    post_urn: Optional[str] = None
    post_text: Optional[str] = None
    post_author_name: Optional[str] = None
    comment_url: Optional[str] = None
    source: str = ""
    intent: Optional[str] = None       # buying_intent | pain | question | praise | None
    author_role: Optional[str] = None  # investor | founder | sales_leader | sales_rep | recruiter | engineer | other


class IntelSignal(BaseModel):
    kind: str  # hiring | funding | launch | gtm_pain | milestone | event | comment_intent | notable_engager | founder_engagement
    trigger_type: str  # mapped Trigger Engine type (gtm_hiring, funding, product_launch, social_discussion, founder_signal)
    headline: str
    evidence: str
    source_url: Optional[str] = None
    posted_at: Optional[str] = None
    actor: Optional[str] = None
    confidence: float = 0.75
    recency_days: Optional[int] = None


class EngagedPerson(BaseModel):
    name: str
    headline: Optional[str] = None
    url: Optional[str] = None
    role: str = "other"
    comment_count: int = 0
    intents: list[str] = []
    sample_comment: Optional[str] = None


class FounderActivity(BaseModel):
    name: Optional[str] = None
    profile_url: Optional[str] = None
    posts_found: int = 0
    comments_made_found: int = 0
    last_active_at: Optional[str] = None
    top_topics: list[str] = []


class LinkedInIntelReport(BaseModel):
    lead_id: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    founders: list[FounderActivity] = []
    company_posts: list[LinkedInPost] = []
    founder_posts: list[LinkedInPost] = []
    post_comments: list[LinkedInComment] = []
    founder_comments: list[LinkedInComment] = []
    signals: list[IntelSignal] = []
    engaged_people: list[EngagedPerson] = []
    topics: list[str] = []
    last_company_post_at: Optional[str] = None
    urgency_score: int = 0
    summary: str = ""
    cost_usd: float = 0.0
    calls_made: int = 0
    budget_exhausted: bool = False
    sources_used: list[str] = []
    errors: list[str] = []
    cached: bool = False
    generated_at: datetime = PyField(default_factory=lambda: datetime.now(timezone.utc))


class LinkedInIntelRequest(BaseModel):
    lead_id: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    founder_linkedin_urls: Optional[list[str]] = None
    founder_names: Optional[list[str]] = None
    max_cost_usd: float = PyField(default=0.06, ge=0.001, le=1.0)
    lookback_days: int = PyField(default=90, ge=1, le=365)
    max_posts_for_comments: int = PyField(default=3, ge=0, le=10)
    comments_per_post: int = PyField(default=25, ge=1, le=100)
    max_founders: int = PyField(default=2, ge=0, le=5)
    include_founder_comments: bool = True
    force_refresh: bool = False
    persist: bool = True


class LinkedInIntelBatchRequest(BaseModel):
    lead_ids: Optional[list[str]] = None
    limit: int = PyField(default=10, ge=1, le=50)
    max_cost_usd_per_account: float = PyField(default=0.06, ge=0.001, le=1.0)
    max_total_cost_usd: float = PyField(default=1.0, ge=0.01, le=20.0)
    force_refresh: bool = False


class LinkedInIntelBatchItem(BaseModel):
    lead_id: str
    company_name: str
    status: str  # scanned | cached | skipped_budget | error
    signals_count: int = 0
    urgency_score: int = 0
    cost_usd: float = 0.0
    summary: str = ""
    error: Optional[str] = None


class LinkedInIntelBatchResponse(BaseModel):
    accounts_requested: int
    accounts_scanned: int
    accounts_cached: int
    total_cost_usd: float
    budget_exhausted: bool
    items: list[LinkedInIntelBatchItem] = []


