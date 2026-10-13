"""ProofLens AI — Cross-Document Comparison Schemas.

Pydantic schemas for validating comparison requests, structured multi-document
comparison findings, verified page-level citations, and synthesis responses.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.query import CitationResponse, RetrievedEvidenceResponse


class ComparisonFindingType(str, Enum):
    """Classification taxonomy for cross-document comparison findings."""

    AGREEMENT = "agreement"
    CONTRADICTION = "contradiction"
    DIFFERENCE = "difference"
    NOT_FOUND = "not_found"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ComparisonRequest(BaseModel):
    """Request payload for executing cross-document comparison."""

    query_text: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The topic, claim, or question to compare across documents.",
        examples=["Compare the reported revenue and margin outlook between 2024 and 2025."],
    )
    document_ids: Optional[List[uuid.UUID]] = Field(
        default=None,
        max_length=5,
        description="Optional list of specific document IDs to compare (min 2, max 5). If omitted, ready documents in workspace are compared.",
    )


class PerDocumentEvidenceResponse(BaseModel):
    """Represents a specific document's stance, excerpt, and verified citations."""

    document_id: uuid.UUID = Field(..., description="Authoritative document UUID.")
    document_filename: str = Field(..., description="Document source filename.")
    statement: str = Field(..., description="Summary of this document's stance or reported fact.")
    citations: List[CitationResponse] = Field(
        default_factory=list,
        description="Verified page-level citations supporting this document's statement.",
    )


class ComparisonFindingResponse(BaseModel):
    """Represents an evidence-backed comparison finding across documents."""

    finding_type: str = Field(
        ...,
        description="Classification: 'agreement', 'contradiction', 'difference', 'not_found', or 'insufficient_evidence'.",
    )
    topic: str = Field(..., description="Specific sub-topic or metric evaluated.")
    summary: str = Field(..., description="Comparative summary explaining the relationship between sources.")
    per_document_evidence: List[PerDocumentEvidenceResponse] = Field(
        default_factory=list,
        description="Document-specific findings and supporting citations.",
    )
    citations: List[CitationResponse] = Field(
        default_factory=list,
        description="Aggregated verified citations supporting this finding.",
    )


class ComparisonResponse(BaseModel):
    """Full evidence-grounded comparison response with per-document provenance."""

    comparison_id: uuid.UUID = Field(..., description="Unique comparison run identifier.")
    workspace_id: uuid.UUID = Field(..., description="Scope workspace UUID.")
    query_text: str = Field(..., description="Original comparison query or topic.")
    document_ids: List[uuid.UUID] = Field(..., description="List of compared document UUIDs.")
    status: str = Field(..., description="Execution status: 'completed' or 'insufficient_evidence'.")
    is_abstention: bool = Field(
        ...,
        description="True if evidence was insufficient to perform a meaningful comparison.",
    )
    findings: List[ComparisonFindingResponse] = Field(
        default_factory=list,
        description="List of verified comparative findings.",
    )
    synthesis: str = Field(..., description="Narrative synthesis comparing the documents.")
    limitations: Optional[str] = Field(
        default=None,
        description="Explanatory notes on differing scopes, timeframes, definitions, or unretrieved aspects.",
    )
    retrieved_evidence: List[RetrievedEvidenceResponse] = Field(
        default_factory=list,
        description="All candidate evidence passages retrieved from PostgreSQL for this comparison.",
    )
    created_at: datetime = Field(..., description="UTC creation timestamp.")


class SavedComparisonResponse(BaseModel):
    """Saved historical comparison run retrieved from a workspace session."""

    model_config = ConfigDict(from_attributes=True)

    comparison_id: uuid.UUID = Field(..., description="Unique comparison execution UUID")
    workspace_id: uuid.UUID = Field(..., description="Owning workspace UUID")
    query_text: str = Field(..., description="Topic or comparison question")
    status: str = Field(..., description="Execution status: completed or insufficient_evidence")
    is_abstention: bool = Field(..., description="Whether comparison abstained")
    top_score: Optional[float] = Field(None, description="Top evidence similarity score")
    synthesis: str = Field(..., description="Narrative synthesis comparing documents")
    citations: List[CitationResponse] = Field(
        default_factory=list,
        description="List of verified citations supporting this comparison",
    )
    retrieved_evidence: List[RetrievedEvidenceResponse] = Field(
        default_factory=list,
        description="List of retrieved evidence chunks",
    )
    created_at: datetime = Field(..., description="UTC creation timestamp")
