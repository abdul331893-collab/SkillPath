import uuid
from typing import List, Dict, Any, Optional
from app.services.embedding_service import embedding_service
from app.services.qdrant_service import qdrant_service
from app.services.gemini_service import gemini_service
from app.core.logging import logger

DEFAULT_KNOWLEDGE_DOCS = [
    {
        "source_id": "doc_react_arch",
        "title": "React Architecture & Virtual DOM Lifecycle",
        "category": "Frontend Development",
        "skill": "React",
        "content": (
            "React uses a virtual DOM to optimize UI updates. When a component state changes, "
            "React creates a new virtual DOM tree and performs reconciliation (the diffing algorithm) "
            "against the previous tree. Hooks like useMemo and useCallback avoid unnecessary recalculations "
            "and rerenders. In React 19, server components and concurrent features provide streaming and "
            "asynchronous rendering primitives."
        )
    },
    {
        "source_id": "doc_fastapi_arch",
        "title": "FastAPI Production Architecture & Async Execution",
        "category": "Backend Development",
        "skill": "FastAPI",
        "content": (
            "FastAPI is an asynchronous web framework built on Starlette and Pydantic. Route endpoints "
            "defined with 'async def' execute directly on the asyncio event loop, whereas standard 'def' "
            "endpoints run inside an external threadpool. Dependency injection enables composable security, "
            "database sessions, and role validation. OpenAPI schema generation is performed automatically."
        )
    },
    {
        "source_id": "doc_sql_concurrency",
        "title": "Database Concurrency Control & Isolation Levels",
        "category": "Backend Development",
        "skill": "SQL & Databases",
        "content": (
            "ACID transactions guarantee consistency. Pessimistic locking locks rows immediately via "
            "SELECT FOR UPDATE, preventing concurrent updates at the cost of concurrency bottlenecks. "
            "Optimistic concurrency control assumes conflict is rare, checking a version or timestamp column "
            "upon commit. If another transaction modified the row, the commit is aborted."
        )
    },
    {
        "source_id": "doc_fe_domain",
        "title": "Frontend Development Domain Architecture & Standards",
        "category": "Frontend Development",
        "skill": "JavaScript",
        "content": (
            "Frontend engineering requires mastery of core JavaScript, component state trees, React hooks, "
            "semantic HTML5, accessible CSS layout patterns, and modern tooling (Vite, Next.js). "
            "Production benchmarks evaluate client-side latency, First Contentful Paint, bundle size reduction, "
            "and WCAG accessibility compliance."
        )
    },
    {
        "source_id": "doc_be_domain",
        "title": "Backend Development Domain Architecture & Standards",
        "category": "Backend Development",
        "skill": "Python",
        "content": (
            "Backend engineering entails architecting robust RESTful and GraphQL APIs, relational database design, "
            "connection pooling, database transaction isolation, and containerized deployment with Docker. "
            "Proficiency in Python (FastAPI/Django) and asynchronous event loops is required."
        )
    },
    {
        "source_id": "doc_devops_domain",
        "title": "Cloud & DevOps Infrastructure Architecture",
        "category": "Infrastructure",
        "skill": "Docker & Containers",
        "content": (
            "Cloud and DevOps engineering demands proficiency in Linux shell automation, containerization with Docker, "
            "automated CI/CD pipelines (GitHub Actions, GitLab CI), infrastructure-as-code, and cloud fundamentals (AWS/GCP). "
            "Key metrics include deployment frequency and mean time to recovery."
        )
    },
    {
        "source_id": "doc_ml_evaluation",
        "title": "Machine Learning Model Evaluation & Overfitting",
        "category": "Data Science",
        "skill": "Machine Learning (Scikit-Learn)",
        "content": (
            "Overfitting occurs when a model fits noise in training data instead of generalizable patterns. "
            "Key diagnostic metrics include high training score contrasted with declining cross-validation or test score. "
            "Techniques to prevent overfitting include regularization (L1 Lasso, L2 Ridge, Dropout), cross-validation, "
            "early stopping, and data augmentation."
        )
    }
]

