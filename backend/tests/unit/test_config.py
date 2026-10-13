"""ProofLens AI — Unit Tests for Configuration & Security Rules.

Validates fail-closed production constraints, default parameters, CORS parsing,
and zero secret exposure in logs/representations.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_development_settings():
    """Verify default development configuration matches PRD and Technical Design."""
    settings = Settings(ENVIRONMENT="development")

    assert settings.ENVIRONMENT == "development"
    assert settings.GEMINI_GENERATION_MODEL == "gemini-3.8-flash"
    assert settings.GEMINI_EMBEDDING_MODEL == "gemini-embedding-2"
    assert settings.EMBEDDING_DIMENSIONS == 768
    assert settings.RAG_MIN_SIMILARITY_THRESHOLD == 0.65
    assert settings.DOCUMENT_PROCESSING_TIMEOUT_SECONDS == 600
    assert settings.RATE_LIMIT_QUERIES_PER_MINUTE == 20
    assert settings.RATE_LIMIT_UPLOADS_PER_HOUR == 30
    assert settings.RATE_LIMIT_REQUESTS_PER_MINUTE == 120


def test_cors_origins_parsing():
    """Verify comma-separated origins are parsed into a normalized list."""
    settings = Settings(
        ENVIRONMENT="development",
        CORS_ALLOWED_ORIGINS="http://localhost:3000, https://demo.prooflens.ai , http://127.0.0.1:3000",
    )
    assert settings.cors_origins_list == [
        "http://localhost:3000",
        "https://demo.prooflens.ai",
        "http://127.0.0.1:3000",
    ]

    empty_settings = Settings(ENVIRONMENT="development", CORS_ALLOWED_ORIGINS="")
    assert empty_settings.cors_origins_list == []


def test_production_fails_without_demo_access_token():
    """Verify production fails closed if DEMO_ACCESS_TOKEN is missing or too short."""
    # Missing token
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEMO_ACCESS_TOKEN="",
            DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db",
            DATABASE_SSL_REQUIRED=True,
            GEMINI_API_KEY="AIzaSyDummyProductionApiKeyLong123",
        )
    assert "DEMO_ACCESS_TOKEN is required" in str(exc_info.value)

    # Token too short (< 16 chars)
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEMO_ACCESS_TOKEN="short-token-123",
            DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db",
            DATABASE_SSL_REQUIRED=True,
            GEMINI_API_KEY="AIzaSyDummyProductionApiKeyLong123",
        )
    assert "at least 16 characters long" in str(exc_info.value)


def test_production_fails_if_auth_disabled():
    """Verify AUTH_ENABLED=false is strictly rejected in production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEMO_ACCESS_TOKEN="valid-production-passkey-123456",
            AUTH_ENABLED=False,
            DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db",
            DATABASE_SSL_REQUIRED=True,
            GEMINI_API_KEY="AIzaSyDummyProductionApiKeyLong123",
        )
    assert "AUTH_ENABLED=false is strictly prohibited in production" in str(exc_info.value)


def test_production_fails_without_database_ssl():
    """Verify DATABASE_SSL_REQUIRED=false is rejected in production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEMO_ACCESS_TOKEN="valid-production-passkey-123456",
            AUTH_ENABLED=True,
            DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db",
            DATABASE_SSL_REQUIRED=False,
            GEMINI_API_KEY="AIzaSyDummyProductionApiKeyLong123",
        )
    assert "DATABASE_SSL_REQUIRED must be set to true in production" in str(exc_info.value)


def test_production_fails_without_gemini_api_key():
    """Verify GEMINI_API_KEY is required in production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEMO_ACCESS_TOKEN="valid-production-passkey-123456",
            AUTH_ENABLED=True,
            DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db",
            DATABASE_SSL_REQUIRED=True,
            GEMINI_API_KEY="",
        )
    assert "GEMINI_API_KEY is required in production" in str(exc_info.value)


def test_valid_production_configuration():
    """Verify valid production settings initialize cleanly with debug disabled."""
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=True,  # Should be forced to False for production safety
        DEMO_ACCESS_TOKEN="valid-production-passkey-123456",
        AUTH_ENABLED=True,
        DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db",
        DATABASE_SSL_REQUIRED=True,
        GEMINI_API_KEY="AIzaSyDummyProductionApiKeyLong123",
    )
    assert settings.ENVIRONMENT == "production"
    assert settings.DEBUG is False
    assert settings.AUTH_ENABLED is True


def test_secrets_redaction_and_repr_safety():
    """Verify secrets are redacted in dictionary export and string representation."""
    settings = Settings(
        ENVIRONMENT="development",
        DEMO_ACCESS_TOKEN="secret-passkey-never-leak",
        GEMINI_API_KEY="secret-gemini-key-never-leak",
        DATABASE_URL="postgresql+asyncpg://user:secretpass@host:5432/db",
        SUPABASE_SERVICE_ROLE_KEY="secret-supabase-key-never-leak",
    )

    safe_dict = settings.to_safe_dict()
    assert safe_dict["DEMO_ACCESS_TOKEN"] == "***REDACTED***"
    assert safe_dict["GEMINI_API_KEY"] == "***REDACTED***"
    assert safe_dict["DATABASE_URL"] == "***REDACTED***"
    assert safe_dict["SUPABASE_SERVICE_ROLE_KEY"] == "***REDACTED***"

    # Verify __repr__ does not reveal raw secrets
    repr_str = repr(settings)
    assert "secret-passkey-never-leak" not in repr_str
    assert "secret-gemini-key-never-leak" not in repr_str
    assert "secretpass" not in repr_str
    assert "***REDACTED***" in repr_str
