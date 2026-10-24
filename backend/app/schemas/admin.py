from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class UserRoleUpdate(BaseModel):
    role: str  # student or admin

class UserStatusUpdate(BaseModel):
    is_active: bool

class UserListItem(BaseModel):
    uid: str
    email: str
    name: Optional[str] = None
    role: str
    is_active: bool = True
    education_level: Optional[str] = None
    institution: Optional[str] = None
    created_at: Optional[str] = None

class SystemStatsResponse(BaseModel):
    total_users: int
    total_students: int
    total_admins: int
    total_registered_students: int
    total_active_jobs: int
    total_active_internships: int
    total_applications: int
    applications_awaiting_review: int
    assessment_attempts_completed: int
    total_assessments_taken: int
    total_resumes_analyzed: int
    total_learning_resources: int
    popular_career_domains: List[Dict[str, Any]]
    average_assessment_score: float

class JobBulkImportRow(BaseModel):
    title: str
    company: str
    domain: str
    location: str
    work_mode: str = "Remote"
    required_skills: str  # comma separated
    preferred_skills: Optional[str] = None
    min_experience_years: Optional[float] = 0.0
    required_education: Optional[str] = None
    description: str
    application_url: Optional[str] = None

class JobBulkImportResponse(BaseModel):
    total_rows: int
    imported_count: int
    failed_count: int
    errors: List[Dict[str, Any]]
