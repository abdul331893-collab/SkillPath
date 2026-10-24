from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.dependencies import get_current_user
from app.core.permissions import AuthenticatedUser
from app.schemas.roadmap import (
    RoadmapGenerateRequest,
    RoadmapResponse,
    RoadmapProgressUpdate
)
from app.services.roadmap_service import RoadmapService
from app.repositories.firestore_repo import FirestoreRepository

router = APIRouter(prefix="/roadmaps", tags=["Learning Roadmaps"])

@router.post("/generate", response_model=RoadmapResponse)
async def generate_learning_roadmap(
    req: RoadmapGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Generates a personalized learning roadmap tailored to measured skill gaps."""
    user = FirestoreRepository.get_document("users", current_user.uid) or {}
    validated_skills = user.get("validated_skills", {})

    roadmap = RoadmapService.generate_roadmap(
        user_id=current_user.uid,
        target_career_domain=req.target_career_domain,
        user_skills=validated_skills,
        weekly_hours=req.weekly_hours_available or 10,
        replace_existing=req.replace_existing
    )
    return roadmap

@router.get("/current", response_model=RoadmapResponse)
@router.get("/latest", response_model=RoadmapResponse)
async def get_current_roadmap(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieves current student's most recently generated learning roadmap."""
    roadmaps = FirestoreRepository.query_documents(
        "roadmaps",
        filters=[("user_id", "==", current_user.uid)],
        limit=10
    )
    if not roadmaps:
        roadmaps = FirestoreRepository.query_documents(
            "roadmaps",
            filters=[("student_id", "==", current_user.uid)],
            limit=10
        )

    if roadmaps:
        # Return latest valid roadmap with phases
        for r in reversed(roadmaps):
            item = dict(r)
            if not item.get("user_id") and item.get("student_id"):
                item["user_id"] = item["student_id"]
            if item.get("phases"):
                return RoadmapResponse(**item)
        item = dict(roadmaps[-1])
        if not item.get("user_id") and item.get("student_id"):
            item["user_id"] = item["student_id"]
        return RoadmapResponse(**item)

    # No saved roadmap yet: check if student has completed an assessment
    now_str = datetime.now(timezone.utc).isoformat()
    return RoadmapResponse(
        id=f"roadmap_unassessed_{current_user.uid}",
        user_id=current_user.uid,
        target_career_domain="Frontend Development",
        target_career_title="Frontend Development",
        baseline_score=0.0,
        requires_assessment=True,
        message="Please complete your skill assessment to generate an evidence-based roadmap.",
        next_action="Complete the Skill Assessment in Step 3 to calibrate your personalized curriculum based on measured weaknesses.",
        phases=[],
        total_estimated_weeks=0,
        completion_percentage=0.0,
        created_at=now_str,
        updated_at=now_str
    )

@router.patch("/{roadmap_id}/progress", response_model=RoadmapResponse)
async def update_roadmap_progress(
    roadmap_id: str,
    update: RoadmapProgressUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Marks a topic or exercise as completed, in progress, or not started."""
    doc = FirestoreRepository.get_document("roadmaps", roadmap_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")

    # Enforce ownership: student can only modify their own roadmap
    if doc.get("user_id") != current_user.uid and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot modify another student's roadmap")

    res = RoadmapService.update_progress(
        roadmap_id=roadmap_id,
        topic_id=update.topic_id,
        completed=update.completed,
        progress_status=update.progress_status
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap or topic not found")
    return res
