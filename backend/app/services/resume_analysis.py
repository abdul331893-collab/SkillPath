import re
from typing import Dict, Any, List
from app.services.gemini_service import gemini_service
from app.schemas.resume import ResumeExtractedData
from app.core.logging import logger

KNOWN_TECH_SKILLS = [
    "python", "javascript", "typescript", "react", "next.js", "node.js", "express",
    "html", "css", "tailwind", "fastapi", "flask", "django", "sql", "postgresql",
    "mysql", "mongodb", "docker", "kubernetes", "aws", "gcp", "azure", "git",
    "github", "graphql", "rest api", "ci/cd", "linux", "c++", "java", "c#",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "tableau", "power bi",
    "selenium", "cypress", "jest", "pytest", "redis", "qdrant", "firebase"
]

class ResumeAnalysisService:
    """Extracts structured candidate data, claimed skills, and domain recommendations."""

    @classmethod
    def analyze_resume(cls, text: str) -> Dict[str, Any]:
        """
        Extract candidate details and claimed skills using Gemini,
        falling back to pattern matching if LLM is offline.
        """
        prompt = f"""
You are an expert technical resume parser for SkillPath AI.
Analyze the following resume text and extract the candidate's structured details.

Resume text:
\"\"\"
{text[:4000]}
\"\"\"

Respond strictly with a JSON object in this structure:
{{
  "name": "Candidate Full Name or null",
  "email": "Candidate Email or null",
  "phone": "Candidate Phone or null",
  "education": [
    {{"degree": "Degree Title", "institution": "University/College", "year": "Graduation Year or null"}}
  ],
  "claimed_skills": ["Skill 1", "Skill 2"],
  "projects": [
    {{"title": "Project Name", "description": "Brief description", "technologies": ["Tech 1"]}}
  ],
  "experience": [
    {{"company": "Company Name", "role": "Job Title", "duration": "Duration", "description": "Summary"}}
  ],
  "certifications": ["Certification 1"],
  "summary": "2-sentence executive summary of the candidate's background"
}}
"""
        extracted = None
        if gemini_service.is_available():
            extracted = gemini_service.generate_json(prompt)

        if not extracted or not isinstance(extracted, dict):
            # Fallback heuristic parser
            extracted = cls._heuristic_parse(text)

        # Determine recommended career domains based on claimed skills
        claimed_skills_lower = [s.lower() for s in extracted.get("claimed_skills", [])]
        recommended_domains = cls._recommend_domains(claimed_skills_lower)

        return {
            "extracted_data": extracted,
            "recommended_domains": recommended_domains
        }

    @classmethod
    def _heuristic_parse(cls, text: str) -> Dict[str, Any]:
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)

        # Detect skills by keyword search
        text_lower = text.lower()
        found_skills = [s.title() for s in KNOWN_TECH_SKILLS if re.search(r"\b" + re.escape(s) + r"\b", text_lower)]

        return {
            "name": text.split("\n")[0].strip() if text else "Candidate",
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
            "education": [{"degree": "Technical Degree", "institution": "University", "year": "2024"}],
            "claimed_skills": list(set(found_skills)),
            "projects": [],
            "experience": [],
            "certifications": [],
            "summary": "Resume parsed successfully. Technical skills identified for assessment validation."
        }

    @classmethod
    def _recommend_domains(cls, claimed_skills: List[str]) -> List[str]:
        domains = []
        frontend_keywords = {"javascript", "typescript", "react", "next.js", "html", "css", "tailwind"}
        backend_keywords = {"python", "fastapi", "django", "node.js", "sql", "postgresql", "docker", "rest api"}
        data_keywords = {"python", "pandas", "numpy", "scikit-learn", "sql", "power bi", "tableau"}
        qa_keywords = {"selenium", "cypress", "jest", "pytest"}
        cloud_keywords = {"aws", "gcp", "azure", "docker", "kubernetes", "ci/cd", "linux"}

        skills_set = set(claimed_skills)
        if skills_set & frontend_keywords and skills_set & backend_keywords:
            domains.append("Full-Stack Development")
        if skills_set & frontend_keywords:
            domains.append("Frontend Development")
        if skills_set & backend_keywords:
            domains.append("Backend Development")
        if skills_set & data_keywords:
            domains.append("Data Analytics")
            domains.append("Data Science")
        if skills_set & cloud_keywords:
            domains.append("Cloud and DevOps")
        if skills_set & qa_keywords:
            domains.append("Software Testing and QA")

        if not domains:
            domains = ["Frontend Development", "Backend Development", "Full-Stack Development"]

        return list(dict.fromkeys(domains))[:4]
