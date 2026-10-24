from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.dependencies import get_current_user
from app.core.permissions import AuthenticatedUser
from app.schemas.job import JobMatchResult, JobListingResponse
from app.services.job_matching import JobMatchingService
from app.repositories.firestore_repo import FirestoreRepository

router = APIRouter(prefix="/jobs", tags=["Job Recommendations"])

@router.get("", response_model=List[JobMatchResult])
async def get_matched_jobs(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    work_mode: Optional[str] = Query(None, description="Filter by Remote/Hybrid/Onsite"),
    opportunity_type: Optional[str] = Query(None, description="Filter by Job or Internship"),
    q: Optional[str] = Query(None, description="Keyword search"),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Returns verified job recommendations ranked by skill match score,
    checking mandatory eligibility requirements against candidate profile.
    """
    user = FirestoreRepository.get_document("users", current_user.uid) or {}
    validated_skills = user.get("validated_skills", {})
    education = user.get("education_level")
    
    # Retrieve confirmed skills from profile, claimed skills, or latest confirmed resume
    confirmed_skills_set = set(user.get("claimed_skills", [])) | set(user.get("technical_skills", []))
    if not confirmed_skills_set:
        latest_resumes = FirestoreRepository.query_documents(
            "resumes", filters=[("user_id", "==", current_user.uid)], limit=1
        )
        if latest_resumes:
            for s in latest_resumes[0].get("confirmed_skills", []):
                s_name = s.get("name") if isinstance(s, dict) else str(s)
                if s_name:
                    confirmed_skills_set.add(s_name)

    return JobMatchingService.match_jobs_for_candidate(
        user_skills=validated_skills,
        user_confirmed_skills=list(confirmed_skills_set),
        user_education=education,
        user_experience_years=float(user.get("experience_years", 0.0)),
        domain_filter=domain,
        work_mode_filter=work_mode,
        opportunity_type_filter=opportunity_type,
        search_query=q
    )

@router.get("/{job_id}", response_model=JobListingResponse)
async def get_job_details(job_id: str):
    """Retrieves full job description and requirements."""
    doc = FirestoreRepository.get_document("jobs", job_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobListingResponse(**doc)
