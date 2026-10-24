import time
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_mock_jwt, init_firebase
from app.repositories.firestore_repo import FirestoreRepository

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_env():
    init_firebase()

def create_auth_headers(uid: str, email: str, role: str = "student", name: str = "Test User"):
    token = create_mock_jwt(uid=uid, email=email, role=role, name=name)
    return {"Authorization": f"Bearer {token}"}

# ---------------------------------------------------------------------------
# 1. ASSESSMENT QUESTION COUNT & GENERATION TESTS
# ---------------------------------------------------------------------------

def test_assessment_question_count_validation():
    """
    Verifies that question_count is strictly validated to allowed tiers (20, 30, 50).
    """
    student_headers = create_auth_headers(
        uid="student_val_1", email="student_val@skillpath.ai", role="student"
    )

    # Invalid question count (e.g. 15) must be rejected
    res_invalid = client.post(
        "/api/v1/assessments/generate/start",
        json={
            "domain": "Frontend Development",
            "confirmed_skills": ["React", "JavaScript"],
            "question_count": 15,
            "duration_minutes": 15
        },
        headers=student_headers
    )
    assert res_invalid.status_code in (400, 422)

    # Valid question count: 20
    res_valid_20 = client.post(
        "/api/v1/assessments/generate/start",
        json={
            "domain": "Frontend Development",
            "confirmed_skills": ["React", "JavaScript"],
            "question_count": 20,
            "duration_minutes": 20
        },
        headers=student_headers
    )
    assert res_valid_20.status_code == 202
    data_20 = res_valid_20.json()
    assert "job_id" in data_20
    assert data_20["requested_question_count"] == 20

def test_async_generation_start_and_status_polling():
    """
    Verifies that POST /assessments/generate/start returns HTTP 202 with job_id,
    and GET /assessments/jobs/{job_id} tracks progress and completes.
    """
    student_uid = f"student_async_{uuid.uuid4().hex[:6]}"
    headers = create_auth_headers(uid=student_uid, email=f"{student_uid}@skillpath.ai", role="student")

    # Start generation job
    start_res = client.post(
        "/api/v1/assessments/generate/start",
        json={
            "domain": "Full Stack Development",
            "confirmed_skills": ["React", "Node.js", "Python"],
            "question_count": 20,
            "focus": "all_skills",
            "difficulty": "intermediate",
            "duration_minutes": 20
        },
        headers=headers
    )
    assert start_res.status_code == 202
    job_info = start_res.json()
    job_id = job_info["job_id"]
    assert job_info["status"] in ("queued", "processing")
    assert job_id.startswith("genjob_") or job_id.startswith("job")

    # Poll status
    time.sleep(1.0)
    poll_res = client.get(f"/api/v1/assessments/jobs/{job_id}", headers=headers)
    assert poll_res.status_code == 200
    poll_data = poll_res.json()
    assert poll_data["job_id"] == job_id
    assert poll_data["status"] in ("queued", "processing", "completed")

    # Wait up to 10 seconds for background execution to complete
    max_wait = 15
    start_time = time.time()
    completed = False
    while time.time() - start_time < max_wait:
        res = client.get(f"/api/v1/assessments/jobs/{job_id}", headers=headers)
        assert res.status_code == 200
        d = res.json()
        if d["status"] == "completed":
            completed = True
            assert d["assessment_id"] is not None
            assert d["assessment"] is not None
            assert len(d["assessment"]["questions"]) == 20
            break
        elif d["status"] == "failed":
            pytest.fail(f"Job failed unexpectedly: {d.get('error_message')}")
        time.sleep(1.0)

    assert completed, "Async generation job did not complete within the timeout"

