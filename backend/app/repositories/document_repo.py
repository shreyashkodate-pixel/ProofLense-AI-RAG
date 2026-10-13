"""ProofLens AI — Document Repository.

Data access functions for documents enforcing strict workspace scoping,
atomic worker claims, duplicate hash detection, and safe row locking.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


async def create_document(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    filename: str,
    content_hash: str,
    file_size_bytes: int,
    storage_path: str,
    status: str = "pending",
) -> Document:
    """Create and persist a new document within a workspace."""
    document = Document(
        workspace_id=workspace_id,
        filename=filename,
        content_hash=content_hash,
        file_size_bytes=file_size_bytes,
        storage_path=storage_path,
        status=status,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def get_document_by_id(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> Optional[Document]:
    """Retrieve document strictly scoped to the workspace ID.

    Guarantees cross-workspace isolation: querying with a mismatched workspace ID
    returns None, preventing identifier-enumeration attacks.
    """
    query = select(Document).where(
        Document.id == doc_id,
        Document.workspace_id == workspace_id,
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_document_by_hash(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    content_hash: str,
) -> Optional[Document]:
    """Check for existing duplicate document in the workspace by SHA-256 hash."""
    query = select(Document).where(
        Document.workspace_id == workspace_id,
        Document.content_hash == content_hash,
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_documents(
    session: AsyncSession,
    workspace_id: uuid.UUID,
) -> List[Document]:
    """List all documents belonging to a workspace ordered by creation date descending."""
    query = (
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def lock_document_for_deletion(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> Optional[Document]:
    """Lock the document row with SELECT ... FOR UPDATE to avoid concurrent deletion races."""
    query = (
        select(Document)
        .where(
            Document.id == doc_id,
            Document.workspace_id == workspace_id,
        )
        .with_for_update()
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def delete_document(
    session: AsyncSession,
    document: Document,
) -> None:
    """Delete document row, triggering ON DELETE CASCADE on child pages/chunks."""
    await session.delete(document)
    await session.commit()


async def atomic_claim_worker(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> Optional[Document]:
    """Atomically claim a document for background processing.

    Executes a single conditional update. If another worker already claimed the job
    (status is not 'pending' or 'failed'), returns None immediately.
    """
    stmt = (
        update(Document)
        .where(
            Document.id == doc_id,
            Document.workspace_id == workspace_id,
            Document.status.in_(["pending", "failed"]),
        )
        .values(
            status="processing",
            processing_started_at=datetime.now(timezone.utc),
            processing_attempts=Document.processing_attempts + 1,
            error_message=None,
        )
        .returning(Document)
    )
    result = await session.execute(stmt)
    claimed_doc = result.scalar_one_or_none()
    if claimed_doc:
        await session.commit()
        await session.refresh(claimed_doc)
    return claimed_doc
