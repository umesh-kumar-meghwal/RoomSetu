"""
config.py
Application configuration loader with environment variable validation.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("CRITICAL SECURITY FAULT: FLASK_SECRET_KEY is not defined in environment.")

    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"
    TESTING = False
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")

    # Supabase Infrastructure Credentials
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Anon key
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not all([SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY]):
        raise ValueError(
            "SUPABASE MISCONFIGURATION: SUPABASE_URL, SUPABASE_KEY, and "
            "SUPABASE_SERVICE_ROLE_KEY must all be specified."
        )

    # Storage Bucket Names
    STORAGE_BUCKET_PROPERTY_MEDIA = os.getenv("STORAGE_BUCKET_PROPERTY_MEDIA", "property-media")
    STORAGE_BUCKET_IDENTITY_DOCS = os.getenv("STORAGE_BUCKET_IDENTITY_DOCS", "identity-documents")
    STORAGE_BUCKET_PROFILE_MEDIA = os.getenv("STORAGE_BUCKET_PROFILE_MEDIA", "profile-media")

    # Security & Cookie Attributes
    SESSION_COOKIE_NAME = "roomsetu_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = FLASK_ENV == "production"
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 Days

    # Uploads & Payload Bounds
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # 10 MB
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    ALLOWED_DOCUMENT_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}

    # Geolocation Bounds
    DEFAULT_SEARCH_RADIUS_KM = float(os.getenv("DEFAULT_SEARCH_RADIUS_KM", 5.0))
    MAX_SEARCH_RADIUS_KM = float(os.getenv("MAX_SEARCH_RADIUS_KM", 25.0))


class TestConfig(Config):
    """Test-specific overrides."""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False