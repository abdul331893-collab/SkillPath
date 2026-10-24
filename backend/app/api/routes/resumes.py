import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from datetime import datetime, timezone
from app.api.dependencies import get_current_user
from app.core.permissions import AuthenticatedUser, UserRole
from app.services.document_parser import (
    DocumentParser,
    DocumentParsingError,
    DocumentUnsupportedError,
    DocumentEmptyError,
    DocumentCorruptedError,
    DocumentEncryptedError,
    DocumentScannedError
)
from app.services.firebase_service import storage_service
from app.services.resume_analysis import ResumeAnalysisService
from app.schemas.resume import (
    ResumeUploadResponse,
    ResumeExtractedData,
    ResumeLatestResponse,
    ConfirmedExtractionPayload
)
from app.repositories.firestore_repo import FirestoreRepository
from app.core.logging import logger

router = APIRouter(prefix="/resumes", tags=["Resume Processing"])

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_and_analyze_resume(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Uploads candidate resume (PDF or DOCX), extracts text, runs structured analysis,
    and identifies claimed technical skills and domain recommendations.
    Ensures no state is persisted if extraction fails.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required.")

    content = await file.read()

    # 1. Validation and Text Extraction
    valid, validation_err = DocumentParser.validate_file(file.filename, content)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=validation_err)

    try:
        extracted_text = DocumentParser.extract_text(file.filename, content)
    except DocumentUnsupportedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DocumentEmptyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DocumentEncryptedError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except DocumentScannedError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except DocumentCorruptedError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected document parsing failure on {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse document: {str(e)}"
        )

    # 2. Structured Resume Analysis
    try:
        analysis_result = ResumeAnalysisService.analyze_resume(extracted_text)
        extracted_data = analysis_result["extracted_data"]
        recommended_domains = analysis_result["recommended_domains"]
    except Exception as e:
        logger.error(f"Resume structured analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze extracted resume content."
        )

    # 3. Storage Upload (Cloudinary / local fallback)
    try:
        file_url, public_id = storage_service.upload_file(content, file.filename, folder="resumes")
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded resume file."
        )

    # 4. Persistence to Firestore
    resume_id = f"resume_{uuid.uuid4()}"
    now_str = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": resume_id,
        "user_id": current_user.uid,
        "file_name": file.filename,
        "file_url": file_url,
        "public_id": public_id,
        "extracted_data": extracted_data,
        "recommended_domains": recommended_domains,
        "created_at": now_str,
    }
    FirestoreRepository.set_document("resumes", resume_id, doc)

    # 5. Sync claimed skills and recommendations back to student profile
    user_doc = FirestoreRepository.get_document("users", current_user.uid) or {"uid": current_user.uid}
    existing_claimed = set(user_doc.get("claimed_skills", []))
    new_claimed = set(extracted_data.get("claimed_skills", []))
    merged_claimed = list(existing_claimed | new_claimed)

    user_doc["claimed_skills"] = merged_claimed
    user_doc["resume_url"] = file_url
    user_doc["resume_id"] = resume_id
    if recommended_domains and not user_doc.get("preferred_career_domains"):
        user_doc["preferred_career_domains"] = recommended_domains

    FirestoreRepository.set_document("users", current_user.uid, user_doc)

    return ResumeUploadResponse(
        id=resume_id,
        user_id=current_user.uid,
        file_name=file.filename,
        file_url=file_url,
        extracted_data=ResumeExtractedData(**extracted_data),
        recommended_domains=recommended_domains,
        created_at=now_str
    )

