"""
app/models.py — SQLModel Database Entities and Pydantic Schemas
==============================================================
All tables use the 'startupscrape_' prefix to guarantee clean isolation
within a shared PostgreSQL database.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from sqlmodel import Field, SQLModel


# =============================================================================
# Enums
# =============================================================================

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class OutreachStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    REPLIED = "replied"
    MEETING = "meeting"
    CONVERTED = "converted"
    DISQUALIFIED = "disqualified"


# =============================================================================
# SQLModel Table Models
# =============================================================================

class User(SQLModel, table=True):
    __tablename__ = "startupscrape_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    full_name: Optional[str] = Field(default=None)
    role: str = Field(default=UserRole.USER.value)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineRun(SQLModel, table=True):
    __tablename__ = "startupscrape_runs"

    id: str = Field(primary_key=True)  # run_YYYYMMDD_HHMMSS
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="running", index=True)  # running, complete, error
    funnel_data: Optional[str] = Field(default=None)  # JSON string
    spend_data: Optional[str] = Field(default=None)   # JSON string
    lead_count: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Lead(SQLModel, table=True):
    __tablename__ = "startupscrape_leads"

    id: str = Field(primary_key=True)  # Unique slug or ID
    run_id: Optional[str] = Field(default=None, index=True)
    company_name: str = Field(index=True)
    website: Optional[str] = Field(default=None)
    one_liner: Optional[str] = Field(default=None)
    batch: Optional[str] = Field(default=None, index=True)
    industry: Optional[str] = Field(default=None, index=True)
    team_size: Optional[str] = Field(default=None)
    tags: Optional[str] = Field(default=None)  # JSON string or comma-separated
    yc_url: Optional[str] = Field(default=None)
    waas_url: Optional[str] = Field(default=None)
    linkedin_url: Optional[str] = Field(default=None)

    # Key Founder / Contact
    founder_name: Optional[str] = Field(default=None)
    founder_title: Optional[str] = Field(default=None)
    founder_linkedin: Optional[str] = Field(default=None)

    # Email & Verification
    email: Optional[str] = Field(default=None, index=True)
    email_status: Optional[str] = Field(default=None)

    # Scoring & GTM Intel
    tier1_score: float = Field(default=0.0)
    final_score: float = Field(default=0.0, index=True)
    is_competitor: bool = Field(default=False)
    is_vertical_product: bool = Field(default=False)

    # Outreach tracking
    outreach_status: str = Field(default=OutreachStatus.NEW.value, index=True)
    notes: Optional[str] = Field(default=None)

    # Raw enriched payloads
    founders_json: Optional[str] = Field(default=None)
    signals_json: Optional[str] = Field(default=None)
    raw_json: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutreachOutcome(SQLModel, table=True):
    __tablename__ = "startupscrape_outcomes"

    id: Optional[int] = Field(default=None, primary_key=True)
    lead_id: str = Field(index=True)
    company_name: Optional[str] = Field(default=None)
    channel: str = Field(default="email")  # email, linkedin, twitter
    status: str = Field(index=True)        # sent, opened, replied, booked, disqualified
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Pydantic Request & Response Schemas
# =============================================================================

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    email: str
    role: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadFilterParams(BaseModel):
    query: Optional[str] = None
    batch: Optional[str] = None
    industry: Optional[str] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    has_email: Optional[bool] = None
    outreach_status: Optional[str] = None
    run_id: Optional[str] = None
    dedupe: bool = True
    sort_by: str = "score_desc"  # score_desc, score_asc, name_asc, date_desc
    limit: int = 50
    offset: int = 0


class LeadStatusUpdateRequest(BaseModel):
    outreach_status: str
    notes: Optional[str] = None


class LeadOutcomeCreateRequest(BaseModel):
    channel: str = "email"
    status: str
    notes: Optional[str] = None


class PipelineTriggerRequest(BaseModel):
    max_leads: int = 20
    max_treg_cost: float = 1.0
    batches: Optional[list[str]] = None   # None = all target batches; e.g. ["Summer 2024","Winter 2024"]
    sources: list[str] = ["yc"]           # ["yc"] | ["waas"] | ["yc","waas"]


class AnalyticsOverviewResponse(BaseModel):
    total_leads: int
    total_runs: int
    avg_score: float
    leads_with_email: int
    status_breakdown: dict[str, int]
    top_batches: list[dict[str, Any]]
