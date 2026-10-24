import os
import json
import re
import time
import httpx
from typing import Dict, Any, Optional, List, Union
from app.core.config import settings
from app.core.logging import logger

class GeminiError(Exception):
    """Base exception for Gemini service failures."""
    pass

class GeminiConfigError(GeminiError):
    """Raised when Gemini API key is missing or misconfigured."""
    pass

class GeminiAuthError(GeminiError):
    """Raised when authentication fails (HTTP 401/403)."""
    pass

class GeminiRateLimitError(GeminiError):
    """Raised when rate limits or quotas are exceeded (HTTP 429)."""
    pass

class GeminiTimeoutError(GeminiError):
    """Raised when request times out."""
    pass

class GeminiAPIError(GeminiError):
    """Raised when the Gemini API returns an error response."""
    pass


class GeminiService:
    """Service communicating with Google Gemini API via REST endpoints."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL or "gemini-3.8-flash"
        if self.api_key:
            logger.info(f"Gemini API initialized with model {self.model_name}")
        else:
            logger.warning("Gemini API key is not configured in settings")

    def is_available(self) -> bool:
        """Checks if a non-empty API key is configured."""
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def _get_url(self, model_name: Optional[str] = None) -> str:
        model = model_name or self.model_name
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.5,
        timeout: float = 60.0,
        max_retries: int = 2
    ) -> str:
        """
        Generate text using Google Gemini API.
        Never pretends success on failure; raises explicit Gemini exceptions.
        Seamlessly falls back to secondary active models if the primary model's daily quota is exhausted.
        """
        if not self.is_available():
            raise GeminiConfigError("Google Gemini API key is not configured on the server. Please set GEMINI_API_KEY in .env.")

        candidate_models = []
        # Prioritize gemini-flash-lite-latest as primary fast model
        for m in ["gemini-flash-lite-latest", self.model_name, "gemini-3.8-flash", "gemini-flash-latest"]:
            if m and m not in candidate_models and m not in ("gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"):
                candidate_models.append(m)

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
            }
        }

        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }

        last_error = None
        for current_model in candidate_models:
            url = self._get_url(current_model)
            for attempt in range(max_retries + 1):
                try:
                    with httpx.Client(timeout=timeout) as client:
                        res = client.post(url, json=payload)

                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text_parts = [p.get("text", "") for p in parts if "text" in p]
                            if text_parts:
                                return "".join(text_parts).strip()
                        raise GeminiAPIError("Gemini returned empty candidates in response")

                    # Handle specific HTTP error status codes
                    if res.status_code in (401, 403):
                        raise GeminiAuthError(f"Gemini authentication failed (HTTP {res.status_code}): {res.text}")
                    elif res.status_code == 429:
                        # If quota is exhausted on this specific model, try the next candidate model
                        logger.warning(f"Quota exceeded on model '{current_model}' (HTTP 429). Attempting fallback...")
                        last_error = GeminiRateLimitError(f"Gemini rate limit or quota exceeded (HTTP 429): {res.text}")
                        break  # Break attempt loop and try next candidate model
                    elif res.status_code in (404, 503):
                        logger.warning(f"Model '{current_model}' returned HTTP {res.status_code}. Attempting fallback...")
                        last_error = GeminiAPIError(f"Gemini model '{current_model}' returned {res.status_code}: {res.text}")
                        break  # Break attempt loop and try next candidate model immediately
                    else:
                        if attempt < max_retries and res.status_code >= 500:
                            time.sleep(1.0 * (attempt + 1))
                            continue
                        raise GeminiAPIError(f"Gemini API returned HTTP {res.status_code}: {res.text}")

                except httpx.TimeoutException as e:
                    logger.warning(f"Gemini request timed out on model {current_model}: {e}. Trying fallback...")
                    last_error = e
                    break
                except (GeminiError, Exception) as e:
                    if isinstance(e, (GeminiAuthError, GeminiConfigError)):
                        raise
                    logger.error(f"Gemini request error on {current_model}: {e}")
                    last_error = e
                    if attempt < max_retries:
                        time.sleep(1.0)
                        continue
                    break

        if isinstance(last_error, GeminiError):
            raise last_error
        raise GeminiAPIError(f"Failed to generate text after trying models {candidate_models}: {last_error}")

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 65.0,
        max_retries: int = 2
    ) -> Any:
        """
        Generate and strictly parse structured JSON output from Gemini.
        Returns parsed list or dict. Raises GeminiAPIError if parsing fails after retries.
        """
        enhanced_prompt = (
            f"{prompt}\n\n"
            "CRITICAL INSTRUCTION: Respond ONLY with a valid, parseable JSON document (matching the requested structure). "
            "Do NOT include markdown formatting like ```json, notes, or prose outside the JSON."
        )

        for attempt in range(max_retries + 1):
            raw_text = self.generate_text(
                prompt=enhanced_prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                timeout=timeout,
                max_retries=1
            )

            if not raw_text:
                if attempt < max_retries:
                    continue
                raise GeminiAPIError("Gemini returned empty text for JSON generation")

            try:
                # Strip leading/trailing markdown fences if model returned them
                cleaned = raw_text.strip()
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
                cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

                # Find outermost JSON object or array if extra conversational text exists
                json_match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
                if json_match:
                    cleaned = json_match.group(1).strip()

                parsed = json.loads(cleaned)
                return parsed
            except json.JSONDecodeError as err:
                logger.warning(f"Failed to parse JSON on attempt {attempt + 1}: {err}. Raw snippet: {raw_text[:200]}")
                if attempt < max_retries:
                    time.sleep(1.0)
                    continue
                raise GeminiAPIError(f"Invalid JSON returned by Gemini: {err}. Response was: {raw_text[:300]}")

        raise GeminiAPIError("Failed to produce valid JSON from Gemini")


gemini_service = GeminiService()
