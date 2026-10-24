import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.skill_normalizer import SkillNormalizer
from app.services.job_matching import JobMatchingService
from app.services.roadmap_service import RoadmapService
from app.services.career_service import CareerService
from app.repositories.firestore_repo import FirestoreRepository, _memory_store

client = TestClient(app)

STUDENT_AUTH_HEADER = {"Authorization": "Bearer demo-student-token"}
OTHER_STUDENT_AUTH_HEADER = {"Authorization": "Bearer dev-user-bob"}


# ============================================================================
# 1. INTERNSHIP MATCH SCORE TESTS
# ============================================================================

def test_match_score_full_match():
    """Verify 100% match when all required skills are present."""
    job = {
        "id": "job_full",
        "title": "Backend Intern",
        "company": "CloudTech",
        "description": "Backend engineering role",
        "domain": "Backend Development",
        "opportunity_type": "Internship",
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": [],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "Remote",
        "work_mode": "Remote",
        "is_active": True
    }
    candidate_skills = {"Python": 90.0, "FastAPI": 85.0, "PostgreSQL": 80.0}

    result = JobMatchingService.calculate_single_match(
        job=job,
        candidate_skills=candidate_skills,
        user_experience_years=0.0,
        user_education="Bachelor's Degree"
    )
    assert result.match_score == 100.0
    assert result.match_status == "calculated"
    assert result.eligibility_met is True
    assert len(result.matched_required_skills) == 3
    assert len(result.missing_required_skills) == 0


def test_match_score_partial_match():
    """Verify deterministic calculation: (2 matched / 4 required) * 100 = 50.0%."""
    job = {
        "id": "job_partial",
        "title": "DevOps Intern",
        "company": "InfraCorp",
        "description": "DevOps role",
        "domain": "DevOps & Cloud Engineering",
        "opportunity_type": "Internship",
        "required_skills": ["Python", "Docker", "Kubernetes", "Terraform"],
        "preferred_skills": ["AWS"],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "Remote",
        "work_mode": "Remote",
        "is_active": True
    }
    candidate_skills = {"Python": 80.0, "Docker": 75.0}

    result = JobMatchingService.calculate_single_match(
        job=job,
        candidate_skills=candidate_skills,
        user_experience_years=0.0,
        user_education="Bachelor's Degree"
    )
    assert result.match_score == 50.0
    assert result.match_status == "calculated"
    assert "Python" in result.matched_required_skills
    assert "Docker" in result.matched_required_skills
    assert "Kubernetes" in result.missing_required_skills
    assert "Terraform" in result.missing_required_skills


def test_match_score_zero_match():
    """Verify deterministic 0.0% match when valid requirements exist but no skills match."""
    job = {
        "id": "job_zero",
        "title": "Embedded Systems Engineer",
        "company": "SiliconTech",
        "description": "Embedded role",
        "domain": "Systems Engineering",
        "opportunity_type": "Internship",
        "required_skills": ["C++", "Assembly", "RTOS"],
        "preferred_skills": [],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "Remote",
        "work_mode": "Remote",
        "is_active": True
    }
    candidate_skills = {"Photoshop": 90.0, "Figma": 85.0}

    result = JobMatchingService.calculate_single_match(
        job=job,
        candidate_skills=candidate_skills,
        user_experience_years=0.0,
        user_education="Bachelor's Degree"
    )
    assert result.match_score == 0.0
    assert result.match_status == "zero_match"
    assert len(result.matched_required_skills) == 0
    assert len(result.missing_required_skills) == 3


