from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

class ProjectItem(BaseModel):
    title: str = ""
    description: str = ""
    technologies: List[str] = []
    link: Optional[str] = None

class ProfileBase(BaseModel):
    name: Optional[str] = None
    education_level: Optional[str] = None  # e.g., Bachelor's, Master's, High School
    degree: Optional[str] = None           # e.g., B.Tech in Computer Science
    institution: Optional[str] = None
    graduation_year: Optional[int] = None
    technical_skills: List[str] = []
    claimed_skills: List[str] = []
    validated_skills: Dict[str, float] = {}
    projects: List[ProjectItem] = []
    interests: List[str] = []
    preferred_career_domains: List[str] = []
    bio: Optional[str] = None

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    uid: str
    email: str
    role: str = "student"
    resume_url: Optional[str] = None
    resume_id: Optional[str] = None
    completion_percentage: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
