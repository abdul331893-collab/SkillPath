import uuid
import re
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.repositories.firestore_repo import FirestoreRepository
from app.schemas.assessment import (
    QuestionPublic,
    QuestionAdmin,
    QuestionCreate,
    QuestionGenerated,
    QuestionType,
    DifficultyLevel,
    AssessmentFocus,
    AssessmentGenerateRequest,
    AssessmentRecordResponse,
    AssessmentSubmissionRequest,
    AssessmentResultResponse,
    QuestionEvaluationResult,
    SkillScoreBreakdown,
    AssessmentJobResponse,
)
from app.services.scoring_service import ScoringService
from app.services.gemini_service import (
    gemini_service,
    GeminiError,
    GeminiConfigError,
    GeminiAuthError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiAPIError
)
from app.core.logging import logger

DEFAULT_QUESTIONS = [
    # Frontend Development
    {
        "id": "q-fe-1",
        "domain": "Frontend Development",
        "skill": "React",
        "question_text": "What is the primary purpose of the React useMemo hook?",
        "question_type": QuestionType.MCQ,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "options": [
            "To memoize the result of an expensive calculation between renders",
            "To manage component lifecycle methods such as componentDidMount",
            "To directly modify the browser DOM elements bypassing Virtual DOM",
            "To synchronize data state with local storage automatically"
        ],
        "correct_answer": "To memoize the result of an expensive calculation between renders",
        "explanation": "useMemo caches the result of an expensive computation based on dependency array changes.",
        "points": 10.0
    },
    {
        "id": "q-fe-2",
        "domain": "Frontend Development",
        "skill": "JavaScript",
        "question_text": "Explain how the JavaScript Event Loop coordinates the Call Stack, Microtask Queue (Promises), and Macrotask Queue (setTimeout). Provide an example sequence.",
        "question_type": QuestionType.DESCRIPTIVE,
        "difficulty": DifficultyLevel.ADVANCED,
        "options": None,
        "rubric": {
            "Call Stack execution": "Explains synchronous frame execution",
            "Microtask vs Macrotask priority": "Explains that microtasks are completely drained before the next macrotask is executed",
            "Event Loop cycle": "Accurately traces example execution order"
        },
        "points": 20.0
    },
    {
        "id": "q-fe-3",
        "domain": "Frontend Development",
        "skill": "HTML & CSS",
        "question_text": "Which CSS display property creates a two-dimensional layout system with rows and columns?",
        "question_type": QuestionType.MCQ,
        "difficulty": DifficultyLevel.BEGINNER,
        "options": ["display: grid", "display: flex", "display: block", "display: inline-block"],
        "correct_answer": "display: grid",
        "explanation": "CSS Grid is a two-dimensional grid-based layout system.",
        "points": 10.0
    },
    # Backend Development
    {
        "id": "q-be-1",
        "domain": "Backend Development",
        "skill": "FastAPI",
        "question_text": "How does FastAPI achieve automated request validation and serialization?",
        "question_type": QuestionType.MCQ,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "options": [
            "Through native integration with Pydantic schemas and Python type hints",
            "By parsing raw JSON strings with custom regular expressions",
            "Through runtime reflection on database SQL schemas",
            "Using XML schema definitions compiled at startup"
        ],
        "correct_answer": "Through native integration with Pydantic schemas and Python type hints",
        "explanation": "FastAPI uses Pydantic data validation and standard Python 3.10+ type annotations.",
        "points": 10.0
    },
    {
        "id": "q-be-2",
        "domain": "Backend Development",
        "skill": "SQL & Databases",
        "question_text": "Describe the difference between an optimistic concurrency lock and a pessimistic lock in relational databases. When would you choose one over the other?",
        "question_type": QuestionType.DESCRIPTIVE,
        "difficulty": DifficultyLevel.ADVANCED,
        "options": None,
        "rubric": {
            "Pessimistic Locking definition": "Explains row/table locking (SELECT FOR UPDATE) preventing concurrent access",
            "Optimistic Locking definition": "Explains version column / timestamp validation on commit",
            "Trade-offs & use case": "Identifies contention levels (high conflict vs low conflict scenarios)"
        },
        "points": 20.0
    },
    {
        "id": "q-be-3",
        "domain": "Backend Development",
        "skill": "Python",
        "question_text": "What is the time complexity of looking up a key in a standard Python dictionary in average case?",
        "question_type": QuestionType.MCQ,
        "difficulty": DifficultyLevel.BEGINNER,
        "options": ["O(1)", "O(n)", "O(log n)", "O(n^2)"],
        "correct_answer": "O(1)",
        "explanation": "Python dictionaries are hash tables with O(1) average lookup time.",
        "points": 10.0
    },
    # Data Science
    {
        "id": "q-ds-1",
        "domain": "Data Science & Machine Learning",
        "skill": "Machine Learning (Scikit-Learn)",
        "question_text": "What is the primary indicator of model overfitting during training?",
        "question_type": QuestionType.MCQ,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "options": [
            "High training accuracy with deteriorating validation/test accuracy",
            "Low training accuracy and low validation accuracy",
            "Both training and validation loss decreasing equally",
            "Validation loss reaching zero while training loss increases"
        ],
        "correct_answer": "High training accuracy with deteriorating validation/test accuracy",
        "explanation": "Overfitting happens when a model memorizes training noise and fails to generalize.",
        "points": 10.0
    },
    {
        "id": "q-ds-2",
        "domain": "Data Science & Machine Learning",
        "skill": "Pandas & Data Manipulation",
        "question_text": "Explain the difference between handling missing data via imputation versus deletion. What risks does mean imputation introduce to statistical distributions?",
        "question_type": QuestionType.DESCRIPTIVE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "options": None,
        "rubric": {
            "Imputation vs Deletion": "Defines row removal vs placeholder replacement",
            "Variance reduction risk": "Explains that mean imputation reduces variance and distorts standard deviation",
            "Recommendation": "Suggests median/KNN/multiple imputation or domain-specific strategies"
        },
        "points": 20.0
    }
]

