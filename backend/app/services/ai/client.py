"""ProofLens AI — Gemini Client Factory.

Provides a configured Google GenAI SDK Client adhering to Zero Secret Exposure
guardrails and fail-closed validation per AGENTS.md.
"""

from typing import Optional
from google import genai

from app.core.config import Settings, get_settings


class EmbeddingProviderConfigurationError(RuntimeError):
    """Raised when the embedding provider is improperly configured or missing credentials."""
    pass


def get_gemini_client(settings: Optional[Settings] = None) -> genai.Client:
    """Instantiate and return a Google GenAI Client with configured credentials.

    Args:
        settings: Application settings. If None, retrieves singleton via get_settings().

    Returns:
        Configured genai.Client instance.

    Raises:
        EmbeddingProviderConfigurationError: If GEMINI_API_KEY is not set or empty.
    """
    settings = settings or get_settings()

    api_key = settings.GEMINI_API_KEY
    if not api_key or not api_key.strip():
        if settings.ENVIRONMENT == "test":
            api_key = "test-dummy-gemini-key"
        else:
            raise EmbeddingProviderConfigurationError(
                "GEMINI_API_KEY is missing or empty. Please set GEMINI_API_KEY in environment."
            )

    return genai.Client(api_key=api_key)
