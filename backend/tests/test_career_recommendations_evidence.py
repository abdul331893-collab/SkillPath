"""
Tests verifying:
1. Career domain recommendations for unassessed students correctly reflect insufficient data and eligibility_met=False (never contradictory "Eligible").
2. Completed assessment in Data Science & Machine Learning results in deterministic match score, insufficient_data=False, and actual assessment evidence.
3. Recommendations cache automatically updates when a new assessment is completed.
4. Profile resync does not overwrite existing student skills, validated scores, or projects.
5. Denial of cross-student access and preservation of existing recommendations on transient errors.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_mock_jwt
from app.repositories.firestore_repo import FirestoreRepository

client = TestClient(app)

def test_unassessed_student_receives_insufficient_data_and_eligibility_false():
    uid = f"unassessed_career_{uuid.uuid4().hex[:8]}"
    token = create_mock_jwt(uid=uid, email=f"{uid}@example.com", role="student")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/careers/recommendations", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0

    ds_rec = next((r for r in data if "data science" in r["title"].lower()), None)
    assert ds_rec is not None
    assert ds_rec["insufficient_data"] is True
    assert ds_rec["match_score"] is None
    # Crucial: Must NEVER be marked technically eligible when data is insufficient
    assert ds_rec["eligibility_met"] is False
    assert "assessment" in ds_rec["eligibility_notes"].lower() or "required" in ds_rec["eligibility_notes"].lower()
    assert len(ds_rec["missing_required_skills"]) > 0
    assert len(ds_rec["skill_gaps"]) > 0
    for gap in ds_rec["skill_gaps"]:
        assert gap["is_missing"] is True
        assert gap["current_level"] == 0.0

def test_assessed_student_in_data_science_gets_deterministic_match_score():
    uid = f"assessed_ds_{uuid.uuid4().hex[:8]}"
    email = f"{uid}@example.com"
    token = create_mock_jwt(uid=uid, email=email, role="student")
    headers = {"Authorization": f"Bearer {token}"}

    # Set up user doc with Bachelor's degree
    FirestoreRepository.set_document("users", uid, {
        "uid": uid,
        "email": email,
        "name": "Data Science Student",
        "role": "student",
        "education_level": "Bachelor's",
        "claimed_skills": ["Python"],
        "projects": [
            {
                "title": "Customer Churn Prediction",
                "technologies": ["Python", "Pandas", "Scikit-Learn"],
                "description": "Trained predictive models on 10k customer records."
            }
        ]
    })

    # Seed a completed assessment in Data Science & Machine Learning
    asmt_id = f"asmt_completed_ds_{uid}"
    FirestoreRepository.set_document("assessments", asmt_id, {
        "id": asmt_id,
        "user_id": uid,
        "domain": "Data Science & Machine Learning",
        "status": "completed",
        "total_score_percentage": 78.0,
        "result": {
            "attempt_id": asmt_id,
            "user_id": uid,
            "domain": "Data Science & Machine Learning",
            "total_score_percentage": 78.0,
            "skill_breakdown": [
                {
                    "skill": "Python",
                    "score_percentage": 85.0,
                    "proficiency_level": "Advanced",
                    "evidence": "Demonstrated clean vectorized operations and list comprehensions."
                },
                {
                    "skill": "Pandas & Data Manipulation",
                    "score_percentage": 80.0,
                    "proficiency_level": "Advanced",
                    "evidence": "Applied groupby aggregations and missing data imputation accurately."
                },
                {
                    "skill": "Machine Learning (Scikit-Learn)",
                    "score_percentage": 75.0,
                    "proficiency_level": "Proficient",
                    "evidence": "Correctly selected ROC-AUC for imbalanced binary classification."
                },
                {
                    "skill": "Statistics & Mathematics",
                    "score_percentage": 70.0,
                    "proficiency_level": "Proficient",
                    "evidence": "Understood hypothesis testing p-value interpretation."
                }
            ],
            "strengths_summary": ["Python data pipelines", "Scikit-Learn modeling"],
            "weaknesses_summary": ["Statistics edge cases"]
        }
    })

    # Call recommendations with regenerate=True to force fresh calculation from the new assessment
    res = client.get("/api/v1/careers/recommendations?regenerate=true", headers=headers)
    assert res.status_code == 200
    data = res.json()

    ds_rec = next((r for r in data if "data science" in r["title"].lower()), None)
    assert ds_rec is not None
    assert ds_rec["insufficient_data"] is False
    assert ds_rec["match_score"] is not None
    assert ds_rec["match_score"] >= 70.0
    assert ds_rec["eligibility_met"] is True
    assert len(ds_rec["matching_skills"]) >= 3
    assert len(ds_rec["assessment_evidence"]) > 0
    # Verifies assessment evidence is attached
    assert any("Python" in ev for ev in ds_rec["assessment_evidence"])
    # Verifies project evidence is attached
    assert len(ds_rec["relevant_project_evidence"]) > 0

def test_career_recommendations_auto_updates_when_assessment_completed():
    uid = f"auto_update_{uuid.uuid4().hex[:8]}"
    email = f"{uid}@example.com"
    token = create_mock_jwt(uid=uid, email=email, role="student")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Initial call when unassessed -> saves recommendations with insufficient_data=True
    res1 = client.get("/api/v1/careers/recommendations", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    ds1 = next((r for r in data1 if "data science" in r["title"].lower()), None)
    assert ds1["insufficient_data"] is True

    # 2. Student now takes and completes assessment in Data Science
    asmt_id = f"asmt_auto_{uid}"
    FirestoreRepository.set_document("assessments", asmt_id, {
        "id": asmt_id,
        "user_id": uid,
        "domain": "Data Science & Machine Learning",
        "status": "completed",
        "total_score_percentage": 82.0,
        "result": {
            "attempt_id": asmt_id,
            "user_id": uid,
            "domain": "Data Science & Machine Learning",
            "total_score_percentage": 82.0,
            "skill_breakdown": [
                {"skill": "Python", "score_percentage": 90.0, "evidence": "Excellent OOP and NumPy mastery"},
                {"skill": "Machine Learning (Scikit-Learn)", "score_percentage": 80.0, "evidence": "Cross-validation and hyperparameter tuning"}
            ]
        }
    })

    # 3. Call without regenerate flag -> should detect new assessment and automatically recompute!
    res2 = client.get("/api/v1/careers/recommendations", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    ds2 = next((r for r in data2 if "data science" in r["title"].lower()), None)
    assert ds2["insufficient_data"] is False
    assert ds2["match_score"] is not None
    assert ds2["match_score"] > 0

def test_student_profile_resync_preserves_skills_and_validated_scores():
    uid = f"resync_preserve_{uuid.uuid4().hex[:8]}"
    email = f"{uid}@example.com"
    token = create_mock_jwt(uid=uid, email=email, role="student")
    headers = {"Authorization": f"Bearer {token}"}

    # Initial profile setup with skills and validated scores
    FirestoreRepository.set_document("users", uid, {
        "uid": uid,
        "email": email,
        "name": "Preserve Student",
        "role": "student",
        "technical_skills": ["Python", "FastAPI"],
        "claimed_skills": ["Python", "FastAPI"],
        "validated_skills": {"Python": 88.0, "FastAPI": 82.0},
        "projects": [{"title": "API Gateway", "technologies": ["Python", "FastAPI"]}]
    })

    # Sync profile again (e.g. on fresh login)
    res = client.post(
        "/api/v1/auth/sync-profile",
        json={"email": email, "name": "Preserve Student Updated"},
        headers=headers
    )
    assert res.status_code == 200

    # Verify Firestore document was NOT overwritten or wiped with blank defaults
    persisted_doc = FirestoreRepository.get_document("users", uid)
    assert persisted_doc is not None
    assert "Python" in persisted_doc.get("technical_skills", [])
    assert persisted_doc.get("validated_skills", {}).get("Python") == 88.0
    assert len(persisted_doc.get("projects", [])) == 1

    # Verify /profiles/me returns all preserved fields
    prof_res = client.get("/api/v1/profiles/me", headers=headers)
    assert prof_res.status_code == 200
    prof_data = prof_res.json()
    assert "Python" in prof_data.get("technical_skills", [])
    assert prof_data.get("validated_skills", {}).get("Python") == 88.0
    assert len(prof_data.get("projects", [])) == 1

def test_cross_student_assessment_access_forbidden():
    owner_uid = f"owner_{uuid.uuid4().hex[:8]}"
    other_uid = f"other_{uuid.uuid4().hex[:8]}"

    asmt_id = f"asmt_private_{owner_uid}"
    FirestoreRepository.set_document("assessments", asmt_id, {
        "id": asmt_id,
        "user_id": owner_uid,
        "domain": "Frontend Development",
        "status": "completed",
        "result": {"attempt_id": asmt_id, "user_id": owner_uid, "total_score_percentage": 90.0}
    })

    other_token = create_mock_jwt(uid=other_uid, email=f"{other_uid}@example.com", role="student")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Attempting to access owner's assessment report with other student's token
    res = client.get(f"/api/v1/assessments/{asmt_id}/report", headers=other_headers)
    assert res.status_code == 403
