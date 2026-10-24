from typing import List, Dict, Any, Optional
from app.repositories.firestore_repo import FirestoreRepository
from app.schemas.career import (
    CareerRecommendationResponse,
    SkillGapItem,
    SuggestedProjectItem
)
from app.schemas.job import JobListingResponse
from app.services.scoring_service import ScoringService
from app.services.gemini_service import gemini_service
from app.services.rag_service import rag_service
from app.services.skill_normalizer import SkillNormalizer
from app.core.logging import logger

DEFAULT_CAREER_DOMAINS = [
    {
        "id": "frontend-dev",
        "title": "Frontend Development",
        "category": "Software Engineering",
        "description": "Building interactive, accessible, and high-performance user interfaces for modern web applications.",
        "min_education_level": "Bachelor's",
        "required_skills": [
            {"skill": "JavaScript", "weight": 1.5, "required_level": 75.0},
            {"skill": "TypeScript", "weight": 1.2, "required_level": 70.0},
            {"skill": "React", "weight": 1.5, "required_level": 75.0},
            {"skill": "HTML & CSS", "weight": 1.0, "required_level": 80.0},
        ],
        "preferred_skills": ["Next.js", "Tailwind CSS", "Testing (Jest/Cypress)", "REST APIs"],
        "recommended_certifications": ["Meta Front-End Developer Professional Certificate"]
    },
    {
        "id": "backend-dev",
        "title": "Backend Development",
        "category": "Software Engineering",
        "description": "Designing and implementing robust APIs, database architectures, microservices, and server-side business logic.",
        "min_education_level": "Bachelor's",
        "required_skills": [
            {"skill": "Python", "weight": 1.5, "required_level": 75.0},
            {"skill": "FastAPI", "weight": 1.2, "required_level": 70.0},
            {"skill": "SQL & Databases", "weight": 1.5, "required_level": 75.0},
            {"skill": "RESTful API Design", "weight": 1.2, "required_level": 70.0},
        ],
        "preferred_skills": ["Docker", "PostgreSQL", "Redis", "Authentication & Security", "Git"],
        "recommended_certifications": ["AWS Certified Developer Associate"]
    },
    {
        "id": "fullstack-dev",
        "title": "Full-Stack Development",
        "category": "Software Engineering",
        "description": "End-to-end web engineering encompassing frontend client experiences, server APIs, and database persistence layers.",
        "min_education_level": "Bachelor's",
        "required_skills": [
            {"skill": "JavaScript", "weight": 1.2, "required_level": 70.0},
            {"skill": "React", "weight": 1.3, "required_level": 70.0},
            {"skill": "Python", "weight": 1.3, "required_level": 70.0},
            {"skill": "SQL & Databases", "weight": 1.2, "required_level": 70.0},
        ],
        "preferred_skills": ["TypeScript", "FastAPI", "Docker", "Next.js", "CI/CD"],
        "recommended_certifications": ["Full Stack Open Certificate"]
    },
    {
        "id": "data-science",
        "title": "Data Science & Machine Learning",
        "category": "Artificial Intelligence",
        "description": "Leveraging statistical modeling, predictive algorithms, and deep learning architectures to extract intelligence from complex datasets.",
        "min_education_level": "Bachelor's",
        "required_skills": [
            {"skill": "Python", "weight": 1.5, "required_level": 80.0},
            {"skill": "Pandas & Data Manipulation", "weight": 1.4, "required_level": 75.0},
            {"skill": "Machine Learning (Scikit-Learn)", "weight": 1.5, "required_level": 75.0},
            {"skill": "Statistics & Mathematics", "weight": 1.2, "required_level": 70.0},
        ],
        "preferred_skills": ["TensorFlow / PyTorch", "Deep Learning", "SQL", "Data Visualization", "Jupyter"],
        "recommended_certifications": ["IBM Data Science Professional Certificate"]
    },
    {
        "id": "cloud-devops",
        "title": "Cloud and DevOps Engineering",
        "category": "Infrastructure",
        "description": "Automating continuous integration, deployment pipelines, container orchestration, and multi-cloud infrastructure.",
        "min_education_level": "Bachelor's",
        "required_skills": [
            {"skill": "Linux & Bash", "weight": 1.3, "required_level": 75.0},
            {"skill": "Docker & Containers", "weight": 1.5, "required_level": 80.0},
            {"skill": "CI/CD Pipelines", "weight": 1.4, "required_level": 75.0},
            {"skill": "Cloud Fundamentals (AWS/GCP)", "weight": 1.5, "required_level": 75.0},
        ],
        "preferred_skills": ["Kubernetes", "Terraform", "Monitoring & Logging", "Python/Go"],
        "recommended_certifications": ["AWS Solutions Architect Associate"]
    },
    {
        "id": "qa-testing",
        "title": "Software Testing and QA",
        "category": "Quality Engineering",
        "description": "Ensuring application quality, test automation coverage, performance benchmarking, and regression prevention.",
        "min_education_level": "Bachelor's",
        "required_skills": [
            {"skill": "Test Automation", "weight": 1.5, "required_level": 75.0},
            {"skill": "Python", "weight": 1.2, "required_level": 70.0},
            {"skill": "API Testing", "weight": 1.3, "required_level": 75.0},
            {"skill": "Software Testing Principles", "weight": 1.2, "required_level": 80.0},
        ],
        "preferred_skills": ["Selenium", "Pytest", "Postman", "Cypress", "Jira"],
        "recommended_certifications": ["ISTQB Foundation Level"]
    },
    {
        "id": "cybersecurity",
        "title": "Cybersecurity",
        "category": "Security Engineering",
        "description": "Securing web systems, conducting vulnerability assessments, configuring access control policies, and mitigating network threats.",
        "min_education_level": "Bachelor's",
        "required_skills": [
            {"skill": "Network Security & Protocols", "weight": 1.5, "required_level": 75.0},
            {"skill": "Linux & Bash", "weight": 1.3, "required_level": 75.0},
            {"skill": "Authentication & Cryptography", "weight": 1.4, "required_level": 70.0},
            {"skill": "Python", "weight": 1.1, "required_level": 65.0},
        ],
        "preferred_skills": ["OWASP Top 10", "Wireshark", "Penetration Testing", "Security Auditing"],
        "recommended_certifications": ["CompTIA Security+", "Certified Ethical Hacker (CEH)"]
    },
    {
        "id": "data-analytics",
        "title": "Data Analytics",
        "category": "Business Intelligence & Data",
        "description": "Transforming raw business data into actionable dashboards, KPIs, statistical insights, and automated executive reporting.",
        "min_education_level": "Bachelor's",
        "required_skills": [
            {"skill": "SQL & Databases", "weight": 1.6, "required_level": 80.0},
            {"skill": "Pandas & Data Manipulation", "weight": 1.4, "required_level": 70.0},
            {"skill": "Data Visualization & Dashboards", "weight": 1.4, "required_level": 75.0},
            {"skill": "Statistics & Mathematics", "weight": 1.2, "required_level": 65.0},
        ],
        "preferred_skills": ["Tableau", "Power BI", "Excel Advanced", "Python"],
        "recommended_certifications": ["Google Data Analytics Professional Certificate"]
    },
    {
        "id": "business-intelligence",
        "title": "Business Intelligence",
        "category": "Enterprise Systems",
        "description": "Designing enterprise data warehouses, dimensional modeling, automated ETL flows, and organizational decision analytics.",
        "min_education_level": "Bachelor's",
        "required_skills": [
            {"skill": "SQL & Databases", "weight": 1.5, "required_level": 80.0},
            {"skill": "Data Modeling & Warehousing", "weight": 1.5, "required_level": 75.0},
            {"skill": "ETL & Data Pipelines", "weight": 1.4, "required_level": 70.0},
            {"skill": "Power BI / Tableau", "weight": 1.3, "required_level": 75.0},
        ],
        "preferred_skills": ["Snowflake", "dbt", "Python", "Data Governance"],
        "recommended_certifications": ["Microsoft Certified: Power BI Data Analyst Associate"]
    }
]

