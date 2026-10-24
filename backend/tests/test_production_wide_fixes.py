import time
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_mock_jwt, init_firebase, verify_token
from app.repositories.firestore_repo import FirestoreRepository
from app.api.routes.auth import _hash_password

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_env():
    init_firebase()

def create_headers(uid: str, email: str, role: str = "student", name: str = "Test User"):
    token = create_mock_jwt(uid=uid, email=email, role=role, name=name)
    return {"Authorization": f"Bearer {token}"}

# ---------------------------------------------------------------------------
# 1. LOGIN WITH EXISTING VALID STUDENT ACCOUNT & INVALID CREDENTIALS
# ---------------------------------------------------------------------------

def test_login_with_existing_valid_student_account():
    uid = f"student_{uuid.uuid4().hex[:8]}"
    email = f"student_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "ValidStudentPassword123"

    user_doc = {
        "uid": uid,
        "email": email,
        "name": "Jane Student",
        "role": "student",
        "password_hash": _hash_password(pwd),
        "is_active": True,
        "claimed_skills": ["Python", "React"],
        "validated_skills": {"Python": 85.0},
    }
    FirestoreRepository.set_document("users", uid, user_doc)

    res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["uid"] == uid
    assert data["user"]["email"] == email
    assert data["user"]["role"] == "student"
    assert "token" in data
    # Token issued must be valid
    verified = verify_token(data["token"])
    assert verified is not None
    assert verified["uid"] == uid

def test_login_with_invalid_credentials_returns_401():
    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword!"})
    assert res.status_code == 401
    assert "Invalid email or password" in res.json().get("detail", "")

def test_disabled_account_login_returns_403():
    uid = f"disabled_{uuid.uuid4().hex[:8]}"
    email = f"disabled_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "MySecretPassword123"

    user_doc = {
        "uid": uid,
        "email": email,
        "name": "Disabled User",
        "role": "student",
        "password_hash": _hash_password(pwd),
        "is_active": False,
    }
    FirestoreRepository.set_document("users", uid, user_doc)

    res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert res.status_code == 403
    assert "disabled" in res.json().get("detail", "").lower()

# ---------------------------------------------------------------------------
# 2. REGISTRATION & IMMEDIATE PROFILE CREATION
# ---------------------------------------------------------------------------

def test_registration_and_immediate_profile_creation():
    reg_email = f"new_student_{uuid.uuid4().hex[:8]}@example.com"
    reg_name = "Alice Wonder"
    pwd = "SecureStudentPassword987"

    res = client.post(
        "/api/v1/auth/register",
        json={
            "name": reg_name,
            "email": reg_email,
            "password": pwd,
            "confirm_password": pwd
        }
    )
    assert res.status_code == 200
    data = res.json()
    uid = data["user"]["uid"]
    assert data["user"]["email"] == reg_email
    assert data["user"]["role"] == "student"

    # Profile must immediately exist in Firestore
    persisted = FirestoreRepository.get_document("users", uid)
    assert persisted is not None
    assert persisted["email"] == reg_email
    assert persisted["name"] == reg_name
    assert persisted["role"] == "student"
    assert "technical_skills" in persisted

# ---------------------------------------------------------------------------
# 3. PROFILE PERSISTENCE & RESYNC PRESERVATION
# ---------------------------------------------------------------------------

def test_profile_resync_preserves_existing_skills_and_scores():
    uid = f"persist_user_{uuid.uuid4().hex[:8]}"
    email = f"persist_{uuid.uuid4().hex[:6]}@example.com"
    headers = create_headers(uid=uid, email=email, role="student")

    initial_doc = {
        "uid": uid,
        "email": email,
        "name": "Persist Test",
        "role": "student",
        "is_active": True,
        "claimed_skills": ["Python", "FastAPI", "Docker"],
        "validated_skills": {"Python": 90.0, "FastAPI": 85.0},
        "projects": [{"title": "Cloud Platform", "technologies": ["Python", "Docker"]}],
    }
    FirestoreRepository.set_document("users", uid, initial_doc)

    # Sync profile with only name and email
    sync_res = client.post(
        "/api/v1/auth/sync-profile",
        json={"name": "Persist Test", "email": email},
        headers=headers
    )
    assert sync_res.status_code == 200

    # Verify existing skills and validated scores were NOT erased
    after_doc = FirestoreRepository.get_document("users", uid)
    assert after_doc["claimed_skills"] == ["Python", "FastAPI", "Docker"]
    assert after_doc["validated_skills"]["Python"] == 90.0
    assert len(after_doc["projects"]) == 1

# ---------------------------------------------------------------------------
# 4. TOKEN REFRESH & EXPIRED TOKEN HANDLING
# ---------------------------------------------------------------------------

