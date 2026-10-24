import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.assessment import QuestionType, DifficultyLevel
from app.services.gemini_service import (
    gemini_service,
    GeminiAPIError,
    GeminiRateLimitError,
    GeminiConfigError
)
from app.repositories.firestore_repo import FirestoreRepository

client = TestClient(app)

STUDENT_AUTH_HEADER = {"Authorization": "Bearer demo-student-token"}
OTHER_STUDENT_AUTH_HEADER = {"Authorization": "Bearer dev-user-student-2"}

def _generate_mock_questions_batch(count: int, start_idx: int = 1, domain: str = "Frontend Development"):
    """Generates synthetic valid batch of questions matching Gemini JSON schema."""
    batch = []
    for i in range(start_idx, start_idx + count):
        q_type = "mcq" if i % 3 != 0 else "short_answer"
        if q_type == "mcq":
            batch.append({
                "skill": "React" if i % 2 == 0 else "TypeScript",
                "related_project": "E-Commerce App" if i % 4 == 0 else None,
                "question_text": f"What is the architectural purpose of component pattern #{i} in modern scalable systems?",
                "question_type": "mcq",
                "difficulty": "intermediate" if i % 2 == 0 else "beginner",
                "options": [
                    f"Option A #{i}: isolates rendering state",
                    f"Option B #{i}: binds global event listener",
                    f"Option C #{i}: performs direct DOM mutation",
                    f"Option D #{i}: caches network response"
                ],
                "correct_answer": f"Option A #{i}: isolates rendering state",
                "rubric": None,
                "explanation": f"Option A #{i} isolates rendering state cleanly.",
                "points": 10.0,
                "source_reference": "React Architecture Guide"
            })
        else:
            batch.append({
                "skill": "TypeScript",
                "related_project": "E-Commerce App",
                "question_text": f"Describe the trade-offs between interface and type aliases when modeling domain entity #{i}.",
                "question_type": "short_answer",
                "difficulty": "advanced",
                "options": None,
                "correct_answer": None,
                "rubric": {
                    "Declaration Merging": "Explains interface declaration merging vs union capabilities",
                    "Performance": "Discusses TypeScript compiler type resolution efficiency"
                },
                "explanation": "Interfaces allow declaration merging while type aliases support complex mapped types.",
                "points": 20.0,
                "source_reference": "TypeScript Handbook"
            })
    return batch

# 1. Test 20 questions generation
def test_request_20_questions_produces_exactly_20_questions():
    with patch.object(gemini_service, "is_available", return_value=True):
        # We need 20 questions (2 batches of 10)
        batch_1 = _generate_mock_questions_batch(10, start_idx=1)
        batch_2 = _generate_mock_questions_batch(10, start_idx=11)

        with patch.object(gemini_service, "generate_json", side_effect=[batch_1, batch_2]):
            res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={
                    "confirmed_skills": ["React", "TypeScript", "FastAPI"],
                    "question_count": 20,
                    "focus": "all_skills",
                    "difficulty": "adaptive",
                    "question_types": "combination",
                    "domain": "Frontend Development"
                }
            )

            assert res.status_code == 200, res.text
            data = res.json()
            assert data["requested_question_count"] == 20
            assert data["actual_question_count"] == 20
            assert len(data["questions"]) == 20

            # Answer keys strictly hidden
            for q in data["questions"]:
                assert "correct_answer" not in q
                assert "rubric" not in q
                assert "explanation" not in q
                assert q["question_text"]

# 2. Test 30 questions generation
def test_request_30_questions_produces_exactly_30_questions():
    with patch.object(gemini_service, "is_available", return_value=True):
        b1 = _generate_mock_questions_batch(10, start_idx=1)
        b2 = _generate_mock_questions_batch(10, start_idx=11)
        b3 = _generate_mock_questions_batch(10, start_idx=21)

        with patch.object(gemini_service, "generate_json", side_effect=[b1, b2, b3]):
            res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={
                    "confirmed_skills": ["Python", "FastAPI", "Docker"],
                    "question_count": 30,
                    "focus": "all_skills",
                    "difficulty": "intermediate",
                    "question_types": "combination",
                    "domain": "Backend Development"
                }
            )

            assert res.status_code == 200, res.text
            data = res.json()
            assert data["requested_question_count"] == 30
            assert data["actual_question_count"] == 30
            assert len(data["questions"]) == 30