SUGGESTED_DOMAIN_PROJECTS: Dict[str, List[SuggestedProjectItem]] = {
    "frontend-dev": [
        SuggestedProjectItem(
            title="Design System & Accessible Component Library",
            description="Build a production-grade component library adhering to WAI-ARIA accessibility benchmarks with Storybook documentation.",
            technologies=["React", "TypeScript", "Tailwind CSS", "Storybook"]
        ),
        SuggestedProjectItem(
            title="Real-Time Collaborative Workspace",
            description="Develop a high-performance single-page workspace with virtualized scrolling, optimistic UI updates, and WebSockets.",
            technologies=["React", "TypeScript", "HTML & CSS"]
        )
    ],
    "backend-dev": [
        SuggestedProjectItem(
            title="High-Throughput Asynchronous Task Processing Pipeline",
            description="Architect a resilient distributed task execution queue with idempotency, dead-letter retries, and Redis caching.",
            technologies=["Python", "FastAPI", "SQL & Databases", "Redis", "Docker"]
        ),
        SuggestedProjectItem(
            title="Microservices Multi-Tenant Auth & Billing Service",
            description="Design an enterprise RESTful microservice with JWT token rotation, role-based access control, and database migrations.",
            technologies=["Python", "FastAPI", "PostgreSQL", "RESTful API Design"]
        )
    ],
    "fullstack-dev": [
        SuggestedProjectItem(
            title="End-to-End Enterprise Resource Planning Portal",
            description="Build a secure SaaS portal with React frontend, FastAPI server, relational schema migrations, and CI/CD automation.",
            technologies=["React", "Python", "FastAPI", "SQL & Databases", "Docker"]
        )
    ],
    "data-science": [
        SuggestedProjectItem(
            title="End-to-End Predictive Model API with Drift Monitoring",
            description="Train, evaluate, and deploy a Scikit-Learn classification pipeline with automated data preprocessing and feature drift detection.",
            technologies=["Python", "Pandas & Data Manipulation", "Machine Learning (Scikit-Learn)", "Statistics & Mathematics"]
        ),
        SuggestedProjectItem(
            title="Exploratory Analytics Dashboard for E-Commerce Churn",
            description="Process multivariate tabular data to extract predictive retention signals with statistical hypothesis validation.",
            technologies=["Python", "Pandas & Data Manipulation", "Data Visualization & Dashboards"]
        )
    ],
    "cloud-devops": [
        SuggestedProjectItem(
            title="Automated Multi-Environment CI/CD GitOps Pipeline",
            description="Configure automated container builds, linting, unit test gates, and continuous delivery with GitHub Actions.",
            technologies=["Linux & Bash", "Docker & Containers", "CI/CD Pipelines", "Cloud Fundamentals (AWS/GCP)"]
        )
    ]
}

