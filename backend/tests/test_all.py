import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.scoring_service import ScoringService
from app.services.career_service import CareerService
from app.services.job_matching import JobMatchingService
from app.services.document_parser import (
    DocumentParser,
    DocumentEmptyError,
    DocumentUnsupportedError,
    DocumentCorruptedError,
    DocumentEncryptedError,
    DocumentScannedError
)
from app.services.rag_service import rag_service
from app.repositories.firestore_repo import FirestoreRepository

client = TestClient(app)

STUDENT_AUTH_HEADER = {"Authorization": "Bearer demo-student-token"}
ADMIN_AUTH_HEADER = {"Authorization": "Bearer demo-admin-token"}

# 1. Health check test
def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "integrations" in data

# 2. Skill Scoring Deterministic Formulas
def test_skill_score_calculation():
    score = ScoringService.calculate_skill_score(8.0, 10.0)
    assert score == 80.0
    assert ScoringService.calculate_skill_score(0.0, 0.0) == 0.0

def test_weighted_overall_score():
    weights = [1.5, 1.0, 0.5]
    scores = [80.0, 60.0, 100.0]
    weighted = ScoringService.calculate_weighted_overall_score(weights, scores)
    assert weighted == 76.67

def test_skill_gap_calculation():
    assert ScoringService.calculate_skill_gap(75.0, 60.0) == 15.0
    assert ScoringService.calculate_skill_gap(70.0, 85.0) == 0.0

# 3. Authentication & Authorization Logic
def test_auth_protection_on_profile():
    unauth_resp = client.get("/api/v1/profiles/me")
    assert unauth_resp.status_code == 401

    auth_resp = client.get("/api/v1/profiles/me", headers=STUDENT_AUTH_HEADER)
    assert auth_resp.status_code == 200
    assert auth_resp.json()["email"] == "student@skillpath.ai"

def test_admin_authorization_enforcement():
    forbidden_resp = client.get("/api/v1/admin/stats", headers=STUDENT_AUTH_HEADER)
    assert forbidden_resp.status_code == 403

    admin_resp = client.get("/api/v1/admin/stats", headers=ADMIN_AUTH_HEADER)
    assert admin_resp.status_code == 200
    assert "total_users" in admin_resp.json()

# 4. Career Matching Engine
def test_career_recommendation_deterministic_scores():
    test_skills = {"React": 85.0, "JavaScript": 90.0, "HTML & CSS": 80.0}
    recs = CareerService.recommend_careers(
        user_skills=test_skills,
        user_education="Bachelor's in Computer Science"
    )
    assert len(recs) > 0
    fe_rec = next(r for r in recs if r.domain_id == "frontend-dev")
    assert fe_rec.match_score > 60.0
    assert fe_rec.eligibility_met is True
    assert len(fe_rec.matching_skills) >= 2

# 5. Job Eligibility & Matching
def test_job_matching_and_eligibility():
    user_skills = {"React": 80.0, "JavaScript": 85.0, "HTML & CSS": 90.0}
    jobs = JobMatchingService.match_jobs_for_candidate(
        user_skills=user_skills,
        user_education="Bachelor's Degree",
        user_experience_years=0.0
    )
    assert len(jobs) > 0
    top_job = jobs[0]
    assert top_job.match_score > 0.0
    assert top_job.eligibility_met is True

# 6. Assessment Submission Validation
def test_assessment_questions_and_submission():
    q_resp = client.get("/api/v1/assessments/questions?domain=Frontend%20Development", headers=STUDENT_AUTH_HEADER)
    assert q_resp.status_code == 200
    questions = q_resp.json()
    assert len(questions) > 0

    for q in questions:
        assert "correct_answer" not in q

    submission_data = {
        "domain": "Frontend Development",
        "answers": [
            {
                "question_id": questions[0]["id"],
                "answer": "To memoize the result of an expensive calculation between renders"
            }
        ]
    }
    sub_resp = client.post("/api/v1/assessments/submit", json=submission_data, headers=STUDENT_AUTH_HEADER)
    assert sub_resp.status_code == 200
    result = sub_resp.json()
    assert result["total_available_points"] > 0
    assert len(result["skill_breakdown"]) > 0