# 3. Test 50 questions generation in manageable batches
def test_request_50_questions_produces_exactly_50_questions():
    with patch.object(gemini_service, "is_available", return_value=True):
        batches = [_generate_mock_questions_batch(10, start_idx=i*10 + 1) for i in range(5)]

        with patch.object(gemini_service, "generate_json", side_effect=batches):
            res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={
                    "confirmed_skills": ["Python", "FastAPI", "Pandas", "Machine Learning"],
                    "question_count": 50,
                    "focus": "all_skills",
                    "difficulty": "adaptive",
                    "question_types": "combination",
                    "domain": "Data Science & Machine Learning"
                }
            )

            assert res.status_code == 200, res.text
            data = res.json()
            assert data["requested_question_count"] == 50
            assert data["actual_question_count"] == 50
            assert len(data["questions"]) == 50

# 4. Unsupported question counts rejected
@pytest.mark.parametrize("invalid_count", [5, 10, 25, 40, 100])
def test_unsupported_question_counts_rejected(invalid_count):
    res = client.post(
        "/api/v1/assessments/generate",
        headers=STUDENT_AUTH_HEADER,
        json={
            "confirmed_skills": ["React"],
            "question_count": invalid_count,
            "domain": "Frontend Development"
        }
    )
    # Validation error or 400
    assert res.status_code in (400, 422)

# 5. Duplicate and malformed questions are rejected or regenerated
def test_duplicate_and_malformed_questions_rejected():
    with patch.object(gemini_service, "is_available", return_value=True):
        # Batch with malformed items: 1 duplicate, 1 MCQ with only 3 options, 1 MCQ where answer is not in options
        malformed_batch = [
            # Valid item 1
            {
                "skill": "React",
                "question_text": "What is the primary trade-off when using React Server Components over Client Components?",
                "question_type": "mcq",
                "difficulty": "intermediate",
                "options": ["Reduces client JS bundle", "Enables browser onClick handlers", "Increases client hydration time", "Bypasses web standards"],
                "correct_answer": "Reduces client JS bundle",
                "points": 10.0
            },
            # Malformed 1: only 3 options
            {
                "skill": "React",
                "question_text": "What does useId generate in concurrent React applications?",
                "question_type": "mcq",
                "difficulty": "beginner",
                "options": ["Unique string identifier", "Random floating number", "Timestamp"],
                "correct_answer": "Unique string identifier",
                "points": 10.0
            },
            # Malformed 2: correct answer doesn't match options
            {
                "skill": "React",
                "question_text": "Which hook should be used to synchronize with an external system in React 19?",
                "question_type": "mcq",
                "difficulty": "intermediate",
                "options": ["useEffect", "useMemo", "useCallback", "useState"],
                "correct_answer": "useExternalStoreNonExistentOption",
                "points": 10.0
            },
            # Malformed 3: Duplicate of item 1
            {
                "skill": "React",
                "question_text": "What is the primary trade-off when using React Server Components over Client Components?",
                "question_type": "mcq",
                "difficulty": "intermediate",
                "options": ["Reduces client JS bundle", "Enables browser onClick handlers", "Increases client hydration time", "Bypasses web standards"],
                "correct_answer": "Reduces client JS bundle",
                "points": 10.0
            }
        ]

        # Subsequent clean batches to reach 20
        clean_batch_1 = _generate_mock_questions_batch(10, start_idx=2)
        clean_batch_2 = _generate_mock_questions_batch(10, start_idx=12)

        with patch.object(gemini_service, "generate_json", side_effect=[malformed_batch, clean_batch_1, clean_batch_2]):
            res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={
                    "confirmed_skills": ["React"],
                    "question_count": 20,
                    "domain": "Frontend Development"
                }
            )

            assert res.status_code == 200, res.text
            data = res.json()
            assert data["actual_question_count"] == 20
            # Ensure no duplicates in final questions
            q_texts = [q["question_text"] for q in data["questions"]]
            assert len(q_texts) == len(set(q_texts))

