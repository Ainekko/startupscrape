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
    raw_data: Optional[Dict[str, Any]] = None

    def to_flat_dict(self) -> Dict[str, Any]:
        """Flatten model for CSV export."""
        return {
            "ID": self.id,
            "Source": self.source,
            "Company Name": self.name,
            "Website": self.website or "",
            "One Liner": self.one_liner or "",
            "Batch": self.batch or "",
            "Industry": self.industry or "",
            "Subindustry": self.subindustry or "",
            "Tags": ", ".join(self.tags),
            "Team Size": self.team_size or "",
            "Locations": "; ".join(self.locations),
            "Is Hiring": "Yes" if self.is_hiring else "No",
            "Open Jobs Count": self.open_jobs_count,
            "Founders": "; ".join([f"{f.name} ({f.title or 'Founder'})" for f in self.founders]),
            "YC URL": self.yc_url or "",
            "WAAS URL": self.waas_url or "",
            "LinkedIn": self.linkedin_url or "",
            "Twitter": self.twitter_url or "",
            "GitHub": self.github_url or "",
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
