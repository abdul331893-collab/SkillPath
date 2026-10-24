from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone
from app.api.dependencies import get_current_user
from app.core.permissions import AuthenticatedUser
from app.schemas.profile import ProfileUpdate, ProfileResponse
from app.repositories.firestore_repo import FirestoreRepository

router = APIRouter(prefix="/profiles", tags=["Student Profiles"])

def _calculate_profile_completion(data: dict) -> int:
    fields = [
        "name", "education_level", "degree", "institution",
        "graduation_year", "technical_skills", "projects",
        "interests", "preferred_career_domains", "resume_url"
    ]
    completed = 0
    for f in fields:
        val = data.get(f)
        if val:
            if isinstance(val, list) and len(val) > 0:
                completed += 1
            elif not isinstance(val, list):
                completed += 1
    return int((completed / len(fields)) * 100)

@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieves current student's profile."""
    doc = FirestoreRepository.get_document("users", current_user.uid)
    if not doc:
        # Create empty profile baseline
        now_str = datetime.now(timezone.utc).isoformat()
        doc = {
            "uid": current_user.uid,
            "email": current_user.email,
            "name": current_user.name or current_user.email.split("@")[0].capitalize(),
            "role": current_user.role.value,
            "technical_skills": [],
            "projects": [],
            "interests": [],
            "preferred_career_domains": [],
            "completion_percentage": 10,
            "created_at": now_str,
            "updated_at": now_str,
        }
        FirestoreRepository.set_document("users", current_user.uid, doc)

    doc["completion_percentage"] = _calculate_profile_completion(doc)
    return ProfileResponse(**doc)

@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    updates: ProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Updates candidate profile details."""
    doc = FirestoreRepository.get_document("users", current_user.uid) or {
        "uid": current_user.uid,
        "email": current_user.email,
        "role": current_user.role.value
    }

    update_dict = updates.model_dump(exclude_unset=True)
    doc.update(update_dict)
    doc["completion_percentage"] = _calculate_profile_completion(doc)
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()

    FirestoreRepository.set_document("users", current_user.uid, doc)
    return ProfileResponse(**doc)