class RAGService:
    """Manages document chunking, vector ingestion, retrieval, and grounded Q&A generation."""

    def __init__(self):
        self._seeded = False

    def seed_initial_knowledge(self):
        if self._seeded:
            return
        for doc in DEFAULT_KNOWLEDGE_DOCS:
            self.ingest_document(
                source_id=doc["source_id"],
                title=doc["title"],
                category=doc["category"],
                skill=doc["skill"],
                content=doc["content"]
            )
        self._seeded = True
        logger.info("Seeded initial knowledge items into RAG vector repository")

    def chunk_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 80) -> List[str]:
        """Splits text using LangChain RecursiveCharacterTextSplitter or fallback windowing."""
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            return splitter.split_text(text)
        except Exception:
            # Fallback simple chunker
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunks.append(text[start:end])
                start += chunk_size - chunk_overlap
            return chunks

    def ingest_document(
        self,
        source_id: str,
        title: str,
        category: str,
        skill: str,
        content: str
    ) -> int:
        """
        Chunks text, computes embeddings, and stores vectors with payload metadata in Qdrant.
        Returns number of chunks ingested.
        """
        chunks = self.chunk_text(content)
        points = []

        for idx, chunk in enumerate(chunks):
            vector = embedding_service.embed_text(chunk)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{source_id}_{idx}"))
            points.append({
                "id": point_id,
                "vector": vector,
                "payload": {
                    "source_id": source_id,
                    "title": title,
                    "category": category,
                    "skill": skill,
                    "chunk_index": idx,
                    "text": chunk
                }
            })

        qdrant_service.upsert_points(points)
        return len(points)

    def retrieve_snippets(self, query: str, skill_filter: Optional[str] = None, top_k: int = 2) -> List[str]:
        """Fast snippet retrieval from indexed vector storage or in-memory knowledge docs."""
        try:
            self.seed_initial_knowledge()
            query_vector = embedding_service.embed_query(query)
            hits = qdrant_service.search(query_vector=query_vector, limit=top_k, filter_skill=skill_filter)
            snippets = [h.get("payload", {}).get("text") for h in hits if h.get("payload", {}).get("text")]
            if snippets:
                return snippets
        except Exception as e:
            logger.debug(f"Vector search snippet retrieval note: {e}")

        # In-memory keyword fallback from DEFAULT_KNOWLEDGE_DOCS
        q_lower = query.lower()
        matched = []
        for doc in DEFAULT_KNOWLEDGE_DOCS:
            if (skill_filter and skill_filter.lower() in doc["skill"].lower()) or doc["skill"].lower() in q_lower or doc["category"].lower() in q_lower:
                matched.append(doc["content"][:300])
                if len(matched) >= top_k:
                    break
        return matched or [DEFAULT_KNOWLEDGE_DOCS[0]["content"][:300]]

    def answer_query(
        self,
        query: str,
        skill_filter: Optional[str] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Retrieves relevant grounded knowledge chunks and generates an evidence-backed answer.
        Explicitly indicates if evidence is insufficient.
        """
        self.seed_initial_knowledge()

        query_vector = embedding_service.embed_query(query)
        hits = qdrant_service.search(query_vector=query_vector, limit=top_k, filter_skill=skill_filter)

        context_chunks = []
        sources = []
        for hit in hits:
            payload = hit.get("payload", {})
            text = payload.get("text")
            if text:
                context_chunks.append(text)
                src = {
                    "source_id": payload.get("source_id"),
                    "title": payload.get("title"),
                    "skill": payload.get("skill"),
                    "relevance_score": round(hit.get("score", 0.0), 3)
                }
                if src not in sources:
                    sources.append(src)

        if not context_chunks:
            return {
                "query": query,
                "answer": "Insufficient knowledge base evidence is currently available to authoritatively answer this specific question.",
                "sources": [],
                "confidence": "low"
            }

        context_str = "\n\n---\n\n".join(context_chunks)

        prompt = f"""
You are the SkillPath AI Career Intelligence Assistant.
Answer the student's question strictly grounded on the provided retrieved context.
If the retrieved context does not contain sufficient factual evidence to answer the question, state:
"Based on the currently indexed resources, there is insufficient evidence to fully answer this topic."
Do not fabricate facts, courses, or external claims.

Retrieved Context:
{context_str}

Student Question:
{query}

Format your answer clearly with bullet points where appropriate.
"""
        answer_text = None
        if gemini_service.is_available():
            answer_text = gemini_service.generate_text(prompt)

        if not answer_text:
            # Deterministic synthesized summary from retrieved chunks
            answer_text = f"Retrieved Reference:\n{context_chunks[0]}\n\n(Generated from indexed learning resources for {sources[0]['title']})."

        return {
            "query": query,
            "answer": answer_text,
            "sources": sources,
            "confidence": "high" if len(sources) > 0 else "medium"
        }

rag_service = RAGService()