class CareerService:
    """Service evaluating career recommendations with deterministic math, Qdrant RAG, and LLM explanations."""

    @classmethod
    def initialize_default_domains(cls):
        """Seed default career domains if none exist."""
        existing = FirestoreRepository.query_documents("career_domains", limit=1)
        if not existing:
            for domain in DEFAULT_CAREER_DOMAINS:
                FirestoreRepository.set_document("career_domains", domain["id"], domain)
            logger.info("Initialized default career domains in repository")

    @classmethod
    def get_all_domains(cls) -> List[Dict[str, Any]]:
        cls.initialize_default_domains()
        return FirestoreRepository.query_documents("career_domains", limit=100)

    @classmethod
    def recommend_careers(
        cls,
        user_skills: Dict[str, float],
        user_confirmed_skills: Optional[List[str]] = None,
        user_education: Optional[str] = None,
        user_interests: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> List[CareerRecommendationResponse]:
        """
        Calculate deterministic match score for each career domain.
        Formula:
        Overall Score = Sum(Skill Weight * Skill Score) / Sum(Skill Weights)
        Skill Gap = Max(0, Required Level - Current Level)
        Handles insufficient data gracefully without fabricating scores.
        """
        cls.initialize_default_domains()
        domains = FirestoreRepository.query_documents("career_domains", limit=100)

        # Retrieve student doc for project and assessment history
        actual_user_id = user_id or ""
        user_doc = FirestoreRepository.get_document("users", actual_user_id) or {} if actual_user_id else {}

        # Confirmed student skills from profile and parsed resume
        confirmed_from_profile = user_doc.get("claimed_skills", []) or user_doc.get("technical_skills", [])
        confirmed_skills_all = list(set((user_confirmed_skills or []) + confirmed_from_profile))

        # Build candidate skill dictionary
        candidate_skills: Dict[str, float] = {}
        for s in confirmed_skills_all:
            if s and str(s).strip():
                candidate_skills[str(s).strip()] = 70.0  # Confirmed skill baseline
        for s, score in (user_skills or {}).items():
            if s and str(s).strip():
                candidate_skills[str(s).strip()] = float(score)

        has_sufficient_data = len(candidate_skills) > 0

        # Retrieve completed assessment breakdown evidence
        assessment_evidence_list: List[str] = []
        if actual_user_id:
            completed_assessments = FirestoreRepository.query_documents(
                "assessments",
                filters=[("user_id", "==", actual_user_id), ("status", "==", "completed")],
                limit=5
            )
            for a in completed_assessments:
                res = a.get("result") or a
                for b in res.get("skill_breakdown", []):
                    s_name = b.get("skill")
                    s_score = b.get("score_percentage", 0)
                    evidence_text = b.get("evidence")
                    if s_name and evidence_text:
                        assessment_evidence_list.append(f"{s_name} ({s_score}%): {evidence_text}")

        # Fetch real job listings from Firestore to attach real opportunities
        all_stored_jobs = FirestoreRepository.query_documents("jobs", limit=100)

        # Confirmed projects
        projects = user_doc.get("projects", [])

        recommendations = []

        for domain in domains:
            domain_id = domain.get("id")
            title = domain.get("title", domain_id)
            desc = domain.get("description", "")
            min_edu = domain.get("min_education_level")
            req_skills = domain.get("required_skills", [])

            # 1. Eligibility Check (Separate from match score)
            eligibility_met = True
            eligibility_notes = []
            if min_edu and user_education:
                edu_hierarchy = ["High School", "Diploma", "Associate", "Bachelor's", "Master's", "Doctorate"]
                user_idx = next((i for i, e in enumerate(edu_hierarchy) if e.lower() in user_education.lower()), -1)
                req_idx = next((i for i, e in enumerate(edu_hierarchy) if e.lower() in min_edu.lower()), -1)
                if user_idx >= 0 and req_idx >= 0 and user_idx < req_idx:
                    eligibility_met = False
                    eligibility_notes.append(f"Minimum required education is {min_edu}; currently registered as {user_education}.")

            # 2. Insufficient Data Handling
            if not has_sufficient_data:
                # Find matching real job listings
                matching_jobs = []
                for j in all_stored_jobs:
                    if title.lower() in j.get("domain", "").lower() or domain_id.lower() in j.get("domain", "").lower():
                        try:
                            matching_jobs.append(JobListingResponse(**j))
                            if len(matching_jobs) >= 3:
                                break
                        except Exception:
                            continue

                recommendations.append(CareerRecommendationResponse(
                    domain_id=domain_id,
                    title=title,
                    description=desc,
                    match_score=None,
                    insufficient_data=True,
                    eligibility_met=eligibility_met,
                    eligibility_notes="; ".join(eligibility_notes) if eligibility_notes else None,
                    matching_skills=[],
                    strong_supporting_skills=[],
                    relevant_project_evidence=[],
                    assessment_evidence=[],
                    weak_or_missing_skills=[r.get("skill") for r in req_skills],
                    skill_gaps=[
                        SkillGapItem(
                            skill=r.get("skill"),
                            required_level=float(r.get("required_level", 70.0)),
                            current_level=0.0,
                            gap=float(r.get("required_level", 70.0)),
                            is_missing=True
                        )
                        for r in req_skills
                    ],
                    missing_required_skills=[r.get("skill") for r in req_skills],
                    ai_explanation=f"Insufficient candidate data available for {title}. Please complete a technical skill assessment or confirm your resume skills to calculate a verified domain match score.",
                    reason_for_recommendation=f"Assessment data is required before evaluating technical readiness for {title}.",
                    suggested_next_steps=[
                        f"Complete the Skill Assessment in Step 3 for {title}",
                        "Upload and confirm technical skills from your resume"
                    ],
                    suggested_projects=SUGGESTED_DOMAIN_PROJECTS.get(domain_id, []),
                    job_ready_steps=[
                        f"Validate core competencies in {', '.join([r.get('skill') for r in req_skills[:2]])}",
                        "Generate and complete personalized learning roadmap"
                    ],
                    related_opportunities=matching_jobs,
                    comparative_analysis=None
                ))
                continue

            # 3. Deterministic Skill Scoring and Gaps with SkillNormalizer
            weights = []
            scores = []
            matching_skills = []
            skill_gaps = []
            missing_required = []

            for req in req_skills:
                skill_name = req.get("skill")
                weight = float(req.get("weight", 1.0))
                req_level = float(req.get("required_level", 70.0))

                # Match against candidate skills using SkillNormalizer
                is_matched, matched_cand_name, cand_score = SkillNormalizer.match_skill_against_collection(
                    skill_name, candidate_skills
                )

                user_level = cand_score if is_matched else 0.0

                weights.append(weight)
                scores.append(user_level)

                gap = ScoringService.calculate_skill_gap(req_level, user_level)
                is_missing = not is_matched or user_level <= 0.0

                if is_missing:
                    missing_required.append(skill_name)

                skill_gaps.append(SkillGapItem(
                    skill=skill_name,
                    required_level=req_level,
                    current_level=user_level,
                    gap=gap,
                    is_missing=is_missing
                ))

                if is_matched and user_level > 0.0:
                    matching_skills.append({"skill": skill_name, "score": user_level})

            # Calculate deterministic weighted match score
            calculated_match_score = ScoringService.calculate_weighted_overall_score(weights, scores)

            # Boost slightly if student explicitly listed this domain in interests
            if user_interests and any(title.lower() in i.lower() for i in user_interests):
                calculated_match_score = min(100.0, round(calculated_match_score + 5.0, 1))

            # Categorize strong vs weak
            strong_supporting = [s["skill"] for s in matching_skills if s["score"] >= 65.0]
            weak_or_missing = list(dict.fromkeys(missing_required + [s["skill"] for s in matching_skills if s["score"] < 65.0]))

            # Project evidence matching
            relevant_project_evidence = []
            for p in projects:
                p_techs = [t.lower() for t in p.get("technologies", [])]
                domain_skills_lower = [r.get("skill", "").lower() for r in req_skills]
                if any(t in domain_skills_lower for t in p_techs):
                    relevant_project_evidence.append(f"Project '{p.get('title')}' demonstrated practical application of {', '.join(p.get('technologies', []))}")

            # Fast evidence-backed explanation based strictly on candidate scores
            if calculated_match_score >= 70.0:
                skills_str = ", ".join([s["skill"] for s in matching_skills[:2]]) or "core competencies"
                explanation = (
                    f"Strong technical alignment with {title} ({calculated_match_score}%) driven by validated proficiency in {skills_str}. "
                    f"Closing remaining gaps in {', '.join(missing_required[:1]) or 'production scaling'} will establish full industry readiness."
                )
            elif calculated_match_score >= 35.0:
                skills_str = ", ".join([s["skill"] for s in matching_skills[:2]]) or "foundational concepts"
                explanation = (
                    f"Moderate foundational alignment for {title} ({calculated_match_score}%). "
                    f"Core proficiencies exist in {skills_str}, but prioritized remediation in {', '.join(missing_required[:2])} is recommended."
                )
            else:
                explanation = (
                    f"Exploratory stage for {title} ({calculated_match_score}%). "
                    f"Recommended to complete foundational coursework and skill assessments in {', '.join(missing_required[:2]) or 'core prerequisites'}."
                )

            # Why is this career domain suitable?
            if calculated_match_score >= 65.0:
                why_suitable = (
                    f"Why is {title} suitable for you? You have verified technical proficiency in "
                    f"{', '.join(strong_supporting[:3]) or 'core foundational principles'} "
                    f"yielding a calculated {calculated_match_score}% domain readiness score. "
                    f"{('Project evidence from ' + relevant_project_evidence[0] + ' reinforces practical readiness.') if relevant_project_evidence else 'Your technical evaluation demonstrates strong alignment with professional engineering expectations.'}"
                )
            elif calculated_match_score >= 35.0:
                why_suitable = (
                    f"Why is {title} suitable for you? You possess foundational competencies in "
                    f"{', '.join(strong_supporting[:2]) or 'introductory requirements'} ({calculated_match_score}% match). "
                    f"With targeted gap remediation in {', '.join(weak_or_missing[:2])}, this domain represents a viable, high-growth path."
                )
            else:
                why_suitable = (
                    f"Why is {title} suitable for you? This domain is an exploratory pathway ({calculated_match_score}% current match). "
                    f"Additional skill assessments in {', '.join(missing_required[:2]) or 'core prerequisites'} are recommended before targeting professional vacancies."
                )

            # Suggested next steps
            suggested_next_steps = [
                f"Close priority skill gap in {weak_or_missing[0]}" if weak_or_missing else "Master production deployment and monitoring",
                "Complete the personalized learning roadmap modules corresponding to this domain",
                "Build suggested portfolio projects to demonstrate verified practical competency"
            ]

            # Job ready steps
            job_ready_steps = [
                f"Complete targeted skill assessments for: {', '.join(weak_or_missing[:2]) if weak_or_missing else 'Advanced Architecture'}",
                f"Build a production-grade portfolio application incorporating {req_skills[0].get('skill') if req_skills else 'core domain tech'}",
                "Review code evaluation rubrics and error boundaries",
                "Apply to matching opportunities on the Jobs page"
            ]

            # Matching real opportunities from stored jobs
            matching_jobs = []
            for j in all_stored_jobs:
                if title.lower() in j.get("domain", "").lower() or domain_id.lower() in j.get("domain", "").lower():
                    try:
                        matching_jobs.append(JobListingResponse(**j))
                        if len(matching_jobs) >= 3:
                            break
                    except Exception:
                        continue

            recommendations.append(CareerRecommendationResponse(
                domain_id=domain_id,
                title=title,
                description=desc,
                match_score=calculated_match_score,
                insufficient_data=False,
                formula_explanation="Deterministic weighted average of domain required skills: Sum(Weight_i × Score_i) / Sum(Weight_i). Unassessed skills count as 0% until evaluated.",
                eligibility_met=eligibility_met,
                eligibility_notes="; ".join(eligibility_notes) if eligibility_notes else None,
                matching_skills=matching_skills,
                strong_supporting_skills=strong_supporting,
                relevant_project_evidence=relevant_project_evidence,
                assessment_evidence=assessment_evidence_list[:3],
                weak_or_missing_skills=weak_or_missing,
                skill_gaps=skill_gaps,
                missing_required_skills=missing_required,
                ai_explanation=explanation,
                reason_for_recommendation=why_suitable,
                suggested_next_steps=suggested_next_steps,
                suggested_projects=SUGGESTED_DOMAIN_PROJECTS.get(domain_id, []),
                job_ready_steps=job_ready_steps,
                related_opportunities=matching_jobs,
                comparative_analysis=None,
                disclaimer="This recommendation is an advisory career alignment based on assessed technical competencies and does not constitute a job offer or employment guarantee."
            ))

        # Sort recommendations descending by match score (None placed last)
        recommendations.sort(
            key=lambda x: (
                0 if x.insufficient_data or x.match_score is None else 1,
                x.match_score if x.match_score is not None else -1.0
            ),
            reverse=True
        )

        # 5. Populate comparative analysis for all recommendations when sufficient data exists
        if has_sufficient_data and len(recommendations) >= 2:
            top_rec = recommendations[0]
            top_title = top_rec.title
            top_score = top_rec.match_score or 0.0

            for rec in recommendations:
                if rec == top_rec:
                    rec.comparative_analysis = (
                        f"{rec.title} ranks highest ({top_score:.1f}%) because your assessed proficiencies and project history "
                        f"show the strongest overlap with its core requirements ({', '.join(rec.strong_supporting_skills[:2]) or 'core prerequisites'})."
                    )
                else:
                    curr_score = rec.match_score or 0.0
                    missing_str = ", ".join(rec.missing_required_skills[:2]) if rec.missing_required_skills else "advanced scaling competencies"
                    rec.comparative_analysis = (
                        f"{rec.title} is ranked lower ({curr_score:.1f}%) compared to your top match {top_title} ({top_score:.1f}%) "
                        f"due to missing or unassessed proficiencies in {missing_str}."
                    )

        return recommendations

    @classmethod
    def _generate_evidence_grounded_explanation(
        cls,
        domain_title: str,
        match_score: float,
        matching_skills: List[Dict[str, Any]],
        missing_skills: List[str],
        project_evidence: List[str],
        assessment_evidence: List[str]
    ) -> str:
        """
        Uses Gemini to produce clear natural-language explanation based strictly on supplied evidence.
        Never hallucinates skills or arbitrary percentages.
        """
        verified_skills_repr = [f"{s.get('skill')}: {s.get('score', 0)}%" for s in matching_skills]
        prompt = f"""
You are the SkillPath AI Career Intelligence Analyst.
Provide a concise, professional 2-sentence explanation of why the candidate has a calculated {match_score}% match with {domain_title}.
Evidence:
- Verified skills: {verified_skills_repr}
- Missing required skills: {missing_skills}
- Project evidence: {project_evidence[:2]}
- Assessment notes: {assessment_evidence[:2]}

Rules:
1. Base your explanation strictly on the provided evidence.
2. Do not invent any skills, degrees, or percentages.
3. Keep it professional, constructive, and evidence-grounded.
"""
        if gemini_service.is_available():
            try:
                text = gemini_service.generate_text(prompt, temperature=0.2, timeout=20.0)
                if text and len(text.strip()) > 20:
                    return text.strip()
            except Exception as e:
                logger.warning(f"Gemini career explanation error: {e}")

        # Deterministic evidence-backed fallback
        if match_score >= 70.0:
            skills_str = ", ".join([s["skill"] for s in matching_skills[:2]]) or "core competencies"
            return f"Strong technical alignment with {domain_title} ({match_score}%) driven by validated proficiency in {skills_str}. Closing remaining gaps in {', '.join(missing_skills[:1]) or 'production scaling'} will establish full industry readiness."
        elif match_score >= 35.0:
            skills_str = ", ".join([s["skill"] for s in matching_skills[:2]]) or "foundational concepts"
            return f"Moderate foundational alignment for {domain_title} ({match_score}%). Core proficiencies exist in {skills_str}, but prioritized remediation in {', '.join(missing_skills[:2])} is recommended."
        else:
            return f"Exploratory stage for {domain_title} ({match_score}%). Recommended to complete foundational coursework and skill assessments in {', '.join(missing_skills[:2]) or 'core prerequisites'}."
