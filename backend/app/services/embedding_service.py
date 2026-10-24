import math
import re
import httpx
from typing import List, Optional
from app.core.config import settings
from app.core.logging import logger

class EmbeddingService:
    """Generates vector embeddings using Gemini Embedding REST API with bag-of-words fallback."""

    def __init__(self):
        self.model_name = settings.GEMINI_EMBEDDING_MODEL or "models/text-embedding-004"
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            logger.info(f"Gemini embedding service configured with {self.model_name}")

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string into a 768-dimensional float vector."""
        if self.is_available():
            clean_model = self.model_name.replace("models/", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:embedContent?key={self.api_key}"
            payload = {
                "content": {
                    "parts": [{"text": text[:2000]}]
                }
            }
            try:
                with httpx.Client(timeout=20.0) as client:
                    res = client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        values = data.get("embedding", {}).get("values")
                        if values and len(values) > 0:
                            return values
                    else:
                        logger.error(f"Gemini embedding API status {res.status_code}: {res.text}")
            except Exception as e:
                logger.error(f"Gemini embedding REST error: {e}")

        # Deterministic semantic fallback
        return self._fallback_embedding(text)

    def embed_query(self, query: str) -> List[float]:
        return self.embed_text(query)

    def _fallback_embedding(self, text: str, dim: int = 768) -> List[float]:
        """Generates consistent normalized vectors for offline testing using bag-of-words hashing."""
        vec = [0.0] * dim
        words = re.findall(r"\b\w+\b", text.lower())
        for word in words:
            h = abs(hash(word)) % dim
            vec[h] += 1.0
        magnitude = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / magnitude, 6) for x in vec]

embedding_service = EmbeddingService()
