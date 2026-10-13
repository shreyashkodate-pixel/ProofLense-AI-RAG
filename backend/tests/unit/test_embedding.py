"""ProofLens AI — Unit Tests for Gemini Embedding Service.

Verifies:
1. Valid chunk texts produce 768-dimensional embeddings.
2. Empty/whitespace/non-string inputs are rejected safely.
3. Wrong dimensions, non-finite values (NaN, Inf), and malformed provider responses are rejected.
4. Provider configuration and authentication errors fail safely.
5. Rate limits, timeouts, and transient errors execute exponential backoff retries.
6. Zero Secret Exposure guardrails prevent API keys or raw document texts from leaking in errors.
"""

import asyncio
import math
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import Settings
from app.services.ai.client import EmbeddingProviderConfigurationError, get_gemini_client
from app.services.ai.embedding import (
    EmbeddingGenerationError,
    EmbeddingInputValidationError,
    EmbeddingResponseValidationError,
    GeminiEmbeddingService,
    get_embedding_service,
    validate_embedding_vector,
)


@pytest.fixture
def embedding_settings():
    return Settings(
        ENVIRONMENT="test",
        GEMINI_API_KEY="dummy-test-gemini-api-key-not-a-real-secret",
        GEMINI_EMBEDDING_MODEL="gemini-embedding-2",
        EMBEDDING_DIMENSIONS=768,
        GEMINI_EMBEDDING_BATCH_SIZE=2,
        GEMINI_REQUEST_TIMEOUT_SECONDS=5,
        GEMINI_MAX_RETRIES=3,
    )


def create_mock_embedding_item(dimension: int = 768, fill_value: float = 0.05):
    """Create a mock ContentEmbedding item with specified dimensions."""
    mock_item = MagicMock()
    mock_item.values = [fill_value] * dimension
    return mock_item


@pytest.mark.asyncio
async def test_valid_chunk_content_produces_768_dim_embedding(embedding_settings):
    """Verify valid text chunks produce verified 768-dimensional vectors."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings = [
        create_mock_embedding_item(768, 0.1),
        create_mock_embedding_item(768, 0.2),
    ]
    mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)

    service = GeminiEmbeddingService(settings=embedding_settings, client=mock_client)
    texts = [
        "First physical chunk from page 1.",
        "Second physical chunk from page 1.",
    ]

    embeddings = await service.embed_texts(texts)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 768
    assert len(embeddings[1]) == 768
    assert embeddings[0][0] == pytest.approx(0.1)
    assert embeddings[1][0] == pytest.approx(0.2)
    mock_client.aio.models.embed_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_batching_respects_batch_size_limit(embedding_settings):
    """Verify texts exceeding GEMINI_EMBEDDING_BATCH_SIZE are partitioned into bounded batches."""
    mock_client = MagicMock()
    mock_response_1 = MagicMock()
    mock_response_1.embeddings = [create_mock_embedding_item(768), create_mock_embedding_item(768)]
    mock_response_2 = MagicMock()
    mock_response_2.embeddings = [create_mock_embedding_item(768)]

    mock_client.aio.models.embed_content = AsyncMock(side_effect=[mock_response_1, mock_response_2])

    service = GeminiEmbeddingService(settings=embedding_settings, client=mock_client)
    # Batch size is 2 in embedding_settings; 3 texts should trigger 2 API calls
    texts = ["Chunk 1", "Chunk 2", "Chunk 3"]

    embeddings = await service.embed_texts(texts)

    assert len(embeddings) == 3
    assert mock_client.aio.models.embed_content.await_count == 2


@pytest.mark.asyncio
async def test_empty_list_returns_empty_list(embedding_settings):
    """Verify empty input list returns empty list without calling API."""
    mock_client = MagicMock()
    mock_client.aio.models.embed_content = AsyncMock()

    service = GeminiEmbeddingService(settings=embedding_settings, client=mock_client)
    embeddings = await service.embed_texts([])

    assert embeddings == []
    mock_client.aio.models.embed_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_or_whitespace_chunk_rejected(embedding_settings):
    """Verify empty or whitespace-only texts are rejected safely."""
    service = GeminiEmbeddingService(settings=embedding_settings)

    with pytest.raises(EmbeddingInputValidationError, match="empty or whitespace-only"):
        await service.embed_texts(["Valid chunk text", "   "])

    with pytest.raises(EmbeddingInputValidationError, match="empty or whitespace-only"):
        await service.embed_texts([""])


@pytest.mark.asyncio
async def test_non_string_chunk_rejected(embedding_settings):
    """Verify non-string inputs are rejected before provider call."""
    service = GeminiEmbeddingService(settings=embedding_settings)

    with pytest.raises(EmbeddingInputValidationError, match="not a string"):
        await service.embed_texts(["Valid text", 12345])  # type: ignore


@pytest.mark.asyncio
async def test_wrong_dimension_response_rejected(embedding_settings):
    """Verify provider returning dimensions other than 768 is rejected."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Provider mistakenly returns 512-dim or 3072-dim vector instead of requested 768
    mock_response.embeddings = [create_mock_embedding_item(512)]
    mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)

    service = GeminiEmbeddingService(settings=embedding_settings, client=mock_client)

    with pytest.raises(EmbeddingResponseValidationError, match="Vector dimension mismatch"):
        await service.embed_texts(["Sample chunk text"])


