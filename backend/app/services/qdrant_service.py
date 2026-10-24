import uuid
import math
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger

class QdrantService:
    """Manages persistent vector storage and similarity searches in Qdrant with local fallback."""

    def __init__(self):
        self.url = settings.QDRANT_URL
        self.api_key = settings.QDRANT_API_KEY
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.client = None
        self._memory_vectors: List[Dict[str, Any]] = []

        if self.url:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.http import models

                self.client = QdrantClient(url=self.url, api_key=self.api_key, timeout=5)
                # Check collection or create
                collections = [c.name for c in self.client.get_collections().collections]
                if self.collection_name not in collections:
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
                    )
                logger.info(f"Connected to Qdrant vector database at {self.url}")
            except Exception as e:
                logger.warning(f"Qdrant connection unavailable ({e}); utilizing resilient in-memory vector store")
                self.client = None

    def upsert_points(self, points: List[Dict[str, Any]]) -> bool:
        """
        Upserts vectors with metadata payload.
        point format: {"id": str, "vector": List[float], "payload": Dict[str, Any]}
        """
        if self.client:
            try:
                from qdrant_client.http import models
                qdrant_points = [
                    models.PointStruct(
                        id=str(p.get("id", uuid.uuid4())),
                        vector=p["vector"],
                        payload=p.get("payload", {})
                    )
                    for p in points
                ]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=qdrant_points
                )
                return True
            except Exception as e:
                logger.error(f"Qdrant upsert error: {e}")

        # Always maintain in-memory fallback store for offline/test reliability
        for p in points:
            pid = str(p.get("id", uuid.uuid4()))
            self._memory_vectors = [m for m in self._memory_vectors if m["id"] != pid]
            self._memory_vectors.append({
                "id": pid,
                "vector": p["vector"],
                "payload": p.get("payload", {})
            })

        if self.client:
            try:
                from qdrant_client.http import models
                qdrant_points = [
                    models.PointStruct(
                        id=p.get("id", str(uuid.uuid4())),
                        vector=p["vector"],
                        payload=p.get("payload", {})
                    )
                    for p in points
                ]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=qdrant_points
                )
                return True
            except Exception as e:
                logger.error(f"Qdrant upsert error: {e}")

        return True

    def search(
        self,
        query_vector: List[float],
        limit: int = 4,
        filter_skill: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Searches nearest vectors matching query."""
        if self.client:
            try:
                from qdrant_client.http import models
                query_filter = None
                if filter_skill:
                    query_filter = models.Filter(
                        must=[models.FieldCondition(key="skill", match=models.MatchValue(value=filter_skill))]
                    )
                if hasattr(self.client, "search"):
                    search_result = self.client.search(
                        collection_name=self.collection_name,
                        query_vector=query_vector,
                        query_filter=query_filter,
                        limit=limit
                    )
                    return [
                        {
                            "id": str(hit.id),
                            "score": hit.score,
                            "payload": hit.payload
                        }
                        for hit in search_result
                    ]
                elif hasattr(self.client, "query_points"):
                    res = self.client.query_points(
                        collection_name=self.collection_name,
                        query=query_vector,
                        query_filter=query_filter,
                        limit=limit
                    )
                    return [
                        {
                            "id": str(hit.id),
                            "score": getattr(hit, "score", 1.0),
                            "payload": hit.payload
                        }
                        for hit in res.points
                    ]
            except Exception as e:
                logger.error(f"Qdrant search error: {e}")

        # In-memory cosine similarity search fallback
        results = []
        for item in self._memory_vectors:
            payload = item.get("payload", {})
            if filter_skill and payload.get("skill") != filter_skill:
                continue

            sim = self._cosine_similarity(query_vector, item["vector"])
            results.append({
                "id": item["id"],
                "score": sim,
                "payload": payload
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

qdrant_service = QdrantService()
