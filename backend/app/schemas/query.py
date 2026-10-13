"""ProofLens AI — Query, Answer, Evidence, and Citation Schemas.

Defines Pydantic request and response models for workspace-scoped grounded Q&A,
server-validated citations, and candidate evidence inspection.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """Incoming request payload for a grounded Q&A query."""

    query_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural-language question to be answered using workspace documents.",
        examples=["What is the total revenue reported in the Q3 financial statement?"],
    )
    top_k: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="Optional limit on the number of candidate chunks to retrieve. Defaults to server setting.",
    )


class CitationResponse(BaseModel):
    """Server-authoritative verified citation linked to an answer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique citation UUID")
    chunk_id: Optional[uuid.UUID] = Field(
        None,
        description="UUID of the supporting chunk, or None if the underlying chunk has been tombstoned.",
    )
    document_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of the parent document, or None if the underlying chunk/document has been tombstoned.",
    )
    document_filename: str = Field(..., description="Authoritative document filename from PostgreSQL")
    page_number: int = Field(..., description="Physical page number from PostgreSQL")
    quoted_snippet: str = Field(..., description="Exact supporting text snippet")


class RetrievedEvidenceResponse(BaseModel):
    """Retrieved candidate evidence chunk for auditability and transparency."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID = Field(..., description="Candidate chunk UUID")
    document_id: uuid.UUID = Field(..., description="Parent document UUID")
    document_filename: str = Field(..., description="Authoritative document filename")
    page_number: int = Field(..., description="Physical page number")
    snippet: str = Field(..., description="Excerpt of the chunk text")
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    rank: int = Field(..., description="Retrieval ranking order (1-indexed)")


class QueryResponse(BaseModel):
    """Full grounded Q&A execution result with server-authoritative citations."""

    model_config = ConfigDict(from_attributes=True)

    query_run_id: uuid.UUID = Field(..., description="Unique query run execution UUID")
    workspace_id: uuid.UUID = Field(..., description="Owning workspace UUID")
    query_text: str = Field(..., description="Original user question")
    status: str = Field(..., description="Execution status: completed or failed")
    answer_text: str = Field(..., description="Synthesized grounded answer")
    is_abstention: bool = Field(
        ...,
        description="True if the system abstained due to insufficient, missing, or contradictory evidence.",
    )
    top_score: Optional[float] = Field(
        None,
        description="Cosine similarity score of the top-ranked retrieved passage.",
    )
    citations: List[CitationResponse] = Field(
        default_factory=list,
        description="List of verified, server-authoritative citations backing the answer.",
    )
    retrieved_evidence: List[RetrievedEvidenceResponse] = Field(
        default_factory=list,
        description="List of candidate chunks retrieved for this query.",
    )
    created_at: datetime = Field(..., description="Timestamp when the query run was created")
