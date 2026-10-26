import os
import uuid
from typing import Optional, Tuple, Dict, Any
from app.core.config import settings
from app.core.logging import logger

class CloudinaryUploadError(Exception):
    """Raised when an upload to Cloudinary fails."""
    pass

class StorageService:
    """Handles persistent file uploads to Cloudinary storage."""

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
                logger.info("Cloudinary storage successfully initialized for project SkillPath AI")
            except Exception as e:
                logger.error(f"Cloudinary initialization failed: {e}")

    @property
    def is_configured(self) -> bool:
        return self._cloudinary_configured

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        folder: str = "resumes"
    ) -> Dict[str, Any]:
        """
        Uploads file to Cloudinary.
        Returns dictionary with secure_url, public_id, resource_type, bytes, format.
        Raises CloudinaryUploadError on upload failure.
        """
        if not self._cloudinary_configured:
            # Check if settings were populated after instantiation
            if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
                import cloudinary
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                    api_key=settings.CLOUDINARY_API_KEY,
                    api_secret=settings.CLOUDINARY_API_SECRET,
                    secure=True
                )
                self._cloudinary_configured = True

        if self._cloudinary_configured:
            try:
                import cloudinary.uploader
                # Sanitize filename for public_id
                base_name = os.path.splitext(filename)[0]
                clean_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_")).strip() or "file"
                unique_public_id = f"{uuid.uuid4().hex[:12]}_{clean_name}"

                try:
                    result = cloudinary.uploader.upload(
                        file_bytes,
                        resource_type="auto",
                        folder=f"skillpath/{folder}",
                        public_id=unique_public_id,
                        timeout=30
                    )
                except Exception as auto_err:
                    logger.warning(f"Cloudinary auto upload note: {auto_err}. Retrying with resource_type='raw'")
                    result = cloudinary.uploader.upload(
                        file_bytes,
                        resource_type="raw",
                        folder=f"skillpath/{folder}",
                        public_id=unique_public_id,
                        timeout=30
                    )
                secure_url = result.get("secure_url")
                public_id = result.get("public_id")
                if not secure_url or not public_id:
                    raise CloudinaryUploadError("Cloudinary upload did not return a valid secure URL or public ID")

                logger.info(f"Cloudinary upload succeeded: {public_id} -> {secure_url}")
                return {
                    "file_url": secure_url,
                    "public_id": public_id,
                    "resource_type": result.get("resource_type", "raw"),
                    "file_size": len(file_bytes),
                    "format": result.get("format", filename.split(".")[-1].lower() if "." in filename else ""),
                    "is_cloudinary": True
                }
            except Exception as e:
                logger.error(f"Cloudinary upload failed: {e}")
                raise CloudinaryUploadError(f"Failed to upload file to Cloudinary: {str(e)}")

        # If Cloudinary is strictly unconfigured, raise error rather than silent fallback
        raise CloudinaryUploadError(
            "Cloudinary storage is not configured. Please ensure CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables are set."
        )

storage_service = StorageService()