@pytest.mark.asyncio
async def test_non_finite_vector_values_rejected(embedding_settings):
    """Verify vectors containing NaN, Inf, or -Inf are rejected."""
    # Test validate_embedding_vector directly
    nan_vector = [0.1] * 767 + [float("nan")]
    with pytest.raises(EmbeddingResponseValidationError, match="non-finite"):
        validate_embedding_vector(nan_vector, 768)

    inf_vector = [0.1] * 767 + [float("inf")]
    with pytest.raises(EmbeddingResponseValidationError, match="non-finite"):
        validate_embedding_vector(inf_vector, 768)

    neg_inf_vector = [0.1] * 767 + [float("-inf")]
    with pytest.raises(EmbeddingResponseValidationError, match="non-finite"):
        validate_embedding_vector(neg_inf_vector, 768)


@pytest.mark.asyncio
async def test_malformed_response_missing_embeddings(embedding_settings):
    """Verify response missing 'embeddings' field is rejected."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings = None
    mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)

    service = GeminiEmbeddingService(settings=embedding_settings, client=mock_client)

    with pytest.raises(EmbeddingResponseValidationError, match="missing 'embeddings'"):
        await service.embed_texts(["Some text"])


@pytest.mark.asyncio
async def test_malformed_response_count_mismatch(embedding_settings):
    """Verify mismatch between batch chunk count and returned embeddings count is rejected."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Batch has 2 texts, but provider returns only 1 embedding
    mock_response.embeddings = [create_mock_embedding_item(768)]
    mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)

    service = GeminiEmbeddingService(settings=embedding_settings, client=mock_client)

    with pytest.raises(EmbeddingResponseValidationError, match="returned 1 embeddings for batch of 2"):
        await service.embed_texts(["Chunk 1", "Chunk 2"])


@pytest.mark.asyncio
async def test_rate_limit_and_transient_error_retries_and_succeeds(embedding_settings):
    """Verify service performs exponential backoff and succeeds on subsequent retry."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings = [create_mock_embedding_item(768)]

    # Attempt 1: rate limit 429, Attempt 2: success
    mock_client.aio.models.embed_content = AsyncMock(
        side_effect=[Exception("429 ResourceExhausted: rate limit exceeded"), mock_response]
    )

    service = GeminiEmbeddingService(settings=embedding_settings, client=mock_client)

    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        embeddings = await service.embed_texts(["Chunk to embed"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 768
        assert mock_client.aio.models.embed_content.await_count == 2
        mock_sleep.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_timeout_retries_and_eventually_fails(embedding_settings):
    """Verify timeouts trigger retries and raise EmbeddingGenerationError if exhausted."""
    mock_client = MagicMock()
    mock_client.aio.models.embed_content = AsyncMock(side_effect=asyncio.TimeoutError())

    service = GeminiEmbeddingService(settings=embedding_settings, client=mock_client)

    with patch("asyncio.sleep", new=AsyncMock()), \
         pytest.raises(EmbeddingGenerationError, match="failed after 3 attempts"):
        await service.embed_texts(["Chunk text"])

    assert mock_client.aio.models.embed_content.await_count == 3


@pytest.mark.asyncio
async def test_secret_zero_redaction_in_exceptions(embedding_settings):
    """Verify API keys are strictly redacted and never leaked in exception messages."""
    mock_client = MagicMock()
    secret_key = embedding_settings.GEMINI_API_KEY
    mock_client.aio.models.embed_content = AsyncMock(
        side_effect=Exception(f"Error calling https://api.google.com?key={secret_key}")
    )

    service = GeminiEmbeddingService(settings=embedding_settings, client=mock_client)

    with patch("asyncio.sleep", new=AsyncMock()), \
         pytest.raises(EmbeddingGenerationError) as exc_info:
        await service.embed_texts(["Chunk text"])

    err_str = str(exc_info.value)
    assert secret_key not in err_str
    assert "***REDACTED***" in err_str


def test_missing_api_key_in_production_raises_configuration_error():
    """Verify missing API key raises configuration error."""
    settings = Settings(
        ENVIRONMENT="development",
        GEMINI_API_KEY="",
    )
    with pytest.raises(EmbeddingProviderConfigurationError, match="GEMINI_API_KEY is missing or empty"):
        get_gemini_client(settings)