def test_skill_aliases_normalization():
    """Verify alias mapping allows non-identical skill strings to match canonical forms."""
    normalizer = SkillNormalizer()

    # Canonical normalization checks
    assert normalizer.normalize("React.js") == "React"
    assert normalizer.normalize("reactjs") == "React"
    assert normalizer.normalize("NodeJS") == "Node.js"
    assert normalizer.normalize("golang") == "Go"
    assert normalizer.normalize("postgres") == "PostgreSQL"
    assert normalizer.normalize("k8s") == "Kubernetes"
    assert normalizer.normalize("fast api") == "FastAPI"

    # Matching candidate with aliases against canonical job requirements
    job = {
        "id": "job_alias",
        "title": "Full Stack Intern",
        "company": "ModernApp Inc",
        "description": "Full stack internship",
        "domain": "Frontend Development",
        "opportunity_type": "Internship",
        "required_skills": ["React", "Node.js", "PostgreSQL", "Kubernetes"],
        "preferred_skills": [],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "Remote",
        "work_mode": "Remote",
        "is_active": True
    }
    candidate_skills = {"React.js": 85.0, "NodeJS": 80.0, "Postgres": 75.0, "K8s": 70.0}

    result = JobMatchingService.calculate_single_match(
        job=job,
        candidate_skills=candidate_skills,
        user_experience_years=0.0,
        user_education="Bachelor's Degree"
    )
    assert result.match_score == 100.0
    assert len(result.matched_required_skills) == 4
    assert len(result.missing_required_skills) == 0


def test_missing_student_skills_status():
    """Verify missing student skills yields assessment_required with None score."""
    job = {
        "id": "job_reqs",
        "title": "Backend Intern",
        "company": "CloudTech",
        "description": "Backend internship",
        "domain": "Backend Development",
        "opportunity_type": "Internship",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": [],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "Remote",
        "work_mode": "Remote",
        "is_active": True
    }
    candidate_skills = {}

    result = JobMatchingService.calculate_single_match(
        job=job,
        candidate_skills=candidate_skills,
        user_experience_years=0.0,
        user_education="Bachelor's Degree"
    )
    assert result.match_score is None
    assert result.match_status == "assessment_required"
    assert "Complete your skill assessment" in result.explanation


def test_missing_internship_requirements_status():
    """Verify job listing with no required skills yields match_unavailable with None score."""
    job = {
        "id": "job_no_reqs",
        "title": "General Intern",
        "company": "General Corp",
        "description": "General open internship",
        "domain": "General",
        "opportunity_type": "Internship",
        "required_skills": [],
        "preferred_skills": [],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "Remote",
        "work_mode": "Remote",
        "is_active": True
    }
    candidate_skills = {"Python": 80.0}

    result = JobMatchingService.calculate_single_match(
        job=job,
        candidate_skills=candidate_skills,
        user_experience_years=0.0,
        user_education="Bachelor's Degree"
    )
    assert result.match_score is None
    assert result.match_status == "match_unavailable"
    assert "Match unavailable" in result.explanation


def test_eligibility_independent_of_match_score():
    """Verify eligibility is strictly evaluated against criteria (experience, education) independent of score."""
    # Case A: 0% skill match, but Eligible on education and experience criteria
    job_a = {
        "id": "job_acad",
        "title": "Systems Intern",
        "company": "OS Tech",
        "description": "Systems role",
        "domain": "Systems",
        "opportunity_type": "Internship",
        "required_skills": ["Rust", "Linux"],
        "preferred_skills": [],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "Remote",
        "work_mode": "Remote",
        "is_active": True
    }
    res_a = JobMatchingService.calculate_single_match(
        job=job_a,
        candidate_skills={"Photoshop": 90.0},
        user_experience_years=0.0,
        user_education="Bachelor's Degree"
    )
    assert res_a.eligibility_met is True
    assert res_a.match_score == 0.0

    # Case B: 100% skill match, but Ineligible due to insufficient experience
    job_b = {
        "id": "job_exp",
        "title": "Senior Systems Engineer",
        "company": "OS Tech",
        "description": "Senior role",
        "domain": "Systems",
        "opportunity_type": "Job",
        "required_skills": ["Rust", "Linux"],
        "preferred_skills": [],
        "min_experience_years": 3.0,
        "required_education": "Bachelor's",
        "location": "Remote",
        "work_mode": "Remote",
        "is_active": True
    }
    res_b = JobMatchingService.calculate_single_match(
        job=job_b,
        candidate_skills={"Rust": 95.0, "Linux": 90.0},
        user_experience_years=1.0,
        user_education="Bachelor's Degree"
    )
    assert res_b.eligibility_met is False
    assert res_b.match_score == 100.0


# ============================================================================
# 2. PERSONALIZED LEARNING ROADMAP TESTS
# ============================================================================

