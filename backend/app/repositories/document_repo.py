"""ProofLens AI — Document Repository.

Data access functions for documents enforcing strict workspace scoping,
atomic worker claims, duplicate hash detection, and safe row locking.
"""

import inspect
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.page import DocumentPage
from app.services.parsing.chunker import ChunkData
from app.services.parsing.pdf_parser import ParsedPage


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


async def persist_extracted_pages_and_chunks(
    session: AsyncSession,
    document_id: uuid.UUID,
    pages: List[ParsedPage],
    chunks: List[ChunkData],
    mark_ready: bool = False,
) -> Tuple[List[DocumentPage], List[DocumentChunk]]:
    """Persist extracted physical pages and bounded chunks in a single transaction.

    Guarantees idempotency on retry: cleans up any pre-existing pages/chunks
    associated with this document before inserting fresh records.
    """
    # 1. Clean up existing chunks and pages (idempotency on retry)
    await session.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    await session.execute(
        delete(DocumentPage).where(DocumentPage.document_id == document_id)
    )

    # 2. Persist DocumentPage records
    page_id_map: dict[int, uuid.UUID] = {}
    created_pages: List[DocumentPage] = []

    for page_data in pages:
        page_id = uuid.uuid4()
        page_id_map[page_data.page_number] = page_id
        page_record = DocumentPage(
            id=page_id,
            document_id=document_id,
            page_number=page_data.page_number,
            raw_text=page_data.raw_text,
            char_count=page_data.char_count,
        )
        session.add(page_record)
        created_pages.append(page_record)

    # 3. Persist DocumentChunk records (embedding is initially None pending Phase 5)
    created_chunks: List[DocumentChunk] = []
    for chunk_data in chunks:
        page_id = page_id_map.get(chunk_data.page_number)
        if not page_id:
            continue
        chunk_record = DocumentChunk(
            id=uuid.uuid4(),
            document_id=document_id,
            page_id=page_id,
            chunk_index=chunk_data.chunk_index,
            chunk_text=chunk_data.chunk_text,
            embedding=None,
            embedding_model="gemini-embedding-2",
            token_count=chunk_data.token_count,
        )
        session.add(chunk_record)
        created_chunks.append(chunk_record)

    # 4. Update Document page_count (and status if explicitly requested)
    update_values: dict = {
        "page_count": len(pages),
        "error_message": None,
    }
    if mark_ready:
        update_values["status"] = "ready"

    await session.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(**update_values)
    )

    await session.commit()
    return created_pages, created_chunks


async def _extract_scalars_list(result) -> list:
    """Safely extract scalar results from SQLAlchemy Result, handling mock coroutines gracefully."""
    if not hasattr(result, "scalars"):
        return []
    scalars_res = result.scalars()
    if inspect.iscoroutine(scalars_res):
        scalars_res = await scalars_res
    if not hasattr(scalars_res, "all"):
        return []
    items = scalars_res.all()
    if inspect.iscoroutine(items):
        items = await items
    return list(items)


async def get_unembedded_chunks(
    session: AsyncSession,
    document_id: uuid.UUID,
) -> List[DocumentChunk]:
    """Retrieve all chunks for a document that are missing embeddings.

    Orders results strictly by chunk_index ascending to preserve document sequence.
    """
    stmt = (
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.embedding.is_(None),
        )
        .order_by(DocumentChunk.chunk_index.asc())
    )
    result = await session.execute(stmt)
    return await _extract_scalars_list(result)



async def update_chunk_embeddings(
    session: AsyncSession,
    chunk_embeddings: List[Tuple[uuid.UUID, List[float], str]],
) -> int:
    """Persist validated vector embeddings to document chunks.

    Args:
        session: Async database session.
        chunk_embeddings: List of tuples (chunk_id, embedding_vector, model_name).

    Returns:
        Number of updated chunk records.
    """
    if not chunk_embeddings:
        return 0

    for chunk_id, embedding_vector, model_name in chunk_embeddings:
        await session.execute(
            update(DocumentChunk)
            .where(DocumentChunk.id == chunk_id)
            .values(
                embedding=embedding_vector,
                embedding_model=model_name,
            )
        )
    await session.commit()
    return len(chunk_embeddings)


async def mark_document_ready(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> None:
    """Transition a document to 'ready' status once embeddings are fully persisted."""
    await session.execute(
        update(Document)
        .where(
            Document.id == doc_id,
            Document.workspace_id == workspace_id,
        )
        .values(
            status="ready",
            error_message=None,
        )
    )
    await session.commit()


async def mark_document_failed(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    doc_id: uuid.UUID,
    error_message: str,
) -> None:
    """Mark a document as failed with an explanatory error message."""
    await session.execute(
        update(Document)
        .where(
            Document.id == doc_id,
            Document.workspace_id == workspace_id,
        )
        .values(
            status="failed",
            error_message=error_message,
        )
    )
    await session.commit()



async def get_document_pages(
    session: AsyncSession,
    document_id: uuid.UUID,
) -> List[DocumentPage]:
    """Retrieve all pages for a document ordered by page_number ascending."""
    stmt = (
        select(DocumentPage)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number.asc())
    )
    result = await session.execute(stmt)
    return await _extract_scalars_list(result)


async def get_document_chunks(
    session: AsyncSession,
    document_id: uuid.UUID,
) -> List[DocumentChunk]:
    """Retrieve all chunks for a document ordered by chunk_index ascending."""
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    result = await session.execute(stmt)
    return await _extract_scalars_list(result)
