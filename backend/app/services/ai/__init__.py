"""ProofLens AI — AI, Generation, and Embedding Services."""

from app.services.ai.client import EmbeddingProviderConfigurationError, get_gemini_client
from app.services.ai.embedding import (
    EmbeddingError,
    EmbeddingGenerationError,
    EmbeddingInputValidationError,
    EmbeddingResponseValidationError,
    GeminiEmbeddingService,
    get_embedding_service,
)
from app.services.ai.generator import (
    GeneratedAnswer,
    GeneratedCitation,
    GeneratedComparisonFinding,
    GeneratedComparisonResult,
    GeneratedFindingCitation,
    GeneratedPerDocumentFinding,
    GenerationError,
    GenerationInputValidationError,
    GenerationResponseValidationError,
    GenerationServiceError,
    GeminiGeneratorService,
    get_gemini_generator,
)

__all__ = [
    "EmbeddingProviderConfigurationError",
    "get_gemini_client",
    "EmbeddingError",
    "EmbeddingInputValidationError",
    "EmbeddingResponseValidationError",
    "EmbeddingGenerationError",
    "GeminiEmbeddingService",
    "get_embedding_service",
    "GeneratedCitation",
    "GeneratedAnswer",
    "GeneratedFindingCitation",
    "GeneratedPerDocumentFinding",
    "GeneratedComparisonFinding",
    "GeneratedComparisonResult",
    "GenerationError",
    "GenerationInputValidationError",
    "GenerationResponseValidationError",
    "GenerationServiceError",
    "GeminiGeneratorService",
    "get_gemini_generator",
]
