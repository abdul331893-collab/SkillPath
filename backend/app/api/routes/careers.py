from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from app.api.dependencies import get_current_user
from app.core.permissions import AuthenticatedUser
from app.schemas.career import CareerRecommendationResponse
from app.services.career_service import CareerService
from app.repositories.firestore_repo import FirestoreRepository

router = APIRouter(prefix="/careers", tags=["Career Recommendations"])

import logging

logger = logging.getLogger("skillpath.careers")

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
    saved_doc = None
    # 1. Check for persisted recommendations in Firestore if not explicitly regenerating
    if not regenerate:
        try:
            saved_doc = FirestoreRepository.get_document("career_recommendations", current_user.uid)
            if saved_doc and saved_doc.get("recommendations"):
                saved_recs = [CareerRecommendationResponse(**r) for r in saved_doc["recommendations"]]
                
                # Check if any saved recommendation previously had insufficient data
                has_insufficient = any(r.insufficient_data for r in saved_recs)
                if not has_insufficient:
                    return saved_recs
                
                # If there are insufficient data entries, check if user has since completed an assessment
                user_assessments = FirestoreRepository.query_documents(
                    "assessments",
                    filters=[("user_id", "==", current_user.uid)],
                    limit=10
                )
                if not user_assessments:
                    user_assessments = FirestoreRepository.query_documents(
                        "assessments",
                        filters=[("student_id", "==", current_user.uid)],
                        limit=10
                    )
                
                has_completed = any(
                    str(a.get("status", "")).lower() == "completed"
                    or (isinstance(a.get("result"), dict) and a.get("result", {}).get("total_score_percentage") is not None)
                    or a.get("total_score_percentage") is not None
                    for a in user_assessments
                )
                
                # If no new assessment evidence has arrived, return the saved recommendations
                if not has_completed:
                    return saved_recs
                # If new completed assessment exists, fall through to recompute with the new evidence
        except Exception as e:
            logger.warning(f"Error checking cached recommendations: {e}")

    # 2. Compute recommendations using authenticated candidate profile evidence
    try:
        user = FirestoreRepository.get_document("users", current_user.uid) or {}
        validated_skills = user.get("validated_skills", {}) if isinstance(user.get("validated_skills"), dict) else {}
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
    except Exception as e:
        logger.error(f"Error computing career recommendations: {e}")
        # Safeguard: Never overwrite valid saved recommendations with an empty response or failure
        if saved_doc and saved_doc.get("recommendations"):
            try:
                return [CareerRecommendationResponse(**r) for r in saved_doc["recommendations"]]
            except Exception:
                pass
        raise

@router.post("/recommendations/regenerate", response_model=List[CareerRecommendationResponse])
async def regenerate_career_recommendations(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Explicit endpoint to force re-computation of recommendations when evidence changes."""
    return await get_career_recommendations(regenerate=True, current_user=current_user)
