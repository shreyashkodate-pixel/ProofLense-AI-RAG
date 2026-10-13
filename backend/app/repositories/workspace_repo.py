"""ProofLens AI — Workspace Repository.

Data access functions for managing workspace records.
"""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace


async def create_workspace(session: AsyncSession, name: str) -> Workspace:
    """Create and persist a new workspace."""
    workspace = Workspace(name=name)
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace


async def get_workspace(session: AsyncSession, workspace_id: uuid.UUID) -> Optional[Workspace]:
    """Retrieve workspace by ID."""
    query = select(Workspace).where(Workspace.id == workspace_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_workspaces(session: AsyncSession) -> List[Workspace]:
    """Retrieve all workspaces ordered by creation date descending."""
    query = select(Workspace).order_by(Workspace.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def delete_workspace(session: AsyncSession, workspace_id: uuid.UUID) -> bool:
    """Delete a workspace and cascade-delete all related records."""
    workspace = await get_workspace(session, workspace_id)
    if not workspace:
        return False
    await session.delete(workspace)
    await session.commit()
    return True
