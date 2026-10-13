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
