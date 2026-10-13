"""ProofLens AI — Workspace Pydantic Schemas.

Defines input/output schemas for workspace creation, retrieval, and listing.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    """Payload for creating a new workspace."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User-friendly name of the workspace",
        examples=["Q3 Financial Analysis"],
    )


class WorkspaceResponse(BaseModel):
    """Public representation of a workspace."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique workspace UUID")
    name: str = Field(..., description="Workspace name")
    created_at: datetime = Field(..., description="Timestamp of creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")
