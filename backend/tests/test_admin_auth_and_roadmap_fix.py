"""
Tests verifying:
1. admin@gmail.com role detection and access to admin-only endpoints.
2. Automatic roadmap generation upon roadmap fetch after assessment completion.
3. Separation of genuine unassessed students (requires_assessment=True) from assessed students (requires_assessment=False).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_mock_jwt
from app.repositories.firestore_repo import FirestoreRepository

client = TestClient(app)

def test_admin_gmail_has_admin_privileges():
    token = create_mock_jwt(uid="admin_gmail_uid", email="admin@gmail.com", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Should succeed accessing admin stats
    res = client.get("/api/v1/admin/stats", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_users" in data
    assert "total_active_jobs" in data

def test_admin_gmail_profile_sync_assigns_admin_role():
    token = create_mock_jwt(uid="admin_gmail_sync_uid", email="admin@gmail.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/auth/sync-profile", json={"email": "admin@gmail.com", "name": "Admin Gmail"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "admin"
    assert data["user"]["email"] == "admin@gmail.com"

def test_student_cannot_access_admin_endpoints():
    token = create_mock_jwt(uid="student_regular_1", email="student1@gmail.com", role="student")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/admin/stats", headers=headers)
    assert res.status_code == 403

def test_roadmap_requires_assessment_when_unassessed():
    token = create_mock_jwt(uid="unassessed_student_test", email="unassessed@example.com", role="student")
    headers = {"Authorization": f"Bearer {token}"}

    # Ensure no roadmaps or assessments exist for this user
    res = client.get("/api/v1/roadmaps/latest", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["requires_assessment"] is True
    assert data["phases"] == []

def test_roadmap_automatically_generated_and_not_requiring_assessment_when_assessed():
    uid = "assessed_student_roadmap_test"
    token = create_mock_jwt(uid=uid, email="assessed@example.com", role="student")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed a completed assessment for this student
    assessment_id = f"asmt_completed_{uid}"
    FirestoreRepository.set_document("assessments", assessment_id, {
        "id": assessment_id,
        "user_id": uid,
        "domain": "Frontend Development",
        "status": "completed",
        "total_score_percentage": 82.5,
        "result": {
            "attempt_id": assessment_id,
            "user_id": uid,
            "domain": "Frontend Development",
            "total_score_percentage": 82.5,
            "total_earned_points": 82.5,
            "total_available_points": 100.0,
            "skill_breakdown": [
                {"skill": "React", "score_percentage": 85.0, "proficiency_level": "Advanced"},
                {"skill": "CSS", "score_percentage": 60.0, "proficiency_level": "Needs Improvement"}
            ],
            "weaknesses_summary": ["CSS flexbox and grid layouts require remediation"],
            "strengths_summary": ["React state management and hooks"]
        }
    })

    # When student calls /roadmaps/latest, it should automatically generate and return evidence-based roadmap
    res = client.get("/api/v1/roadmaps/latest", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["requires_assessment"] is False
    assert len(data["phases"]) > 0
    assert data["baseline_score"] == 82.5
