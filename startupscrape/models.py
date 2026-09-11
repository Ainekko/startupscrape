from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Founder(BaseModel):
    name: str
    title: Optional[str] = None
    avatar_thumb: Optional[str] = None
    twitter_url: Optional[str] = None
    linkedin_url: Optional[str] = None


class JobPosting(BaseModel):
    id: Optional[str] = None
    title: str
    role_type: Optional[str] = None
    location: Optional[str] = None
    has_salary: Optional[bool] = None
    has_equity: Optional[bool] = None
    visa_sponsored: Optional[bool] = None
    url: Optional[str] = None


class GTMAnalysis(BaseModel):
    score: int = Field(default=5, description="GTM scaling readiness score (1-10)")
    stage: Optional[str] = Field(default="Early", description="Funding stage (Seed / Series A / etc.)")
    key_signals: List[str] = Field(default_factory=list, description="Key hiring and growth signals")
    best_contact_role: Optional[str] = Field(default="Founder / CEO", description="Recommended target persona")
    best_contact_name: Optional[str] = Field(default=None, description="Identified contact name")
    suggested_angle: Optional[str] = Field(default=None, description="Recommended sales hook / value prop")
    first_message: Optional[str] = Field(default=None, description="Draft first outreach message")


class StartupLead(BaseModel):
    id: str = Field(description="Unique identifier or slug")
    source: str = Field(description="Source directory: yc or workatastartup")
    name: str
    slug: Optional[str] = None
    website: Optional[str] = None
    one_liner: Optional[str] = None
    long_description: Optional[str] = None
    batch: Optional[str] = None
    status: Optional[str] = "Active"
    industry: Optional[str] = None
    subindustry: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    team_size: Optional[int] = None
    team_size_range: Optional[str] = None
    locations: List[str] = Field(default_factory=list)
    country: Optional[str] = None
    city: Optional[str] = None
    is_hiring: bool = False
    open_jobs_count: int = 0
    jobs: List[JobPosting] = Field(default_factory=list)
    founders: List[Founder] = Field(default_factory=list)
    yc_url: Optional[str] = None
    waas_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    github_url: Optional[str] = None
    gtm_analysis: Optional[GTMAnalysis] = None
    raw_data: Optional[Dict[str, Any]] = None

    def to_flat_dict(self) -> Dict[str, Any]:
        """Flatten model for CSV and table export."""
        gtm = self.gtm_analysis or GTMAnalysis()
        return {
            "ID": self.id,
            "Source": self.source,
            "Company Name": self.name,
            "Score": gtm.score,
            "Stage": gtm.stage or "",
            "Key Signals": "; ".join(gtm.key_signals),
            "Best Contact": f"{gtm.best_contact_name} ({gtm.best_contact_role})" if gtm.best_contact_name else (gtm.best_contact_role or ""),
            "Suggested Angle": gtm.suggested_angle or "",
            "First Message": gtm.first_message or "",
            "Website": self.website or "",
            "Company LinkedIn": self.linkedin_url or "",
            "Company Twitter": self.twitter_url or "",
            "One Liner": self.one_liner or "",
            "Batch": self.batch or "",
            "Industry": self.industry or "",
            "Team Size": self.team_size or "",
            "Is Hiring": "Yes" if self.is_hiring else "No",
            "Open Jobs Count": self.open_jobs_count,
            "YC URL": self.yc_url or "",
            "WAAS URL": self.waas_url or "",
        }


class FilterQuery(BaseModel):
    query_text: Optional[str] = ""
    batches: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    is_hiring: Optional[bool] = None
    nonprofit: Optional[bool] = None
    team_size_min: Optional[int] = None
    team_size_max: Optional[int] = None
    job_types: List[str] = Field(default_factory=list)
    has_salary: Optional[bool] = None
    has_equity: Optional[bool] = None
    visa_not_required: Optional[bool] = None
    sort_by: Optional[str] = "created_desc"
    limit: int = 50
