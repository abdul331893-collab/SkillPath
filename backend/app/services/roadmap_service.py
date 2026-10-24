import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.repositories.firestore_repo import FirestoreRepository
from app.schemas.roadmap import (
    RoadmapResponse,
    RoadmapPhase,
    RoadmapTopic,
    ResourceReference,
    RoadmapProgressUpdate
)
from app.services.gemini_service import gemini_service
from app.services.rag_service import rag_service
from app.services.skill_normalizer import SkillNormalizer
from app.core.logging import logger

CURATED_LEARNING_RESOURCES = {
    "javascript": [
        ResourceReference(title="MDN Web Docs - JavaScript Guide", url="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", resource_type="official_docs", description="Authoritative reference for modern JavaScript syntax, closures, and async patterns."),
        ResourceReference(title="JavaScript.info - The Modern JavaScript Tutorial", url="https://javascript.info/", resource_type="tutorial", description="In-depth guide from fundamentals to advanced event loops and prototypes.")
    ],
    "react": [
        ResourceReference(title="Official React Documentation", url="https://react.dev/", resource_type="official_docs", description="Interactive guide for React 19, hooks, state management, and component architecture."),
        ResourceReference(title="Full Stack Open - React Deep Dive", url="https://fullstackopen.com/en/", resource_type="tutorial", description="Modern single-page web application architecture with React.")
    ],
    "typescript": [
        ResourceReference(title="TypeScript Official Handbook", url="https://www.typescriptlang.org/docs/handbook/intro.html", resource_type="official_docs", description="Complete reference for static typing, generics, and utility types."),
        ResourceReference(title="Total TypeScript Tutorial", url="https://www.totaltypescript.com/tutorials/beginners-typescript", resource_type="tutorial", description="Practical TypeScript patterns and type-safe development.")
    ],
    "html & css": [
        ResourceReference(title="MDN Web Docs - HTML Developer Guide", url="https://developer.mozilla.org/en-US/docs/Learn/HTML", resource_type="official_docs", description="Semantic HTML5 elements and web accessibility standards."),
        ResourceReference(title="Web.dev - Learn CSS", url="https://web.dev/learn/css", resource_type="tutorial", description="Modern responsive layouts, Flexbox, CSS Grid, and responsive design.")
    ],
    "python": [
        ResourceReference(title="Official Python Tutorial", url="https://docs.python.org/3/tutorial/", resource_type="official_docs", description="Core language specification, data structures, and standard library modules."),
        ResourceReference(title="Real Python Tutorials", url="https://realpython.com/", resource_type="tutorial", description="Production-grade Python programming and software design patterns.")
    ],
    "fastapi": [
        ResourceReference(title="FastAPI Official Documentation", url="https://fastapi.tiangolo.com/tutorial/", resource_type="official_docs", description="Building high-performance asynchronous REST APIs with Python 3.10+."),
        ResourceReference(title="FastAPI Async Database Integration", url="https://fastapi.tiangolo.com/tutorial/sql-databases/", resource_type="official_docs", description="Asynchronous ORM setup and dependency injection with SQL.")
    ],
    "sql & databases": [
        ResourceReference(title="PostgreSQL Official Documentation", url="https://www.postgresql.org/docs/", resource_type="official_docs", description="Relational data modeling, indexing strategies, transactions, and complex queries."),
        ResourceReference(title="SQLBolt - Interactive SQL Lessons", url="https://sqlbolt.com/", resource_type="tutorial", description="Interactive exercises for relational database query mastery.")
    ],
    "docker & containers": [
        ResourceReference(title="Docker Documentation & Getting Started", url="https://docs.docker.com/get-started/", resource_type="official_docs", description="Containerization best practices, multi-stage builds, and Dockerfile optimization."),
        ResourceReference(title="Docker Compose Guide", url="https://docs.docker.com/compose/", resource_type="official_docs", description="Multi-container application orchestration for local and production setups.")
    ],
    "linux & bash": [
        ResourceReference(title="Linux Journey Tutorial", url="https://linuxjourney.com/", resource_type="tutorial", description="Command line mastery, file permissions, process management, and networking."),
        ResourceReference(title="GNU Bash Reference Manual", url="https://www.gnu.org/software/bash/manual/", resource_type="official_docs", description="Shell scripting syntax, pipe redirection, and automation patterns.")
    ],
    "ci/cd pipelines": [
        ResourceReference(title="GitHub Actions Documentation", url="https://docs.github.com/en/actions", resource_type="official_docs", description="Automated testing workflows, continuous deployment, and secrets management."),
        ResourceReference(title="Continuous Delivery Foundation", url="https://cd.foundation/", resource_type="official_docs", description="Industry guidelines for automated testing pipelines and zero-downtime deployment.")
    ],
    "machine learning (scikit-learn)": [
        ResourceReference(title="Scikit-Learn User Guide", url="https://scikit-learn.org/stable/user_guide.html", resource_type="official_docs", description="Supervised and unsupervised statistical machine learning algorithms and cross-validation."),
        ResourceReference(title="Google Machine Learning Crash Course", url="https://developers.google.com/machine-learning/crash-course", resource_type="tutorial", description="Core concepts in regression, classification, loss minimization, and regularization.")
    ],
    "pandas & data manipulation": [
        ResourceReference(title="Pandas Official User Guide", url="https://pandas.pydata.org/docs/user_guide/index.html", resource_type="official_docs", description="High-performance data frames, grouping, aggregation, and time series analysis."),
        ResourceReference(title="10 Minutes to Pandas", url="https://pandas.pydata.org/docs/user_guide/10min.html", resource_type="tutorial", description="Quick overview of essential data manipulation techniques.")
    ],
    "restful api design": [
        ResourceReference(title="Microsoft REST API Guidelines", url="https://github.com/microsoft/api-guidelines", resource_type="official_docs", description="Enterprise architectural guidelines for RESTful API design, versioning, and error handling."),
        ResourceReference(title="RESTful API Tutorial", url="https://restfulapi.net/", resource_type="tutorial", description="HTTP verbs, status codes, resource naming, and idempotency conventions.")
    ],
    "software testing principles": [
        ResourceReference(title="Pytest Official Documentation", url="https://docs.pytest.org/en/stable/", resource_type="official_docs", description="Automated unit testing, fixtures, parameterization, and mocking."),
        ResourceReference(title="Jest Documentation", url="https://jestjs.io/docs/getting-started", resource_type="official_docs", description="Frontend unit and integration testing with snapshot assertions.")
    ]
}

