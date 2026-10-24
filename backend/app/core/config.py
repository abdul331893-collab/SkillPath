import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=(
            str(_BACKEND_DIR / ".env"),
            str(_ROOT_DIR / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    APP_NAME: str = "SkillPath AI"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    FRONTEND_URL: str = "https://skillpath-a7ca.onrender.com"
    ALLOWED_ORIGINS: str = "https://skillpath-a7ca.onrender.com,http://localhost:3000,http://127.0.0.1:3000"
    ADMIN_EMAILS: str = "admin@gmail.com,admin@skillpath.ai"

    # Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

    # Firebase
    FIREBASE_SERVICE_ACCOUNT_KEY: Optional[str] = None
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CLIENT_EMAIL: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None

    # Qdrant
    QDRANT_URL: Optional[str] = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "skillpath_knowledge"

    @property
    def cors_origins(self) -> List[str]:
        raw_items = [orig.strip() for orig in self.ALLOWED_ORIGINS.split(",") if orig.strip()]
        if self.FRONTEND_URL and self.FRONTEND_URL.strip():
            raw_items.append(self.FRONTEND_URL.strip())

        # Production deployed frontend origin must always be explicitly allowed
        production_frontend = "https://skillpath-a7ca.onrender.com"
        if production_frontend not in raw_items:
            raw_items.append(production_frontend)

        # Sanitize: strip whitespace, quotes, and trailing slashes
        cleaned: List[str] = []
        for origin in raw_items:
            clean = origin.strip().strip('"').strip("'").rstrip("/")
            if clean and clean not in cleaned:
                cleaned.append(clean)
        return cleaned

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT.lower() in ("development", "dev", "test")


settings = Settings()
