import pytest
from unittest.mock import patch
from app.services.gemini_service import gemini_service

from app.services.embedding_service import embedding_service

@pytest.fixture(autouse=True)
def mock_external_services_for_legacy_tests(request):
    """
    Mocks Gemini and external services for automated tests unless explicitly testing real integration.
    Allows automated tests to run fast, reliably, and deterministically without burning API quotas.
    """
    if "test_assessment_generation" in request.node.nodeid:
        yield
        return

    def mock_generate_json(prompt, *args, **kwargs):
        if "learning roadmap" in prompt.lower() or "curriculum architect" in prompt.lower() or "3-phase" in prompt.lower():
            return [
                {
                    "phase_number": 1,
                    "title": "Foundation & Gap Remediation",
                    "description": "Remediate critical assessment gaps.",
                    "estimated_weeks": 3,
                    "topics": [
                        {
                            "id": "t_docker",
                            "title": "Docker Containerization Essentials",
                            "skill": "Docker",
                            "objective": "Build and optimize multi-stage container images.",
                            "why_improvement_needed": "Assessment demonstrated weakness in containerization and layer caching.",
                            "current_level": "42%",
                            "target_level": "75%",
                            "learning_objectives": ["Write multi-stage Dockerfiles", "Configure container volumes"],
                            "ordered_steps": ["Step 1: Read Docker documentation", "Step 2: Build sample container", "Step 3: Test integration"],
                            "exercise": "Dockerize a Python REST service with PostgreSQL.",
                            "estimated_duration": "Estimated: 8 hours",
                            "estimated_hours": 8,
                            "measurable_criterion": "Pass clean container build and container health check.",
                            "progress_status": "Not Started"
                        },
                        {
                            "id": "t_sql",
                            "title": "SQL Database Indexing & Query Tuning",
                            "skill": "SQL & Databases",
                            "objective": "Design normalized schemas and query execution plans.",
                            "why_improvement_needed": "Assessment score was 48% with measured weakness in indexing.",
                            "current_level": "48%",
                            "target_level": "80%",
                            "learning_objectives": ["Write complex JOIN queries", "Analyze EXPLAIN ANALYZE"],
                            "ordered_steps": ["Step 1: Study query plans", "Step 2: Add compound indexes", "Step 3: Benchmark"],
                            "exercise": "Optimize slow queries to achieve 50% latency reduction.",
                            "estimated_duration": "Estimated: 8 hours",
                            "estimated_hours": 8,
                            "measurable_criterion": "Demonstrated benchmark improvement.",
                            "progress_status": "Not Started"
                        }
                    ],
                    "mini_project": {
                        "title": "Containerized Service Diagnostic",
                        "description": "Deploy a containerized API with database persistence."
                    }
                },
                {
                    "phase_number": 2,
                    "title": "Production Architecture & Scaling",
                    "description": "Scale and secure production components.",
                    "estimated_weeks": 3,
                    "topics": [
                        {
                            "id": "t_arch",
                            "title": "Microservice Architecture & Event Streams",
                            "skill": "RESTful API Design",
                            "objective": "Implement decoupled microservice communication.",
                            "why_improvement_needed": "Required competency for senior backend development.",
                            "current_level": "55%",
                            "target_level": "85%",
                            "learning_objectives": ["Design idempotent endpoints", "Handle distributed failures"],
                            "ordered_steps": ["Step 1: Design contracts", "Step 2: Implement circuit breaker", "Step 3: Verify"],
                            "exercise": "Build resilient API gateway with rate limiting.",
                            "estimated_duration": "Estimated: 10 hours",
                            "estimated_hours": 10,
                            "measurable_criterion": "Pass fault-tolerance benchmark.",
                            "progress_status": "Not Started"
                        }
                    ],
                    "mini_project": {
                        "title": "Production Microservice Capstone",
                        "description": "Construct full-featured API gateway."
                    }
                },
                {
                    "phase_number": 3,
                    "title": "Enterprise Reliability & Observability",
                    "description": "Deploy and monitor robust backend architectures.",
                    "estimated_weeks": 4,
                    "topics": [
                        {
                            "id": "t_fastapi",
                            "title": "Asynchronous FastAPI Services & Resiliency",
                            "skill": "FastAPI",
                            "objective": "Deploy high-throughput asynchronous services with automated health diagnostics.",
                            "why_improvement_needed": "Required framework proficiency for high-load backend infrastructure.",
                            "current_level": "60%",
                            "target_level": "90%",
                            "learning_objectives": ["Implement asynchronous database pools", "Configure structured distributed logging"],
                            "ordered_steps": ["Step 1: Benchmark async handlers", "Step 2: Configure circuit breaker", "Step 3: Deploy"],
                            "exercise": "Build high-throughput service with Redis caching and PostgreSQL persistence.",
                            "estimated_duration": "Estimated: 12 hours",
                            "estimated_hours": 12,
                            "measurable_criterion": "Pass automated concurrency and fault tolerance benchmarks.",
                            "progress_status": "Not Started"
                        }
                    ],
                    "mini_project": {
                        "title": "Enterprise Capstone Infrastructure",
                        "description": "Construct end-to-end resilient microservice with automated verification."
                    }
                }
            ]
        elif "technical assessment questions" in prompt.lower() or "lead technical examiner" in prompt.lower() or "question_type" in prompt.lower():
            # Return synthetic batch of 20 questions
            batch = []
            for i in range(1, 21):
                batch.append({
                    "skill": "React" if i % 2 == 0 else "TypeScript",
                    "question_text": f"What is the architectural purpose of component pattern #{i}?",
                    "question_type": "mcq",
                    "difficulty": "intermediate",
                    "options": [
                        f"Option A #{i}: isolates rendering state",
                        f"Option B #{i}: binds global event listener",
                        f"Option C #{i}: performs direct DOM mutation",
                        f"Option D #{i}: caches network response"
                    ],
                    "correct_answer": f"Option A #{i}: isolates rendering state",
                    "rubric": None,
                    "explanation": f"Option A #{i} isolates rendering state cleanly.",
                    "points": 10.0
                })
            return batch
        elif "student's answer" in prompt.lower() or "student answer" in prompt.lower() or "points_awarded" in prompt.lower() or "evaluator" in prompt.lower():
            return {
                "points_awarded": 18.0,
                "feedback": "Strong architectural reasoning and clear explanation.",
                "improvement_suggestion": "Continue practicing edge cases."
            }
        elif "resume" in prompt.lower():
            return {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "555-0100",
                "claimed_skills": ["Python", "React", "FastAPI", "SQL"],
                "education": [{"degree": "B.Tech Computer Science", "institution": "Stanford University", "year": "2024"}],
                "projects": [{"title": "API Backend", "description": "High throughput service", "technologies": ["Python", "FastAPI"]}],
                "experience": [],
                "certifications": [],
                "summary": "Full stack engineer with Python and React."
            }
        elif "question" in prompt.lower() or "assessment" in prompt.lower():
            batch = []
            for i in range(1, 21):
                batch.append({
                    "skill": "React" if i % 2 == 0 else "TypeScript",
                    "question_text": f"What is the architectural purpose of component pattern #{i}?",
                    "question_type": "mcq",
                    "difficulty": "intermediate",
                    "options": [
                        f"Option A #{i}: isolates rendering state",
                        f"Option B #{i}: binds global event listener",
                        f"Option C #{i}: performs direct DOM mutation",
                        f"Option D #{i}: caches network response"
                    ],
                    "correct_answer": f"Option A #{i}: isolates rendering state",
                    "rubric": None,
                    "explanation": f"Option A #{i} isolates rendering state cleanly.",
                    "points": 10.0
                })
            return batch
        return {"result": "success"}

    def mock_generate_text(prompt, *args, **kwargs):
        return "Validated conceptual and practical alignment with technical requirements."

    with patch.object(gemini_service, "is_available", return_value=True), \
         patch.object(gemini_service, "generate_json", side_effect=mock_generate_json), \
         patch.object(gemini_service, "generate_text", side_effect=mock_generate_text), \
         patch.object(embedding_service, "embed_text", side_effect=embedding_service._fallback_embedding):
        yield
