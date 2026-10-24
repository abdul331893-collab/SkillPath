import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from app.repositories.firestore_repo import FirestoreRepository
from app.schemas.job import JobListingResponse, JobMatchResult, JobListingCreate
from app.core.logging import logger

DEFAULT_JOBS = [
    {
        "id": "job-frontend-1",
        "title": "Junior Frontend Engineer",
        "company": "TechVenture Systems",
        "description": "Develop and maintain accessible, responsive web interfaces using React, TypeScript, and modern CSS tooling. Collaborate with product designers and backend engineers.",
        "domain": "Frontend Development",
        "opportunity_type": "Job",
        "required_skills": ["React", "JavaScript", "HTML & CSS"],
        "preferred_skills": ["TypeScript", "Next.js", "Tailwind CSS"],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "San Francisco, CA",
        "work_mode": "Hybrid",
        "application_url": "https://example.com/careers/techventure-fe",
        "deadline": "2026-12-31",
        "is_active": True,
        "created_at": "2026-01-15T00:00:00Z",
        "updated_at": "2026-01-15T00:00:00Z"
    },
    {
        "id": "intern-frontend-1",
        "title": "Frontend Engineering Intern",
        "company": "Veloce Web Studio",
        "description": "Summer internship focusing on modern single-page application development, component testing, and responsive UI optimization with React and Tailwind CSS.",
        "domain": "Frontend Development",
        "opportunity_type": "Internship",
        "required_skills": ["React", "JavaScript", "HTML & CSS"],
        "preferred_skills": ["Tailwind CSS", "Git"],
        "min_experience_years": 0.0,
        "required_education": "Undergraduate",
        "location": "Remote",
        "work_mode": "Remote",
        "application_url": "https://example.com/careers/veloce-intern",
        "deadline": "2026-11-30",
        "is_active": True,
        "created_at": "2026-02-01T00:00:00Z",
        "updated_at": "2026-02-01T00:00:00Z"
    },
    {
        "id": "job-backend-1",
        "title": "Associate Backend Developer",
        "company": "CloudScale Data",
        "description": "Design high-throughput REST APIs, write database migrations, and maintain microservice integrations with Python and FastAPI.",
        "domain": "Backend Development",
        "opportunity_type": "Job",
        "required_skills": ["Python", "FastAPI", "SQL & Databases"],
        "preferred_skills": ["Docker", "PostgreSQL", "Redis"],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "New York, NY",
        "work_mode": "Remote",
        "application_url": "https://example.com/careers/cloudscale-backend",
        "deadline": "2026-12-15",
        "is_active": True,
        "created_at": "2026-01-18T00:00:00Z",
        "updated_at": "2026-01-18T00:00:00Z"
    },
    {
        "id": "intern-backend-1",
        "title": "Backend Engineering Intern",
        "company": "DataStream Solutions",
        "description": "Work directly with senior systems architects to build RESTful API endpoints, write automated unit tests, and optimize PostgreSQL queries.",
        "domain": "Backend Development",
        "opportunity_type": "Internship",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["SQL & Databases", "Docker"],
        "min_experience_years": 0.0,
        "required_education": "Undergraduate",
        "location": "Chicago, IL",
        "work_mode": "Hybrid",
        "application_url": "https://example.com/careers/datastream-intern",
        "deadline": "2026-12-01",
        "is_active": True,
        "created_at": "2026-02-05T00:00:00Z",
        "updated_at": "2026-02-05T00:00:00Z"
    },
    {
        "id": "job-fullstack-1",
        "title": "Full-Stack Software Engineer",
        "company": "Nexus HealthTech",
        "description": "Full lifecycle development of healthcare software solutions connecting patient portals with secure clinical management APIs.",
        "domain": "Full-Stack Development",
        "opportunity_type": "Job",
        "required_skills": ["React", "Python", "SQL & Databases"],
        "preferred_skills": ["TypeScript", "FastAPI", "Docker"],
        "min_experience_years": 1.0,
        "required_education": "Bachelor's",
        "location": "Austin, TX",
        "work_mode": "Remote",
        "application_url": "https://example.com/careers/nexus-fullstack",
        "deadline": "2026-12-31",
        "is_active": True,
        "created_at": "2026-01-20T00:00:00Z",
        "updated_at": "2026-01-20T00:00:00Z"
    },
    {
        "id": "job-ai-1",
        "title": "Junior Machine Learning Engineer",
        "company": "Cognitive AI Labs",
        "description": "Assist in fine-tuning, training data preprocessing, and model evaluation for computer vision and NLP pipelines.",
        "domain": "Data Science & Machine Learning",
        "opportunity_type": "Job",
        "required_skills": ["Python", "Pandas & Data Manipulation", "Machine Learning (Scikit-Learn)"],
        "preferred_skills": ["TensorFlow / PyTorch", "Deep Learning", "SQL"],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "Boston, MA",
        "work_mode": "Remote",
        "application_url": "https://example.com/careers/cognitive-ml",
        "deadline": "2026-11-20",
        "is_active": True,
        "created_at": "2026-01-22T00:00:00Z",
        "updated_at": "2026-01-22T00:00:00Z"
    },
    {
        "id": "intern-ai-1",
        "title": "AI & Machine Learning Research Intern",
        "company": "NeuralEdge Technologies",
        "description": "Hands-on internship assisting researchers with exploratory data analysis, feature engineering, and model validation using Python and Scikit-Learn.",
        "domain": "Data Science & Machine Learning",
        "opportunity_type": "Internship",
        "required_skills": ["Python", "Pandas & Data Manipulation"],
        "preferred_skills": ["Machine Learning (Scikit-Learn)", "SQL"],
        "min_experience_years": 0.0,
        "required_education": "Undergraduate",
        "location": "San Jose, CA",
        "work_mode": "Hybrid",
        "application_url": "https://example.com/careers/neuraledge-intern",
        "deadline": "2026-12-10",
        "is_active": True,
        "created_at": "2026-02-10T00:00:00Z",
        "updated_at": "2026-02-10T00:00:00Z"
    },
    {
        "id": "job-devops-1",
        "title": "Junior DevOps & Cloud Associate",
        "company": "InfraGuard Solutions",
        "description": "Configure CI/CD automated build pipelines, monitor cloud infrastructure, and maintain containerized services.",
        "domain": "Cloud and DevOps Engineering",
        "opportunity_type": "Job",
        "required_skills": ["Linux & Bash", "Docker & Containers", "CI/CD Pipelines"],
        "preferred_skills": ["Kubernetes", "Cloud Fundamentals (AWS/GCP)"],
        "min_experience_years": 0.0,
        "required_education": "Bachelor's",
        "location": "Seattle, WA",
        "work_mode": "Hybrid",
        "application_url": "https://example.com/careers/infraguard-devops",
        "deadline": "2026-12-31",
        "is_active": True,
        "created_at": "2026-01-25T00:00:00Z",
        "updated_at": "2026-01-25T00:00:00Z"
    }
]