# 7. RAG Service Behavior
def test_rag_pipeline_query():
    rag_service.seed_initial_knowledge()
    res = rag_service.answer_query("Explain React Virtual DOM and reconciliation")
    assert "answer" in res
    assert len(res["sources"]) > 0
    assert res["sources"][0]["skill"] == "React"

# =========================================================================
# 8. RESUME MODULE REGRESSION TESTS
# =========================================================================

def _generate_valid_docx() -> bytes:
    import docx
    doc = docx.Document()
    doc.add_heading("Alex Mercer", 0)
    doc.add_paragraph("Email: alex@example.com | Phone: 555-0199")
    doc.add_heading("Education", level=1)
    doc.add_paragraph("B.Tech in Computer Science - Stanford University, 2024")
    doc.add_heading("Technical Skills", level=1)
    doc.add_paragraph("Python, React, FastAPI, Docker, SQL, TypeScript")
    doc.add_heading("Projects", level=1)
    doc.add_paragraph("Developed a high-throughput microservice backend in Python and FastAPI.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def _generate_valid_pdf() -> bytes:
    import pypdf
    # Raw compliant PDF with readable text
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 75 >> stream\n"
        b"BT /F1 12 Tf 100 700 Td (Alex Mercer Software Engineer with Python React and FastAPI) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000370 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n445\n%%EOF\n"
    )
    return pdf_content

def _generate_encrypted_pdf() -> bytes:
    import pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret_password")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def _generate_scanned_pdf() -> bytes:
    import pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

# Test 8.1: Latest resume does not exist (Clean HTTP 200 with {"resume": null})
def test_latest_resume_does_not_exist():
    new_user_header = {"Authorization": "Bearer dev-user-fresh-user-without-resume"}
    res = client.get("/api/v1/resumes/latest", headers=new_user_header)
    assert res.status_code == 200
    data = res.json()
    assert "resume" in data
    assert data["resume"] is None

