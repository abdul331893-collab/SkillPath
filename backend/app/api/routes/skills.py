from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user
from app.core.permissions import AuthenticatedUser
from app.repositories.firestore_repo import FirestoreRepository

router = APIRouter(prefix="/skills", tags=["Skills Analysis"])

@router.get("/analysis")
async def get_skill_analysis(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns full skill analysis distinguishing validated skills from claimed skills,
    highlighting top strengths, weaknesses requiring improvement, and unassessed claimed skills.
    """
    user = FirestoreRepository.get_document("users", current_user.uid) or {}
    validated_skills = user.get("validated_skills", {})  # Dict[str, float]
    claimed_skills = user.get("claimed_skills", [])      # List[str]

    # Categorize validated skills
    strengths = []
    needs_improvement = []

    for skill, score in validated_skills.items():
        entry = {"skill": skill, "score": score}
        if score >= 70.0:
            strengths.append(entry)
        else:
            needs_improvement.append(entry)

    strengths.sort(key=lambda x: x["score"], reverse=True)
    needs_improvement.sort(key=lambda x: x["score"])

    # Claimed but not yet assessed
    validated_lower = {s.lower() for s in validated_skills.keys()}
    unassessed_claimed = [s for s in claimed_skills if s.lower() not in validated_lower]

    # Calculate overall verified average
    scores = list(validated_skills.values())
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    return {
        "overall_assessed_score": avg_score,
        "assessments_completed": user.get("assessments_completed", 0),
        "validated_skills": validated_skills,
        "strengths": strengths,
        "needs_improvement": needs_improvement,
        "unassessed_claimed_skills": unassessed_claimed,
        "recommended_next_assessment": (
            unassessed_claimed[0] if unassessed_claimed else (
                needs_improvement[0]["skill"] if needs_improvement else "Frontend Development"
            )
        )
    }
