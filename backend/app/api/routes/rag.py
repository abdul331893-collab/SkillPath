from typing import Optional
from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel
from app.api.dependencies import get_current_user, require_admin
from app.core.permissions import AuthenticatedUser
from app.services.rag_service import rag_service

router = APIRouter(prefix="/rag", tags=["Retrieval-Augmented Generation"])

class QueryRequest(BaseModel):
    query: str
    skill_filter: Optional[str] = None

class IngestionRequest(BaseModel):
    source_id: str
    title: str
    category: str
    skill: str
    content: str

@router.post("/query")
async def query_knowledge_base(
    req: QueryRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Submits a query to the RAG pipeline.
    Retrieves vector chunks from Qdrant and generates a grounded response with citations.
    """
    return rag_service.answer_query(
        query=req.query,
        skill_filter=req.skill_filter
    )

@router.post("/ingest")
async def ingest_knowledge_document(
    req: IngestionRequest,
    admin: AuthenticatedUser = Depends(require_admin)
):
    """Admin-only endpoint to ingest learning materials or rubrics into the vector repository."""
    chunks = rag_service.ingest_document(
        source_id=req.source_id,
        title=req.title,
        category=req.category,
        skill=req.skill,
        content=req.content
    )
    return {"message": f"Successfully ingested {chunks} chunks into vector knowledge base", "source_id": req.source_id}
