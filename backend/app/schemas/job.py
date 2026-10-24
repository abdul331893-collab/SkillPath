from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class JobListingBase(BaseModel):
    title: str
    company: str
    description: str = ""
    domain: str = "General"
    opportunity_type: str = "Job"  # "Job" or "Internship"
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    min_experience_years: float = 0.0
    required_education: Optional[str] = None  # e.g. "Bachelor's"
    location: str = "Remote"
    work_mode: str = "Remote"  # Remote, Hybrid, Onsite
    application_url: Optional[str] = None
    deadline: Optional[str] = None
    is_active: bool = True
    expiry_date: Optional[str] = None

class JobListingCreate(JobListingBase):
    pass

class JobListingUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    opportunity_type: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    min_experience_years: Optional[float] = None
    required_education: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None
    application_url: Optional[str] = None
    deadline: Optional[str] = None
    is_active: Optional[bool] = None
    expiry_date: Optional[str] = None

class JobListingResponse(JobListingBase):
    id: str
    created_at: str = ""
    updated_at: str = ""

class JobMatchResult(BaseModel):
    job: JobListingResponse
    match_score: Optional[float] = None  # 0 to 100, None if missing skills or requirements
    match_status: str = "calculated"  # calculated, assessment_required, match_unavailable, zero_match
    explanation: Optional[str] = None
    eligibility_met: bool
    eligibility_notes: Optional[str] = None
    matched_required_skills: List[str] = []
    missing_required_skills: List[str] = []
    matched_preferred_skills: List[str] = []
    missing_preferred_skills: List[str] = []
    matching_skills: List[str] = []  # backward compatibility
