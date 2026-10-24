from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from app.api.dependencies import get_current_user
from app.core.permissions import AuthenticatedUser
from app.schemas.assessment import (
    QuestionPublic,
    AssessmentGenerateRequest,
    AssessmentRecordResponse,
    AssessmentSubmissionRequest,
    AssessmentAnswersUpdateRequest,
    AssessmentResultResponse,
    AssessmentJobResponse
)
from app.services.assessment_service import AssessmentService
from app.repositories.firestore_repo import FirestoreRepository

router = APIRouter(prefix="/assessments", tags=["Skill Assessments"])

@router.post("/generate/start", status_code=status.HTTP_202_ACCEPTED, response_model=AssessmentJobResponse)
async def start_assessment_generation_job(
    req: AssessmentGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Step A: Validates requirements, creates an asynchronous generation job in Firestore,
    enqueues the background question synthesizer, and returns HTTP 202 Accepted.
    """
    job = AssessmentService.start_generation_job(user_id=current_user.uid, req=req)
    background_tasks.add_task(
        AssessmentService.execute_generation_job,
        job["job_id"],
        current_user.uid,
        req
    )
    return AssessmentJobResponse(**job)

@router.get("/jobs/active", response_model=Optional[AssessmentJobResponse])
async def get_active_generation_job(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves any currently running generation job for the authenticated student."""
    job = AssessmentService.get_active_generation_job(current_user.uid)
    if not job:
        return None
    return AssessmentJobResponse(**job)

@router.get("/jobs/{job_id}", response_model=AssessmentJobResponse)
async def get_generation_job_status(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Step C: Polls generation job status. Returns processing, completed, or failed states.
    When completed, returns the full generated assessment payload.
    """
    job = AssessmentService.get_generation_job(job_id, current_user.uid)
    return AssessmentJobResponse(**job)

@router.post("/generate", response_model=AssessmentRecordResponse)
async def generate_assessment(
    req: AssessmentGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Generates a personalized, multi-question technical assessment using the Gemini API.
    Supports exactly 20, 30, or 50 questions, evaluated against confirmed skills and real projects.
    Enforces student ownership and persists the assessment record securely in Firestore.
    """
    return AssessmentService.create_and_generate_assessment(
        user_id=current_user.uid,
        req=req
    )

@router.get("/questions", response_model=List[QuestionPublic])
async def get_assessment_questions(
    domain: str = Query("Frontend Development", description="Target technical domain"),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Legacy endpoint retrieving assessment questions for the chosen domain."""
    return AssessmentService.get_questions_for_domain(domain)

@router.get("/history", response_model=List[AssessmentResultResponse])
async def get_assessment_history(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieves student's previous assessment attempts."""
    attempts = FirestoreRepository.query_documents(
        "assessments",
        filters=[("user_id", "==", current_user.uid), ("status", "==", "completed")],
        limit=50
    )
    results = []
    for a in attempts:
        res_data = a.get("result") or a
        if "total_score_percentage" in res_data:
            results.append(AssessmentResultResponse(**res_data))
    return results

@router.get("/latest", response_model=Optional[AssessmentResultResponse])
async def get_latest_assessment(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieves the latest completed assessment result for the current user."""
    attempts = FirestoreRepository.query_documents(
        "assessments",
        filters=[("user_id", "==", current_user.uid), ("status", "==", "completed")],
        limit=10
    )
    if not attempts:
        return None
    attempts.sort(key=lambda a: a.get("completed_at") or a.get("created_at") or "", reverse=True)
    latest = attempts[0]
    res_data = latest.get("result") or latest
    if "total_score_percentage" in res_data:
        return AssessmentResultResponse(**res_data)
    return None

@router.get("/{assessment_id}", response_model=AssessmentRecordResponse)
async def get_assessment_by_id(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves assessment metadata, question count, and public questions.
    Prevents access by students who do not own the assessment.
    """
    return AssessmentService.get_assessment(assessment_id, current_user.uid)

@router.get("/{assessment_id}/questions", response_model=List[QuestionPublic])
async def get_assessment_questions_by_id(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves the persisted generated questions for a student's active assessment.
    Answer keys and grading rubrics are strictly stripped from the returned response.
    """
    return AssessmentService.get_assessment_questions(assessment_id, current_user.uid)

@router.put("/{assessment_id}/answers")
async def update_assessment_answers(
    assessment_id: str,
    body: AssessmentAnswersUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Persists student's intermediate answers and navigation progress safely.
    Prevents modifications if the assessment has already been submitted.
    """
    return AssessmentService.save_answers(
        assessment_id=assessment_id,
        user_id=current_user.uid,
        answers=body.answers,
        time_remaining_seconds=body.time_remaining_seconds
    )

@router.post("/{assessment_id}/submit", response_model=AssessmentResultResponse)
async def submit_specific_assessment(
    assessment_id: str,
    submission: AssessmentSubmissionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Submits and evaluates answers for a specific generated assessment.
    Evaluates MCQs and short answer rubrics, updates student proficiencies,
    and returns a comprehensive performance report.
    """
    return AssessmentService.evaluate_submission(
        user_id=current_user.uid,
        submission=submission,
        assessment_id=assessment_id
    )

@router.get("/{assessment_id}/report", response_model=AssessmentResultResponse)
async def get_assessment_report(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves the performance report for a completed assessment."""
    return AssessmentService.get_assessment_report(assessment_id, current_user.uid)

@router.post("/submit", response_model=AssessmentResultResponse)
async def submit_assessment(
    submission: AssessmentSubmissionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Legacy general submission endpoint. Evaluates submission answers,
    updates user profile proficiencies, and saves the assessment result.
    """
    if not submission.answers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission must contain at least one answered question"
        )

    return AssessmentService.evaluate_submission(
        user_id=current_user.uid,
        submission=submission,
        assessment_id=submission.assessment_id
    )