def test_missing_assessment_blocks_roadmap_generation():
    """Roadmap generation must block when student has no completed assessment."""
    user_id = "student_no_assessment"
    _memory_store["assessments"] = {
        k: v for k, v in _memory_store.get("assessments", {}).items()
        if v.get("user_id") != user_id
    }

    result = RoadmapService.generate_roadmap(
        user_id=user_id,
        target_career_domain="backend-dev",
        replace_existing=True
    )

    assert result.requires_assessment is True
    assert "complete your skill assessment" in (result.message or "").lower()
    assert "Step 3" in (result.next_action or "")
    assert len(result.phases) == 0


def test_successful_roadmap_generation_from_completed_assessment():
    """Roadmap is generated targeting verified assessment weaknesses with all 10 required fields."""
    user_id = "student_with_assessment"
    assessment_id = "assess_test_1"

    FirestoreRepository.set_document("assessments", assessment_id, {
        "id": assessment_id,
        "user_id": user_id,
        "skill": "Backend Engineering",
        "score": 62.0,
        "status": "completed",
        "strengths": ["Python syntax", "REST APIs"],
        "weaknesses": ["Docker containerization", "SQL indexing"],
        "skill_breakdown": [
            {
                "skill": "Python",
                "score_percentage": 85.0,
                "evidence": "Strong handling of data models and decorators.",
                "improvement_suggestion": "Advance to concurrency paradigms."
            },
            {
                "skill": "Docker",
                "score_percentage": 42.0,
                "evidence": "Uncertain about multi-stage builds and layer caching.",
                "improvement_suggestion": "Practice Dockerfile optimization."
            },
            {
                "skill": "SQL & Databases",
                "score_percentage": 48.0,
                "evidence": "Struggled with complex indexing and join plans.",
                "improvement_suggestion": "Study execution plans and normalization."
            }
        ],
        "created_at": "2026-10-21T10:00:00Z"
    })

    roadmap = RoadmapService.generate_roadmap(
        user_id=user_id,
        target_career_domain="backend-dev",
        replace_existing=True
    )

    assert roadmap.requires_assessment is False
    assert len(roadmap.phases) > 0

    all_topics = [t for phase in roadmap.phases for t in phase.topics]
    assert len(all_topics) >= 2

    # Check that topics address weaknesses
    topic_skills = [t.skill.lower() for t in all_topics]
    assert any("docker" in s for s in topic_skills)
    assert any("sql" in s or "database" in s or "postgres" in s for s in topic_skills)

    # Verify all 10 required fields are present on each topic
    for topic in all_topics:
        assert topic.skill is not None
        assert topic.why_improvement_needed is not None
        assert topic.current_level is not None
        assert topic.target_level is not None
        assert isinstance(topic.learning_objectives, list) and len(topic.learning_objectives) > 0
        assert isinstance(topic.ordered_steps, list) and len(topic.ordered_steps) > 0
        assert topic.exercise is not None
        assert topic.estimated_duration is not None
        assert topic.measurable_criterion is not None
        assert topic.progress_status in ["Not Started", "In Progress", "Completed"]

        # Verify resources have valid working URLs
        assert len(topic.resources) > 0
        for res in topic.resources:
            assert res.title
            assert str(res.url).startswith("https://")


def test_roadmap_duplicate_prevention_unless_replacing():
    """Generating without replace_existing=True must preserve existing roadmap topics."""
    user_id = "student_dup_test"
    assessment_id = "assess_dup_test"

    FirestoreRepository.set_document("assessments", assessment_id, {
        "id": assessment_id,
        "user_id": user_id,
        "skill": "Backend Engineering",
        "score": 60.0,
        "status": "completed",
        "skill_breakdown": [
            {"skill": "Python", "score_percentage": 80.0, "evidence": "Good syntax", "improvement_suggestion": "None"},
            {"skill": "Docker", "score_percentage": 40.0, "evidence": "Failed containers", "improvement_suggestion": "Study Docker"}
        ],
        "created_at": "2026-10-21T10:00:00Z"
    })

    # First generation
    rm1 = RoadmapService.generate_roadmap(
        user_id=user_id,
        target_career_domain="backend-dev",
        replace_existing=True
    )
    initial_topic_count = sum(len(p.topics) for p in rm1.phases)

    # Second generation without replace_existing
    rm2 = RoadmapService.generate_roadmap(
        user_id=user_id,
        target_career_domain="backend-dev",
        replace_existing=False
    )
    second_topic_count = sum(len(p.topics) for p in rm2.phases)
    assert second_topic_count == initial_topic_count


