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
from app.services.ai.embedding import GeminiEmbeddingService, get_embedding_service
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
    embedding_service: Optional[GeminiEmbeddingService] = None,
) -> bool:
    """Execute complete ingestion pipeline for a single document.

    Args:
        document_id: UUID of the document to process.
        workspace_id: UUID of the owning workspace.
        session: Optional existing AsyncSession (acquired from factory if None).
        storage: Optional BaseStorageService (acquired from factory if None).
        settings: Optional Settings (acquired from get_settings if None).
        embedding_service: Optional GeminiEmbeddingService (acquired via factory if None).

    Returns:
        True if ingestion succeeded and document is 'ready', False if failed.
    """
    settings = settings or get_settings()
    storage = storage or get_storage_service()
    embedding_service = embedding_service or get_embedding_service(settings=settings)

    if session is None:
        session_factory = get_session_factory()
        async with session_factory() as owned_session:
            return await _execute_pipeline_core(
                document_id=document_id,
                workspace_id=workspace_id,
                session=owned_session,
                storage=storage,
                settings=settings,
                embedding_service=embedding_service,
            )
    else:
        return await _execute_pipeline_core(
            document_id=document_id,
            workspace_id=workspace_id,
            session=session,
            storage=storage,
            settings=settings,
            embedding_service=embedding_service,
        )


async def _execute_pipeline_core(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID,
    session: AsyncSession,
    storage: BaseStorageService,
    settings: Settings,
    embedding_service: GeminiEmbeddingService,
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

    # 3. Check if document already has chunks persisted (e.g. from retry after embedding failure)
    existing_chunks = await document_repo.get_document_chunks(session, document_id)
    chunks_to_embed = []

    if not existing_chunks:
        # Retrieve physical file from storage
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

        # Parse PDF into pages
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

        # Chunk extracted pages
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

        # Persist pages and bounded chunks (keep in 'processing' status pending embeddings)
        try:
            persist_res = await document_repo.persist_extracted_pages_and_chunks(
                session=session,
                document_id=document_id,
                pages=parsed_pdf.pages,
                chunks=chunks,
                mark_ready=False,
            )
            logger.info(
                f"Document {document_id} ('{doc.filename}') chunks persisted: "
                f"{parsed_pdf.total_pages} pages, {len(chunks)} chunks."
            )
        except Exception as exc:
            await session.rollback()
            err_msg = f"Database persistence error: {str(exc)}"
            logger.error(f"Persistence error for document {document_id}: {err_msg}")
            await document_repo.mark_document_failed(session, workspace_id, document_id, err_msg)
            return False

        if isinstance(persist_res, (list, tuple)) and len(persist_res) == 2:
            _, raw_chunks = persist_res
            if isinstance(raw_chunks, list):
                chunks_to_embed = raw_chunks
    else:
        # Document was already parsed and chunked; only embed missing chunks
        logger.info(
            f"Document {document_id} already has {len(existing_chunks)} persisted chunks. Resuming embedding."
        )
        unembedded = await document_repo.get_unembedded_chunks(session, document_id)
        chunks_to_embed = unembedded


    if chunks_to_embed:
        chunk_texts = [c.chunk_text for c in chunks_to_embed if hasattr(c, "chunk_text")]
        if chunk_texts:
            try:
                embeddings = await embedding_service.embed_texts(chunk_texts)
            except Exception as exc:
                err_msg = f"Embedding generation failed: {str(exc)}"
                logger.error(f"Embedding error for document {document_id}: {err_msg}")
                await document_repo.mark_document_failed(session, workspace_id, document_id, err_msg)
                return False

            chunk_embeddings = [
                (c.id, vector, settings.GEMINI_EMBEDDING_MODEL)
                for c, vector in zip(chunks_to_embed, embeddings)
            ]
            try:
                await document_repo.update_chunk_embeddings(session, chunk_embeddings)
                logger.info(
                    f"Persisted {len(chunk_embeddings)} embeddings for document {document_id}."
                )
            except Exception as exc:
                await session.rollback()
                err_msg = f"Vector persistence error: {str(exc)}"
                logger.error(f"Vector persistence error for document {document_id}: {err_msg}")
                await document_repo.mark_document_failed(session, workspace_id, document_id, err_msg)
                return False

    # 8. Atomically transition document to 'ready' once all chunks are embedded
    try:
        await document_repo.mark_document_ready(session, workspace_id, document_id)
        logger.info(f"Document {document_id} ('{doc.filename}') successfully transitioned to 'ready'.")
        return True
    except Exception as exc:
        await session.rollback()
        err_msg = f"Status transition error: {str(exc)}"
        logger.error(f"Ready status transition failed for document {document_id}: {err_msg}")
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
