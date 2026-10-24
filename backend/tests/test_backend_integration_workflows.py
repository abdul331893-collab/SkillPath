import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.firestore_repo import FirestoreRepository

client = TestClient(app)

STUDENT_TOKEN = "demo-student-token"
STUDENT_AUTH = {"Authorization": f"Bearer {STUDENT_TOKEN}"}
ADMIN_TOKEN = "demo-admin-token"
ADMIN_AUTH = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

# =========================================================================
# 1. AUTHENTICATION, PERSISTENCE & SAFE PROFILE RECOVERY
# =========================================================================

def test_new_student_registration_and_firestore_persistence():
    """Verify registration creates student record in Firestore with UID, correct role, and timestamps."""
    unique_email = f"student_{uuid.uuid4().hex[:8]}@university.edu"
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "Jordan Lee",
        "email": unique_email,
        "password": "securePassword123!",
        "confirm_password": "securePassword123!"
    })
    assert reg_res.status_code == 200
    data = reg_res.json()
    user = data["user"]
    uid = user["uid"]

    assert user["role"] == "student"  # Server-side enforcement
    assert user["email"] == unique_email
    assert user["is_active"] is True
    assert "token" in data

    # Verify Firestore document existence and fields
    doc = FirestoreRepository.get_document("users", uid)
    assert doc is not None
    assert doc["uid"] == uid
    assert doc["email"] == unique_email
    assert doc["name"] == "Jordan Lee"
    assert doc["role"] == "student"
    assert "password_hash" in doc
    assert doc["password_hash"] != "securePassword123!"  # Never plaintext
    assert "created_at" in doc

def test_existing_student_login_and_credential_validation():
    """Verify existing registered student can log in and invalid credentials are rejected."""
    email = f"login_test_{uuid.uuid4().hex[:8]}@university.edu"
    password = "validPassword123!"

    # Register
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "Taylor Swift",
        "email": email,
        "password": password,
        "confirm_password": password
    })
    assert reg_res.status_code == 200

    # Successful login
    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["user"]["email"] == email
    assert login_data["user"]["role"] == "student"
    assert "token" in login_data

    # Invalid password rejected
    bad_pwd_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "wrongPassword123"
    })
    assert bad_pwd_res.status_code == 401
    assert "Invalid email or password" in bad_pwd_res.json()["detail"]

    # Non-existent email rejected
    bad_email_res = client.post("/api/v1/auth/login", json={
        "email": "nonexistent@university.edu",
        "password": password
    })
    assert bad_email_res.status_code == 401

def test_disabled_account_login_rejection():
    """Verify disabled account cannot log in and returns 403 Forbidden."""
    email = f"disabled_{uuid.uuid4().hex[:8]}@university.edu"
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "Disabled Student",
        "email": email,
        "password": "password123!",
        "confirm_password": "password123!"
    })
    assert reg_res.status_code == 200
    uid = reg_res.json()["user"]["uid"]

    # Disable account in Firestore
    FirestoreRepository.update_document("users", uid, {"is_active": False})

    # Attempt login
    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123!"
    })
    assert login_res.status_code == 403
    assert "disabled" in login_res.json()["detail"].lower()

def test_missing_firestore_profile_safe_recovery():
    """Verify that when a user token exists but Firestore doc is missing, profile is safely recovered."""
    recovered_uid = f"recovered_{uuid.uuid4().hex[:10]}"
    recovered_token = f"dev-user-{recovered_uid}"
    recovered_auth = {"Authorization": f"Bearer {recovered_token}"}

    # Ensure doc is not in Firestore initially
    FirestoreRepository.delete_document("users", recovered_uid)

    # 1. Sync profile endpoint safely initializes the profile
    sync_res = client.post("/api/v1/auth/sync-profile", headers=recovered_auth, json={
        "name": "Recovered Student",
        "email": f"{recovered_uid}@domain.com"
    })
    assert sync_res.status_code == 200
    assert sync_res.json()["user"]["uid"] == recovered_uid
    assert sync_res.json()["user"]["role"] == "student"

    # Verify document now exists in Firestore
    recovered_doc = FirestoreRepository.get_document("users", recovered_uid)
    assert recovered_doc is not None
    assert recovered_doc["name"] == "Recovered Student"

    # 2. Repeated calls are idempotent and do not create duplicates
    sync_res_again = client.post("/api/v1/auth/sync-profile", headers=recovered_auth, json={
        "name": "Recovered Student",
        "email": f"{recovered_uid}@domain.com"
    })
    assert sync_res_again.status_code == 200
    assert sync_res_again.json()["user"]["uid"] == recovered_uid