class RoadmapService:
    """Service generating structured, evidence-backed learning roadmaps tailored to measured assessment gaps."""

    @classmethod
    def get_approved_resources_for_skill(cls, skill_name: str) -> List[ResourceReference]:
        """Returns verified, working learning resource URLs for a given skill."""
        canonical = SkillNormalizer.normalize(skill_name).lower()
        clean = SkillNormalizer.clean_token(skill_name)

        for key, res in CURATED_LEARNING_RESOURCES.items():
            if key == canonical or key == clean or key in canonical or canonical in key:
                return res

        # Check keyword containment
        if "react" in clean:
            return CURATED_LEARNING_RESOURCES["react"]
        if "script" in clean or "js" in clean:
            return CURATED_LEARNING_RESOURCES["javascript"]
        if "python" in clean:
            return CURATED_LEARNING_RESOURCES["python"]
        if "sql" in clean or "data" in clean:
            return CURATED_LEARNING_RESOURCES["sql & databases"]
        if "docker" in clean or "container" in clean:
            return CURATED_LEARNING_RESOURCES["docker & containers"]
        if "linux" in clean or "bash" in clean:
            return CURATED_LEARNING_RESOURCES["linux & bash"]
        if "learn" in clean or "model" in clean:
            return CURATED_LEARNING_RESOURCES["machine learning (scikit-learn)"]

        # Default to authoritative MDN reference with a working URL
        return [
            ResourceReference(
                title=f"{skill_name} Developer Reference on MDN",
                url="https://developer.mozilla.org/en-US/",
                resource_type="official_docs",
                description=f"Standard reference documentation and architecture patterns for {skill_name}."
            )
        ]

    @classmethod
    def generate_roadmap(
        cls,
        user_id: str,
        target_career_domain: str,
        user_skills: Optional[Dict[str, float]] = None,
        weekly_hours: int = 10,
        replace_existing: bool = False
    ) -> RoadmapResponse:
        """
        Creates a custom multi-phase learning roadmap prioritizing measured skill gaps.
        Enforces completion of technical assessment before evidence-based generation.
        Prevents duplicate roadmap generation unless explicitly requested.
        """
        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Fetch Career Domain Details
        domain = FirestoreRepository.get_document("career_domains", target_career_domain)
        if not domain:
            from app.services.career_service import CareerService
            CareerService.initialize_default_domains()
            domain = FirestoreRepository.get_document("career_domains", target_career_domain)

        career_title = domain.get("title", target_career_domain) if domain else target_career_domain
        required_skills = domain.get("required_skills", []) if domain else []

        # 2. Check for completed assessments (MANDATORY REQUIREMENT)
        completed_assessments = FirestoreRepository.query_documents(
            "assessments",
            filters=[("user_id", "==", user_id), ("status", "==", "completed")],
            limit=10
        )

        if not completed_assessments:
            logger.info(f"User {user_id} has not completed an assessment yet. Blocking evidence-based roadmap.")
            return RoadmapResponse(
                id=f"roadmap_unassessed_{user_id}",
                user_id=user_id,
                target_career_domain=target_career_domain,
                target_career_title=career_title,
                baseline_score=0.0,
                requires_assessment=True,
                message="Please complete your skill assessment before receiving an evidence-based roadmap.",
                next_action="Complete the Skill Assessment in Step 3 to calibrate your personalized curriculum based on measured weaknesses.",
                phases=[],
                total_estimated_weeks=0,
                completion_percentage=0.0,
                created_at=now_str,
                updated_at=now_str
            )

        # 3. Prevent duplicate roadmap items unless explicit replace requested
        if not replace_existing:
            existing_roadmaps = FirestoreRepository.query_documents(
                "roadmaps",
                filters=[("user_id", "==", user_id), ("target_career_domain", "==", target_career_domain)],
                limit=1
            )
            if existing_roadmaps and existing_roadmaps[0].get("phases"):
                logger.info(f"Returning existing roadmap for user {user_id} and domain {target_career_domain}")
                return RoadmapResponse(**existing_roadmaps[0])

        # 4. Extract student assessment evidence, scores, and weaknesses
        latest_assessment = completed_assessments[-1]
        res_data = latest_assessment.get("result") or latest_assessment
        assessment_id = latest_assessment.get("id") or latest_assessment.get("assessment_id")
        skill_breakdown = res_data.get("skill_breakdown", [])
        total_score = float(res_data.get("total_score_percentage", 0.0))

        # Retrieve confirmed projects and confirmed skills from profile/resume
        user_doc = FirestoreRepository.get_document("users", user_id) or {}
        confirmed_skills = user_doc.get("claimed_skills", []) or user_doc.get("technical_skills", [])
        confirmed_projects = user_doc.get("projects", [])

        # Map assessed skills with their measured scores and evidence
        assessed_map: Dict[str, Dict[str, Any]] = {}
        for item in skill_breakdown:
            s_name = item.get("skill", "")
            assessed_map[s_name.lower().strip()] = {
                "skill": s_name,
                "score": float(item.get("score_percentage", 0.0)),
                "level": item.get("performance_level") or item.get("proficiency_level") or "Moderate",
                "evidence": item.get("evidence", "Assessed performance in technical evaluation."),
                "improvement_suggestion": item.get("improvement_suggestion", "Strengthen practical implementation.")
            }

        # 5. Identify specific skill gaps by comparing assessment performance with domain requirements
        skill_gaps: List[Dict[str, Any]] = []
        for req in required_skills:
            req_skill = req.get("skill")
            req_level = float(req.get("required_level", 75.0))
            
            # Match against assessed skills using SkillNormalizer
            matched_key = None
            for key in assessed_map.keys():
                if SkillNormalizer.are_skills_equivalent(req_skill, key):
                    matched_key = key
                    break

            if matched_key:
                info = assessed_map[matched_key]
                current_score = info["score"]
                if current_score < req_level:
                    skill_gaps.append({
                        "skill": req_skill,
                        "current_score": current_score,
                        "required_level": req_level,
                        "evidence": info["evidence"],
                        "suggestion": info["improvement_suggestion"],
                        "is_missing": False
                    })
            else:
                # Skill required but student has not validated it yet
                skill_gaps.append({
                    "skill": req_skill,
                    "current_score": 0.0,
                    "required_level": req_level,
                    "evidence": f"No assessment questions answered yet for {req_skill}.",
                    "suggestion": f"Master fundamental principles of {req_skill} to meet domain requirements.",
                    "is_missing": True
                })

        # Also include any assessed skill where student scored below threshold (< 70%)
        for a_skill, info in assessed_map.items():
            if not any(SkillNormalizer.are_skills_equivalent(a_skill, g["skill"]) for g in skill_gaps):
                if info["score"] < 70.0:
                    skill_gaps.append({
                        "skill": a_skill,
                        "current_score": info["score"],
                        "required_level": 75.0,
                        "evidence": info["evidence"],
                        "suggestion": info["improvement_suggestion"],
                        "is_missing": False
                    })

        # Sort gaps: largest score deficit first
        skill_gaps.sort(key=lambda x: (x["required_level"] - x["current_score"]), reverse=True)
        if not skill_gaps:
            # If all required skills met the threshold, focus on advanced mastery
            skill_gaps = [
                {
                    "skill": req.get("skill"),
                    "current_score": 75.0,
                    "required_level": 90.0,
                    "evidence": "Achieved passing score; advancing to architectural scaling.",
                    "suggestion": "Focus on high-availability and concurrency patterns.",
                    "is_missing": False
                }
                for req in required_skills[:3]
            ] or [{
                "skill": "Core Architecture",
                "current_score": 60.0,
                "required_level": 85.0,
                "evidence": "Foundational competency measured.",
                "suggestion": "Build scalable portfolio projects.",
                "is_missing": False
            }]

        priority_gap_names = [g["skill"] for g in skill_gaps]

        # 6. Retrieve relevant learning materials via RAG Qdrant
        rag_context_snippets = []
        try:
            for gap in skill_gaps[:3]:
                snippets = rag_service.retrieve_snippets(
                    query=f"Essential principles, design patterns, and study topics for {gap['skill']}",
                    skill_filter=gap["skill"],
                    top_k=1
                )
                if snippets:
                    rag_context_snippets.append(f"{gap['skill']}: {snippets[0][:200]}")
        except Exception as e:
            logger.warning(f"RAG snippet retrieval note: {e}")

        # 7. Generate curriculum content using Gemini LLM with structured evidence
        phases = cls._generate_evidence_based_phases(
            career_title=career_title,
            skill_gaps=skill_gaps,
            projects=confirmed_projects,
            weekly_hours=weekly_hours,
            rag_snippets=rag_context_snippets
        )

        roadmap_id = f"roadmap_{uuid.uuid4()}"
        roadmap_dict = {
            "id": roadmap_id,
            "user_id": user_id,
            "target_career_domain": target_career_domain,
            "target_career_title": career_title,
            "baseline_score": total_score,
            "priority_skill_gaps": priority_gap_names,
            "phases": [p.model_dump() for p in phases],
            "total_estimated_weeks": sum(p.estimated_weeks for p in phases),
            "completion_percentage": 0.0,
            "requires_assessment": False,
            "message": f"Evidence-based roadmap generated from your {total_score:.0f}% assessment performance.",
            "next_action": f"Begin Phase 1: {phases[0].title if phases else 'Foundation'}",
            "assessment_id": assessment_id,
            "created_at": now_str,
            "updated_at": now_str
        }

        FirestoreRepository.set_document("roadmaps", roadmap_id, roadmap_dict)
        return RoadmapResponse(**roadmap_dict)

    @classmethod
    def _generate_evidence_based_phases(
        cls,
        career_title: str,
        skill_gaps: List[Dict[str, Any]],
        projects: List[Dict[str, Any]],
        weekly_hours: int,
        rag_snippets: List[str]
    ) -> List[RoadmapPhase]:
        """
        Uses Gemini to generate learning content from structured student evidence.
        Falls back to deterministic evidence-backed phase construction if Gemini fails or is unavailable.
        """
        # Attempt Gemini structured generation
        if gemini_service.is_available():
            try:
                gaps_summary = "\n".join([
                    f"- Skill: {g['skill']}, Measured Score: {g['current_score']}%, Target: {g['required_level']}%, "
                    f"Evidence: \"{g['evidence']}\", Suggestion: \"{g['suggestion']}\""
                    for g in skill_gaps[:4]
                ])

                projects_summary = ", ".join([p.get("title", "Project") for p in projects[:2]]) if projects else "None"

                prompt = f"""
You are the Lead Technical Curriculum Architect for SkillPath AI.
Generate a strictly personalized 3-phase learning roadmap for a student targeting: {career_title}.
Student Measured Evidence from Assessment:
{gaps_summary}

Student Portfolio Projects: {projects_summary}
Knowledge Base Context: {"; ".join(rag_snippets) if rag_snippets else "Standard modern industry patterns."}

Instructions:
1. Base the topics directly on the student's measured weaknesses and assessment evidence.
2. For each topic, explain EXACTLY why it needs improvement citing the evidence.
3. Include 2-3 topics per phase.
4. Output must be a valid JSON array of 3 phase objects conforming to this schema:
[
  {{
    "phase_number": 1,
    "title": "Phase Title",
    "description": "Phase Description",
    "estimated_weeks": 3,
    "mini_project": {{"title": "Project Title", "description": "Hands-on implementation task"}},
    "topics": [
      {{
        "id": "p1_t1",
        "title": "Topic Name",
        "skill": "Skill Name",
        "why_improvement_needed": "Citing assessment evidence and score",
        "current_level": "45%",
        "target_level": "75%",
        "objective": "Clear measurable objective",
        "learning_objectives": ["Objective 1", "Objective 2"],
        "ordered_steps": ["Step 1: Read documentation", "Step 2: Complete tutorial", "Step 3: Implement pattern"],
        "exercise": "Specific coding exercise",
        "estimated_duration": "Estimated: 8 hours",
        "estimated_hours": 8,
        "measurable_criterion": "Benchmark to verify mastery",
        "progress_status": "Not Started"
      }}
    ]
  }}
]
"""
                parsed = gemini_service.generate_json(prompt, temperature=0.2, timeout=45.0)
                if isinstance(parsed, list) and len(parsed) >= 2:
                    validated_phases = []
                    for p_data in parsed:
                        topics = []
                        for t_data in p_data.get("topics", []):
                            skill_name = t_data.get("skill") or skill_gaps[0]["skill"]
                            # Retrieve approved authentic resources
                            approved_res = cls.get_approved_resources_for_skill(skill_name)
                            topics.append(RoadmapTopic(
                                id=t_data.get("id", f"t_{uuid.uuid4().hex[:6]}"),
                                title=t_data.get("title", f"Remediate {skill_name}"),
                                skill=skill_name,
                                objective=t_data.get("objective", f"Master core competencies in {skill_name}."),
                                why_improvement_needed=t_data.get("why_improvement_needed", "Assessment indicated gap in this technical competency."),
                                current_level=str(t_data.get("current_level", "50%")),
                                target_level=str(t_data.get("target_level", "75%")),
                                learning_objectives=t_data.get("learning_objectives") or [t_data.get("objective", "Master skill")],
                                ordered_steps=t_data.get("ordered_steps") or ["Review official documentation", "Implement test pattern", "Verify with code review"],
                                resources=approved_res,
                                exercise=t_data.get("exercise", f"Build a practical module utilizing {skill_name}."),
                                estimated_duration=str(t_data.get("estimated_duration", "Estimated: 8 hours")),
                                estimated_hours=int(t_data.get("estimated_hours", 8)),
                                measurable_criterion=t_data.get("measurable_criterion", "Achieve >=75% in validation exercise."),
                                progress_status=t_data.get("progress_status", "Not Started"),
                                is_completed=False
                            ))

                        validated_phases.append(RoadmapPhase(
                            phase_number=int(p_data.get("phase_number", len(validated_phases) + 1)),
                            title=p_data.get("title", f"Phase {len(validated_phases) + 1}"),
                            description=p_data.get("description", "Structured gap remediation."),
                            estimated_weeks=int(p_data.get("estimated_weeks", 3)),
                            topics=topics,
                            mini_project=p_data.get("mini_project", {
                                "title": f"{career_title} Milestone Implementation",
                                "description": "Construct an end-to-end service module incorporating learned principles."
                            })
                        ))

                    if validated_phases:
                        return validated_phases
            except Exception as e:
                logger.warning(f"Gemini roadmap generation fallback to deterministic engine: {e}")

        # Deterministic evidence-backed fallback
        return cls._build_deterministic_evidence_phases(career_title, skill_gaps, projects, weekly_hours)

    @classmethod
    def _build_deterministic_evidence_phases(
        cls,
        career_title: str,
        skill_gaps: List[Dict[str, Any]],
        projects: List[Dict[str, Any]],
        weekly_hours: int
    ) -> List[RoadmapPhase]:
        """Constructs 3 phases strictly citing measured assessment evidence and approved resources."""
        phases = []

        # Phase 1: Immediate Gap Remediation
        p1_topics = []
        for i, gap in enumerate(skill_gaps[:2]):
            s_name = gap["skill"]
            curr_score = gap["current_score"]
            req_lvl = gap["required_level"]
            evidence = gap["evidence"]
            suggestion = gap["suggestion"]
            approved_res = cls.get_approved_resources_for_skill(s_name)

            p1_topics.append(RoadmapTopic(
                id=f"p1_t{i+1}",
                title=f"{s_name} Fundamentals & Pattern Mastery",
                skill=s_name,
                objective=f"Close measured baseline gap in {s_name} to achieve target competency of {req_lvl:.0f}%.",
                why_improvement_needed=f"Assessment evidence: {evidence}. Measured current score is {curr_score:.0f}% vs required {req_lvl:.0f}%. {suggestion}",
                current_level=f"{curr_score:.0f}%",
                target_level=f"{req_lvl:.0f}%",
                learning_objectives=[
                    f"Understand core syntax, lifecycles, and architecture paradigms in {s_name}",
                    f"Implement test-driven error handling and asynchronous patterns in {s_name}",
                    "Optimize algorithmic efficiency and prevent common memory/rendering bottlenecks"
                ],
                ordered_steps=[
                    f"Step 1: Read the official documentation guidelines for {s_name}",
                    f"Step 2: Study real-world architectural code examples and common failure modes",
                    f"Step 3: Complete interactive coding exercises focused on {s_name} edge cases"
                ],
                resources=approved_res,
                exercise=f"Develop 3 standalone algorithmic exercises and component patterns utilizing {s_name}.",
                estimated_duration="Estimated: 6-8 hours",
                estimated_hours=max(6, 40 // max(weekly_hours, 5)),
                measurable_criterion=f"Pass all unit tests for the {s_name} component and explain architectural decisions.",
                progress_status="Not Started",
                is_completed=False
            ))

        phases.append(RoadmapPhase(
            phase_number=1,
            title="Foundation & Priority Gap Remediation",
            description=f"Address immediate assessment weaknesses in {', '.join([g['skill'] for g in skill_gaps[:2]])}.",
            estimated_weeks=3,
            topics=p1_topics,
            mini_project={
                "title": f"{career_title} Diagnostic Prototype",
                "description": f"Build a focused proof-of-concept integrating {', '.join([g['skill'] for g in skill_gaps[:2]])} with automated testing."
            }
        ))

        # Phase 2: Production Patterns & Integration
        p2_topics = []
        secondary_gaps = skill_gaps[2:4] if len(skill_gaps) >= 4 else skill_gaps[:2]
        for i, gap in enumerate(secondary_gaps):
            s_name = gap["skill"]
            curr_score = gap["current_score"]
            req_lvl = gap["required_level"]
            evidence = gap["evidence"]
            approved_res = cls.get_approved_resources_for_skill(s_name)

            p2_topics.append(RoadmapTopic(
                id=f"p2_t{i+1}",
                title=f"Advanced {s_name} Production Architecture",
                skill=s_name,
                objective=f"Bridge isolated {s_name} knowledge into scalable production workflows.",
                why_improvement_needed=f"Assessment highlighted need for advanced execution: {evidence}",
                current_level=f"{curr_score:.0f}%",
                target_level=f"{req_lvl:.0f}%",
                learning_objectives=[
                    f"Apply production-grade security, logging, and concurrency paradigms in {s_name}",
                    "Integrate API contracts with automated schema validation and database migrations"
                ],
                ordered_steps=[
                    f"Step 1: Review production architecture best practices for {s_name}",
                    "Step 2: Build a containerized microservice connecting client, API, and persistence layers",
                    "Step 3: Write comprehensive end-to-end integration tests"
                ],
                resources=approved_res,
                exercise=f"Write comprehensive automated tests and error boundaries for a service module in {s_name}.",
                estimated_duration="Estimated: 8-10 hours",
                estimated_hours=8,
                measurable_criterion="Achieve zero unhandled exceptions under concurrency benchmark testing.",
                progress_status="Not Started",
                is_completed=False
            ))

        phases.append(RoadmapPhase(
            phase_number=2,
            title="Production Architecture & System Integration",
            description="Bridge isolated skills into scalable, secure, and resilient application components.",
            estimated_weeks=4,
            topics=p2_topics,
            mini_project={
                "title": f"Production-Ready {career_title} Service",
                "description": "Construct a full-lifecycle module with containerization, API contracts, and persistent storage."
            }
        ))

        # Phase 3: Portfolio Mastery & Career Readiness
        p3_topics = [
            RoadmapTopic(
                id="p3_t1",
                title="Performance Optimization & Profiling",
                skill=skill_gaps[0]["skill"] if skill_gaps else "System Engineering",
                objective="Analyze latency bottlenecks, optimize caching, and reduce compute overhead.",
                why_improvement_needed="Essential requirement for production readiness and senior engineering interviews.",
                current_level="60%",
                target_level="85%",
                learning_objectives=[
                    "Profile runtime execution and database query latency",
                    "Implement multi-layer caching with Redis or memory store"
                ],
                ordered_steps=[
                    "Step 1: Benchmark baseline performance with load testing tools",
                    "Step 2: Identify top 3 bottlenecks and implement indexes/caching",
                    "Step 3: Verify benchmark improvement"
                ],
                resources=[ResourceReference(title="Web & API Performance Optimization Guide", url="https://web.dev/explore/fast", resource_type="official_docs")],
                exercise="Profile an application, benchmark before/after metrics, and reduce execution latency by 30%.",
                estimated_duration="Estimated: 10 hours",
                estimated_hours=10,
                measurable_criterion="Documented before/after benchmark results showing >=30% latency reduction.",
                progress_status="Not Started",
                is_completed=False
            ),
            RoadmapTopic(
                id="p3_t2",
                title="CI/CD & Cloud Deployment Pipeline Automation",
                skill="CI/CD Pipelines",
                objective="Deploy cloud-hosted solution with automated testing and continuous integration.",
                why_improvement_needed="Demonstrates practical devops capability required for modern engineering roles.",
                current_level="50%",
                target_level="80%",
                learning_objectives=[
                    "Write declarative GitHub Actions workflows",
                    "Automate linting, unit testing, and container deployment"
                ],
                ordered_steps=[
                    "Step 1: Configure continuous integration workflow file in .github/workflows",
                    "Step 2: Integrate secrets and environment variables safely",
                    "Step 3: Automate build verification and deployment triggers"
                ],
                resources=[ResourceReference(title="GitHub Actions Guide", url="https://docs.github.com/en/actions", resource_type="official_docs")],
                exercise="Configure automated test runs and continuous deployment to a cloud platform.",
                estimated_duration="Estimated: 8 hours",
                estimated_hours=8,
                measurable_criterion="Successfully trigger automated green CI build and deployment on git push.",
                progress_status="Not Started",
                is_completed=False
            )
        ]

        phases.append(RoadmapPhase(
            phase_number=3,
            title="Portfolio Mastery & Career Readiness",
            description="Finalize capstone portfolio project demonstrating complete professional competency.",
            estimated_weeks=3,
            topics=p3_topics,
            mini_project={
                "title": f"Capstone Portfolio Project for {career_title}",
                "description": "Deploy a complete full-featured project with documentation, live URL, and GitHub repository."
            }
        ))

        return phases

    @classmethod
    def update_progress(
        cls,
        roadmap_id: str,
        topic_id: str,
        completed: Optional[bool] = None,
        progress_status: Optional[str] = None
    ) -> Optional[RoadmapResponse]:
        """
        Updates the progress status of a specific roadmap topic.
        Persists update to Firestore and recalculates overall completion percentage.
        """
        doc = FirestoreRepository.get_document("roadmaps", roadmap_id)
        if not doc:
            return None

        total_topics = 0
        completed_topics = 0
        phases = doc.get("phases", [])

        # Determine target status
        target_status = progress_status
        if target_status is None and completed is not None:
            target_status = "Completed" if completed else "Not Started"

        for phase in phases:
            for topic in phase.get("topics", []):
                total_topics += 1
                if topic.get("id") == topic_id:
                    if target_status:
                        topic["progress_status"] = target_status
                        topic["is_completed"] = (target_status == "Completed")
                    elif completed is not None:
                        topic["is_completed"] = completed
                        topic["progress_status"] = "Completed" if completed else "Not Started"

                if topic.get("is_completed") or topic.get("progress_status") == "Completed":
                    completed_topics += 1

        pct = round((completed_topics / total_topics) * 100.0, 1) if total_topics > 0 else 0.0
        doc["completion_percentage"] = pct
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()

        FirestoreRepository.set_document("roadmaps", roadmap_id, doc)
        return RoadmapResponse(**doc)
