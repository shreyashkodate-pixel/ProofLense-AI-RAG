"""ProofLens AI Schemas Package."""

from app.schemas.comparison import (
    ComparisonFindingResponse,
    ComparisonFindingType,
    ComparisonRequest,
    ComparisonResponse,
    PerDocumentEvidenceResponse,
)
from app.schemas.document import DocumentResponse, UploadBatchResponse
from app.schemas.query import (
    CitationResponse,
    QueryRequest,
    QueryResponse,
    RetrievedEvidenceResponse,
)
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse

__all__ = [
    "WorkspaceCreate",
    "WorkspaceResponse",
    "DocumentResponse",
    "UploadBatchResponse",
    "QueryRequest",
    "QueryResponse",
    "CitationResponse",
    "RetrievedEvidenceResponse",
    "ComparisonFindingType",
    "ComparisonRequest",
    "ComparisonResponse",
    "ComparisonFindingResponse",
    "PerDocumentEvidenceResponse",
]