def test_roadmap_progress_update_and_persistence():
    """Updating topic progress updates status, recalculates completion percentage, and persists."""
    user_id = "student_progress_test"
    assessment_id = "assess_prog_test"

    FirestoreRepository.set_document("assessments", assessment_id, {
        "id": assessment_id,
        "user_id": user_id,
        "score": 65.0,
        "status": "completed",
        "skill_breakdown": [
            {"skill": "Docker", "score_percentage": 45.0, "evidence": "Needs practice", "improvement_suggestion": "Learn Compose"},
            {"skill": "SQL & Databases", "score_percentage": 50.0, "evidence": "Needs indexes", "improvement_suggestion": "Learn indexing"}
        ],
        "created_at": "2026-10-21T10:00:00Z"
    })

    rm = RoadmapService.generate_roadmap(
        user_id=user_id,
        target_career_domain="backend-dev",
        replace_existing=True
    )
    first_topic = rm.phases[0].topics[0]
    topic_id = first_topic.id

    # Update to In Progress
    updated = RoadmapService.update_progress(
        roadmap_id=rm.id,
        topic_id=topic_id,
        progress_status="In Progress"
    )
    assert updated is not None
    topic_updated = next(t for p in updated.phases for t in p.topics if t.id == topic_id)
    assert topic_updated.progress_status == "In Progress"

    # Update to Completed
    completed = RoadmapService.update_progress(
        roadmap_id=rm.id,
        topic_id=topic_id,
        progress_status="Completed"
    )
    topic_completed = next(t for p in completed.phases for t in p.topics if t.id == topic_id)
    assert topic_completed.progress_status == "Completed"
    assert completed.completion_percentage > 0.0


# ============================================================================
# 3. TRANSPARENT CAREER RECOMMENDATIONS TESTS
# ============================================================================

def test_career_recommendations_rankings_use_deterministic_scores():
    """Career recommendations must rank domains by deterministic match score descending."""
    user_id = "student_career_rankings"

    FirestoreRepository.set_document("users", user_id, {
        "id": user_id,
        "claimed_skills": ["React", "JavaScript", "HTML5", "CSS3", "TypeScript"],
        "technical_skills": ["React", "TypeScript"],
        "validated_skills": {
            "React": 90.0,
            "TypeScript": 85.0,
            "JavaScript": 88.0
        }
    })

    recs = CareerService.recommend_careers(
        user_skills={"React": 90.0, "TypeScript": 85.0, "JavaScript": 88.0},
        user_confirmed_skills=["React", "JavaScript", "HTML5", "CSS3", "TypeScript"],
        user_id=user_id
    )

    assert len(recs) > 0
    scores = [r.match_score for r in recs if r.match_score is not None]
    assert scores == sorted(scores, reverse=True)

    frontend_rec = next((r for r in recs if "Frontend" in r.title), None)
    ds_rec = next((r for r in recs if "Data Science" in r.title), None)
    assert frontend_rec is not None
    assert ds_rec is not None
    assert frontend_rec.match_score > ds_rec.match_score


def test_career_recommendations_insufficient_data():
    """When student has no skills or assessment evidence, label recommendation Insufficient Data."""
    user_id = "student_blank_slate"

    recs = CareerService.recommend_careers(
        user_skills={},
        user_confirmed_skills=[],
        user_id=user_id
    )

    assert len(recs) > 0
    for r in recs:
        assert r.insufficient_data is True
        assert r.match_score is None


