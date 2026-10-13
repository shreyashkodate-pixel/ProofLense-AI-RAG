"""ProofLens AI — Document Pydantic Schemas.

Defines schemas for document responses, upload summaries, and lifecycle state tracking.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Public representation of an ingested document."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique document UUID")
    workspace_id: uuid.UUID = Field(..., description="Owning workspace UUID")
    filename: str = Field(..., description="Original filename of the uploaded PDF")
    content_hash: str = Field(..., description="SHA-256 hash of the document content")
    file_size_bytes: int = Field(..., description="File size in bytes")
    page_count: Optional[int] = Field(None, description="Extracted physical page count")
    status: str = Field(..., description="Ingestion state: pending, processing, ready, failed")
    error_message: Optional[str] = Field(None, description="Error diagnostics if failed")
    processing_attempts: int = Field(..., description="Number of worker processing attempts")
    processing_started_at: Optional[datetime] = Field(None, description="Timestamp when current processing started")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UploadBatchResponse(BaseModel):
    """Response returned upon completing a multi-file batch upload."""

    uploaded: List[DocumentResponse] = Field(..., description="List of successfully uploaded documents")
    total_uploaded: int = Field(..., description="Total count of successfully uploaded documents")


class DocumentChunkDetailResponse(BaseModel):
    """Detailed representation of an extracted document chunk with provenance."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique chunk UUID")
    document_id: uuid.UUID = Field(..., description="Parent document UUID")
    page_id: uuid.UUID = Field(..., description="Parent page UUID")
    chunk_index: int = Field(..., description="Sequential chunk index (0-indexed)")
    chunk_text: str = Field(..., description="Chunk text content")
    token_count: Optional[int] = Field(None, description="Heuristic token count")
    page_number: Optional[int] = Field(None, description="1-indexed physical page number")


class DocumentPageDetailResponse(BaseModel):
    """Detailed representation of an extracted document page and its chunks."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique page UUID")
    document_id: uuid.UUID = Field(..., description="Parent document UUID")
    page_number: int = Field(..., description="1-indexed physical page number")
    raw_text: str = Field(..., description="Full extracted raw text of the page")
    char_count: int = Field(..., description="Character count of raw page text")
    chunks: List[DocumentChunkDetailResponse] = Field(
        default_factory=list,
        description="List of chunks bounded to this page",
    )


class DocumentPagesResponse(BaseModel):
    """Collection response of all extracted pages and chunks for a document."""

    document_id: uuid.UUID = Field(..., description="Parent document UUID")
    workspace_id: uuid.UUID = Field(..., description="Owning workspace UUID")
    total_pages: int = Field(..., description="Total extracted pages count")
    pages: List[DocumentPageDetailResponse] = Field(
        default_factory=list,
        description="Extracted pages sorted in ascending order",
    )
