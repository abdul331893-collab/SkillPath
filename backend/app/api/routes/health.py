from fastapi import APIRouter
from datetime import datetime, timezone
from app.core.config import settings
from app.services.gemini_service import gemini_service
from app.services.qdrant_service import qdrant_service

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
async def get_health():
    """Health check endpoint validating application and integration statuses."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "integrations": {
            "gemini": "configured" if gemini_service.is_available() else "mock_fallback",
            "qdrant": "connected" if qdrant_service.client is not None else "in_memory_fallback",
            "storage": "cloudinary" if settings.CLOUDINARY_CLOUD_NAME else "local_disk"
        }
    }
