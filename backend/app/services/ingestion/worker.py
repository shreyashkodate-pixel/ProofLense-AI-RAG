"""ProofLens AI — Document Ingestion Worker.

Coordinates the end-to-end ingestion lifecycle:
1. Atomic worker claiming (pending/failed -> processing).
2. Physical file retrieval from storage.
3. Page-by-page text extraction with pypdf and scanned/zero-text detection.
4. Bounded page-aware text chunking.
5. Atomic database persistence of DocumentPage and DocumentChunk records.
6. Error capture and transition to 'failed' with actionable messages.
"""

import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session_factory
from app.core.logging import logger
from app.repositories import document_repo
from app.services.parsing.chunker import chunk_document_pages
from app.services.parsing.pdf_parser import PDFParsingError, extract_pdf_pages
from app.services.storage.base import BaseStorageService
from app.services.storage.factory import get_storage_service


async def run_ingestion_pipeline(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID,
    session: Optional[AsyncSession] = None,
    storage: Optional[BaseStorageService] = None,
    settings: Optional[Settings] = None,
) -> bool:
    """Execute complete ingestion pipeline for a single document.

    Args:
        document_id: UUID of the document to process.
        workspace_id: UUID of the owning workspace.
        session: Optional existing AsyncSession (acquired from factory if None).
        storage: Optional BaseStorageService (acquired from factory if None).
        settings: Optional Settings (acquired from get_settings if None).

    Returns:
        True if ingestion succeeded and document is 'ready', False if failed.
    """
    settings = settings or get_settings()
    storage = storage or get_storage_service()

    if session is None:
        session_factory = get_session_factory()
        async with session_factory() as owned_session:
            return await _execute_pipeline_core(
                document_id=document_id,
                workspace_id=workspace_id,
                session=owned_session,
                storage=storage,
                settings=settings,
            )
    else:
        return await _execute_pipeline_core(
            document_id=document_id,
            workspace_id=workspace_id,
            session=session,
            storage=storage,
            settings=settings,
        )


async def _execute_pipeline_core(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID,
    session: AsyncSession,
    storage: BaseStorageService,
    settings: Settings,
) -> bool:
    """Internal implementation executing ingestion pipeline steps with provided session."""
    # 1. Fetch document and verify scope
    doc = await document_repo.get_document_by_id(session, workspace_id, document_id)
    if not doc:
        logger.warning(
            f"Ingestion aborted: document {document_id} not found in workspace {workspace_id}."
        )
        return False

    # 2. Atomic claim if document is pending
    if doc.status == "pending":
        claimed = await document_repo.atomic_claim_worker(session, workspace_id, document_id)
        if not claimed:
            logger.info(
                f"Document {document_id} was already claimed by another worker or is not claimable."
            )
            return False
        doc = claimed
    elif doc.status != "processing":
        # If document is not in 'processing' (e.g. from retry endpoint) or 'pending', skip
        logger.info(
            f"Document {document_id} in status '{doc.status}' is not eligible for processing."
        )
        return False

    # 3. Retrieve physical file from storage
    storage_path = doc.storage_path
    try:
        file_bytes = await storage.get_file(storage_path)
    except Exception as exc:
        err_msg = f"Storage retrieval error: {str(exc)}"
        logger.error(f"Failed to read file from storage for document {document_id}: {err_msg}")
        await document_repo.mark_document_failed(session, workspace_id, document_id, err_msg)
        return False

    if file_bytes is None:
        err_msg = f"Physical file not found in storage: {storage_path}"
        logger.warning(f"File missing in storage for document {document_id}: {err_msg}")
        await document_repo.mark_document_failed(session, workspace_id, document_id, err_msg)
        return False

    # 4. Parse PDF into pages
    try:
        parsed_pdf = extract_pdf_pages(file_bytes)
    except PDFParsingError as exc:
        err_msg = str(exc)
        logger.warning(f"Extraction failed for document {document_id}: {err_msg}")
        await document_repo.mark_document_failed(session, workspace_id, document_id, err_msg)
        return False
    except Exception as exc:
        err_msg = f"Unexpected PDF parsing error: {str(exc)}"
        logger.error(f"Extraction error for document {document_id}: {err_msg}")
        await document_repo.mark_document_failed(session, workspace_id, document_id, err_msg)
        return False

    # 5. Chunk extracted pages
    try:
        chunks = chunk_document_pages(
            pages=parsed_pdf.pages,
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        )
    except Exception as exc:
        err_msg = f"Chunking error: {str(exc)}"
        logger.error(f"Chunking error for document {document_id}: {err_msg}")
        await document_repo.mark_document_failed(session, workspace_id, document_id, err_msg)
        return False

    # 6. Persist pages, chunks, and transition document to 'ready'
    try:
        await document_repo.persist_extracted_pages_and_chunks(
            session=session,
            document_id=document_id,
            pages=parsed_pdf.pages,
            chunks=chunks,
        )
        logger.info(
            f"Document {document_id} ('{doc.filename}') ingested successfully: "
            f"{parsed_pdf.total_pages} pages, {len(chunks)} chunks persisted."
        )
        return True
    except Exception as exc:
        await session.rollback()
        err_msg = f"Database persistence error: {str(exc)}"
        logger.error(f"Persistence error for document {document_id}: {err_msg}")
        await document_repo.mark_document_failed(session, workspace_id, document_id, err_msg)
        return False


async def schedule_ingestion_background_task(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    """Entrypoint for FastAPI BackgroundTasks.

    Safely executes the ingestion pipeline in a dedicated database session.
    """
    settings = get_settings()
    if not settings.DATABASE_URL:
        logger.info(
            f"DATABASE_URL not configured; skipping background ingestion task for document {document_id}."
        )
        return

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await run_ingestion_pipeline(
                document_id=document_id,
                workspace_id=workspace_id,
                session=session,
                settings=settings,
            )
    except Exception as exc:
        logger.error(
            f"Unhandled exception in background ingestion task for document {document_id}: {exc}"
        )
