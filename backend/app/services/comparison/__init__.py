"""ProofLens AI — Cross-Document Comparison Package."""

from app.services.comparison.comparator import (
    ComparisonError,
    ComparisonInputValidationError,
    ComparisonPipelineError,
    ComparisonResult,
    CrossDocumentComparator,
    DocumentNotFoundError,
    DocumentNotReadyError,
    InsufficientDocumentsError,
    WorkspaceNotFoundError,
    get_cross_document_comparator,
)

__all__ = [
    "ComparisonError",
    "ComparisonInputValidationError",
    "ComparisonPipelineError",
    "ComparisonResult",
    "CrossDocumentComparator",
    "DocumentNotFoundError",
    "DocumentNotReadyError",
    "InsufficientDocumentsError",
    "WorkspaceNotFoundError",
    "get_cross_document_comparator",
]