# Test 8.2: Upload valid DOCX and verify latest resume exists
def test_upload_valid_docx_and_latest_exists():
    user_header = {"Authorization": "Bearer dev-user-docx-tester"}
    docx_bytes = _generate_valid_docx()

    files = {"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    upload_res = client.post("/api/v1/resumes/upload", files=files, headers=user_header)
    assert upload_res.status_code == 200
    uploaded_data = upload_res.json()
    assert uploaded_data["file_name"] == "resume.docx"
    assert "claimed_skills" in uploaded_data["extracted_data"]

    # Now verify GET /resumes/latest returns this resume
    latest_res = client.get("/api/v1/resumes/latest", headers=user_header)
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data["resume"] is not None
    assert latest_data["resume"]["id"] == uploaded_data["id"]
    assert latest_data["resume"]["file_name"] == "resume.docx"

# Test 8.3: Upload valid text-based PDF
def test_upload_valid_pdf():
    user_header = {"Authorization": "Bearer dev-user-pdf-tester"}
    pdf_bytes = _generate_valid_pdf()

    files = {"file": ("engineer_cv.pdf", pdf_bytes, "application/pdf")}
    res = client.post("/api/v1/resumes/upload", files=files, headers=user_header)
    assert res.status_code == 200
    data = res.json()
    assert data["file_name"] == "engineer_cv.pdf"
    assert len(data["extracted_data"]["claimed_skills"]) > 0

# Test 8.4: Unauthenticated access to resume routes
def test_resume_unauthenticated_access():
    res_latest = client.get("/api/v1/resumes/latest")
    assert res_latest.status_code == 401

    res_upload = client.post("/api/v1/resumes/upload")
    assert res_upload.status_code == 401

    res_get = client.get("/api/v1/resumes/some_id")
    assert res_get.status_code == 401

# Test 8.5: Student attempting to access another student's resume (403 Forbidden)
def test_student_forbidden_access_to_other_resume():
    student_a_header = {"Authorization": "Bearer dev-user-student-a"}
    student_b_header = {"Authorization": "Bearer dev-user-student-b"}

    # Student A uploads a resume
    docx_bytes = _generate_valid_docx()
    files = {"file": ("resume_a.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res_a = client.post("/api/v1/resumes/upload", files=files, headers=student_a_header)
    assert res_a.status_code == 200
    resume_a_id = res_a.json()["id"]

    # Student B attempts to access Student A's resume by ID
    res_forbidden = client.get(f"/api/v1/resumes/{resume_a_id}", headers=student_b_header)
    assert res_forbidden.status_code == 403
    assert "not authorized" in res_forbidden.json()["detail"].lower()

    # Admin CAN access Student A's resume
    res_admin = client.get(f"/api/v1/resumes/{resume_a_id}", headers=ADMIN_AUTH_HEADER)
    assert res_admin.status_code == 200
    assert res_admin.json()["id"] == resume_a_id

# Test 8.6: Empty document upload (400 Bad Request)
def test_upload_empty_document():
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = client.post("/api/v1/resumes/upload", files=files, headers=STUDENT_AUTH_HEADER)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()

# Test 8.7: Unsupported document format (400 Bad Request)
def test_upload_unsupported_document():
    files = {"file": ("malicious.exe", b"MZ\x90\x00executable", "application/x-msdownload")}
    res = client.post("/api/v1/resumes/upload", files=files, headers=STUDENT_AUTH_HEADER)
    assert res.status_code == 400
    assert "unsupported file extension" in res.json()["detail"].lower()

# Test 8.8: Encrypted PDF upload (422 Unprocessable Entity)
def test_upload_encrypted_pdf():
    enc_bytes = _generate_encrypted_pdf()
    files = {"file": ("encrypted.pdf", enc_bytes, "application/pdf")}
    res = client.post("/api/v1/resumes/upload", files=files, headers=STUDENT_AUTH_HEADER)
    assert res.status_code == 422
    assert "password-protected or encrypted" in res.json()["detail"].lower()

# Test 8.9: Corrupted PDF document (422 Unprocessable Entity)
def test_upload_corrupted_document():
    corrupted_bytes = b"%PDF-1.4\nCorrupted binary noise junk trailing"
    files = {"file": ("corrupt.pdf", corrupted_bytes, "application/pdf")}
    res = client.post("/api/v1/resumes/upload", files=files, headers=STUDENT_AUTH_HEADER)
    assert res.status_code == 422
    assert "corrupted" in res.json()["detail"].lower()

# Test 8.10: Scanned PDF when OCR is unavailable vs available
def test_scanned_pdf_handling(monkeypatch):
    scanned_bytes = _generate_scanned_pdf()

    # Case A: OCR unavailable -> Returns clean actionable 422
    monkeypatch.setattr(DocumentParser, "is_ocr_available", lambda: False)
    files = {"file": ("scanned.pdf", scanned_bytes, "application/pdf")}
    res = client.post("/api/v1/resumes/upload", files=files, headers=STUDENT_AUTH_HEADER)
    assert res.status_code == 422
    assert "scanned document" in res.json()["detail"].lower()
    assert "ocr" in res.json()["detail"].lower()

    # Case B: OCR available -> Extracts text successfully
    monkeypatch.setattr(DocumentParser, "is_ocr_available", lambda: True)
    monkeypatch.setattr(
        DocumentParser,
        "_attempt_ocr",
        lambda content: "Jane Doe Senior Python and React Engineer Stanford University 2023"
    )
    files = {"file": ("scanned_with_ocr.pdf", scanned_bytes, "application/pdf")}
    res_ocr = client.post("/api/v1/resumes/upload", files=files, headers=STUDENT_AUTH_HEADER)
    assert res_ocr.status_code == 200
    data = res_ocr.json()
    assert data["file_name"] == "scanned_with_ocr.pdf"
    assert "Python" in data["extracted_data"]["claimed_skills"]
