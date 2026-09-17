"""
services/storage_service.py
Handles file validation, MIME verification, path generation, and Supabase Storage uploads.
"""
import os
import uuid
import logging
from typing import Tuple
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from config import Config
from services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

# Magic byte signatures for secure MIME validation
MIME_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",
    b"%PDF": "application/pdf"
}


class StorageService:
    """Provides methods for managing uploads to Supabase Storage."""

    @staticmethod
    def _validate_file_content(file_obj: FileStorage, allowed_types: set[str]) -> Tuple[bool, str]:
        """Sniffs initial file header bytes to confirm authentic MIME identity."""
        file_obj.seek(0)
        header = file_obj.read(16)
        file_obj.seek(0)

        detected_mime = None
        for sig, mime in MIME_SIGNATURES.items():
            if header.startswith(sig):
                detected_mime = mime
                break

        if not detected_mime or detected_mime not in allowed_types:
            return False, f"File format validation failed. Detected MIME: {detected_mime}"
        return True, detected_mime

    @classmethod
    def upload_identity_document(cls, user_id: str, file: FileStorage) -> Tuple[bool, str]:
        """
        Uploads landlord KYC proof into the private 'identity-documents' bucket.
        Path format: landlords/{user_id}/{unique_filename}
        """
        allowed_mimes = {"image/jpeg", "image/png", "application/pdf"}
        valid, msg_or_mime = cls._validate_file_content(file, allowed_mimes)
        if not valid:
            return False, msg_or_mime

        ext = secure_filename(file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in Config.ALLOWED_DOCUMENT_EXTENSIONS:
            return False, f"Extension .{ext} is not allowed for identity documents."

        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        storage_path = f"landlords/{user_id}/{unique_filename}"

        try:
            service = get_service_client()
            file.seek(0)
            file_bytes = file.read()
            service.storage.from_(Config.STORAGE_BUCKET_IDENTITY_DOCS).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": msg_or_mime, "x-upsert": "true"}
            )
            return True, storage_path
        except Exception as exc:
            logger.error(f"Failed identity document upload: {exc}")
            return False, str(exc)

    @classmethod
    def upload_property_media(cls, property_id: str, file: FileStorage, category: str = "front") -> Tuple[bool, str]:
        """
        Uploads property or room photos to the public 'property-media' bucket.
        Path format: properties/{property_id}/{category}/{unique_filename}
        """
        allowed_mimes = {"image/jpeg", "image/png", "image/webp"}
        valid, msg_or_mime = cls._validate_file_content(file, allowed_mimes)
        if not valid:
            return False, msg_or_mime

        ext = secure_filename(file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in Config.ALLOWED_IMAGE_EXTENSIONS:
            return False, f"Extension .{ext} is not permitted for images."

        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        storage_path = f"properties/{property_id}/{category}/{unique_filename}"

        try:
            service = get_service_client()
            file.seek(0)
            file_bytes = file.read()
            service.storage.from_(Config.STORAGE_BUCKET_PROPERTY_MEDIA).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": msg_or_mime, "x-upsert": "true"}
            )
            return True, storage_path
        except Exception as exc:
            logger.error(f"Failed property media upload: {exc}")
            return False, str(exc)

    @staticmethod
    def generate_signed_url(bucket_name: str, path: str, expires_in_seconds: int = 900) -> str | None:
        """
        Generates a secure, temporary signed URL for viewing private files.
        Default expiration is 15 minutes.
        """
        try:
            service = get_service_client()
            res = service.storage.from_(bucket_name).create_signed_url(path, expires_in_seconds)
            if isinstance(res, dict) and "signedURL" in res:
                return res["signedURL"]
            elif hasattr(res, "signed_url"):
                return res.signed_url
            return str(res)
        except Exception as exc:
            logger.error(f"Signed URL generation failed for {path}: {exc}")
            return None