def test_career_recommendations_cite_supplied_evidence_and_identify_missing():
    """Recommendations cite actual evidence and identify missing required skills."""
    user_id = "student_evidence_test"

    recs = CareerService.recommend_careers(
        user_skills={"Python": 85.0, "FastAPI": 75.0},
        user_confirmed_skills=["Python", "FastAPI"],
        user_id=user_id
    )

    backend_rec = next((r for r in recs if "Backend" in r.title), None)
    assert backend_rec is not None
    assert backend_rec.insufficient_data is False
    assert backend_rec.match_score is not None

    matching_names = [
        (s.get("skill") if isinstance(s, dict) else s.skill).lower()
        for s in backend_rec.matching_skills
    ]
    assert "python" in matching_names

    missing_lower = [m.lower() for m in backend_rec.missing_required_skills]
    assert any("sql" in m or "database" in m or "api" in m for m in missing_lower)

    assert backend_rec.formula_explanation is not None
    assert "Formula" in backend_rec.formula_explanation or "weighted" in backend_rec.formula_explanation.lower()
    assert len(backend_rec.suggested_projects) > 0
    assert backend_rec.disclaimer is not None


def test_career_recommendations_attach_real_job_listings():
    """Related opportunities must be populated from real listings in the database."""
    job_id = "job_real_be_1"
    FirestoreRepository.set_document("jobs", job_id, {
        "id": job_id,
        "title": "Junior Backend Developer",
        "company": "Tech Corp",
        "description": "Backend job at Tech Corp",
        "location": "Remote",
        "opportunity_type": "Job",
        "domain": "Backend Development",
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker"],
        "is_active": True,
        "min_experience_years": 0.0,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    })

    recs = CareerService.recommend_careers(
        user_skills={"Python": 90.0},
        user_confirmed_skills=["Python"],
        user_id="student_jobs_attach"
    )

    backend_rec = next((r for r in recs if "Backend" in r.title), None)
    assert backend_rec is not None
    opp_titles = [opp.title for opp in backend_rec.related_opportunities]
    assert "Junior Backend Developer" in opp_titles


# ============================================================================
# 4. AUTHORIZATION, SECURITY & API CONTRACT TESTS
# ============================================================================

def test_student_cannot_update_another_students_roadmap():
    """Student B cannot modify Student A's roadmap (403 Forbidden)."""
    # Create an assessment first to ensure topics exist
    FirestoreRepository.set_document("assessments", "assess_auth_test", {
        "id": "assess_auth_test",
        "user_id": "student-demo-user-1",
        "score": 60.0,
        "status": "completed",
        "skill_breakdown": [
            {"skill": "Python", "score_percentage": 70.0, "evidence": "Passing", "improvement_suggestion": "None"},
            {"skill": "Docker", "score_percentage": 40.0, "evidence": "Failed", "improvement_suggestion": "Learn Docker"}
        ],
        "created_at": "2026-10-21T10:00:00Z"
    })
    rm = RoadmapService.generate_roadmap(
        user_id="student-demo-user-1",
        target_career_domain="backend-dev",
        replace_existing=True
    )

    all_topics = [t for p in rm.phases for t in p.topics]
    assert len(all_topics) > 0
    topic_id = all_topics[0].id

    # Student B attempts to update Student A's roadmap progress
    response = client.patch(
        f"/api/v1/roadmaps/{rm.id}/progress",
        json={"topic_id": topic_id, "completed": True, "progress_status": "Completed"},
        headers=OTHER_STUDENT_AUTH_HEADER
    )
    # Must be forbidden for Student B
    assert response.status_code == 403


def test_jobs_api_contract():
    """Verify /api/v1/jobs/ endpoint returns valid schema with deterministic match fields."""
    response = client.get("/api/v1/jobs", headers=STUDENT_AUTH_HEADER)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        match_item = data[0]
        assert "job" in match_item
        assert "match_status" in match_item
        assert "eligibility_met" in match_item
        assert "matched_required_skills" in match_item
        assert "missing_required_skills" in match_item


def test_career_recommendations_api_contract():
    """Verify /api/v1/careers/recommendations endpoint returns transparent recommendation schema."""
    response = client.get("/api/v1/careers/recommendations", headers=STUDENT_AUTH_HEADER)
    assert response.status_code == 200
    recs = response.json()
    assert isinstance(recs, list)
    assert len(recs) > 0
    rec = recs[0]
    assert "domain_id" in rec
    assert "title" in rec
    assert "insufficient_data" in rec
    assert "formula_explanation" in rec
    assert "matching_skills" in rec
    assert "missing_required_skills" in rec
    assert "suggested_projects" in rec
    assert "disclaimer" in rec
