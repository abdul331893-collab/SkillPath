import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.repositories.firestore_repo import FirestoreRepository

client = TestClient(app)

PROD_ORIGIN = "https://skillpath-a7ca.onrender.com"
STUDENT_AUTH = {"Authorization": "Bearer demo-student-token"}
ADMIN_AUTH = {"Authorization": "Bearer demo-admin-token"}

# ==============================================================================
# 1. CORS PREFLIGHT & ORIGIN TESTS
# ==============================================================================

def test_cors_preflight_production_frontend():
    """Verify that OPTIONS preflight from the deployed Render frontend is permitted."""
    endpoints = [
        "/api/v1/resumes/latest",
        "/api/v1/resumes/upload",
        "/api/v1/assessments/jobs/active",
        "/api/v1/careers/recommendations",
        "/api/v1/profiles/me",
        "/api/v1/admin/stats",
        "/api/v1/jobs",
        "/api/v1/applications",
    ]
    for ep in endpoints:
        res = client.options(
            ep,
            headers={
                "Origin": PROD_ORIGIN,
                "Access-Control-Request-Method": "GET" if "upload" not in ep else "POST",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            }
        )
        assert res.status_code == 200, f"Preflight failed for {ep} with status {res.status_code}"
        assert res.headers.get("access-control-allow-origin") == PROD_ORIGIN
        assert res.headers.get("access-control-allow-credentials") == "true"
        allow_methods = res.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods or "POST" in allow_methods

def test_cors_disallowed_origin_rejected():
    """Verify that an unauthorized origin is not granted CORS headers."""
    res = client.options(
        "/api/v1/profiles/me",
        headers={
            "Origin": "https://attacker-malicious-site.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        }
    )
    assert res.headers.get("access-control-allow-origin") is None

def test_cors_localhost_allowed_in_dev():
    """Verify that localhost development origin is permitted."""
    res = client.options(
        "/api/v1/jobs",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        }
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"

def test_cors_headers_present_on_error_responses():
    """Verify that CORS headers are consistently attached even on 401, 403, and 404 responses."""
    # 401 Unauthorized
    res_401 = client.get("/api/v1/profiles/me", headers={"Origin": PROD_ORIGIN})
    assert res_401.status_code == 401
    assert res_401.headers.get("access-control-allow-origin") == PROD_ORIGIN

    # 403 Forbidden (student trying admin route)
    res_403 = client.get("/api/v1/admin/stats", headers={"Origin": PROD_ORIGIN, **STUDENT_AUTH})
    assert res_403.status_code == 403
    assert res_403.headers.get("access-control-allow-origin") == PROD_ORIGIN

    # 404 Not Found
    res_404 = client.get("/api/v1/jobs/non-existent-job-xyz", headers={"Origin": PROD_ORIGIN})
    assert res_404.status_code == 404
    assert res_404.headers.get("access-control-allow-origin") == PROD_ORIGIN

# ==============================================================================
# 2. STUDENT CLOUD PROFILE TESTS
# ==============================================================================

def test_student_cloud_profile_read_and_update():
    """Verify profile retrieval, mutation, and persistence."""
    # 1. Fetch initial profile
    res = client.get("/api/v1/profiles/me", headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN})
    assert res.status_code == 200
    data = res.json()
    assert "uid" in data
    assert "email" in data

    # 2. Update profile
    update_payload = {
        "name": "Alex Mercer Updated",
        "education_level": "Bachelor's",
        "institution": "Stanford University",
        "degree": "B.S. in Computer Science",
        "graduation_year": 2026,
        "technical_skills": ["React", "TypeScript", "FastAPI", "PostgreSQL"],
        "interests": ["Full-Stack Engineering", "Cloud Computing"],
        "preferred_career_domains": ["Frontend Development", "Backend Development"],
        "bio": "Passionate software engineer building resilient web platforms.",
        "projects": [
            {
                "title": "Cloud Resume Parser",
                "description": "High performance document parsing and skill validation engine.",
                "technologies": ["Python", "FastAPI"]
            }
        ]
    }
    put_res = client.put(
        "/api/v1/profiles/me",
        json=update_payload,
        headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN}
    )
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["name"] == "Alex Mercer Updated"
    assert "React" in updated_data["technical_skills"]
    assert updated_data["completion_percentage"] > 0

    # 3. Read again to confirm persistence
    re_res = client.get("/api/v1/profiles/me", headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN})
    assert re_res.status_code == 200
    assert re_res.json()["name"] == "Alex Mercer Updated"

# ==============================================================================
# 3. ADMIN CONSOLE DATA LOADING TESTS
# ==============================================================================

