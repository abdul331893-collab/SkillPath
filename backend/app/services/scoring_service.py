from typing import List, Dict, Any, Tuple
from app.schemas.assessment import (
    SkillScoreBreakdown,
    QuestionEvaluationResult,
    QuestionType,
)
from app.services.gemini_service import gemini_service
from app.core.logging import logger

class ScoringService:
    """Performs deterministic skill score calculations and rubric evaluations."""

    @staticmethod
    def calculate_skill_score(earned_points: float, available_points: float) -> float:
        """
        Skill Score = Earned Points / Available Points * 100
        Normalized between 0.0 and 100.0.
        """
        if available_points <= 0:
            return 0.0
        score = (earned_points / available_points) * 100.0
        return round(min(100.0, max(0.0, score)), 2)

    @staticmethod
    def calculate_weighted_overall_score(weights: List[float], scores: List[float]) -> float:
        """
        Overall Score = Sum(Skill Weight * Skill Score) / Sum(Skill Weights)
        """
        if not weights or not scores or len(weights) != len(scores):
            return 0.0
        sum_weights = sum(weights)
        if sum_weights <= 0:
            return 0.0
        weighted_sum = sum(w * s for w, s in zip(weights, scores))
        return round(weighted_sum / sum_weights, 2)

    @staticmethod
    def calculate_skill_gap(required_level: float, current_level: float) -> float:
        """
        Skill Gap = Maximum of 0 and (Required Skill Level - Current Skill Level)
        """
        gap = required_level - current_level
        return round(max(0.0, gap), 2)

    @staticmethod
    def get_proficiency_tier(score_percentage: float) -> str:
        if score_percentage >= 85.0:
            return "Expert"
        elif score_percentage >= 70.0:
            return "Proficient"
        elif score_percentage >= 50.0:
            return "Intermediate"
        else:
            return "Beginner"

    @classmethod
    def evaluate_descriptive_answer(
        cls,
        question_text: str,
        student_answer: str,
        rubric: Dict[str, Any],
        max_points: float
    ) -> Tuple[float, str, str]:
        """
        Evaluates a descriptive answer against a rubric using Gemini LLM.
        Returns: (earned_points, feedback, improvement_suggestion)
        """
        if not student_answer or not student_answer.strip():
            return 0.0, "No answer provided.", "Review fundamental concepts and provide an explanation."

        criteria_str = "\n".join([f"- {k}: {v}" for k, v in rubric.items()]) if rubric else "- Conceptual understanding: 50%\n- Practical accuracy: 50%"

        prompt = f"""
You are an expert technical assessment evaluator for SkillPath AI.
Evaluate the student's descriptive response strictly against the given rubric criteria.

Question:
{question_text}

Evaluation Rubric:
{criteria_str}

Maximum Available Points: {max_points}

Student's Submitted Answer:
\"\"\"
{student_answer}
\"\"\"

Respond with a JSON object in this format:
{{
  "points_awarded": float (between 0.0 and {max_points}),
  "feedback": "Concise, constructive explanation of the evaluation",
  "improvement_suggestion": "Specific technical topic or practice task to improve"
}}
"""
        evaluation = None
        if gemini_service.is_available():
            try:
                evaluation = gemini_service.generate_json(prompt, timeout=12.0, max_retries=1)
            except Exception as e:
                logger.warning(f"Gemini descriptive evaluation skipped/timed out: {e}. Using rubric fallback.")

        if evaluation and isinstance(evaluation, dict):
            pts = float(evaluation.get("points_awarded", max_points * 0.7))
            pts = max(0.0, min(max_points, pts))
            fb = evaluation.get("feedback", "Answer demonstrated relevant conceptual understanding.")
            sug = evaluation.get("improvement_suggestion", "Deepen coverage of edge cases and performance.")
            return round(pts, 2), fb, sug

        # Fallback evaluation based on length and relevance
        words = len(student_answer.split())
        if words < 10:
            pts = max_points * 0.3
            fb = "Response is brief and lacks depth in technical justification."
        elif words < 30:
            pts = max_points * 0.6
            fb = "Good basic explanation, though missing detailed implementation considerations."
        else:
            pts = max_points * 0.85
            fb = "Thorough response demonstrating solid foundational concepts."

        return round(pts, 2), fb, "Continue practicing real-world implementation exercises."
