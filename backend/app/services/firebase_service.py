import os
import uuid
from typing import Optional, Tuple
from app.core.config import settings
from app.core.logging import logger

class StorageService:
    """Handles file uploads to Cloudinary or local static fallback directory."""

    def __init__(self):
        self._cloudinary_configured = False
        if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
            try:
                import cloudinary
                import cloudinary.uploader
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                    api_key=settings.CLOUDINARY_API_KEY,
                    api_secret=settings.CLOUDINARY_API_SECRET,
                    secure=True
                )
                self._cloudinary_configured = True
                logger.info("Cloudinary storage successfully initialized")
            except Exception as e:
                logger.warning(f"Cloudinary initialization failed: {e}")

    def upload_file(self, file_bytes: bytes, filename: str, folder: str = "resumes") -> Tuple[str, str]:
        """
        Uploads file to Cloudinary or saves locally.
        Returns: (file_url, public_id)
        """
        public_id = f"{folder}/{uuid.uuid4()}_{filename}"

        if self._cloudinary_configured:
            try:
                import cloudinary.uploader
                result = cloudinary.uploader.upload(
                    file_bytes,
                    resource_type="auto",
                    folder=f"skillpath/{folder}",
                    public_id=f"{uuid.uuid4()}_{filename}",
                )
                return result.get("secure_url"), result.get("public_id")
            except Exception as e:
                logger.error(f"Cloudinary upload failed: {e}. Falling back to local storage.")

        # Local storage fallback
        local_dir = os.path.join(os.getcwd(), "uploads", folder)
        os.makedirs(local_dir, exist_ok=True)
        local_filename = f"{uuid.uuid4()}_{filename}"
        local_path = os.path.join(local_dir, local_filename)
        with open(local_path, "wb") as f:
            f.write(file_bytes)

        file_url = f"/uploads/{folder}/{local_filename}"
        return file_url, local_filename

storage_service = StorageService()