from app.services.skill_normalizer import SkillNormalizer

class JobMatchingService:
    """Matches candidate validated skills and qualifications against verified job postings."""

    _jobs_initialized: bool = False

    @classmethod
    def initialize_default_jobs(cls):
        if cls._jobs_initialized:
            return
        existing = FirestoreRepository.query_documents("jobs", limit=1)
        if not existing:
            for job in DEFAULT_JOBS:
                FirestoreRepository.set_document("jobs", job["id"], job)
            logger.info("Seeded default job postings in repository")
        cls._jobs_initialized = True

    @classmethod
    def match_jobs_for_candidate(
        cls,
        user_skills: Dict[str, float],
        user_confirmed_skills: Optional[List[str]] = None,
        user_education: Optional[str] = None,
        user_experience_years: float = 0.0,
        domain_filter: Optional[str] = None,
        work_mode_filter: Optional[str] = None,
        opportunity_type_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[JobMatchResult]:
        cls.initialize_default_jobs()
        all_jobs = FirestoreRepository.query_documents("jobs", limit=200)

        # Build candidate skill lookup merging assessed skills and confirmed resume/profile skills
        candidate_skills: Dict[str, float] = {}
        for s in (user_confirmed_skills or []):
            if s and str(s).strip():
                candidate_skills[str(s).strip()] = 70.0  # Confirmed skill baseline
        for s, score in (user_skills or {}).items():
            if s and str(s).strip():
                candidate_skills[str(s).strip()] = float(score)

        has_student_skills = len(candidate_skills) > 0

        results = []

        for job in all_jobs:
            if not job.get("is_active", True):
                continue

            # Check expiry date
            expiry = job.get("expiry_date") or job.get("deadline")
            if expiry:
                try:
                    if datetime.fromisoformat(expiry.replace("Z", "+00:00")) < datetime.now(timezone.utc):
                        continue
                except Exception:
                    pass

            # Opportunity type filter (Job vs Internship)
            if opportunity_type_filter and opportunity_type_filter.lower() != "all":
                job_type = job.get("opportunity_type", "Job")
                if job_type.lower() != opportunity_type_filter.lower():
                    continue

            # Domain filter
            if domain_filter and domain_filter.lower() != "all":
                if domain_filter.lower() not in job.get("domain", "").lower():
                    continue

            # Work mode filter
            if work_mode_filter and work_mode_filter.lower() != "all":
                if work_mode_filter.lower() != job.get("work_mode", "").lower():
                    continue

            # Search query
            if search_query:
                q = search_query.lower()
                title_match = q in job.get("title", "").lower()
                comp_match = q in job.get("company", "").lower()
                desc_match = q in job.get("description", "").lower()
                skills_match = any(q in s.lower() for s in job.get("required_skills", []))
                if not (title_match or comp_match or desc_match or skills_match):
                    continue

            match_result = cls.calculate_single_match(
                job=job,
                candidate_skills=candidate_skills,
                user_experience_years=user_experience_years,
                user_education=user_education
            )
            results.append(match_result)

        # Sort: eligible candidates first, then descending by match score (None placed last)
        results.sort(
            key=lambda r: (
                1 if r.eligibility_met else 0,
                r.match_score if r.match_score is not None else -1.0
            ),
            reverse=True
        )
        return results

    @classmethod
    def calculate_single_match(
        cls,
        job: Dict[str, Any],
        candidate_skills: Dict[str, float],
        user_experience_years: float = 0.0,
        user_education: Optional[str] = None
    ) -> JobMatchResult:
        """
        Calculates deterministic match score, aliases matching, eligibility, and breakdown for a single job.
        """
        # 1. Mandatory Eligibility Check (Separate from match score)
        eligibility_met = True
        eligibility_notes = []

        min_exp = float(job.get("min_experience_years", 0.0))
        if user_experience_years < min_exp:
            eligibility_met = False
            eligibility_notes.append(f"Requires {min_exp} years of experience; candidate has {user_experience_years} years.")

        req_edu = job.get("required_education")
        if req_edu and user_education:
            edu_hierarchy = ["High School", "Diploma", "Associate", "Bachelor's", "Master's", "Doctorate"]
            u_idx = next((i for i, e in enumerate(edu_hierarchy) if e.lower() in user_education.lower()), -1)
            r_idx = next((i for i, e in enumerate(edu_hierarchy) if e.lower() in req_edu.lower()), -1)
            if u_idx >= 0 and r_idx >= 0 and u_idx < r_idx:
                eligibility_met = False
                eligibility_notes.append(f"Requires minimum education of {req_edu}; candidate has {user_education}.")

        # 2. Skill Matching & Score Calculation
        req_skills = job.get("required_skills", []) or []
        pref_skills = job.get("preferred_skills", []) or []

        matched_req_skills = []
        missing_req_skills = []
        matched_pref_skills = []
        missing_pref_skills = []

        has_student_skills = len(candidate_skills) > 0

        # Condition A: Student confirmed skills are missing
        if not has_student_skills:
            match_score = None
            match_status = "assessment_required"
            explanation = "Complete your skill assessment"
            missing_req_skills = list(req_skills)
            missing_pref_skills = list(pref_skills)

        # Condition B: Internship requirements are missing
        elif not req_skills:
            match_score = None
            match_status = "match_unavailable"
            explanation = "Match unavailable: Requirements not specified for this opportunity"

        # Condition C: Normal matching with SkillNormalizer alias resolution
        else:
            for req in req_skills:
                is_match, matched_name, _ = SkillNormalizer.match_skill_against_collection(req, candidate_skills)
                if is_match:
                    matched_req_skills.append(req)
                else:
                    missing_req_skills.append(req)

            for pref in pref_skills:
                is_match, matched_name, _ = SkillNormalizer.match_skill_against_collection(pref, candidate_skills)
                if is_match:
                    matched_pref_skills.append(pref)
                else:
                    missing_pref_skills.append(pref)

            matched_count = len(matched_req_skills)
            total_count = len(req_skills)

            # Deterministic formula: Match Score = (Matched required skills / Total required skills) * 100
            if matched_count == 0:
                match_score = 0.0
                match_status = "zero_match"
                explanation = f"0% Match Score: None of the {total_count} required skills match your current confirmed skills."
            else:
                score_val = (matched_count / total_count) * 100.0
                match_score = round(min(100.0, max(0.0, score_val)), 1)
                match_status = "calculated"
                missing_str = ", ".join(missing_req_skills) if missing_req_skills else "None"
                explanation = f"Matched {matched_count} of {total_count} required skills ({', '.join(matched_req_skills)}). Missing: {missing_str}."

        matching_skills = matched_req_skills + [f"{p} (Preferred)" for p in matched_pref_skills]
        job_resp = JobListingResponse(**job)

        return JobMatchResult(
            job=job_resp,
            match_score=match_score,
            match_status=match_status,
            explanation=explanation,
            eligibility_met=eligibility_met,
            eligibility_notes="; ".join(eligibility_notes) if eligibility_notes else None,
            matched_required_skills=matched_req_skills,
            missing_required_skills=missing_req_skills,
            matched_preferred_skills=matched_pref_skills,
            missing_preferred_skills=missing_pref_skills,
            matching_skills=matching_skills
        )

    @classmethod
    def bulk_import_csv(cls, rows: List[Dict[str, Any]]) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        Validates and imports bulk job rows.
        Returns: (imported_count, failed_count, errors)
        """
        imported_count = 0
        failed_count = 0
        errors = []

        for idx, row in enumerate(rows):
            row_num = idx + 1
            title = row.get("title", "").strip()
            company = row.get("company", "").strip()
            domain = row.get("domain", "").strip()
            location = row.get("location", "").strip()

            if not title or not company or not domain or not location:
                failed_count += 1
                errors.append({"row": row_num, "error": "Missing mandatory fields (title, company, domain, or location)"})
                continue

            req_skills = [s.strip() for s in str(row.get("required_skills", "")).split(",") if s.strip()]
            if not req_skills:
                failed_count += 1
                errors.append({"row": row_num, "error": "At least one required skill must be specified"})
                continue

            pref_skills = [s.strip() for s in str(row.get("preferred_skills", "")).split(",") if s.strip()]

            try:
                min_exp = float(row.get("min_experience_years", 0.0))
            except ValueError:
                min_exp = 0.0

            job_id = f"job-{uuid.uuid4()}"
            now_str = datetime.now(timezone.utc).isoformat()

            opp_type = row.get("opportunity_type", "Job").strip()
            if opp_type.lower() in ("internship", "intern"):
                opp_type = "Internship"
            else:
                opp_type = "Job"

            new_job = {
                "id": job_id,
                "title": title,
                "company": company,
                "description": row.get("description", f"Position for {title} at {company}"),
                "domain": domain,
                "opportunity_type": opp_type,
                "required_skills": req_skills,
                "preferred_skills": pref_skills,
                "min_experience_years": min_exp,
                "required_education": row.get("required_education"),
                "location": location,
                "work_mode": row.get("work_mode", "Remote"),
                "application_url": row.get("application_url"),
                "deadline": row.get("deadline"),
                "is_active": True,
                "created_at": now_str,
                "updated_at": now_str
            }

            FirestoreRepository.set_document("jobs", job_id, new_job)
            imported_count += 1

        return imported_count, failed_count, errors
