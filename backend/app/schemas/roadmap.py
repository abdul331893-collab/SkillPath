from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ResourceReference(BaseModel):
    title: str
    url: Optional[str] = None
    resource_type: str = "official_docs"  # documentation, tutorial, project_guide, official_docs
    description: Optional[str] = None

class RoadmapTopic(BaseModel):
    id: str
    title: str
    skill: str
    objective: str
    why_improvement_needed: str
    current_level: Optional[str] = None
    target_level: Optional[str] = None
    learning_objectives: List[str] = []
    ordered_steps: List[str] = []
    resources: List[ResourceReference] = []
    exercise: Optional[str] = None
    estimated_duration: str = "Estimated: 6-8 hours"
    estimated_hours: int = 8
    measurable_criterion: str = "Achieve >=75% in module practice test and push working code to repository."
    progress_status: str = "Not Started"  # "Not Started", "In Progress", "Completed"
    is_completed: bool = False

class RoadmapPhase(BaseModel):
    phase_number: int
    title: str
    description: str
    estimated_weeks: int
    topics: List[RoadmapTopic] = []
    mini_project: Optional[Dict[str, Any]] = None

class RoadmapGenerateRequest(BaseModel):
    target_career_domain: str
    weekly_hours_available: Optional[int] = 10
    replace_existing: bool = False

class RoadmapResponse(BaseModel):
    id: str
    user_id: str
    target_career_domain: str
    target_career_title: str
    baseline_score: float
    priority_skill_gaps: List[str] = []
    phases: List[RoadmapPhase] = []
    total_estimated_weeks: int = 0
    completion_percentage: float = 0.0
    requires_assessment: bool = False
    message: Optional[str] = None
    next_action: Optional[str] = None
    assessment_id: Optional[str] = None
    created_at: str
    updated_at: str

class RoadmapProgressUpdate(BaseModel):
    topic_id: str
    completed: Optional[bool] = None
    progress_status: Optional[str] = None
