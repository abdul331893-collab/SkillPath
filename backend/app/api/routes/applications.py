import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, require_admin
from app.core.permissions import AuthenticatedUser, UserRole
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
    ApplicationStatus,
    StatusHistoryItem
)
from app.repositories.firestore_repo import FirestoreRepository
from app.core.logging import logger

router = APIRouter(prefix="/applications", tags=["Student Applications"])

@router.post("/apply", response_model=ApplicationResponse)
async def submit_application(
    req: ApplicationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Submits an official application for an active job or internship.
    - Validates caller authentication
    - Validates opportunity existence and active state
    - Prevents duplicate applications for the same listing
    - Persists application record to Firestore
    - Initializes status to 'Submitted' and logs status history
    """
    job_doc = FirestoreRepository.get_document("jobs", req.job_id)
    if not job_doc or not job_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected opportunity is no longer accepting applications or does not exist."
        )

    # Prevent duplicate applications
    student_apps = FirestoreRepository.query_documents(
        "applications",
        filters=[("student_id", "==", current_user.uid)],
        limit=100
    )
    if not student_apps:
        student_apps = FirestoreRepository.query_documents(
            "applications",
            filters=[("user_id", "==", current_user.uid)],
            limit=100
        )
    existing_apps = [a for a in student_apps if a.get("job_id") == req.job_id]
    active_existing = [a for a in existing_apps if a.get("status") != ApplicationStatus.WITHDRAWN.value]
    if active_existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You have already applied for '{job_doc.get('title')}'. Your current status is: {active_existing[0].get('status')}."
        )

    # Retrieve student profile snapshot
    student_doc = FirestoreRepository.get_document("users", current_user.uid) or {}
    student_name = student_doc.get("name") or current_user.name or current_user.email.split("@")[0].capitalize()
    resume_url = student_doc.get("resume_url")

    # If specific resume_id requested, check it
    if req.resume_id:
        resume_doc = FirestoreRepository.get_document("resumes", req.resume_id)
        if resume_doc and resume_doc.get("user_id") == current_user.uid:
            resume_url = resume_doc.get("file_url")

    app_id = f"app_{uuid.uuid4().hex[:12]}"
    now_str = datetime.now(timezone.utc).isoformat()

    initial_history = [
        {
            "status": ApplicationStatus.SUBMITTED.value,
            "timestamp": now_str,
            "updated_by": student_name,
            "notes": "Application submitted by student"
        }
    ]

    application_data = {
        "id": app_id,
        "student_id": current_user.uid,
        "student_name": student_name,
        "student_email": current_user.email,
        "job_id": req.job_id,
        "job_title": job_doc.get("title", "Opportunity"),
        "company": job_doc.get("company", "Company"),
        "opportunity_type": job_doc.get("opportunity_type", "Job"),
        "location": job_doc.get("location", "Remote"),
        "work_mode": job_doc.get("work_mode", "Remote"),
        "resume_id": req.resume_id,
        "resume_url": resume_url,
        "cover_letter": req.cover_letter.strip() if req.cover_letter else None,
        "submission_date": now_str,
        "status": ApplicationStatus.SUBMITTED.value,
        "admin_notes": None,
        "status_history": initial_history,
        "created_at": now_str,
        "updated_at": now_str,
    }

    FirestoreRepository.set_document("applications", app_id, application_data)
    logger.info(f"Student {current_user.uid} applied to {req.job_id} -> App ID {app_id}")

    return ApplicationResponse(**application_data)

@router.get("/my", response_model=List[ApplicationResponse])
async def get_my_applications(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Retrieves all applications submitted by the authenticated student.
    Internal administrator notes are strictly masked to preserve confidentiality.
    """
    apps = FirestoreRepository.query_documents(
        "applications",
        filters=[("student_id", "==", current_user.uid)],
        limit=100
    )
    if not apps:
        apps = FirestoreRepository.query_documents(
            "applications",
            filters=[("user_id", "==", current_user.uid)],
            limit=100
        )

    # Sort descending by submission date
    apps.sort(key=lambda x: x.get("submission_date", ""), reverse=True)

    results = []
    for a in apps:
        # Mask admin notes for student privacy
        clean_app = dict(a)
        clean_app["admin_notes"] = None
        results.append(ApplicationResponse(**clean_app))

    return results

@router.patch("/{app_id}/withdraw", response_model=ApplicationResponse)
async def withdraw_my_application(
    app_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Allows a student to withdraw their active application.
    Enforces student ownership validation.
    """
    doc = FirestoreRepository.get_document("applications", app_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if doc.get("student_id") != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify another student's application."
        )

    if doc.get("status") in (
        ApplicationStatus.SELECTED.value,
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.WITHDRAWN.value
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot withdraw an application with final status: {doc.get('status')}."
        )

    now_str = datetime.now(timezone.utc).isoformat()
    history = doc.get("status_history", [])
    history.append({
        "status": ApplicationStatus.WITHDRAWN.value,
        "timestamp": now_str,
        "updated_by": current_user.name or current_user.email,
        "notes": "Withdrawn by candidate"
    })

    updates = {
        "status": ApplicationStatus.WITHDRAWN.value,
        "status_history": history,
        "updated_at": now_str
    }

    updated_doc = FirestoreRepository.update_document("applications", app_id, updates)
    clean_app = dict(updated_doc or doc)
    clean_app["admin_notes"] = None
    return ApplicationResponse(**clean_app)

@router.get("", response_model=List[ApplicationResponse])
async def list_all_applications_admin(
    status: Optional[str] = Query(None, description="Filter by application status"),
    opportunity_type: Optional[str] = Query(None, description="Filter by Job or Internship"),
    job_id: Optional[str] = Query(None, description="Filter by specific job listing"),
    q: Optional[str] = Query(None, description="Search candidate name, email, or company"),
    admin: AuthenticatedUser = Depends(require_admin)
):
    """
    Administrator endpoint: Lists all student applications across the entire platform.
    Includes administrator review notes and status history.
    """
    filters = []
    if status and status != "all":
        filters.append(("status", "==", status))
    if job_id:
        filters.append(("job_id", "==", job_id))

    apps = FirestoreRepository.query_documents("applications", filters=filters, limit=500)

    # In-memory post-filters for flexible search and opportunity type
    filtered = []
    for a in apps:
        if a.get("is_deleted", False) and status != "Archived":
            continue
        if opportunity_type and opportunity_type != "all":
            if a.get("opportunity_type", "Job").lower() != opportunity_type.lower():
                continue
        if q:
            search_str = f"{a.get('student_name', '')} {a.get('student_email', '')} {a.get('job_title', '')} {a.get('company', '')}".lower()
            if q.lower() not in search_str:
                continue
        filtered.append(a)

    # Sort descending by submission date
    filtered.sort(key=lambda x: x.get("submission_date", ""), reverse=True)
    return [ApplicationResponse(**a) for a in filtered]

@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application_details(
    app_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves full details of a specific application.
    Students can only view their own; administrators can view any with admin notes.
    """
    doc = FirestoreRepository.get_document("applications", app_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    is_admin = current_user.role == UserRole.ADMIN
    if not is_admin and doc.get("student_id") != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot view this application."
        )

    clean_app = dict(doc)
    if not is_admin:
        clean_app["admin_notes"] = None

    return ApplicationResponse(**clean_app)

ALLOWED_TRANSITIONS = {
    ApplicationStatus.SUBMITTED: [
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    ],
    ApplicationStatus.UNDER_REVIEW: [
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    ],
    ApplicationStatus.SHORTLISTED: [
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.SELECTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    ],
    ApplicationStatus.INTERVIEW: [
        ApplicationStatus.SELECTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    ],
    ApplicationStatus.SELECTED: [],  # Terminal
    ApplicationStatus.REJECTED: [],  # Terminal
    ApplicationStatus.WITHDRAWN: [],  # Terminal
}

@router.patch("/{app_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    app_id: str,
    update: ApplicationStatusUpdate,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """
    Administrator endpoint: Updates application review status and records review notes.
    Strictly validates allowed status transitions and persists audit trail in status history.
    """
    doc = FirestoreRepository.get_document("applications", app_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    current_status_str = doc.get("status", ApplicationStatus.SUBMITTED.value)
    try:
        current_status_enum = ApplicationStatus(current_status_str)
    except ValueError:
        current_status_enum = ApplicationStatus.SUBMITTED

    target_status = update.status

    # Validate allowed transition if status is being changed
    if current_status_enum != target_status:
        allowed = ALLOWED_TRANSITIONS.get(current_status_enum, [])
        if target_status not in allowed:
            allowed_names = [s.value for s in allowed]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status transition from '{current_status_str}' to '{target_status.value}'. "
                    f"Allowed transitions from '{current_status_str}': {', '.join(allowed_names) if allowed_names else 'None (terminal state)'}."
                )
            )

    now_str = datetime.now(timezone.utc).isoformat()
    history = list(doc.get("status_history", []))
    history.append({
        "status": update.status.value,
        "timestamp": now_str,
        "updated_by": admin.name or admin.email,
        "notes": update.admin_notes or f"Status updated to {update.status.value}"
    })

    updates = {
        "status": update.status.value,
        "status_history": history,
        "updated_at": now_str
    }
    if update.admin_notes is not None:
        updates["admin_notes"] = update.admin_notes

    updated_doc = FirestoreRepository.update_document("applications", app_id, updates)
    return ApplicationResponse(**(updated_doc or doc))

@router.delete("/{app_id}")
async def delete_application(
    app_id: str,
    hard_delete: bool = Query(False, description="Whether to permanently remove the document"),
    admin: AuthenticatedUser = Depends(require_admin)
):
    """
    Administrator endpoint: Deletes or archives a student application.
    Enforces administrator authorization, audit logging, and relationship integrity.
    Never deletes the student account, profile, resume, or job opportunity listing.
    """
    doc = FirestoreRepository.get_document("applications", app_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    now_str = datetime.now(timezone.utc).isoformat()
    if hard_delete:
        FirestoreRepository.delete_document("applications", app_id)
        logger.info(f"Admin {admin.uid} ({admin.email}) permanently deleted application {app_id}")
        return {
            "status": "success",
            "message": f"Application {app_id} permanently deleted.",
            "deleted_id": app_id,
            "hard_deleted": True
        }
    else:
        history = list(doc.get("status_history", []))
        history.append({
            "status": "Archived",
            "timestamp": now_str,
            "updated_by": admin.name or admin.email,
            "notes": f"Archived/deleted by administrator {admin.email}"
        })
        FirestoreRepository.update_document("applications", app_id, {
            "status": "Archived",
            "is_deleted": True,
            "deleted_at": now_str,
            "deleted_by": admin.uid,
            "status_history": history
        })
        logger.info(f"Admin {admin.uid} ({admin.email}) archived application {app_id}")
        return {
            "status": "success",
            "message": f"Application {app_id} archived and removed from active pipeline.",
            "deleted_id": app_id,
            "hard_deleted": False
        }