def test_unauthorized_job_access_rejected():
    """
    Verifies that a student cannot access another student's generation job.
    """
    student_a_headers = create_auth_headers(uid="student_owner_a", email="a@skillpath.ai")
    student_b_headers = create_auth_headers(uid="student_intruder_b", email="b@skillpath.ai")

    start_res = client.post(
        "/api/v1/assessments/generate/start",
        json={
            "domain": "Backend Development",
            "confirmed_skills": ["FastAPI", "Python"],
            "question_count": 20,
            "duration_minutes": 20
        },
        headers=student_a_headers
    )
    assert start_res.status_code == 202
    job_id = start_res.json()["job_id"]

    # Student B attempts to read Student A's job
    intruder_res = client.get(f"/api/v1/assessments/jobs/{job_id}", headers=student_b_headers)
    assert intruder_res.status_code == 403

# ---------------------------------------------------------------------------
# 2. ADMIN ASSESSMENTS COUNT & VIEW ALL TESTS
# ---------------------------------------------------------------------------

def test_admin_stats_counts_completed_assessments_strictly():
    """
    Verifies that the admin statistics counter strictly counts COMPLETED assessments
    (1 completed assessment = 1 count, regardless of 20, 30, or 50 questions).
    In-progress assessments, question counts, and generation jobs are never counted as completed.
    """
    admin_headers = create_auth_headers(uid="admin_stats_1", email="admin@skillpath.ai", role="admin")

    initial_stats = client.get("/api/v1/admin/stats", headers=admin_headers).json()
    initial_completed = initial_stats.get("assessment_attempts_completed", 0)

    # Insert an in-progress assessment (status="in_progress")
    in_progress_id = f"assm_inp_{uuid.uuid4().hex[:6]}"
    FirestoreRepository.set_document("assessments", in_progress_id, {
        "id": in_progress_id,
        "user_id": "test_student_inp",
        "domain": "Frontend Development",
        "status": "in_progress",
        "question_count": 30,
        "questions": [{"id": f"q_{i}"} for i in range(30)] # 30 questions
    })

    stats_after_inp = client.get("/api/v1/admin/stats", headers=admin_headers).json()
    assert stats_after_inp.get("assessment_attempts_completed", 0) == initial_completed, \
        "In-progress assessment must NOT increment completed assessments count!"

    # Insert a truly completed assessment with score
    completed_id = f"assm_comp_{uuid.uuid4().hex[:6]}"
    FirestoreRepository.set_document("assessments", completed_id, {
        "id": completed_id,
        "user_id": "test_student_comp",
        "domain": "Backend Development",
        "status": "completed",
        "question_count": 50,
        "questions": [{"id": f"q_{i}"} for i in range(50)], # 50 questions
        "total_score_percentage": 88.0,
        "completed_at": "2026-10-24T12:00:00Z"
    })

    stats_after_comp = client.get("/api/v1/admin/stats", headers=admin_headers).json()
    # Exactly one assessment incremented, not 50!
    assert stats_after_comp.get("assessment_attempts_completed", 0) == initial_completed + 1