# 6. Missing Gemini credentials produce clear error
def test_missing_gemini_credentials_error():
    with patch.object(gemini_service, "is_available", return_value=False):
        res = client.post(
            "/api/v1/assessments/generate",
            headers=STUDENT_AUTH_HEADER,
            json={
                "confirmed_skills": ["React"],
                "question_count": 20,
                "domain": "Frontend Development"
            }
        )
        assert res.status_code == 503
        assert "Gemini API credentials are not configured" in res.json()["detail"]

# 7. Gemini API failure does not create false successful assessment
def test_gemini_api_failures_no_false_success():
    with patch.object(gemini_service, "is_available", return_value=True):
        with patch.object(gemini_service, "generate_json", side_effect=GeminiRateLimitError("Quota exceeded 429")):
            res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={
                    "confirmed_skills": ["Python"],
                    "question_count": 20,
                    "domain": "Backend Development"
                }
            )
            assert res.status_code == 502
            assert "Gemini API error" in res.json()["detail"]

# 8. Correct answers remain hidden before submission
def test_correct_answers_hidden_before_submission():
    with patch.object(gemini_service, "is_available", return_value=True):
        batch1 = _generate_mock_questions_batch(10, start_idx=1)
        batch2 = _generate_mock_questions_batch(10, start_idx=11)
        with patch.object(gemini_service, "generate_json", side_effect=[batch1, batch2]):
            gen_res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={"confirmed_skills": ["React"], "question_count": 20}
            )
            assert gen_res.status_code == 200
            asmt_id = gen_res.json()["id"]

            # GET questions endpoint
            q_res = client.get(f"/api/v1/assessments/{asmt_id}/questions", headers=STUDENT_AUTH_HEADER)
            assert q_res.status_code == 200
            questions = q_res.json()
            assert len(questions) == 20
            for q in questions:
                assert "correct_answer" not in q
                assert "rubric" not in q
                assert "explanation" not in q

# 9. Student ownership: other students cannot access assessment
def test_student_ownership_and_access_control():
    with patch.object(gemini_service, "is_available", return_value=True):
        b1 = _generate_mock_questions_batch(10, start_idx=1)
        b2 = _generate_mock_questions_batch(10, start_idx=11)
        with patch.object(gemini_service, "generate_json", side_effect=[b1, b2]):
            gen_res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={"confirmed_skills": ["React"], "question_count": 20}
            )
            asmt_id = gen_res.json()["id"]

            # Try accessing from another student
            other_res = client.get(f"/api/v1/assessments/{asmt_id}", headers=OTHER_STUDENT_AUTH_HEADER)
            assert other_res.status_code == 403
            assert "another student" in other_res.json()["detail"].lower()

            # Try modifying answers from another student
            other_put = client.put(
                f"/api/v1/assessments/{asmt_id}/answers",
                headers=OTHER_STUDENT_AUTH_HEADER,
                json={"answers": {"q1": "test"}}
            )
            assert other_put.status_code == 403

# 10. Intermediate answer saving and persistence
def test_assessment_answers_persistence():
    with patch.object(gemini_service, "is_available", return_value=True):
        b1 = _generate_mock_questions_batch(10, start_idx=1)
        b2 = _generate_mock_questions_batch(10, start_idx=11)
        with patch.object(gemini_service, "generate_json", side_effect=[b1, b2]):
            gen_res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={"confirmed_skills": ["React"], "question_count": 20}
            )
            asmt_id = gen_res.json()["id"]
            q_id = gen_res.json()["questions"][0]["id"]

            # Save answer
            put_res = client.put(
                f"/api/v1/assessments/{asmt_id}/answers",
                headers=STUDENT_AUTH_HEADER,
                json={"answers": {q_id: "Option A #1: isolates rendering state"}, "time_remaining_seconds": 1100}
            )
            assert put_res.status_code == 200
            assert put_res.json()["status"] == "success"

            # Check that answer is persisted
            get_res = client.get(f"/api/v1/assessments/{asmt_id}", headers=STUDENT_AUTH_HEADER)
            assert get_res.status_code == 200
            saved_answers = get_res.json().get("saved_answers", {})
            assert saved_answers.get(q_id) == "Option A #1: isolates rendering state"

