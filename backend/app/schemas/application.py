from typing import List, Optional, Dict, Any
from pydantic import BaseModel, model_validator
from enum import Enum

class ApplicationStatus(str, Enum):
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    SHORTLISTED = "Shortlisted"
    INTERVIEW = "Interview"
    SELECTED = "Selected"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"

class ApplicationCreate(BaseModel):
    job_id: str
    cover_letter: Optional[str] = None
    resume_id: Optional[str] = None

class StatusHistoryItem(BaseModel):
    status: str
    timestamp: str
    updated_by: str
    notes: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: str
    student_id: str
    student_name: str
    student_email: str
    job_id: str
    job_title: str
    company: str
    company_name: Optional[str] = None
    opportunity_type: str
    location: str
    work_mode: str
    resume_id: Optional[str] = None
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None
    submission_date: str
    status: str
    admin_notes: Optional[str] = None  # None for student responses
    status_history: List[StatusHistoryItem] = []
    updated_at: str

    @model_validator(mode="before")
    @classmethod
    def populate_company_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            comp = values.get("company") or values.get("company_name") or "Company"
            values["company"] = comp
            values["company_name"] = comp
        return values

class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    admin_notes: Optional[str] = None