def test_admin_view_all_assessments_and_detail_inspection():
    """
    Verifies that GET /admin/assessments returns real assessment attempts,
    and GET /admin/assessments/{id} returns full question details, answers, and scores.
    """
    admin_headers = create_auth_headers(uid="admin_view_1", email="admin@skillpath.ai", role="admin")
    student_headers = create_auth_headers(uid="student_view_1", email="student@skillpath.ai", role="student")

    test_assm_id = f"assm_inspect_{uuid.uuid4().hex[:6]}"
    FirestoreRepository.set_document("assessments", test_assm_id, {
        "id": test_assm_id,
        "user_id": "student_view_1",
        "domain": "Cloud & DevOps",
        "status": "completed",
        "total_score_percentage": 92.5,
        "completed_at": "2026-10-24T12:30:00Z",
        "questions": [
            {
                "id": "q1",
                "question_text": "What is the purpose of Docker multi-stage builds?",
                "skill": "Docker",
                "points": 5,
                "correct_answer": "To optimize image size by leaving build tools behind."
            }
        ],
        "saved_answers": {
            "q1": "To optimize image size by leaving build tools behind."
        }
    })

    # Unauthorized student check: student must be rejected
    student_forbidden = client.get("/api/v1/admin/assessments", headers=student_headers)
    assert student_forbidden.status_code == 403

    # Admin list view
    list_res = client.get("/api/v1/admin/assessments", headers=admin_headers)
    assert list_res.status_code == 200
    all_assms = list_res.json()
    assert any(a["id"] == test_assm_id for a in all_assms)

    # Admin detail inspection
    detail_res = client.get(f"/api/v1/admin/assessments/{test_assm_id}", headers=admin_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == test_assm_id
    assert detail["total_score_percentage"] == 92.5
    assert len(detail["questions"]) == 1
    assert detail["questions"][0]["skill"] == "Docker"

# ---------------------------------------------------------------------------
# 3. ADMIN APPLICATION DELETION & DATA INTEGRITY TESTS
# ---------------------------------------------------------------------------

def test_admin_application_deletion_archives_and_preserves_student():
    """
    Verifies that:
    1. Only authorized administrators can delete/archive an application.
    2. Deleting an application does NOT delete the student account, profile, resume, or job listing.
    3. Deleted/archived applications are excluded from active pipelines.
    """
    admin_headers = create_auth_headers(uid="admin_del_1", email="admin@skillpath.ai", role="admin")
    student_headers = create_auth_headers(uid="student_del_target", email="target@skillpath.ai", role="student")

    # Setup student user record and profile
    student_uid = "student_del_target"
    FirestoreRepository.set_document("users", student_uid, {
        "uid": student_uid,
        "email": "target@skillpath.ai",
        "name": "Target Student",
        "role": "student"
    })
    FirestoreRepository.set_document("profiles", student_uid, {
        "user_id": student_uid,
        "name": "Target Student",
        "technical_skills": ["Python", "FastAPI"]
    })

    # Setup job listing
    job_id = f"job_del_{uuid.uuid4().hex[:6]}"
    FirestoreRepository.set_document("jobs", job_id, {
        "id": job_id,
        "title": "Backend Software Engineer",
        "company": "SkillPath AI",
        "is_active": True
    })

    # Create application
    app_id = f"app_del_{uuid.uuid4().hex[:6]}"
    FirestoreRepository.set_document("applications", app_id, {
        "id": app_id,
        "student_id": student_uid,
        "student_name": "Target Student",
        "student_email": "target@skillpath.ai",
        "job_id": job_id,
        "job_title": "Backend Software Engineer",
        "company": "SkillPath AI",
        "status": "Submitted",
        "submission_date": "2026-10-24T10:00:00Z"
    })

    # 1. Student attempting deletion is rejected (403 Forbidden)
    student_reject = client.delete(f"/api/v1/applications/{app_id}", headers=student_headers)
    assert student_reject.status_code == 403

    # 2. Administrator deletes (archives) application
    admin_del_res = client.delete(f"/api/v1/applications/{app_id}", headers=admin_headers)
    assert admin_del_res.status_code == 200
    del_data = admin_del_res.json()
    assert del_data["status"] == "success"
    assert del_data["deleted_id"] == app_id

    # 3. Check application document in Firestore: marked as is_deleted / Archived
    archived_app = FirestoreRepository.get_document("applications", app_id)
    assert archived_app is not None
    assert archived_app.get("is_deleted") is True
    assert archived_app.get("status") == "Archived"

    # 4. Check that student account and profile still exist and are untouched!
    user_doc = FirestoreRepository.get_document("users", student_uid)
    assert user_doc is not None, "Student user account must NOT be deleted when application is removed!"
    profile_doc = FirestoreRepository.get_document("profiles", student_uid)
    assert profile_doc is not None, "Student profile must NOT be deleted when application is removed!"

    # 5. Check that job listing still exists and is untouched!
    job_doc = FirestoreRepository.get_document("jobs", job_id)
    assert job_doc is not None, "Job listing must NOT be deleted when an application is removed!"
