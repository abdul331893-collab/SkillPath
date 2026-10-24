from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.schemas.job import JobListingResponse

class SkillRequirement(BaseModel):
    skill: str
    weight: float = 1.0
    required_level: float = 70.0  # percentage

class CareerDomainBase(BaseModel):
    id: str
    title: str
    description: str
    category: str
    required_skills: List[SkillRequirement] = []
    preferred_skills: List[str] = []
    min_education_level: Optional[str] = None  # e.g., "Bachelor's"
    recommended_certifications: List[str] = []

class CareerDomainCreate(CareerDomainBase):
    pass

class SkillGapItem(BaseModel):
    skill: str
    required_level: float
    current_level: float
    gap: float  # max(0, required_level - current_level)
    is_missing: bool = False

class SuggestedProjectItem(BaseModel):
    title: str
    description: str
    technologies: List[str] = []

class CareerRecommendationResponse(BaseModel):
    domain_id: str
    title: str
    description: str
    match_score: Optional[float] = None  # 0 to 100, None if insufficient data
    insufficient_data: bool = False
    formula_explanation: str = "Weighted average of required domain skills: Sum(Weight_i × Score_i) / Sum(Weight_i). Unassessed skills count as 0% until evaluated."
    eligibility_met: bool
    eligibility_notes: Optional[str] = None
    matching_skills: List[Dict[str, Any]] = []  # skill, score
    strong_supporting_skills: List[str] = []
    relevant_project_evidence: List[str] = []
    assessment_evidence: List[str] = []
    weak_or_missing_skills: List[str] = []
    skill_gaps: List[SkillGapItem] = []
    missing_required_skills: List[str] = []
    ai_explanation: str
    reason_for_recommendation: Optional[str] = None
    suggested_next_steps: List[str] = []
    suggested_projects: List[SuggestedProjectItem] = []
    job_ready_steps: List[str] = []
    related_opportunities: List[JobListingResponse] = []
    comparative_analysis: Optional[str] = None
    disclaimer: str = "This recommendation is an advisory career alignment based on assessed technical competencies and does not constitute a job offer or employment guarantee."