def test_token_verification_failures():
    """Verify that missing, malformed, or invalid tokens are rejected with 401."""
    # Missing header
    res_no_auth = client.get("/api/v1/auth/me")
    assert res_no_auth.status_code == 401

    # Malformed header
    res_bad_format = client.get("/api/v1/auth/me", headers={"Authorization": "Basic 12345"})
    assert res_bad_format.status_code == 401

    # Invalid token string
    res_invalid_token = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer totally-invalid-random-token"})
    assert res_invalid_token.status_code == 401

def test_profile_persistence_and_update():
    """Verify student profile details can be updated and persist across subsequent queries."""
    uid = f"persist_user_{uuid.uuid4().hex[:8]}"
    token = f"dev-user-{uid}"
    auth = {"Authorization": f"Bearer {token}"}

    # Initialize profile
    client.post("/api/v1/auth/sync-profile", headers=auth, json={
        "name": "Alex Profile Test",
        "email": f"{uid}@test.edu"
    })

    # Update profile fields
    update_res = client.put("/api/v1/profiles/me", headers=auth, json={
        "degree": "Computer Science",
        "institution": "State University",
        "technical_skills": ["Python", "FastAPI", "React"],
        "projects": [
            {
                "title": "Cloud Dashboard",
                "description": "Full-stack dashboard with real-time updates",
                "technologies": ["Python", "FastAPI"]
            }
        ],
        "interests": ["Backend Development", "Cloud Systems"]
    })
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["institution"] == "State University"
    assert "FastAPI" in updated_data["technical_skills"]

    # Query profile again (simulating browser reload / new session)
    get_res = client.get("/api/v1/profiles/me", headers=auth)
    assert get_res.status_code == 200
    persisted = get_res.json()
    assert persisted["institution"] == "State University"
    assert "FastAPI" in persisted["technical_skills"]
    assert len(persisted["projects"]) == 1

# =========================================================================
# 2. TRANSPARENT CAREER DOMAIN RECOMMENDATIONS
# =========================================================================

def test_career_recommendations_insufficient_evidence():
    """Verify that a candidate with no confirmed skills or assessments gets insufficient_data=True."""
    uid = f"nodata_user_{uuid.uuid4().hex[:8]}"
    token = f"dev-user-{uid}"
    auth = {"Authorization": f"Bearer {token}"}

    client.post("/api/v1/auth/sync-profile", headers=auth, json={
        "name": "No Data Student",
        "email": f"{uid}@test.edu"
    })

    recs_res = client.get("/api/v1/careers/recommendations?regenerate=true", headers=auth)
    assert recs_res.status_code == 200
    recs = recs_res.json()
    assert len(recs) > 0
    for r in recs:
        assert r["insufficient_data"] is True
        assert r["match_score"] is None
        assert "incomplete" in r["ai_explanation"].lower() or "assessment" in r["ai_explanation"].lower() or "evidence" in r["ai_explanation"].lower()

