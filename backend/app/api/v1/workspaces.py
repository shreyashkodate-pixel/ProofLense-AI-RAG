"""ProofLens AI — Workspaces API Router.

Provides CRUD endpoints for creating, retrieving, and deleting isolated workspaces.
Protected by the Application-Level Access Passkey Gatekeeper.
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_access_passkey
from app.repositories import workspace_repo
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter(
    prefix="/workspaces",
    tags=["Workspaces"],
    dependencies=[Depends(verify_access_passkey)],
)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
async def create_workspace_endpoint(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new workspace for uploading documents and running grounded queries."""
    workspace = await workspace_repo.create_workspace(db, name=payload.name)
    return workspace


@router.get(
    "",
    response_model=List[WorkspaceResponse],
    summary="List all workspaces",
)
async def list_workspaces_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all available workspaces."""
    return await workspace_repo.list_workspaces(db)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get workspace details by ID",
)
async def get_workspace_endpoint(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific workspace."""
    workspace = await workspace_repo.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Workspace '{workspace_id}' not found.",
                "details": {"workspace_id": str(workspace_id)},
            },
        )
    return workspace


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace",
)
async def delete_workspace_endpoint(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete workspace and cascade-delete all contained documents, pages, and chunks."""
    deleted = await workspace_repo.delete_workspace(db, workspace_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Workspace '{workspace_id}' not found.",
                "details": {"workspace_id": str(workspace_id)},
            },
        )
    return None
