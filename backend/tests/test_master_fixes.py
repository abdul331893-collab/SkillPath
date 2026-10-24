import time
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_mock_jwt, verify_token, init_firebase
from app.repositories.firestore_repo import FirestoreRepository
from app.core.permissions import UserRole

client = TestClient(app)

def test_fast_token_verification_no_gcp_metadata_hang():
    """
    Verifies that token verification takes milliseconds, avoiding the 18s GCP metadata hang
    when running without cloud service account credentials.
    """
    init_firebase()
    token = create_mock_jwt(
        uid="test_student_perf_1",
        email="teststudent@skillpath.ai",
        role="student",
        name="Test Student"
    )
    
    start = time.perf_counter()
    claims = verify_token(token)
    duration = time.perf_counter() - start
    
    assert claims is not None
    assert claims["uid"] == "test_student_perf_1"
    assert claims["role"] == "student"
    # Verification must execute well under 100ms (typically < 2ms)
    assert duration < 0.1, f"Token verification was too slow: {duration}s"

def test_firestore_repository_disk_persistence():
    """
    Verifies FirestoreRepository accurately persists and restores documents across operations.
    """
    doc_id = f"test_persistence_doc_{uuid.uuid4().hex[:6]}"
    data = {
        "id": doc_id,
        "name": "Persistence Verification",
        "timestamp": time.time(),
        "tags": ["python", "fastapi"]
    }
    
    # Write
    FirestoreRepository.set_document("test_collection", doc_id, data)
    
    # Read back
    retrieved = FirestoreRepository.get_document("test_collection", doc_id)
    assert retrieved is not None
    assert retrieved["name"] == "Persistence Verification"
    assert retrieved["tags"] == ["python", "fastapi"]
    
    # Update
    FirestoreRepository.update_document("test_collection", doc_id, {"tags": ["python", "fastapi", "pytest"]})
    updated = FirestoreRepository.get_document("test_collection", doc_id)
    assert "pytest" in updated["tags"]

def test_auth_sync_profile_and_session_restoration():
    """
    Verifies that authenticating and syncing student profile canonicalizes on UID
    and persists across calls.
    """
    student_uid = f"student_auth_{uuid.uuid4().hex[:8]}"
    token = create_mock_jwt(uid=student_uid, email=f"{student_uid}@skillpath.ai", role="student", name="Jane Student")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post("/api/v1/auth/sync-profile", headers=headers, json={"role": "student"})
    assert response.status_code == 200, response.text
    res_data = response.json()
    assert res_data["user"]["uid"] == student_uid
    assert res_data["user"]["role"] == "student"
    
    # Verify persisted in database
    user_doc = FirestoreRepository.get_document("users", student_uid)
    assert user_doc is not None
    assert user_doc["email"] == f"{student_uid}@skillpath.ai"
    assert user_doc["role"] == "student"

