import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.firestore_repo import FirestoreRepository

client = TestClient(app)

STUDENT_AUTH_HEADER = {"Authorization": "Bearer demo-student-token"}
ADMIN_AUTH_HEADER = {"Authorization": "Bearer demo-admin-token"}

def test_student_registration_validation_and_duplicate_prevention():
    # 1. Invalid email
    res = client.post("/api/v1/auth/register", json={
        "name": "Jane Doe",
        "email": "not-an-email",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert res.status_code == 422

    unique_email = f"jane.{uuid.uuid4().hex[:6]}@example.com"
    # 2. Mismatched passwords
    res = client.post("/api/v1/auth/register", json={
        "name": "Jane Doe",
        "email": unique_email,
        "password": "password123",
        "confirm_password": "differentpassword"
    })
    assert res.status_code == 400
    assert "do not match" in res.json()["detail"]

    # 3. Successful student registration
    res = client.post("/api/v1/auth/register", json={
        "name": "Jane Doe",
        "email": unique_email,
        "password": "password123",
        "confirm_password": "password123"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "student"  # Server-side enforcement
    assert data["user"]["email"] == unique_email
    assert "token" in data

    # 4. Duplicate registration prevention
    dup_res = client.post("/api/v1/auth/register", json={
        "name": "Jane Doe",
        "email": unique_email,
        "password": "password123",
        "confirm_password": "password123"
    })
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"]

def test_student_and_admin_login():
    # Demo student login
    res = client.post("/api/v1/auth/login", json={
        "email": "student@skillpath.ai",
        "password": "anypassword"
    })
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "student"

    # Demo admin login
    res_admin = client.post("/api/v1/auth/login", json={
        "email": "admin@skillpath.ai",
        "password": "anypassword"
    })
    assert res_admin.status_code == 200
    assert res_admin.json()["user"]["role"] == "admin"

def test_jobs_and_internships_filtering():
    # Fetch all opportunities
    res_all = client.get("/api/v1/jobs", headers=STUDENT_AUTH_HEADER)
    assert res_all.status_code == 200
    all_opps = res_all.json()
    assert len(all_opps) > 0

    # Filter only internships
    res_intern = client.get("/api/v1/jobs?opportunity_type=Internship", headers=STUDENT_AUTH_HEADER)
    assert res_intern.status_code == 200
    internships = res_intern.json()
    assert len(internships) > 0
    for item in internships:
        assert item["job"]["opportunity_type"] == "Internship"

    # Filter only jobs
    res_jobs = client.get("/api/v1/jobs?opportunity_type=Job", headers=STUDENT_AUTH_HEADER)
    assert res_jobs.status_code == 200
    jobs = res_jobs.json()
    assert len(jobs) > 0
    for item in jobs:
        assert item["job"]["opportunity_type"] == "Job"

def test_job_application_lifecycle():
    # Clean up any leftover active application for test user on job-frontend-1
    for old_app in FirestoreRepository.query_documents("applications", filters=[("student_id", "==", "student-demo-user-1"), ("job_id", "==", "job-frontend-1")], limit=100):
        if old_app.get("status") != "Withdrawn":
            FirestoreRepository.update_document("applications", old_app["id"], {"status": "Withdrawn"})

    # 1. Student applies for a job
    apply_res = client.post("/api/v1/applications/apply", headers=STUDENT_AUTH_HEADER, json={
        "job_id": "job-frontend-1",
        "cover_letter": "I am passionate about building modern React interfaces.",
    })
    assert apply_res.status_code == 200
    app_data = apply_res.json()
    app_id = app_data["id"]
    assert app_data["status"] == "Submitted"
    assert app_data["job_id"] == "job-frontend-1"
    assert app_data["admin_notes"] is None

    # 2. Prevent duplicate application for the same opportunity
    dup_apply = client.post("/api/v1/applications/apply", headers=STUDENT_AUTH_HEADER, json={
        "job_id": "job-frontend-1",
        "cover_letter": "Duplicate attempt",
    })
    assert dup_apply.status_code == 409
    assert "already applied" in dup_apply.json()["detail"]

    # 3. Student views their applications
    my_apps = client.get("/api/v1/applications/my", headers=STUDENT_AUTH_HEADER)
    assert my_apps.status_code == 200
    assert any(a["id"] == app_id for a in my_apps.json())

    # 4. Administrator views applications and changes status with review notes
    admin_list = client.get("/api/v1/applications", headers=ADMIN_AUTH_HEADER)
    assert admin_list.status_code == 200
    assert any(a["id"] == app_id for a in admin_list.json())

    # Update status to Under Review with internal notes
    status_update = client.patch(f"/api/v1/applications/{app_id}/status", headers=ADMIN_AUTH_HEADER, json={
        "status": "Under Review",
        "admin_notes": "Candidate shows strong front-end promise. Verify assessment score."
    })
    assert status_update.status_code == 200
    assert status_update.json()["status"] == "Under Review"
    assert status_update.json()["admin_notes"] == "Candidate shows strong front-end promise. Verify assessment score."

    # Verify student cannot see admin notes
    student_view = client.get(f"/api/v1/applications/{app_id}", headers=STUDENT_AUTH_HEADER)
    assert student_view.status_code == 200
    assert student_view.json()["status"] == "Under Review"
    assert student_view.json()["admin_notes"] is None  # Protected

    # 5. Student withdraws application
    withdraw_res = client.patch(f"/api/v1/applications/{app_id}/withdraw", headers=STUDENT_AUTH_HEADER)
    assert withdraw_res.status_code == 200
    assert withdraw_res.json()["status"] == "Withdrawn"

def test_confirmed_skills_and_personalized_assessment():
    # 1. Update confirmed skills and projects
    save_res = client.put("/api/v1/resumes/resume-test-1/confirmed", headers=STUDENT_AUTH_HEADER, json={
        "skills": [
            {"name": "React", "source": "resume-claimed"},
            {"name": "TypeScript", "source": "student-added"}
        ],
        "projects": [
            {
                "title": "E-Commerce Dashboard",
                "description": "High performance dashboard built with React and TypeScript.",
                "technologies": ["React", "TypeScript", "Tailwind CSS"]
            }
        ],
        "recommended_domains": ["Frontend Development"]
    })
    # If resume doc does not exist, initialize and retry
    if save_res.status_code == 404:
        FirestoreRepository.set_document("resumes", "resume-test-1", {
            "id": "resume-test-1",
            "user_id": "student-demo-user-1",
            "file_name": "resume.pdf",
            "file_url": "https://example.com/resume.pdf",
            "extracted_data": {"claimed_skills": ["React"], "projects": []},
            "created_at": "2026-01-01T00:00:00Z"
        })
        save_res = client.put("/api/v1/resumes/resume-test-1/confirmed", headers=STUDENT_AUTH_HEADER, json={
            "skills": [
                {"name": "React", "source": "resume-claimed"},
                {"name": "TypeScript", "source": "student-added"}
            ],
            "projects": [
                {
                    "title": "E-Commerce Dashboard",
                    "description": "High performance dashboard built with React and TypeScript.",
                    "technologies": ["React", "TypeScript", "Tailwind CSS"]
                }
            ],
            "recommended_domains": ["Frontend Development"]
        })
    assert save_res.status_code == 200
    assert len(save_res.json()["skills"]) == 2

    # 2. Generate personalized assessment questions
    gen_res = client.post("/api/v1/assessments/generate", headers=STUDENT_AUTH_HEADER, json={
        "confirmed_skills": ["React", "TypeScript"],
        "projects": [
            {
                "title": "E-Commerce Dashboard",
                "description": "High performance dashboard built with React and TypeScript.",
                "technologies": ["React", "TypeScript"]
            }
        ],
        "domain": "Frontend Development"
    })
    assert gen_res.status_code == 200
    questions = gen_res.json()
    assert len(questions) > 0
    # Answer keys must never be exposed
    for q in questions:
        assert "correct_answer" not in q

def test_career_recommendation_why_suitable():
    # Career recommendations should include why_suitable explanation and job ready steps
    recs_res = client.get("/api/v1/careers/recommendations", headers=STUDENT_AUTH_HEADER)
    assert recs_res.status_code == 200
    recs = recs_res.json()
    assert len(recs) > 0
    top_rec = recs[0]
    assert "reason_for_recommendation" in top_rec
    assert "Why is" in top_rec["reason_for_recommendation"]
    assert len(top_rec["job_ready_steps"]) > 0
