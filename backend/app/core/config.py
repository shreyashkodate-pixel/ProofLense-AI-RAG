"""ProofLens AI — Central Application Configuration.

Implements strict startup validation via Pydantic BaseSettings, enforcing
fail-closed production security, environment-driven parameters, and Zero Secret
Exposure guardrails per AGENTS.md and TECHNICAL-DESIGN.md.
"""

from functools import lru_cache
from typing import Any, List, Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment-driven validation."""

    # --- Core Runtime ---
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = True
    PORT: int = 8000
    LOG_LEVEL: str = "info"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    # --- Database & Storage ---
    DATABASE_URL: str = ""
    DATABASE_SSL_REQUIRED: bool = False
    STORAGE_BACKEND: Literal["local", "supabase"] = "local"
    LOCAL_STORAGE_DIR: str = "./data/uploads"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "prooflens-documents"

    # --- AI Provider (Google Gemini) ---
    GEMINI_API_KEY: str = ""
    GEMINI_GENERATION_MODEL: str = "gemini-3.8-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIMENSIONS: int = 768
    GEMINI_EMBEDDING_BATCH_SIZE: int = 50
    GEMINI_REQUEST_TIMEOUT_SECONDS: int = 30
    GEMINI_MAX_RETRIES: int = 3

    # --- RAG & Retrieval Parameters ---
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K_RETRIEVAL: int = 5
    RAG_MIN_SIMILARITY_THRESHOLD: float = 0.65

    # --- Ingestion & Upload Guardrails ---
    MAX_UPLOAD_FILE_SIZE_BYTES: int = 10_485_760  # 10 MB
    MAX_UPLOAD_FILES_PER_BATCH: int = 5
    DOCUMENT_PROCESSING_TIMEOUT_SECONDS: int = 600

    # --- Application Security & Demo Passkey ---
    AUTH_ENABLED: bool = True
    DEMO_ACCESS_TOKEN: str = ""

    # --- Local In-Memory Rate Limiting (Heuristic) ---
    RATE_LIMIT_QUERIES_PER_MINUTE: int = 20
    RATE_LIMIT_UPLOADS_PER_HOUR: int = 30
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS allowed origins into a clean list."""
        if not self.CORS_ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_environment_constraints(self) -> "Settings":
        """Validate environment-specific constraints and fail-closed rules."""
        if self.ENVIRONMENT == "production":
            # 1. Access Passkey Gatekeeper Validation
            if not self.DEMO_ACCESS_TOKEN or len(self.DEMO_ACCESS_TOKEN.strip()) < 16:
                raise ValueError(
                    "In production, DEMO_ACCESS_TOKEN is required, must not be empty, "
                    "and must be at least 16 characters long."
                )

            # 2. Strict Authentication Requirement
            if not self.AUTH_ENABLED:
                raise ValueError("AUTH_ENABLED=false is strictly prohibited in production.")

            # 3. Database URL & SSL Enforcements
            if not self.DATABASE_URL or not self.DATABASE_URL.strip():
                raise ValueError("DATABASE_URL is required in production.")

            if not self.DATABASE_SSL_REQUIRED:
                raise ValueError("DATABASE_SSL_REQUIRED must be set to true in production.")

            # 4. Gemini API Key Requirement
            if not self.GEMINI_API_KEY or not self.GEMINI_API_KEY.strip():
                raise ValueError("GEMINI_API_KEY is required in production.")

            # 5. Production Storage Checks
            if self.STORAGE_BACKEND == "supabase":
                if not self.SUPABASE_URL or not self.SUPABASE_SERVICE_ROLE_KEY:
                    raise ValueError(
                        "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required when "
                        "STORAGE_BACKEND is set to 'supabase'."
                    )

            # 6. Debug disabled in production
            if self.DEBUG:
                # Override debug to false in production for safety
                self.DEBUG = False

        elif self.ENVIRONMENT == "test":
            # For tests, provide a safe dummy key if none provided
            if not self.GEMINI_API_KEY:
                self.GEMINI_API_KEY = "test-dummy-gemini-key"

        return self

    def to_safe_dict(self) -> dict[str, Any]:
        """Return configuration dictionary with all secret values redacted."""
        secret_keys = {
            "GEMINI_API_KEY",
            "DEMO_ACCESS_TOKEN",
            "SUPABASE_SERVICE_ROLE_KEY",
            "DATABASE_URL",
        }
        data = self.model_dump()
        for key in secret_keys:
            if key in data and data[key]:
                data[key] = "***REDACTED***"
        return data

    def __repr__(self) -> str:
        """Prevent secrets from leaking in string representations."""
        return f"Settings({self.to_safe_dict()})"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