def test_career_recommendations_with_evidence_and_persistence():
    """Verify recommendations calculate deterministic scores from student skills and persist in Firestore."""
    uid = f"evidenced_user_{uuid.uuid4().hex[:8]}"
    token = f"dev-user-{uid}"
    auth = {"Authorization": f"Bearer {token}"}

    # Setup student with confirmed skills in Backend Development
    FirestoreRepository.set_document("users", uid, {
        "uid": uid,
        "email": f"{uid}@test.edu",
        "name": "Backend Specialist",
        "role": "student",
        "education_level": "Bachelor's",
        "technical_skills": ["Python", "FastAPI", "SQL & Databases"],
        "claimed_skills": ["Python", "FastAPI"],
        "validated_skills": {"Python": 85.0, "FastAPI": 80.0, "SQL & Databases": 75.0},
        "projects": [
            {
                "title": "API Gateway",
                "technologies": ["Python", "FastAPI", "PostgreSQL"]
            }
        ],
        "interests": ["Backend Development"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    # Generate recommendations
    gen_res = client.post("/api/v1/careers/recommendations/regenerate", headers=auth)
    assert gen_res.status_code == 200
    recs = gen_res.json()
    assert len(recs) > 0

    # Backend Development should score highest with strong match
    backend_rec = next((r for r in recs if "backend" in r["domain_id"].lower()), None)
    assert backend_rec is not None
    assert backend_rec["match_score"] is not None
    assert backend_rec["match_score"] >= 65.0
    assert backend_rec["insufficient_data"] is False
    assert len(backend_rec["matching_skills"]) > 0
    assert "formula_explanation" in backend_rec
    assert "reason_for_recommendation" in backend_rec
    assert len(backend_rec["suggested_next_steps"]) > 0

    # Verify persisted in Firestore collection career_recommendations
    saved_doc = FirestoreRepository.get_document("career_recommendations", uid)
    assert saved_doc is not None
    assert len(saved_doc["recommendations"]) == len(recs)

    # Subsequent GET without regenerate returns persisted recommendations
    cached_res = client.get("/api/v1/careers/recommendations", headers=auth)
    assert cached_res.status_code == 200
    assert len(cached_res.json()) == len(recs)

# =========================================================================
# 3. RECOMMENDED JOBS & INTERNSHIPS MATCHING
# =========================================================================

def test_jobs_matching_active_listings_and_scoring():
    """Verify jobs returned are active Firestore listings, scored deterministically against candidate skills."""
    res = client.get("/api/v1/jobs", headers=STUDENT_AUTH)
    assert res.status_code == 200
    listings = res.json()
    assert len(listings) > 0

    for item in listings:
        job = item["job"]
        assert job["is_active"] is True
        assert "title" in job
        assert "company" in job
        assert "opportunity_type" in job
        assert "required_skills" in job

        # Check match score format
        assert item["match_status"] in ("calculated", "zero_match", "assessment_required", "match_unavailable")
        if item["match_status"] == "calculated":
            assert item["match_score"] is not None
            assert 0.0 <= item["match_score"] <= 100.0
        elif item["match_status"] == "zero_match":
            assert item["match_score"] == 0.0

def test_jobs_filtering_and_empty_state():
    """Verify filters work and impossible filters return empty list gracefully."""
    empty_res = client.get("/api/v1/jobs?domain=NonExistentDomain12345", headers=STUDENT_AUTH)
    assert empty_res.status_code == 200
    assert len(empty_res.json()) == 0

# =========================================================================
# 4. JOB & INTERNSHIP APPLICATIONS LIFECYCLE & ADMIN GOVERNANCE
# =========================================================================

def test_application_submission_duplicate_prevention_and_status_transitions():
    """
    Complete end-to-end test of:
    1. Student submits application.
    2. Duplicate application prevented (409 Conflict).
    3. Student views only their applications with masked admin notes.
    4. Student cannot update own status (403 Forbidden).
    5. Admin updates status through valid transitions (Submitted -> Under Review -> Shortlisted).
    6. Invalid transitions rejected with 400 Bad Request.
    7. Student withdraws application.
    8. Withdrawal on final status rejected.
    """
    student_uid = f"app_student_{uuid.uuid4().hex[:8]}"
    student_token = f"dev-user-{student_uid}"
    student_auth = {"Authorization": f"Bearer {student_token}"}

    # Initialize student profile
    client.post("/api/v1/auth/sync-profile", headers=student_auth, json={
        "name": "Applicant Student",
        "email": f"{student_uid}@test.edu"
    })

    # Ensure a known active job exists
    job_id = "job-backend-1"

    # 1. Submit application
    apply_res = client.post("/api/v1/applications/apply", headers=student_auth, json={
        "job_id": job_id,
        "cover_letter": "I have extensive Python backend experience and would love to join CloudScale Data."
    })
    assert apply_res.status_code == 200
    app_data = apply_res.json()
    app_id = app_data["id"]
    assert app_data["status"] == "Submitted"
    assert app_data["student_id"] == student_uid
    assert app_data["admin_notes"] is None  # Never exposed to student

    # 2. Prevent duplicate application
    dup_res = client.post("/api/v1/applications/apply", headers=student_auth, json={
        "job_id": job_id,
        "cover_letter": "Second attempt"
    })
    assert dup_res.status_code == 409
    assert "already applied" in dup_res.json()["detail"].lower()

    # 3. Student views their own applications
    my_apps_res = client.get("/api/v1/applications/my", headers=student_auth)
    assert my_apps_res.status_code == 200
    my_apps = my_apps_res.json()
    assert any(a["id"] == app_id for a in my_apps)
    # Ensure notes are masked
    my_app = next(a for a in my_apps if a["id"] == app_id)
    assert my_app["admin_notes"] is None

    # 4. Student CANNOT change application status directly
    hack_res = client.patch(f"/api/v1/applications/{app_id}/status", headers=student_auth, json={
        "status": "Selected"
    })
    assert hack_res.status_code == 403

    # 5. Admin updates status: Submitted -> Under Review
    admin_step1 = client.patch(f"/api/v1/applications/{app_id}/status", headers=ADMIN_AUTH, json={
        "status": "Under Review",
        "admin_notes": "Reviewed resume: Strong Python alignment."
    })
    assert admin_step1.status_code == 200
    assert admin_step1.json()["status"] == "Under Review"
    assert admin_step1.json()["admin_notes"] == "Reviewed resume: Strong Python alignment."

    # Verify status history audit trail
    history = admin_step1.json()["status_history"]
    assert len(history) >= 2
    assert history[-1]["status"] == "Under Review"

    # Admin updates status: Under Review -> Shortlisted
    admin_step2 = client.patch(f"/api/v1/applications/{app_id}/status", headers=ADMIN_AUTH, json={
        "status": "Shortlisted",
        "admin_notes": "Candidate moved to interview pipeline."
    })
    assert admin_step2.status_code == 200
    assert admin_step2.json()["status"] == "Shortlisted"

    # 6. Invalid transition rejected: Shortlisted -> Submitted is not allowed
    invalid_trans_res = client.patch(f"/api/v1/applications/{app_id}/status", headers=ADMIN_AUTH, json={
        "status": "Submitted"
    })
    assert invalid_trans_res.status_code == 400
    assert "invalid status transition" in invalid_trans_res.json()["detail"].lower()

    # 7. Student checks their application detail: status is Shortlisted, admin notes masked
    student_view_res = client.get(f"/api/v1/applications/{app_id}", headers=student_auth)
    assert student_view_res.status_code == 200
    assert student_view_res.json()["status"] == "Shortlisted"
    assert student_view_res.json()["admin_notes"] is None

    # 8. Student withdraws active application
    withdraw_res = client.patch(f"/api/v1/applications/{app_id}/withdraw", headers=student_auth)
    assert withdraw_res.status_code == 200
    assert withdraw_res.json()["status"] == "Withdrawn"

    # 9. Cannot withdraw already withdrawn application
    withdraw_again = client.patch(f"/api/v1/applications/{app_id}/withdraw", headers=student_auth)
    assert withdraw_again.status_code == 400