def test_admin_console_endpoints_with_admin_auth():
    """Verify every API call utilized by the Admin Console returns valid data."""
    # 1. System Stats
    res_stats = client.get("/api/v1/admin/stats", headers={**ADMIN_AUTH, "Origin": PROD_ORIGIN})
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "total_users" in stats
    assert "total_active_jobs" in stats
    assert "total_applications" in stats

    # 2. Users directory
    res_users = client.get("/api/v1/admin/users", headers={**ADMIN_AUTH, "Origin": PROD_ORIGIN})
    assert res_users.status_code == 200
    assert isinstance(res_users.json(), list)

    # 3. Question bank
    res_q = client.get("/api/v1/admin/questions", headers={**ADMIN_AUTH, "Origin": PROD_ORIGIN})
    assert res_q.status_code == 200
    assert isinstance(res_q.json(), list)

    # 4. Jobs list
    res_jobs = client.get("/api/v1/jobs", headers={**ADMIN_AUTH, "Origin": PROD_ORIGIN})
    assert res_jobs.status_code == 200
    assert isinstance(res_jobs.json(), list)

    # 5. Dedicated admin jobs list
    res_admin_jobs = client.get("/api/v1/admin/jobs", headers={**ADMIN_AUTH, "Origin": PROD_ORIGIN})
    assert res_admin_jobs.status_code == 200
    assert isinstance(res_admin_jobs.json(), list)

    # 6. Applications list
    res_apps = client.get("/api/v1/applications", headers={**ADMIN_AUTH, "Origin": PROD_ORIGIN})
    assert res_apps.status_code == 200
    assert isinstance(res_apps.json(), list)

    # 7. Assessments list
    res_assess = client.get("/api/v1/admin/assessments", headers={**ADMIN_AUTH, "Origin": PROD_ORIGIN})
    assert res_assess.status_code == 200
    assert isinstance(res_assess.json(), list)

def test_admin_endpoints_reject_student():
    """Verify students cannot access any admin-restricted endpoints."""
    forbidden_endpoints = [
        "/api/v1/admin/stats",
        "/api/v1/admin/users",
        "/api/v1/admin/questions",
        "/api/v1/admin/jobs",
        "/api/v1/applications",
        "/api/v1/admin/assessments",
    ]
    for ep in forbidden_endpoints:
        res = client.get(ep, headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN})
        assert res.status_code == 403, f"Expected 403 for {ep}, got {res.status_code}"

# ==============================================================================
# 4. RESUME ENDPOINTS TESTS
# ==============================================================================

def test_resume_latest_clean_contract():
    """Verify /resumes/latest returns 200 with resume: null for a user with no uploaded resume."""
    from app.core.security import create_mock_jwt
    fresh_uid = "fresh-student-no-resume"
    token = create_mock_jwt(uid=fresh_uid, email="fresh@example.com")
    auth_hdr = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/resumes/latest", headers={**auth_hdr, "Origin": PROD_ORIGIN})
    assert res.status_code == 200
    data = res.json()
    assert data == {"resume": None}

def test_resume_upload_validation_and_parsing():
    """Verify file format validation and parsing error handling on upload."""
    # 1. Invalid file extension rejected with 400
    res_bad_ext = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("malicious.exe", b"executable bytes", "application/octet-stream")},
        headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN}
    )
    assert res_bad_ext.status_code == 400
    assert "Only PDF and DOCX files are allowed" in res_bad_ext.json()["detail"]

    # 2. Empty file rejected with 400
    res_empty = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN}
    )
    assert res_empty.status_code == 400

    # 3. Valid PDF uploaded and parsed
    sample_pdf_bytes = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 120 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n"
        b"(John Doe\\nSoftware Engineer with Python and React experience) Tj\nET\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000206 00000 n\n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n378\n%%EOF\n"
    )
    res_upload = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", sample_pdf_bytes, "application/pdf")},
        headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN}
    )
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert "id" in upload_data
    assert upload_data["file_name"] == "resume.pdf"
    assert "extracted_data" in upload_data

    # 4. Now latest should return the uploaded resume
    res_latest = client.get("/api/v1/resumes/latest", headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN})
    assert res_latest.status_code == 200
    latest_data = res_latest.json()
    assert latest_data["resume"] is not None
    assert latest_data["resume"]["file_name"] == "resume.pdf"

# ==============================================================================
# 5. JOBS AND CAREER RECOMMENDATIONS TESTS
# ==============================================================================

def test_active_assessment_jobs_endpoint():
    """Verify /assessments/jobs/active returns 200 (either None or job record)."""
    res = client.get("/api/v1/assessments/jobs/active", headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN})
    assert res.status_code == 200
    # None or valid AssessmentJobResponse
    data = res.json()
    assert data is None or "job_id" in data

def test_career_recommendations_endpoint():
    """Verify career recommendations retrieve valid domains without 500 error."""
    res = client.get("/api/v1/careers/recommendations", headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN})
    assert res.status_code == 200
    recs = res.json()
    assert isinstance(recs, list)
    if recs:
        first = recs[0]
        assert "domain_id" in first
        assert "title" in first
        assert "eligibility_met" in first

def test_job_listings_retrieval():
    """Verify verified jobs return ranked match results."""
    res = client.get("/api/v1/jobs", headers={**STUDENT_AUTH, "Origin": PROD_ORIGIN})
    assert res.status_code == 200
    jobs = res.json()
    assert isinstance(jobs, list)
    if jobs:
        first = jobs[0]
        assert "job" in first
        assert "eligibility_met" in first