class AssessmentService:
    """Manages dynamic question generation, assessment persistence, progress, scoring, and history."""

    @classmethod
    def initialize_default_questions(cls):
        existing = FirestoreRepository.query_documents("questions", limit=1)
        if not existing:
            for q in DEFAULT_QUESTIONS:
                FirestoreRepository.set_document("questions", q["id"], q)

    @classmethod
    def validate_generation_request(cls, req: AssessmentGenerateRequest):
        """Strictly validates assessment configuration, question count, and confirmed skills."""
        requested_count = req.question_count
        if requested_count not in (20, 30, 50):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported question count: {requested_count}. Must be exactly 20, 30, or 50."
            )
        target_skills = req.selected_skills if (req.focus == "selected_skills" and req.selected_skills) else req.confirmed_skills
        if not target_skills:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one confirmed skill is required to generate a personalized assessment."
            )
        if req.focus == "project_based" and not req.projects:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project-based assessment requires at least one project in your profile."
            )
        if not gemini_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini API credentials are not configured on the server. Assessment generation cannot proceed."
            )

    @classmethod
    def start_generation_job(cls, user_id: str, req: AssessmentGenerateRequest) -> Dict[str, Any]:
        """Creates and persists an asynchronous generation job record in Firestore."""
        cls.validate_generation_request(req)
        cls.initialize_default_questions()

        job_id = f"genjob_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()
        job_doc = {
            "id": job_id,
            "job_id": job_id,
            "user_id": user_id,
            "status": "queued",
            "progress_message": "Preparing your personalized assessment...",
            "requested_question_count": req.question_count,
            "domain": req.domain or "Frontend Development",
            "focus": req.focus,
            "difficulty": req.difficulty,
            "question_types": req.question_types,
            "assessment_id": None,
            "error_message": None,
            "created_at": now_str,
            "updated_at": now_str
        }
        FirestoreRepository.set_document("assessment_jobs", job_id, job_doc)
        logger.info(f"Initialized assessment generation job {job_id} for user {user_id}")
        return job_doc

    @classmethod
    def execute_generation_job(cls, job_id: str, user_id: str, req: AssessmentGenerateRequest):
        """Asynchronously runs question generation and updates job status upon completion or failure."""
        now_str = datetime.now(timezone.utc).isoformat()
        FirestoreRepository.update_document("assessment_jobs", job_id, {
            "status": "processing",
            "progress_message": "Creating and validating questions based on your confirmed skills...",
            "updated_at": now_str
        })
        try:
            assessment = cls.create_and_generate_assessment(user_id=user_id, req=req)
            done_str = datetime.now(timezone.utc).isoformat()
            FirestoreRepository.update_document("assessment_jobs", job_id, {
                "status": "completed",
                "progress_message": f"Successfully generated {assessment.actual_question_count} questions.",
                "assessment_id": assessment.id,
                "updated_at": done_str
            })
            logger.info(f"Assessment job {job_id} completed successfully -> Assessment {assessment.id}")
        except Exception as e:
            fail_str = datetime.now(timezone.utc).isoformat()
            err_msg = str(e)
            logger.error(f"Assessment generation job {job_id} failed: {err_msg}")
            FirestoreRepository.update_document("assessment_jobs", job_id, {
                "status": "failed",
                "progress_message": "Question generation encountered an error.",
                "error_message": err_msg,
                "updated_at": fail_str
            })

    @classmethod
    def get_generation_job(cls, job_id: str, user_id: str) -> Dict[str, Any]:
        """Retrieves generation job status with ownership enforcement."""
        job = FirestoreRepository.get_document("assessment_jobs", job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")
        if job.get("user_id") != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot access another student's generation job")

        job_copy = dict(job)
        if job_copy.get("status") == "completed" and job_copy.get("assessment_id"):
            try:
                assessment = cls.get_assessment(job_copy["assessment_id"], user_id)
                job_copy["assessment"] = assessment
            except Exception as e:
                logger.debug(f"Could not load completed assessment for job {job_id}: {e}")
        return job_copy

    @classmethod
    def get_active_generation_job(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves any in-flight (queued or processing) generation job for the student."""
        jobs = FirestoreRepository.query_documents("assessment_jobs", filters=[("user_id", "==", user_id)], limit=10)
        active = [j for j in jobs if j.get("status") in ("queued", "processing")]
        if not active:
            return None
        active.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        return dict(active[0])

    @classmethod
    def create_and_generate_assessment(
        cls,
        user_id: str,
        req: AssessmentGenerateRequest
    ) -> AssessmentRecordResponse:
        """
        Creates a new personalized assessment record in Firestore by generating exactly
        20, 30, or 50 validated questions via Gemini in manageable batches.
        Enforces strict schema validation, question deduplication, and secure persistence.
        """
        cls.initialize_default_questions()

        # 1. Enforce question count is strictly 20, 30, or 50
        requested_count = req.question_count
        if requested_count not in (20, 30, 50):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported question count: {requested_count}. Must be exactly 20, 30, or 50."
            )

        # 2. Determine and validate target skills & projects
        target_skills = req.selected_skills if (req.focus == "selected_skills" and req.selected_skills) else req.confirmed_skills
        if not target_skills:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one confirmed skill is required to generate a personalized assessment."
            )

        if req.focus == "project_based" and not req.projects:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project-based assessment requires at least one project in your profile."
            )

        # 3. Check Gemini availability on server; never fake generation
        if not gemini_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini API credentials are not configured on the server. Assessment generation cannot proceed."
            )

        domain = req.domain or "Frontend Development"
        projects = req.projects or []

        # 4. Optional RAG context retrieval
        rag_context = ""
        try:
            from app.services.rag_service import DEFAULT_KNOWLEDGE_DOCS
            matched_docs = []
            for s in target_skills:
                s_lower = s.lower()
                for doc in DEFAULT_KNOWLEDGE_DOCS:
                    if doc["skill"].lower() in s_lower or s_lower in doc["skill"].lower():
                        ref_str = f"Approved Reference [{doc['title']} - {doc['skill']}]: {doc['content']}"
                        if ref_str not in matched_docs:
                            matched_docs.append(ref_str)
            if matched_docs:
                rag_context = "Context from Approved Curriculum Resources:\n" + "\n".join(matched_docs[:3])
        except Exception as e:
            logger.debug(f"Optional RAG grounding skipped: {e}")

        # 5. Batch generation loop
        # We generate in batches of 10 (or 5-10) to respect model output limits
        batch_size = 10
        validated_questions: List[Dict[str, Any]] = []
        seen_texts: Set[str] = set()

        max_batches = (requested_count // batch_size) + 4
        attempts = 0

        projects_summary = "\n".join([
            f"- Project '{p.get('title', 'Project')}': Technologies: {', '.join(p.get('technologies', []))}. Description: {p.get('description', '')}"
            for p in projects[:3]
        ])

        while len(validated_questions) < requested_count and attempts < max_batches:
            attempts += 1
            needed_in_batch = min(batch_size, requested_count - len(validated_questions))

            # Difficulty guidance
            if req.difficulty == "adaptive":
                diff_guidance = (
                    "Create an adaptive distribution: approximately 30% beginner foundational questions, "
                    "40% intermediate implementation questions, and 30% advanced architectural/problem-solving questions."
                )
            else:
                diff_guidance = f"All generated questions must target {req.difficulty} difficulty level."

            # Question types guidance
            if req.question_types == "mcq":
                types_guidance = "Generate ONLY Multiple Choice Questions (mcq)."
            elif req.question_types == "short_answer":
                types_guidance = "Generate ONLY Short Answer / Descriptive questions (short_answer)."
            else:
                types_guidance = "Generate a combination of Multiple Choice Questions (mcq) (around 70%) and Short Answer questions (short_answer) (around 30%)."

            # Project guidance
            if req.focus == "project_based" or (projects and len(validated_questions) % 4 == 0):
                proj_guidance = (
                    "Directly ground practical questions in the candidate's actual projects listed above. "
                    "Reference the project's stated technologies, architecture, and engineering trade-offs. Never invent projects."
                )
            else:
                proj_guidance = "Cover the confirmed skills proportionally across core fundamentals and real-world scenarios."

            batch_prompt = f"""
You are the Lead Technical Examiner for SkillPath AI.
Generate exactly {needed_in_batch} rigorous, non-trivial technical assessment questions evaluating the candidate.

Candidate Target Domain: {domain}
Assessment Focus: {req.focus}
Confirmed Skills: {', '.join(target_skills)}
Candidate Real Projects:
{projects_summary or "No projects specified"}

{rag_context}

Generation Instructions:
1. Skills coverage: Proportionally distribute questions across the candidate's confirmed skills ({', '.join(target_skills)}).
2. Difficulty: {diff_guidance}
3. Question Types: {types_guidance}
4. Practical Application: {proj_guidance}
5. For Multiple Choice (mcq):
   - Provide EXACTLY 4 distinct, plausible options in the "options" list.
   - Provide EXACTLY ONE "correct_answer" that must be an exact string match to one of the 4 options.
   - "rubric" must be null.
   - "points": 10.0.
6. For Short Answer (short_answer):
   - "options" must be null.
   - "correct_answer" must be null.
   - Provide a detailed "rubric" dictionary mapping key evaluation criteria (e.g. concept explanation, trade-off analysis) to grading benchmarks.
   - "points": 20.0.
7. Explanations: Include a concise, educational "explanation" for every question.
8. Uniqueness: Questions must be completely distinct. Do not duplicate concepts or questions already generated.

Respond STRICTLY with a JSON array of question objects:
[
  {{
    "skill": "Specific Skill Name from Confirmed Skills",
    "related_project": "Project Title or null",
    "question_text": "Detailed, clear question text...",
    "question_type": "mcq" or "short_answer",
    "difficulty": "beginner" | "intermediate" | "advanced",
    "options": ["Option A", "Option B", "Option C", "Option D"] or null,
    "correct_answer": "Option A" or null,
    "rubric": {{"Key Concept": "Criteria detail"}} or null,
    "explanation": "Why this answer is correct...",
    "points": 10.0,
    "source_reference": "Approved curriculum reference title or null"
  }}
]
"""
            try:
                raw_response = gemini_service.generate_json(
                    prompt=batch_prompt,
                    temperature=0.3,
                    timeout=70.0
                )
            except GeminiError as e:
                logger.error(f"Gemini API failure during assessment batch generation: {e}")
                # If we haven't generated any questions or cannot continue, raise explicit error
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Gemini API error during question generation: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Unexpected generation failure: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unexpected error during assessment generation: {str(e)}"
                )

            if not isinstance(raw_response, list):
                logger.warning(f"Batch {attempts}: Gemini returned non-list JSON: {type(raw_response)}")
                continue

            for raw_q in raw_response:
                if len(validated_questions) >= requested_count:
                    break

                # Validate with Pydantic model
                try:
                    q_model = QuestionGenerated(**raw_q)
                except Exception as val_err:
                    logger.warning(f"Discarding malformed question from batch: {val_err}")
                    continue

                norm_text = re.sub(r"\s+", " ", q_model.question_text.strip().lower())
                if len(norm_text) < 15 or norm_text in seen_texts:
                    logger.warning("Discarding duplicate or trivial question text")
                    continue

                # Validate MCQ structure
                if q_model.question_type == QuestionType.MCQ:
                    if not q_model.options or len(q_model.options) != 4:
                        logger.warning("Discarding MCQ: does not have exactly 4 options")
                        continue
                    if len(set(q_model.options)) != 4:
                        logger.warning("Discarding MCQ: duplicate options found")
                        continue
                    if not q_model.correct_answer:
                        logger.warning("Discarding MCQ: missing correct_answer")
                        continue

                    # Verify correct answer matches one of the options
                    ans_str = str(q_model.correct_answer).strip()
                    matched_opt = next((opt for opt in q_model.options if opt.strip().lower() == ans_str.lower()), None)
                    if not matched_opt:
                        # Check if model gave option index or letter e.g. "A", "B", "0"
                        letter_map = {"a": 0, "b": 1, "c": 2, "d": 3}
                        if ans_str.lower() in letter_map:
                            matched_opt = q_model.options[letter_map[ans_str.lower()]]
                        elif ans_str.isdigit() and int(ans_str) in range(4):
                            matched_opt = q_model.options[int(ans_str)]
                        else:
                            logger.warning(f"Discarding MCQ: correct_answer '{ans_str}' not found in options")
                            continue

                    correct_answer_final = matched_opt
                    rubric_final = None
                    points_final = 10.0
                    q_type_final = QuestionType.MCQ

                elif q_model.question_type in (QuestionType.SHORT_ANSWER, QuestionType.DESCRIPTIVE):
                    q_type_final = QuestionType.SHORT_ANSWER
                    correct_answer_final = None
                    rubric_final = q_model.rubric or {"Understanding": "Demonstrates clear conceptual and practical explanation"}
                    points_final = 20.0
                    q_model.options = None
                else:
                    continue

                qid = f"q-{uuid.uuid4().hex[:10]}"
                question_record = {
                    "id": qid,
                    "domain": domain,
                    "skill": q_model.skill or target_skills[0],
                    "related_project": q_model.related_project,
                    "question_text": q_model.question_text.strip(),
                    "question_type": q_type_final,
                    "difficulty": q_model.difficulty,
                    "options": q_model.options,
                    "correct_answer": correct_answer_final,
                    "rubric": rubric_final,
                    "explanation": q_model.explanation or "Standardized curriculum assessment criteria.",
                    "points": points_final,
                    "source_reference": q_model.source_reference
                }

                seen_texts.add(norm_text)
                validated_questions.append(question_record)
                # Save to general questions collection for backward compatibility
                FirestoreRepository.set_document("questions", qid, question_record)

        # 6. Verify exact requested count was achieved
        if len(validated_questions) < requested_count:
            logger.error(f"Assessment generation incomplete: generated {len(validated_questions)}/{requested_count}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    f"Gemini was unable to generate the full requested assessment size. "
                    f"Generated {len(validated_questions)} of {requested_count} questions. Please retry."
                )
            )

        # Truncate to exact requested count
        final_questions = validated_questions[:requested_count]
        now_str = datetime.now(timezone.utc).isoformat()
        assessment_id = f"asmt_{uuid.uuid4().hex[:12]}"

        # 7. Persist complete assessment record in Firestore
        assessment_doc = {
            "id": assessment_id,
            "user_id": user_id,
            "domain": domain,
            "requested_question_count": requested_count,
            "actual_question_count": len(final_questions),
            "focus": req.focus,
            "difficulty": req.difficulty,
            "question_types": req.question_types,
            "duration_minutes": req.duration_minutes or (requested_count),
            "status": "generated",
            "created_at": now_str,
            "profile_snapshot": {
                "confirmed_skills": target_skills,
                "projects": projects,
                "domain": domain
            },
            "questions": final_questions,
            "answers": {},
            "submitted_at": None,
            "result": None
        }

        FirestoreRepository.set_document("assessments", assessment_id, assessment_doc)
        logger.info(f"Successfully generated and persisted assessment {assessment_id} with {len(final_questions)} questions for user {user_id}")

        # 8. Return public view (correct answers and rubrics strictly excluded)
        public_questions = [
            QuestionPublic(
                id=q["id"],
                domain=q["domain"],
                skill=q["skill"],
                related_project=q.get("related_project"),
                question_text=q["question_text"],
                question_type=q["question_type"],
                difficulty=q["difficulty"],
                options=q.get("options"),
                points=float(q.get("points", 10.0)),
                source_reference=q.get("source_reference")
            )
            for q in final_questions
        ]

        return AssessmentRecordResponse(
            id=assessment_id,
            user_id=user_id,
            domain=domain,
            requested_question_count=requested_count,
            actual_question_count=len(final_questions),
            focus=req.focus,
            difficulty=req.difficulty,
            question_types=req.question_types,
            duration_minutes=assessment_doc["duration_minutes"],
            status="generated",
            created_at=now_str,
            questions=public_questions,
            saved_answers={}
        )

    @classmethod
    def get_assessment(cls, assessment_id: str, user_id: str) -> AssessmentRecordResponse:
        """Retrieves an existing assessment, enforcing student ownership."""
        doc = FirestoreRepository.get_document("assessments", assessment_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment '{assessment_id}' not found."
            )

        if doc.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot access another student's assessment."
            )

        questions = doc.get("questions", [])
        public_questions = [
            QuestionPublic(
                id=q["id"],
                domain=q.get("domain", doc.get("domain", "")),
                skill=q.get("skill", "General"),
                related_project=q.get("related_project"),
                question_text=q["question_text"],
                question_type=q["question_type"],
                difficulty=q.get("difficulty", DifficultyLevel.INTERMEDIATE),
                options=q.get("options"),
                points=float(q.get("points", 10.0)),
                source_reference=q.get("source_reference")
            )
            for q in questions
        ]

        return AssessmentRecordResponse(
            id=doc["id"],
            user_id=doc["user_id"],
            domain=doc.get("domain", "Frontend Development"),
            requested_question_count=doc.get("requested_question_count", len(questions)),
            actual_question_count=doc.get("actual_question_count", len(questions)),
            focus=doc.get("focus", "all_skills"),
            difficulty=doc.get("difficulty", "adaptive"),
            question_types=doc.get("question_types", "combination"),
            duration_minutes=doc.get("duration_minutes"),
            status=doc.get("status", "in_progress"),
            created_at=doc.get("created_at", datetime.now(timezone.utc).isoformat()),
            questions=public_questions,
            saved_answers=doc.get("answers", {})
        )

    @classmethod
    def get_assessment_questions(cls, assessment_id: str, user_id: str) -> List[QuestionPublic]:
        """Retrieves questions for an assessment, ensuring answer keys are NEVER exposed."""
        assessment = cls.get_assessment(assessment_id, user_id)
        return assessment.questions

    @classmethod
    def save_answers(
        cls,
        assessment_id: str,
        user_id: str,
        answers: Dict[str, str],
        time_remaining_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Saves intermediate student answers, preventing modification of submitted tests."""
        doc = FirestoreRepository.get_document("assessments", assessment_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment '{assessment_id}' not found."
            )

        if doc.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot modify another student's assessment answers."
            )

        if doc.get("status") == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This assessment has already been submitted and cannot be modified."
            )

        current_answers = doc.get("answers", {})
        current_answers.update(answers)

        updates: Dict[str, Any] = {
            "answers": current_answers,
            "status": "in_progress"
        }
        if time_remaining_seconds is not None:
            updates["time_remaining_seconds"] = time_remaining_seconds

        FirestoreRepository.update_document("assessments", assessment_id, updates)
        return {"status": "success", "saved_count": len(current_answers)}

    @classmethod
    def get_questions_for_domain(cls, domain: str) -> List[QuestionPublic]:
        """Legacy helper retrieving curated questions for a domain."""
        cls.initialize_default_questions()
        all_bank = FirestoreRepository.query_documents("questions", limit=100)
        matching = [q for q in all_bank if domain.lower() in q.get("domain", "").lower()]
        if not matching:
            matching = all_bank[:5]
        return [
            QuestionPublic(
                id=q["id"],
                domain=q.get("domain", domain),
                skill=q.get("skill", "General"),
                question_text=q["question_text"],
                question_type=q["question_type"],
                difficulty=q.get("difficulty", DifficultyLevel.INTERMEDIATE),
                options=q.get("options"),
                points=float(q.get("points", 10.0))
            )
            for q in matching
        ]

    @classmethod
    def generate_personalized_assessment(
        cls,
        confirmed_skills: List[str],
        projects: List[Dict[str, Any]],
        domain: Optional[str] = None
    ) -> List[QuestionPublic]:
        """Legacy route compatibility wrapper."""
        cls.initialize_default_questions()
        domain = domain or "Frontend Development"
        all_bank = FirestoreRepository.query_documents("questions", limit=100)
        skills_lower = {s.lower() for s in confirmed_skills}
        matching = [
            q for q in all_bank
            if q.get("skill", "").lower() in skills_lower or domain.lower() in q.get("domain", "").lower()
        ]
        if not matching:
            matching = all_bank[:5]
        return [
            QuestionPublic(
                id=q["id"],
                domain=q.get("domain", domain),
                skill=q.get("skill", "General"),
                question_text=q["question_text"],
                question_type=q["question_type"],
                difficulty=q.get("difficulty", DifficultyLevel.INTERMEDIATE),
                options=q.get("options"),
                points=float(q.get("points", 10.0))
            )
            for q in matching[:5]
        ]

    @classmethod
    def evaluate_submission(
        cls,
        user_id: str,
        submission: AssessmentSubmissionRequest,
        assessment_id: Optional[str] = None
    ) -> AssessmentResultResponse:
        """
        Submits and grades assessment. Evaluates MCQs deterministically,
        evaluates descriptive questions against rubrics using Gemini or scoring rules,
        updates profile proficiencies, and saves the final report.
        Prevents duplicate submissions and tampering.
        """
        cls.initialize_default_questions()
        target_asmt_id = assessment_id or submission.assessment_id

        stored_questions_map: Dict[str, Dict[str, Any]] = {}
        target_asmt_doc: Optional[Dict[str, Any]] = None

        if target_asmt_id:
            target_asmt_doc = FirestoreRepository.get_document("assessments", target_asmt_id)
            if not target_asmt_doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assessment '{target_asmt_id}' not found."
                )

            if target_asmt_doc.get("user_id") != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cannot submit another student's assessment."
                )

            # Prevent duplicate submissions
            if target_asmt_doc.get("status") == "completed" and target_asmt_doc.get("result"):
                logger.info(f"Assessment {target_asmt_id} was already completed; returning existing report")
                return AssessmentResultResponse(**target_asmt_doc["result"])

            for q in target_asmt_doc.get("questions", []):
                stored_questions_map[q["id"]] = q

        now_str = datetime.now(timezone.utc).isoformat()
        attempt_id = target_asmt_id or f"attempt_{uuid.uuid4().hex[:10]}"

        # Map student submitted answers
        submitted_answers_map = {item.question_id: (item.answer or "").strip() for item in submission.answers}

        # Determine complete question set to evaluate
        if stored_questions_map:
            all_questions_to_evaluate = list(stored_questions_map.values())
        else:
            all_questions_to_evaluate = [
                stored_questions_map.get(item.question_id) or FirestoreRepository.get_document("questions", item.question_id)
                for item in submission.answers
            ]
            all_questions_to_evaluate = [q for q in all_questions_to_evaluate if q]

        # Concurrently evaluate descriptive questions to eliminate serial LLM delay
        descriptive_results: Dict[str, Tuple[float, str, str]] = {}
        descriptive_questions = [
            q for q in all_questions_to_evaluate
            if q.get("question_type") != QuestionType.MCQ and submitted_answers_map.get(q["id"])
        ]

        if descriptive_questions:
            def _eval_single(q_doc_item):
                q_id = q_doc_item["id"]
                s_ans = submitted_answers_map.get(q_id, "")
                pts, fb, sug = ScoringService.evaluate_descriptive_answer(
                    question_text=q_doc_item.get("question_text", ""),
                    student_answer=s_ans,
                    rubric=q_doc_item.get("rubric", {}),
                    max_points=float(q_doc_item.get("points", 10.0))
                )
                return q_id, pts, fb, sug

            workers = min(len(descriptive_questions), 5)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for q_id, pts, fb, sug in executor.map(_eval_single, descriptive_questions):
                    descriptive_results[q_id] = (pts, fb, sug)

        question_evaluations: List[QuestionEvaluationResult] = []
        skill_point_tracker: Dict[str, Dict[str, Any]] = {}

        total_earned = 0.0
        total_available = 0.0

        for q_doc in all_questions_to_evaluate:
            q_id = q_doc["id"]
            skill = q_doc.get("skill", "General")
            raw_type = q_doc.get("question_type")
            if raw_type:
                try:
                    q_type = QuestionType(raw_type)
                except Exception:
                    q_type = QuestionType.MCQ if q_doc.get("options") else QuestionType.SHORT_ANSWER
            else:
                q_type = QuestionType.MCQ if q_doc.get("options") else QuestionType.SHORT_ANSWER
            max_pts = float(q_doc.get("points", 10.0))
            correct_ans = q_doc.get("correct_answer")
            submitted_ans = submitted_answers_map.get(q_id, "")

            if skill not in skill_point_tracker:
                skill_point_tracker[skill] = {
                    "earned": 0.0,
                    "available": 0.0,
                    "correct_count": 0,
                    "total_count": 0,
                    "answers": []
                }
            skill_point_tracker[skill]["available"] += max_pts
            skill_point_tracker[skill]["total_count"] += 1
            total_available += max_pts

            if q_type == QuestionType.MCQ:
                is_correct = False
                if submitted_ans:
                    if isinstance(correct_ans, int) and submitted_ans.isdigit():
                        is_correct = int(submitted_ans) == correct_ans
                    elif str(correct_ans).strip().lower() == submitted_ans.lower():
                        is_correct = True

                pts_awarded = max_pts if is_correct else 0.0
                total_earned += pts_awarded
                skill_point_tracker[skill]["earned"] += pts_awarded
                if is_correct:
                    skill_point_tracker[skill]["correct_count"] += 1

                fb = "Correct option chosen." if is_correct else (
                    f"Incorrect. Concept explanation: {q_doc.get('explanation', '')}" if submitted_ans else "Question was not answered."
                )
                sug = None if is_correct else f"Review core concepts of {skill}."

                question_evaluations.append(QuestionEvaluationResult(
                    question_id=q_id,
                    skill=skill,
                    question_type=QuestionType.MCQ,
                    points_awarded=pts_awarded,
                    max_points=max_pts,
                    is_correct=is_correct,
                    feedback=fb,
                    improvement_suggestion=sug
                ))
            else:
                # Short Answer / Descriptive evaluation
                if not submitted_ans:
                    pts = 0.0
                    fb = "Question was not answered."
                    sug = f"Provide a complete technical explanation for {skill}."
                    is_satisfactory = False
                else:
                    eval_tuple = descriptive_results.get(q_id)
                    if eval_tuple:
                        pts, fb, sug = eval_tuple
                    else:
                        pts, fb, sug = ScoringService.evaluate_descriptive_answer(
                            question_text=q_doc.get("question_text", ""),
                            student_answer=submitted_ans,
                            rubric=q_doc.get("rubric", {}),
                            max_points=max_pts
                        )
                    is_satisfactory = pts >= (max_pts * 0.7)

                total_earned += pts
                skill_point_tracker[skill]["earned"] += pts
                if is_satisfactory:
                    skill_point_tracker[skill]["correct_count"] += 1

                question_evaluations.append(QuestionEvaluationResult(
                    question_id=q_id,
                    skill=skill,
                    question_type=q_type,
                    points_awarded=pts,
                    max_points=max_pts,
                    is_correct=is_satisfactory,
                    feedback=fb,
                    improvement_suggestion=sug
                ))

        breakdown: List[SkillScoreBreakdown] = []
        strengths_summary: List[str] = []
        weaknesses_summary: List[str] = []

        for skill_name, tracker in skill_point_tracker.items():
            pct = ScoringService.calculate_skill_score(tracker["earned"], tracker["available"])
            tier = ScoringService.get_proficiency_tier(pct)

            if pct >= 70.0:
                perf_level = "Strong"
                strong_areas = [f"Demonstrated solid conceptual understanding of {skill_name}"]
                weak_areas = []
                evidence = f"Scored {tracker['earned']:.1f}/{tracker['available']:.1f} pts ({pct:.0f}%) on assessment questions."
                suggestion = f"Maintain fluency in {skill_name} and explore advanced design patterns."
                strengths_summary.append(f"{skill_name} ({pct:.0f}%)")
            elif pct >= 40.0:
                perf_level = "Moderate"
                strong_areas = [f"Basic foundational knowledge of {skill_name}"]
                weak_areas = ["Inconsistent depth in edge cases or architectural trade-offs"]
                evidence = f"Scored {tracker['earned']:.1f}/{tracker['available']:.1f} pts ({pct:.0f}%)."
                suggestion = f"Deepen practical hands-on exercises in {skill_name}."
            else:
                perf_level = "Needs Improvement"
                strong_areas = []
                weak_areas = ["Gaps in core fundamentals and practical problem-solving"]
                evidence = f"Scored {tracker['earned']:.1f}/{tracker['available']:.1f} pts ({pct:.0f}%)."
                suggestion = f"Prioritize foundational courses and guided tutorials for {skill_name}."
                weaknesses_summary.append(f"{skill_name} ({pct:.0f}%)")

            breakdown.append(SkillScoreBreakdown(
                skill=skill_name,
                earned_points=tracker["earned"],
                available_points=tracker["available"],
                score_percentage=pct,
                proficiency_level=tier,
                performance_level=perf_level,
                strong_areas=strong_areas,
                weak_areas=weak_areas,
                answer_evidence=evidence,
                improvement_suggestion=suggestion
            ))

        total_pct = ScoringService.calculate_skill_score(total_earned, total_available)

        # Update profile validated proficiencies
        user_doc = FirestoreRepository.get_document("users", user_id) or {}
        claimed_skills = user_doc.get("claimed_skills", [])
        assessed_skills_lower = {b.skill.lower() for b in breakdown}
        unassessed_skills = [s for s in claimed_skills if s.lower() not in assessed_skills_lower]

        cls._update_user_validated_skills(user_id, breakdown)

        domain_final = submission.domain or (target_asmt_doc.get("domain") if target_asmt_doc else "Frontend Development")

        overall_feedback = (
            f"Overall Assessment Score: {total_pct}% across {len(breakdown)} evaluated skills. "
            f"Validated proficiencies have been saved to your student profile."
        )

        recommended_next_steps = [
            "Review performance breakdown and targeted feedback for each skill.",
            "Generate your personalized learning roadmap targeting identified improvement areas.",
            "Explore matching career domains and job recommendations based on your verified proficiencies."
        ]

        result_dict = {
            "attempt_id": attempt_id,
            "user_id": user_id,
            "domain": domain_final,
            "total_score_percentage": total_pct,
            "total_earned_points": round(total_earned, 2),
            "total_available_points": round(total_available, 2),
            "submitted_at": now_str,
            "skill_breakdown": [b.model_dump() for b in breakdown],
            "unassessed_skills": unassessed_skills,
            "strengths_summary": strengths_summary,
            "weaknesses_summary": weaknesses_summary,
            "question_evaluations": [e.model_dump() for e in question_evaluations],
            "overall_feedback": overall_feedback,
            "recommended_next_steps": recommended_next_steps,
            "assessment_id": target_asmt_id,
            "status": "completed",
            "completed_at": now_str
        }

        # Update assessment document status if associated with specific assessment
        if target_asmt_id:
            FirestoreRepository.update_document("assessments", target_asmt_id, {
                "status": "completed",
                "completed_at": now_str,
                "submitted_at": now_str,
                "total_score_percentage": total_pct,
                "result": result_dict
            })
        else:
            doc_to_save = dict(result_dict)
            doc_to_save["result"] = result_dict
            FirestoreRepository.set_document("assessments", attempt_id, doc_to_save)

        return AssessmentResultResponse(**result_dict)

    @classmethod
    def get_assessment_report(cls, assessment_id: str, user_id: str) -> AssessmentResultResponse:
        """Retrieves the graded report of a completed assessment."""
        doc = FirestoreRepository.get_document("assessments", assessment_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment '{assessment_id}' not found."
            )

        if doc.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access another student's report."
            )

        result_data = doc.get("result")
        if not result_data:
            # Check if document itself is an attempt result (legacy format)
            if "total_score_percentage" in doc:
                return AssessmentResultResponse(**doc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This assessment has not been submitted or evaluated yet."
            )

        return AssessmentResultResponse(**result_data)

    @classmethod
    def _update_user_validated_skills(cls, user_id: str, breakdown: List[SkillScoreBreakdown]):
        user = FirestoreRepository.get_document("users", user_id) or {"uid": user_id}
        validated_skills = user.get("validated_skills", {})
        for b in breakdown:
            curr = validated_skills.get(b.skill, 0.0)
            validated_skills[b.skill] = max(curr, b.score_percentage)

        user["validated_skills"] = validated_skills
        user["assessments_completed"] = user.get("assessments_completed", 0) + 1
        FirestoreRepository.set_document("users", user_id, user)
