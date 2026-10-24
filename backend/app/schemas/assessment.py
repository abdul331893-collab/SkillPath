from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class QuestionType(str, Enum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    DESCRIPTIVE = "descriptive"

class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ADAPTIVE = "adaptive"

class AssessmentFocus(str, Enum):
    ALL_SKILLS = "all_skills"
    SELECTED_SKILLS = "selected_skills"
    PROJECT_BASED = "project_based"

class QuestionPublic(BaseModel):
    id: str
    domain: str
    skill: str
    related_project: Optional[str] = None
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    options: Optional[List[str]] = None  # None for short answer / descriptive
    points: float = 10.0
    source_reference: Optional[str] = None

class QuestionAdmin(QuestionPublic):
    correct_answer: Optional[Union[str, int]] = None
    rubric: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None

class QuestionGenerated(BaseModel):
    """Schema used to strictly parse and validate each question output from Gemini."""
    skill: str
    question_text: str
    question_type: QuestionType = QuestionType.MCQ
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    options: Optional[List[str]] = None
    correct_answer: Optional[Union[str, int]] = None
    rubric: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    points: float = 10.0
    related_project: Optional[str] = None
    source_reference: Optional[str] = None

    @field_validator("options", mode="before")
    @classmethod
    def clean_options(cls, v):
        if isinstance(v, list):
            cleaned = [str(opt).strip() for opt in v if str(opt).strip()]
            return cleaned if cleaned else None
        return None

class QuestionCreate(BaseModel):
    domain: str
    skill: str
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    options: Optional[List[str]] = None
    correct_answer: Optional[Union[str, int]] = None
    rubric: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    points: float = 10.0
    related_project: Optional[str] = None
    source_reference: Optional[str] = None

class AnswerSubmissionItem(BaseModel):
    question_id: str
    answer: str  # Option text for MCQ, or text paragraph for descriptive / short answer

class AssessmentSubmissionRequest(BaseModel):
    domain: Optional[str] = "Frontend Development"
    assessment_id: Optional[str] = None
    answers: List[AnswerSubmissionItem]
    time_taken_seconds: Optional[int] = None

class AssessmentAnswersUpdateRequest(BaseModel):
    answers: Dict[str, str] = {}
    time_remaining_seconds: Optional[int] = None

class QuestionEvaluationResult(BaseModel):
    question_id: str
    skill: str
    question_type: QuestionType
    points_awarded: float
    max_points: float
    is_correct: Optional[bool] = None
    feedback: str
    improvement_suggestion: Optional[str] = None

class AssessmentGenerateRequest(BaseModel):
    confirmed_skills: List[str] = []
    selected_skills: Optional[List[str]] = None
    projects: List[Dict[str, Any]] = []
    domain: Optional[str] = "Frontend Development"
    question_count: int = 20
    focus: str = "all_skills"  # all_skills, selected_skills, project_based
    difficulty: str = "adaptive"  # adaptive, beginner, intermediate, advanced
    question_types: str = "combination"  # mcq, short_answer, combination
    duration_minutes: Optional[int] = None

    @field_validator("question_count")
    @classmethod
    def validate_question_count(cls, v: int) -> int:
        if v not in (20, 30, 50):
            raise ValueError("question_count must be exactly 20, 30, or 50")
        return v

class AssessmentRecordResponse(BaseModel):
    id: str
    user_id: str
    domain: str
    requested_question_count: int
    actual_question_count: int
    focus: str
    difficulty: str
    question_types: str
    duration_minutes: Optional[int] = None
    status: str
    created_at: str
    questions: List[QuestionPublic]
    saved_answers: Optional[Dict[str, str]] = {}

class SkillScoreBreakdown(BaseModel):
    skill: str
    earned_points: float
    available_points: float
    score_percentage: float
    proficiency_level: str  # Beginner, Intermediate, Proficient, Expert
    performance_level: str = "Moderate"  # Strong, Moderate, Needs Improvement, Unassessed
    strong_areas: List[str] = []
    weak_areas: List[str] = []
    answer_evidence: Optional[str] = None
    improvement_suggestion: Optional[str] = None

class AssessmentResultResponse(BaseModel):
    attempt_id: str
    user_id: str
    domain: str
    total_score_percentage: float
    total_earned_points: float
    total_available_points: float
    submitted_at: str
    skill_breakdown: List[SkillScoreBreakdown]
    unassessed_skills: List[str] = []
    strengths_summary: List[str] = []
    weaknesses_summary: List[str] = []
    question_evaluations: List[QuestionEvaluationResult]
    overall_feedback: str
    recommended_next_steps: List[str]
    assessment_id: Optional[str] = None
    status: Optional[str] = "completed"

class AssessmentJobResponse(BaseModel):
    job_id: str
    user_id: str
    status: str  # "queued", "processing", "completed", "failed"
    progress_message: Optional[str] = None
    requested_question_count: Optional[int] = None
    domain: Optional[str] = None
    assessment_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    assessment: Optional[AssessmentRecordResponse] = None