def test_job_application_submission_duplicate_prevention_and_admin_sync():
    """
    Verifies the end-to-end application lifecycle:
    1. Student applies to an existing job listing.
    2. Duplicate application returns HTTP 409 Conflict.
    3. Student views application under /applications/my (admin notes masked).
    4. Admin views application under /applications with review notes.
    5. Admin updates application status.
    """
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    job_data = {
        "id": job_id,
        "title": "Full Stack Engineer",
        "company": "Tech Innovations Inc",
        "opportunity_type": "Job",
        "domain": "Frontend Development",
        "location": "Remote",
        "work_mode": "Remote",
        "is_active": True,
        "required_skills": ["React", "TypeScript", "Python"]
    }
    FirestoreRepository.set_document("jobs", job_id, job_data)
    
    student_uid = f"student_app_{uuid.uuid4().hex[:8]}"
    student_token = create_mock_jwt(uid=student_uid, email=f"{student_uid}@skillpath.ai", role="student", name="Alex Applicant")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    
    # 1. Apply
    apply_resp = client.post(
        "/api/v1/applications/apply",
        headers=student_headers,
        json={"job_id": job_id, "cover_letter": "I have 3 years of React and Python experience."}
    )
    assert apply_resp.status_code == 200, apply_resp.text
    app_data = apply_resp.json()
    app_id = app_data["id"]
    assert app_data["job_id"] == job_id
    assert app_data["status"] == "Submitted"
    
    # 2. Duplicate prevention
    dup_resp = client.post(
        "/api/v1/applications/apply",
        headers=student_headers,
        json={"job_id": job_id, "cover_letter": "Duplicate attempt"}
    )
    assert dup_resp.status_code == 409
    
    # 3. Student views /applications/my
    my_resp = client.get("/api/v1/applications/my", headers=student_headers)
    assert my_resp.status_code == 200
    my_apps = my_resp.json()
    assert any(a["id"] == app_id for a in my_apps)
    matching_my_app = next(a for a in my_apps if a["id"] == app_id)
    assert matching_my_app["admin_notes"] is None # confidential notes masked
    
    # 4. Admin views /applications
    admin_token = create_mock_jwt(uid="admin_governance_user", email="admin@skillpath.ai", role="admin", name="Admin Lead")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    admin_list_resp = client.get("/api/v1/applications", headers=admin_headers)
    assert admin_list_resp.status_code == 200
    all_apps = admin_list_resp.json()
    assert any(a["id"] == app_id for a in all_apps)
    
    # 5. Admin updates status
    patch_resp = client.patch(
        f"/api/v1/applications/{app_id}/status",
        headers=admin_headers,
        json={"status": "Under Review", "admin_notes": "Candidate meets all technical prerequisites."}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "Under Review"

def test_assessment_submission_and_scoring_persistence():
    """
    Verifies that assessment submission scores correctly, sets status to 'completed',
    and is retrievable by /assessments/latest and /admin/assessments.
    """
    student_uid = f"student_assess_{uuid.uuid4().hex[:8]}"
    token = create_mock_jwt(uid=student_uid, email=f"{student_uid}@skillpath.ai", role="student", name="Eva Student")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Sync profile with skills
    client.post("/api/v1/auth/sync-profile", headers=headers, json={"role": "student"})
    FirestoreRepository.update_document("users", student_uid, {
        "technical_skills": ["React", "JavaScript", "HTML", "CSS"],
        "claimed_skills": ["React", "JavaScript"]
    })
    
    # Create assessment in database
    assess_id = f"assess_{uuid.uuid4().hex[:8]}"
    questions = [
        {
            "id": "q_react_state_1",
            "question_text": "What Hook manages state in a functional component?",
            "domain": "Frontend Development",
            "skill": "React",
            "options": ["useEffect", "useState", "useContext", "useReducer"],
            "correct_answer": "useState",
            "points": 10
        },
        {
            "id": "q_js_promise_1",
            "question_text": "Which method handles fulfilled Promises?",
            "domain": "Frontend Development",
            "skill": "JavaScript",
            "options": [".catch()", ".then()", ".finally()", ".all()"],
            "correct_answer": ".then()",
            "points": 10
        }
    ]
    
    FirestoreRepository.set_document("assessments", assess_id, {
        "id": assess_id,
        "assessment_id": assess_id,
        "user_id": student_uid,
        "domain": "Frontend Development",
        "questions": questions,
        "status": "in_progress",
        "created_at": "2026-10-24T00:00:00Z"
    })
    
    # Submit answers
    submit_resp = client.post(
        f"/api/v1/assessments/{assess_id}/submit",
        headers=headers,
        json={
            "domain": "Frontend Development",
            "assessment_id": assess_id,
            "answers": [
                {"question_id": "q_react_state_1", "answer": "useState"},
                {"question_id": "q_js_promise_1", "answer": ".then()"}
            ],
            "time_taken_seconds": 120
        }
    )
    assert submit_resp.status_code == 200, submit_resp.text
    result = submit_resp.json()
    assert result["total_score_percentage"] == 100.0
    assert result.get("status") == "completed"
    
    # Verify latest assessment reflects completed status
    latest_resp = client.get("/api/v1/assessments/latest", headers=headers)
    assert latest_resp.status_code == 200
    latest = latest_resp.json()
    assert latest["total_score_percentage"] == 100.0
    assert latest.get("status") == "completed"
    
    # Verify admin can inspect completed assessments
    admin_token = create_mock_jwt(uid="admin_eval_inspector", email="admin@skillpath.ai", role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_assess_resp = client.get("/api/v1/admin/assessments", headers=admin_headers)
    assert admin_assess_resp.status_code == 200
    admin_assess_list = admin_assess_resp.json()
    assert any(a.get("id") == assess_id or a.get("assessment_id") == assess_id for a in admin_assess_list)

def test_roadmap_latest_endpoint_and_no_regeneration_loop():
    """
    Verifies that /roadmaps/latest exists and returns existing roadmap
    without forcing re-generation.
    """
    student_uid = f"student_roadmap_{uuid.uuid4().hex[:8]}"
    token = create_mock_jwt(uid=student_uid, email=f"{student_uid}@skillpath.ai", role="student")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Seed saved roadmap
    roadmap_id = f"roadmap_{student_uid}"
    roadmap_data = {
        "id": roadmap_id,
        "user_id": student_uid,
        "target_career_domain": "Frontend Development",
        "target_career_title": "Frontend Development",
        "baseline_score": 85.0,
        "phases": [
            {
                "phase_number": 1,
                "title": "Remediation Phase",
                "description": "Targeted remediation",
                "estimated_weeks": 3,
                "topics": [
                    {
                        "id": "t1",
                        "title": "Advanced TypeScript",
                        "skill": "TypeScript",
                        "objective": "Master TypeScript generics and strict null safety",
                        "why_improvement_needed": "Required by Frontend roadmap",
                        "progress_status": "Not Started"
                    }
                ]
            }
        ],
        "created_at": "2026-10-24T00:00:00Z",
        "updated_at": "2026-10-24T00:00:00Z"
    }
    FirestoreRepository.set_document("roadmaps", roadmap_id, roadmap_data)
    
    # Query /roadmaps/latest
    resp = client.get("/api/v1/roadmaps/latest", headers=headers)
    assert resp.status_code == 200
    fetched = resp.json()
    assert fetched["id"] == roadmap_id
    assert fetched["target_career_domain"] == "Frontend Development"

def test_admin_stats_returns_authentic_nonzero_counts():
    """
    Verifies that /admin/stats returns genuine platform metrics reflecting real records.
    """
    admin_token = create_mock_jwt(uid="admin_stats_inspector", email="admin_stat@skillpath.ai", role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    stats_resp = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    
    # We seeded users, jobs, questions, applications, and assessments
    assert stats["total_users"] >= 2
    assert stats["total_active_jobs"] >= 1
    assert stats["total_applications"] >= 1
    assert "popular_career_domains" in stats
