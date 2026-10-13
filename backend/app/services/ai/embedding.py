"""ProofLens AI — Gemini Embedding Service.

Provides batch vector generation using Google Gemini API (`gemini-embedding-2`)
configured with 768-dimensional Matryoshka Representation Learning (MRL).
Enforces strict input validation, dimensional integrity, finite float verification,
exponential backoff retries, and Zero Secret Exposure guardrails.
"""

import asyncio
import math
import re
from typing import List, Optional
from google import genai
from google.genai import types

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.services.ai.client import EmbeddingProviderConfigurationError, get_gemini_client


class EmbeddingError(Exception):
    """Base exception for all embedding-related errors."""
    pass


class EmbeddingInputValidationError(EmbeddingError):
    """Raised when chunk input text is empty, invalid, or malformed."""
    pass


class EmbeddingResponseValidationError(EmbeddingError):
    """Raised when provider returns invalid, malformed, or mismatched dimensional vectors."""
    pass


class EmbeddingGenerationError(EmbeddingError):
    """Raised when embedding provider API calls fail after retries or encounter fatal errors."""
    pass


def _sanitize_error_message(error: Exception, settings: Settings) -> str:
    """Sanitize error message to prevent secret key leakage in logs or exceptions."""
    msg = str(error)
    if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 4:
        msg = msg.replace(settings.GEMINI_API_KEY, "***REDACTED***")
    # Redact common key patterns like AIzaSy...
    msg = re.sub(r"AIza[0-9A-Za-z\-_]{35}", "***REDACTED***", msg)
    return msg


def validate_embedding_vector(vector: List[float], expected_dim: int) -> List[float]:
    """Validate that an embedding vector conforms to strict mathematical invariants.

    Args:
        vector: List of floating-point values from embedding provider.
        expected_dim: Expected vector dimensionality (e.g., 768).

    Returns:
        The validated vector as list of floats.

    Raises:
        EmbeddingResponseValidationError: If vector is wrong dimension, non-finite, or malformed.
    """
    if not isinstance(vector, (list, tuple)):
        raise EmbeddingResponseValidationError(
            f"Embedding response vector must be a sequence, got {type(vector).__name__}."
        )

    actual_dim = len(vector)
    if actual_dim != expected_dim:
        raise EmbeddingResponseValidationError(
            f"Vector dimension mismatch: expected {expected_dim}, received {actual_dim}."
        )

    for idx, val in enumerate(vector):
        if not isinstance(val, (int, float)):
            raise EmbeddingResponseValidationError(
                f"Vector component at index {idx} is not numeric ({type(val).__name__})."
            )
        if not math.isfinite(val):
            raise EmbeddingResponseValidationError(
                f"Vector component at index {idx} is non-finite ({val}). Non-finite vectors rejected."
            )

    return [float(v) for v in vector]


class GeminiEmbeddingService:
    """Enterprise embedding service coordinating Gemini API vector generation."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[genai.Client] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client

    @property
    def client(self) -> genai.Client:
        """Lazily initialize client with configured credentials."""
        if self._client is None:
            self._client = get_gemini_client(self.settings)
        return self._client

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate verified embeddings for a list of chunk texts.

        Processes chunks in bounded batches, enforcing strict validation, timeout,
        and exponential backoff retry behavior.

        Args:
            texts: List of non-empty text strings to embed.

        Returns:
            List of 768-dimensional float vectors matching the order of input texts.

        Raises:
            EmbeddingInputValidationError: If any text is empty or non-string.
            EmbeddingResponseValidationError: If provider response is malformed or dimension != 768.
            EmbeddingGenerationError: If provider API fails after max retries.
        """
        if not texts:
            return []

        # 1. Validate inputs
        for idx, text in enumerate(texts):
            if not isinstance(text, str):
                raise EmbeddingInputValidationError(
                    f"Chunk at index {idx} is not a string (type: {type(text).__name__})."
                )
            if not text or not text.strip():
                raise EmbeddingInputValidationError(
                    f"Chunk at index {idx} is empty or whitespace-only. Empty texts cannot be embedded."
                )

        batch_size = max(1, self.settings.GEMINI_EMBEDDING_BATCH_SIZE)
        total_chunks = len(texts)
        all_embeddings: List[List[float]] = []

        # 2. Process in bounded batches
        for batch_start in range(0, total_chunks, batch_size):
            batch = texts[batch_start : batch_start + batch_size]
            batch_embeddings = await self._embed_batch_with_retry(batch, batch_index=batch_start // batch_size)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _embed_batch_with_retry(
        self,
        batch: List[str],
        batch_index: int,
    ) -> List[List[float]]:
        """Execute single batch embedding call with exponential backoff retries."""
        max_retries = max(1, self.settings.GEMINI_MAX_RETRIES)
        timeout = float(self.settings.GEMINI_REQUEST_TIMEOUT_SECONDS)
        expected_dim = self.settings.EMBEDDING_DIMENSIONS
        model_name = self.settings.GEMINI_EMBEDDING_MODEL

        config = types.EmbedContentConfig(
            output_dimensionality=expected_dim,
        )

        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                # Call Gemini async API with timeout
                response = await asyncio.wait_for(
                    self.client.aio.models.embed_content(
                        model=model_name,
                        contents=batch,
                        config=config,
                    ),
                    timeout=timeout,
                )

                # Validate response structure
                if not response or not hasattr(response, "embeddings") or response.embeddings is None:
                    raise EmbeddingResponseValidationError(
                        f"Provider response missing 'embeddings' field for batch {batch_index}."
                    )

                embeddings_list = response.embeddings
                if len(embeddings_list) != len(batch):
                    raise EmbeddingResponseValidationError(
                        f"Provider returned {len(embeddings_list)} embeddings for batch of {len(batch)} chunks."
                    )

                validated_batch: List[List[float]] = []
                for item_idx, emb_item in enumerate(embeddings_list):
                    if not hasattr(emb_item, "values") or emb_item.values is None:
                        raise EmbeddingResponseValidationError(
                            f"Embedding at index {item_idx} missing 'values' vector."
                        )
                    vector = validate_embedding_vector(emb_item.values, expected_dim)
                    validated_batch.append(vector)

                return validated_batch

            except (EmbeddingInputValidationError, EmbeddingResponseValidationError):
                # Validation errors are non-retryable
                raise

            except asyncio.TimeoutError as exc:
                last_error = exc
                sanitized_msg = f"Gemini embedding API timed out after {timeout}s on attempt {attempt}/{max_retries}."
                logger.warning(sanitized_msg)
                if attempt < max_retries:
                    backoff = min(8.0, 1.0 * (2 ** (attempt - 1)))
                    await asyncio.sleep(backoff)

            except Exception as exc:
                last_error = exc
                sanitized_msg = _sanitize_error_message(exc, self.settings)
                logger.warning(
                    f"Gemini embedding API call failed on attempt {attempt}/{max_retries}: {sanitized_msg}"
                )
                if attempt < max_retries:
                    backoff = min(8.0, 1.0 * (2 ** (attempt - 1)))
                    await asyncio.sleep(backoff)

        # If exhausted all retries
        sanitized_final = _sanitize_error_message(last_error, self.settings) if last_error else "Unknown error"
        raise EmbeddingGenerationError(
            f"Embedding generation failed after {max_retries} attempts: {sanitized_final}"
        )


def get_embedding_service(
    settings: Optional[Settings] = None,
    client: Optional[genai.Client] = None,
) -> GeminiEmbeddingService:
    """Create and return a configured GeminiEmbeddingService instance."""
    return GeminiEmbeddingService(settings=settings, client=client)