# 11. Submission, scoring and report verification
def test_submission_and_scoring():
    with patch.object(gemini_service, "is_available", return_value=True):
        b1 = _generate_mock_questions_batch(10, start_idx=1)
        b2 = _generate_mock_questions_batch(10, start_idx=11)
        batch_queue = [b1, b2]

        def mock_generate_json(prompt, *args, **kwargs):
            if "evaluate the student's descriptive response" in prompt.lower():
                return {
                    "points_awarded": 18.0,
                    "feedback": "Strong architectural reasoning and clear data flow description.",
                    "improvement_suggestion": "Explore distributed state synchronization."
                }
            if batch_queue:
                return batch_queue.pop(0)
            return []

        with patch.object(gemini_service, "generate_json", side_effect=mock_generate_json):
            gen_res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={"confirmed_skills": ["React"], "question_count": 20}
            )
            asmt_id = gen_res.json()["id"]
            questions = gen_res.json()["questions"]

            answers = []
            for q in questions:
                if q["question_type"] == "mcq":
                    answers.append({"question_id": q["id"], "answer": q["options"][0]})
                else:
                    answers.append({"question_id": q["id"], "answer": "In-depth explanation covering architecture and trade-offs."})

            sub_res = client.post(
                f"/api/v1/assessments/{asmt_id}/submit",
                headers=STUDENT_AUTH_HEADER,
                json={"answers": answers, "time_taken_seconds": 450}
            )
            assert sub_res.status_code == 200
            report = sub_res.json()
            assert report["total_available_points"] > 0
            assert "skill_breakdown" in report
            assert len(report["skill_breakdown"]) > 0

            # Verification of report endpoint
            rep_res = client.get(f"/api/v1/assessments/{asmt_id}/report", headers=STUDENT_AUTH_HEADER)
            assert rep_res.status_code == 200
            assert rep_res.json()["attempt_id"] == asmt_id

# 12. Duplicate submission prevention and answer modification locking
def test_prevent_duplicate_submission_and_modification():
    with patch.object(gemini_service, "is_available", return_value=True):
        b1 = _generate_mock_questions_batch(10, start_idx=1)
        b2 = _generate_mock_questions_batch(10, start_idx=11)
        with patch.object(gemini_service, "generate_json", side_effect=[b1, b2]):
            gen_res = client.post(
                "/api/v1/assessments/generate",
                headers=STUDENT_AUTH_HEADER,
                json={"confirmed_skills": ["React"], "question_count": 20}
            )
            asmt_id = gen_res.json()["id"]
            q_id = gen_res.json()["questions"][0]["id"]

            # First submission
            sub_res = client.post(
                f"/api/v1/assessments/{asmt_id}/submit",
                headers=STUDENT_AUTH_HEADER,
                json={"answers": [{"question_id": q_id, "answer": "Option A #1: isolates rendering state"}]}
            )
            assert sub_res.status_code == 200

            # Modifying answers on submitted assessment must be rejected
            put_res = client.put(
                f"/api/v1/assessments/{asmt_id}/answers",
                headers=STUDENT_AUTH_HEADER,
                json={"answers": {q_id: "Modified answer"}}
            )
            assert put_res.status_code == 400
            assert "already been submitted" in put_res.json()["detail"].lower()

            # Second submission should return existing report without error or corruption
            sub_res_2 = client.post(
                f"/api/v1/assessments/{asmt_id}/submit",
                headers=STUDENT_AUTH_HEADER,
                json={"answers": [{"question_id": q_id, "answer": "Another answer"}]}
            )
            assert sub_res_2.status_code == 200
            assert sub_res_2.json()["attempt_id"] == asmt_id
