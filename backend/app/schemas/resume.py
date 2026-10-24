from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ResumeExtractedData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: List[Dict[str, Any]] = []
    claimed_skills: List[str] = []
    projects: List[Dict[str, Any]] = []
    experience: List[Dict[str, Any]] = []
    certifications: List[str] = []
    summary: Optional[str] = None

class SkillItem(BaseModel):
    name: str
    source: str = "resume-claimed"  # "resume-claimed" or "student-added"

class ProjectItem(BaseModel):
    title: str
    description: str
    technologies: List[str] = []

class ConfirmedExtractionPayload(BaseModel):
    skills: List[SkillItem] = []
    projects: List[ProjectItem] = []
    recommended_domains: Optional[List[str]] = None

class ResumeUploadResponse(BaseModel):
    id: str
    user_id: str
    file_name: str
    file_url: str
    extracted_data: ResumeExtractedData
    recommended_domains: List[str] = []
    created_at: str

class ResumeLatestResponse(BaseModel):
    resume: Optional[ResumeUploadResponse] = None
