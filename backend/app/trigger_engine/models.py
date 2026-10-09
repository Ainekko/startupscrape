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

