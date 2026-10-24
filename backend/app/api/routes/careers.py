from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from app.api.dependencies import get_current_user
from app.core.permissions import AuthenticatedUser
from app.schemas.career import CareerRecommendationResponse
from app.services.career_service import CareerService
from app.repositories.firestore_repo import FirestoreRepository

router = APIRouter(prefix="/careers", tags=["Career Recommendations"])

@router.get("/domains")
async def list_career_domains():
    """Lists all configured career domains and requirements."""
    return CareerService.get_all_domains()

@router.get("/recommendations", response_model=List[CareerRecommendationResponse])
async def get_career_recommendations(
    regenerate: bool = Query(False, description="Force recomputation of recommendations"),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves persisted career recommendations or computes transparent recommendations
    derived from validated assessment scores, education level, confirmed skills, and projects.
    Persists recommendations in Firestore under the student UID.
    """
    # 1. Check for persisted recommendations in Firestore if not explicitly regenerating
    if not regenerate:
        saved_doc = FirestoreRepository.get_document("career_recommendations", current_user.uid)
        if saved_doc and saved_doc.get("recommendations"):
            try:
                return [CareerRecommendationResponse(**r) for r in saved_doc["recommendations"]]
            except Exception:
                pass

    # 2. Compute recommendations using authenticated candidate profile evidence
    user = FirestoreRepository.get_document("users", current_user.uid) or {}
    validated_skills = user.get("validated_skills", {})
    education = user.get("education_level")
    interests = user.get("interests", [])
    confirmed_skills = list(set(user.get("claimed_skills", []) + user.get("technical_skills", [])))

    recommendations = CareerService.recommend_careers(
        user_skills=validated_skills,
        user_confirmed_skills=confirmed_skills,
        user_education=education,
        user_interests=interests,
        user_id=current_user.uid
    )

    # 3. Persist generated recommendations in Firestore
    now_str = datetime.now(timezone.utc).isoformat()
    FirestoreRepository.set_document("career_recommendations", current_user.uid, {
        "user_id": current_user.uid,
        "recommendations": [r.model_dump() for r in recommendations],
        "updated_at": now_str
    })

    return recommendations

@router.post("/recommendations/regenerate", response_model=List[CareerRecommendationResponse])
async def regenerate_career_recommendations(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Explicit endpoint to force re-computation of recommendations when evidence changes."""
    return await get_career_recommendations(regenerate=True, current_user=current_user)
