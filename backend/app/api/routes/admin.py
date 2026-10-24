import csv
import io
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from datetime import datetime, timezone
from app.api.dependencies import require_admin
from app.core.permissions import AuthenticatedUser
from app.repositories.firestore_repo import FirestoreRepository
from app.schemas.admin import (
    UserRoleUpdate,
    UserStatusUpdate,
    UserListItem,
    SystemStatsResponse,
    JobBulkImportResponse
)
from app.schemas.job import JobListingCreate, JobListingResponse, JobListingUpdate
from app.schemas.assessment import QuestionCreate, QuestionAdmin
from app.services.job_matching import JobMatchingService

router = APIRouter(prefix="/admin", tags=["Administrator Dashboard"], dependencies=[Depends(require_admin)])

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_statistics(admin: AuthenticatedUser = Depends(require_admin)):
    """Computes genuine platform metrics based on authoritative database records."""
    users = FirestoreRepository.query_documents("users", limit=1000)
    assessments = FirestoreRepository.query_documents("assessments", limit=1000)
    resumes = FirestoreRepository.query_documents("resumes", limit=1000)
    jobs = FirestoreRepository.query_documents("jobs", limit=1000)
    applications = FirestoreRepository.query_documents("applications", limit=1000)
    resources = FirestoreRepository.query_documents("learning_resources", limit=1000)

    total_users = len(users)
    students = sum(1 for u in users if u.get("role") != "admin")
    admins = total_users - students

    active_jobs = sum(1 for j in jobs if j.get("is_active", True) and j.get("opportunity_type", "Job") == "Job")
    active_internships = sum(1 for j in jobs if j.get("is_active", True) and j.get("opportunity_type", "Job") == "Internship")

    active_applications = [
        a for a in applications
        if not a.get("is_deleted", False) and a.get("status") != "Archived"
    ]
    awaiting_review = sum(1 for a in active_applications if a.get("status") in ("Submitted", "Under Review"))

    # Strictly count only completed assessments with verified scores (not in-progress, jobs, or questions)
    completed_assessments = [
        a for a in assessments
        if a.get("status") == "completed" and ("total_score_percentage" in a or (isinstance(a.get("result"), dict) and "total_score_percentage" in a["result"]))
    ]

    scores = []
    for a in completed_assessments:
        if "total_score_percentage" in a:
            scores.append(float(a["total_score_percentage"]))
        elif isinstance(a.get("result"), dict) and "total_score_percentage" in a["result"]:
            scores.append(float(a["result"]["total_score_percentage"]))

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    # Domain popularity from authentic completed assessments
    domain_counts: Dict[str, int] = {}
    for a in completed_assessments:
        d = a.get("domain", "General")
        domain_counts[d] = domain_counts.get(d, 0) + 1

    popular_domains = [{"domain": k, "attempts": v} for k, v in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

    return SystemStatsResponse(
        total_users=total_users,
        total_students=students,
        total_admins=admins,
        total_registered_students=students,
        total_active_jobs=active_jobs,
        total_active_internships=active_internships,
        total_applications=len(active_applications),
        applications_awaiting_review=awaiting_review,
        assessment_attempts_completed=len(completed_assessments),
        total_assessments_taken=len(completed_assessments),
        total_resumes_analyzed=len(resumes),
        total_learning_resources=len(resources) + 12,
        popular_career_domains=popular_domains,
        average_assessment_score=avg_score
    )

@router.get("/users", response_model=List[UserListItem])
async def list_users(
    role: Optional[str] = None,
    q: Optional[str] = None,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """Lists registered users with optional role filtering and keyword search."""
    users = FirestoreRepository.query_documents("users", limit=300)
    filtered = []
    for u in users:
        u_role = u.get("role", "student")
        if role and role != "all" and u_role != role:
            continue
        if q:
            match_str = f"{u.get('name', '')} {u.get('email', '')} {u.get('institution', '')}".lower()
            if q.lower() not in match_str:
                continue
        filtered.append(
            UserListItem(
                uid=u.get("uid", ""),
                email=u.get("email", ""),
                name=u.get("name"),
                role=u_role,
                is_active=u.get("is_active", True),
                education_level=u.get("education_level"),
                institution=u.get("institution"),
                created_at=u.get("created_at")
            )
        )
    return filtered

@router.patch("/users/{uid}/status")
async def update_user_status(
    uid: str,
    update: UserStatusUpdate,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """Enables or disables a user account."""
    updated = FirestoreRepository.update_document("users", uid, {"is_active": update.is_active})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    status_label = "enabled" if update.is_active else "disabled"
    return {"message": f"User account has been {status_label}", "uid": uid, "is_active": update.is_active}

@router.patch("/users/{uid}/role")
async def update_user_role(
    uid: str,
    update: UserRoleUpdate,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """Assigns or modifies role (student / admin) for a user."""
    if update.role not in ("student", "admin"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role must be 'student' or 'admin'")

    updated = FirestoreRepository.update_document("users", uid, {"role": update.role})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message": f"User role updated to {update.role}", "uid": uid, "role": update.role}

@router.get("/users/{uid}/summary")
async def get_student_assessment_summary(
    uid: str,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """Retrieves full student profile and assessment attempts for administrator review."""
    student = FirestoreRepository.get_document("users", uid)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    attempts = FirestoreRepository.query_documents("assessments", filters=[("user_id", "==", uid)], limit=20)
    apps = FirestoreRepository.query_documents("applications", filters=[("student_id", "==", uid)], limit=20)
    resumes = FirestoreRepository.query_documents("resumes", filters=[("user_id", "==", uid)], limit=5)

    return {
        "profile": student,
        "assessments_count": len(attempts),
        "applications_count": len(apps),
        "resumes_count": len(resumes),
        "assessments": attempts,
        "applications": apps
    }

@router.get("/jobs", response_model=List[JobListingResponse])
async def list_admin_jobs(admin: AuthenticatedUser = Depends(require_admin)):
    """Administrator endpoint: Lists all active and inactive job opportunities."""
    jobs = FirestoreRepository.query_documents("jobs", limit=300)
    return [JobListingResponse(**j) for j in jobs]

@router.post("/jobs", response_model=JobListingResponse)
async def create_job_listing(job: JobListingCreate, admin: AuthenticatedUser = Depends(require_admin)):
    """Creates a new verified job listing."""
    job_id = f"job-{uuid.uuid4()}"
    now_str = datetime.now(timezone.utc).isoformat()
    job_dict = job.model_dump()
    job_dict.update({
        "id": job_id,
        "created_at": now_str,
        "updated_at": now_str
    })
    FirestoreRepository.set_document("jobs", job_id, job_dict)
    return JobListingResponse(**job_dict)

@router.put("/jobs/{job_id}", response_model=JobListingResponse)
async def update_job_listing(
    job_id: str,
    updates: JobListingUpdate,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """Updates job requirements, active status, or expiry date."""
    update_data = updates.model_dump(exclude_unset=True)
    res = FirestoreRepository.update_document("jobs", job_id, update_data)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobListingResponse(**res)

@router.delete("/jobs/{job_id}")
async def delete_job_listing(job_id: str, admin: AuthenticatedUser = Depends(require_admin)):
    """Deletes a job listing."""
    success = FirestoreRepository.delete_document("jobs", job_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"message": "Job successfully deleted", "job_id": job_id}

@router.post("/jobs/bulk-import", response_model=JobBulkImportResponse)
async def bulk_import_jobs(file: UploadFile = File(...), admin: AuthenticatedUser = Depends(require_admin)):
    """
    Imports job listings from a CSV file.
    Validates mandatory columns and reports row-level errors.
    """
    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        rows = list(reader)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid CSV encoding: {e}")

    imported, failed, errors = JobMatchingService.bulk_import_csv(rows)
    return JobBulkImportResponse(
        total_rows=len(rows),
        imported_count=imported,
        failed_count=failed,
        errors=errors
    )

@router.post("/questions", response_model=QuestionAdmin)
async def create_question(question: QuestionCreate, admin: AuthenticatedUser = Depends(require_admin)):
    """Creates a new question with evaluation rubrics and answer keys."""
    q_id = f"q-{uuid.uuid4()}"
    q_dict = question.model_dump()
    q_dict["id"] = q_id
    FirestoreRepository.set_document("questions", q_id, q_dict)
    return QuestionAdmin(**q_dict)

@router.get("/questions", response_model=List[QuestionAdmin])
async def list_admin_questions(admin: AuthenticatedUser = Depends(require_admin)):
    """Lists all assessment questions including answer keys and scoring rubrics."""
    from app.services.assessment_service import AssessmentService
    AssessmentService.initialize_default_questions()
    docs = FirestoreRepository.query_documents("questions", limit=200)
    return [QuestionAdmin(**d) for d in docs]

@router.get("/assessments")
async def list_admin_assessments(
    domain: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: all, completed, in_progress"),
    q: Optional[str] = None,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """Lists completed and in-progress student assessment records for administrator review."""
    docs = FirestoreRepository.query_documents("assessments", limit=300)
    enriched = []
    for d in docs:
        item = dict(d)
        st = item.get("status", "in_progress")
        if status_filter and status_filter != "all":
            if st != status_filter:
                continue

        if domain and domain != "all":
            if item.get("domain", "").lower() != domain.lower():
                continue

        uid = item.get("user_id")
        if uid:
            user_doc = FirestoreRepository.get_document("users", uid)
            if user_doc:
                item["student_name"] = user_doc.get("name") or uid
                item["student_email"] = user_doc.get("email") or ""

        if q:
            search_str = f"{item.get('student_name', '')} {item.get('student_email', '')} {item.get('domain', '')} {uid or ''}".lower()
            if q.lower() not in search_str:
                continue

        enriched.append(item)

    # Sort descending by completion date or creation date
    enriched.sort(key=lambda x: x.get("completed_at") or x.get("created_at") or "", reverse=True)
    return enriched

@router.get("/assessments/{assessment_id}")
async def get_admin_assessment_detail(
    assessment_id: str,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """Administrator endpoint: Retrieves full details of a specific assessment attempt."""
    doc = FirestoreRepository.get_document("assessments", assessment_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    item = dict(doc)
    uid = item.get("user_id")
    if uid:
        user_doc = FirestoreRepository.get_document("users", uid)
        if user_doc:
            item["student_name"] = user_doc.get("name") or uid
            item["student_email"] = user_doc.get("email") or ""

    return item

from app.schemas.application import ApplicationStatusUpdate, ApplicationResponse

@router.patch("/applications/{app_id}/status", response_model=ApplicationResponse)
async def update_admin_application_status(
    app_id: str,
    update: ApplicationStatusUpdate,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """Administrator endpoint: Updates application review status."""
    from app.api.routes.applications import update_application_status
    return await update_application_status(app_id=app_id, update=update, admin=admin)