@router.get("/latest", response_model=ResumeLatestResponse)
async def get_latest_resume(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Retrieves current user's latest parsed resume.
    Returns HTTP 200 with {"resume": null} if no resume has been uploaded yet,
    guaranteeing a predictable and clean contract for first-time users.
    """
    docs = FirestoreRepository.query_documents("resumes", filters=[("user_id", "==", current_user.uid)], limit=50)
    if not docs:
        return ResumeLatestResponse(resume=None)

    docs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    d = docs[0]
    extracted = d.get("extracted_data")
    if not isinstance(extracted, dict):
        extracted = {}

    return ResumeLatestResponse(
        resume=ResumeUploadResponse(
            id=d.get("id") or str(uuid.uuid4()),
            user_id=d.get("user_id") or current_user.uid,
            file_name=d.get("file_name") or "resume.pdf",
            file_url=d.get("file_url") or "",
            extracted_data=ResumeExtractedData(**extracted),
            recommended_domains=d.get("recommended_domains", []),
            created_at=d.get("created_at") or datetime.now(timezone.utc).isoformat()
        )
    )

@router.get("/{resume_id}", response_model=ResumeUploadResponse)
async def get_resume_by_id(
    resume_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves specific resume by ID with strict ownership verification.
    Students can only view their own resume. Administrators can view any resume.
    """
    doc = FirestoreRepository.get_document("resumes", resume_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume record not found.")

    if current_user.role != UserRole.ADMIN and doc.get("user_id") != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You are not authorized to view another student's resume."
        )

    return ResumeUploadResponse(
        id=doc["id"],
        user_id=doc["user_id"],
        file_name=doc["file_name"],
        file_url=doc["file_url"],
        extracted_data=ResumeExtractedData(**doc["extracted_data"]),
        recommended_domains=doc.get("recommended_domains", []),
        created_at=doc["created_at"]
    )

@router.put("/{resume_id}/confirmed")
async def save_confirmed_extraction(
    resume_id: str,
    payload: ConfirmedExtractionPayload,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Step 2: Saves the student's reviewed and edited skills and projects.
    Distinguishes 'resume-claimed' from 'student-added' skills.
    Synchronizes confirmed skills and projects with student profile in Firestore.
    """
    doc = FirestoreRepository.get_document("resumes", resume_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume record not found.")

    if current_user.role != UserRole.ADMIN and doc.get("user_id") != current_user.uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    skills_data = [s.model_dump() for s in payload.skills]
    projects_data = [p.model_dump() for p in payload.projects]

    doc["confirmed_skills"] = skills_data
    doc["confirmed_projects"] = projects_data
    if payload.recommended_domains:
        doc["recommended_domains"] = payload.recommended_domains

    FirestoreRepository.set_document("resumes", resume_id, doc)

    # Sync back to user profile
    user_doc = FirestoreRepository.get_document("users", current_user.uid) or {"uid": current_user.uid}
    user_doc["claimed_skills"] = [s["name"] for s in skills_data]
    user_doc["projects"] = projects_data
    if payload.recommended_domains:
        user_doc["preferred_career_domains"] = payload.recommended_domains
    FirestoreRepository.set_document("users", current_user.uid, user_doc)

    return {
        "message": "Extracted skills and projects confirmed successfully.",
        "skills": skills_data,
        "projects": projects_data,
        "recommended_domains": doc.get("recommended_domains", [])
    }

@router.get("/{resume_id}/confirmed")
async def get_confirmed_extraction(
    resume_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves confirmed skills and projects for an uploaded resume."""
    doc = FirestoreRepository.get_document("resumes", resume_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume record not found.")

    if current_user.role != UserRole.ADMIN and doc.get("user_id") != current_user.uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    confirmed_skills = doc.get("confirmed_skills")
    if not confirmed_skills:
        # Default from initial extraction
        extracted_skills = doc.get("extracted_data", {}).get("claimed_skills", [])
        confirmed_skills = [{"name": s, "source": "resume-claimed"} for s in extracted_skills]

    confirmed_projects = doc.get("confirmed_projects")
    if not confirmed_projects:
        confirmed_projects = doc.get("extracted_data", {}).get("projects", [])

    return {
        "resume_id": resume_id,
        "skills": confirmed_skills,
        "projects": confirmed_projects,
        "recommended_domains": doc.get("recommended_domains", [])
    }