def test_expired_token_handling():
    uid = f"expired_user_{uuid.uuid4().hex[:8]}"
    email = f"expired_{uuid.uuid4().hex[:6]}@example.com"

    import jwt
    past_now = time.time() - 3600
    expired_payload = {
        "iss": "https://securetoken.google.com/skillpath-c8115",
        "aud": "skillpath-c8115",
        "sub": uid,
        "user_id": uid,
        "email": email,
        "role": "student",
        "iat": int(past_now - 3600),
        "exp": int(past_now),
    }
    expired_token = jwt.encode(expired_payload, "skillpath-secure-dev-jwt-signing-key-32b", algorithm="HS256")

    # Expired token must be rejected
    res_expired = client.get("/api/v1/profiles/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_expired.status_code == 401

    # Fresh token for same user succeeds
    fresh_headers = create_headers(uid=uid, email=email, role="student")
    user_doc = {"uid": uid, "email": email, "role": "student", "is_active": True}
    FirestoreRepository.set_document("users", uid, user_doc)

    res_fresh = client.get("/api/v1/profiles/me", headers=fresh_headers)
    assert res_fresh.status_code == 200
    assert res_fresh.json()["uid"] == uid

# ---------------------------------------------------------------------------
# 5. ADMIN LOGIN & UNAUTHORIZED ADMIN ACCESS PREVENTION
# ---------------------------------------------------------------------------

def test_unauthorized_student_cannot_access_admin_endpoints():
    student_headers = create_headers(uid="student_test_1", email="student@example.com", role="student")

    res = client.get("/api/v1/admin/users", headers=student_headers)
    assert res.status_code == 403
    assert "privilege" in res.json().get("detail", "").lower() or "administrator" in res.json().get("detail", "").lower()

def test_admin_user_can_access_admin_endpoints():
    admin_headers = create_headers(uid="admin_uid_1", email="admin@gmail.com", role="admin")

    res = client.get("/api/v1/admin/users", headers=admin_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

# ---------------------------------------------------------------------------
# 6. CROSS-STUDENT DATA ACCESS PREVENTION
# ---------------------------------------------------------------------------

def test_prevention_of_cross_student_resume_access():
    student_a_uid = f"student_a_{uuid.uuid4().hex[:6]}"
    student_b_uid = f"student_b_{uuid.uuid4().hex[:6]}"

    headers_a = create_headers(uid=student_a_uid, email=f"{student_a_uid}@example.com", role="student")
    headers_b = create_headers(uid=student_b_uid, email=f"{student_b_uid}@example.com", role="student")

    resume_id = f"resume_{uuid.uuid4().hex[:8]}"
    doc = {
        "id": resume_id,
        "user_id": student_a_uid,
        "file_name": "student_a_resume.pdf",
        "file_url": "https://example.com/a.pdf",
        "extracted_data": {"claimed_skills": ["Python"]},
        "recommended_domains": ["Backend Development"],
        "created_at": "2026-01-01T00:00:00Z"
    }
    FirestoreRepository.set_document("resumes", resume_id, doc)

    # Student A can access their own resume
    res_a = client.get(f"/api/v1/resumes/{resume_id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["id"] == resume_id

    # Student B CANNOT access Student A's resume (403 Forbidden)
    res_b = client.get(f"/api/v1/resumes/{resume_id}", headers=headers_b)
    assert res_b.status_code == 403

def test_missing_resume_and_incorrect_resume_id_handling():
    headers = create_headers(uid="student_test_x", email="student_x@example.com", role="student")
    res = client.get(f"/api/v1/resumes/nonexistent_resume_id_12345", headers=headers)
    assert res.status_code == 404

# ---------------------------------------------------------------------------
# 7. RESUME ASSESSMENT ROUTE ALIASES PREVENT 404
# ---------------------------------------------------------------------------

def test_resume_assessment_route_aliases_no_404():
    headers = create_headers(uid="student_alias_1", email="student_alias@example.com", role="student")

    # /api/v1/resumes/assessment must return 200 with resume: null (not 404)
    res_alias_1 = client.get("/api/v1/resumes/assessment", headers=headers)
    assert res_alias_1.status_code == 200
    assert "resume" in res_alias_1.json()

    # /api/v1/resume-assessment must return 200 with resume: null (not 404)
    res_alias_2 = client.get("/api/v1/resume-assessment", headers=headers)
    assert res_alias_2.status_code == 200
    assert "resume" in res_alias_2.json()

# ---------------------------------------------------------------------------
# 8. APPLICATION SUBMISSION & PERSISTENCE
# ---------------------------------------------------------------------------

def test_application_submission_and_status_persistence():
    student_uid = f"student_app_{uuid.uuid4().hex[:6]}"
    headers = create_headers(uid=student_uid, email=f"{student_uid}@example.com", role="student")

    job_id = f"job_{uuid.uuid4().hex[:6]}"
    FirestoreRepository.set_document("jobs", job_id, {
        "id": job_id,
        "title": "Software Engineer Intern",
        "company": "Tech Corp",
        "domain": "Full-Stack Development",
        "required_skills": ["React", "FastAPI"],
        "status": "published",
        "is_active": True,
    })

    app_res = client.post(
        "/api/v1/applications/apply",
        json={
            "job_id": job_id,
            "cover_letter": "Eager to contribute."
        },
        headers=headers
    )
    assert app_res.status_code in (200, 201)
    app_data = app_res.json()
    app_id = app_data["id"]

    my_apps = client.get("/api/v1/applications/me", headers=headers)
    assert my_apps.status_code == 200
    found = any(a["id"] == app_id for a in my_apps.json())
    assert found is True

    admin_headers = create_headers(uid="admin_app_1", email="admin@gmail.com", role="admin")
    update_res = client.patch(
        f"/api/v1/admin/applications/{app_id}/status",
        json={"status": "Under Review", "notes": "Strong portfolio."},
        headers=admin_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "Under Review"

    persisted_app = FirestoreRepository.get_document("applications", app_id)
    assert persisted_app["status"] == "Under Review"
