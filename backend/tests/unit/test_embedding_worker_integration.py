"""ProofLens AI — Unit Tests for Ingestion Worker & Embedding Integration.

Verifies:
1. Ingestion pipeline extracts text, chunks pages, generates 768-dim embeddings, and transitions document to 'ready'.
2. If embedding generation fails, document transitions to 'failed' and is never marked 'ready'.
3. Retrying an already-chunked document resumes embedding unembedded chunks without re-parsing PDF.
4. Already-embedded documents transition to 'ready' without re-generating embeddings.
5. Database failures during vector persistence roll back and mark document as failed.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import Settings
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.page import DocumentPage
from app.services.ai.embedding import EmbeddingGenerationError
from app.services.ingestion.worker import run_ingestion_pipeline
from app.services.parsing.chunker import ChunkData
from app.services.parsing.pdf_parser import ParsedPage
from tests.unit.test_pdf_parser import create_in_memory_pdf


@pytest.fixture
def worker_settings():
    return Settings(
        ENVIRONMENT="test",
        GEMINI_API_KEY="test-dummy-gemini-key",
        GEMINI_EMBEDDING_MODEL="gemini-embedding-2",
        EMBEDDING_DIMENSIONS=768,
        RAG_CHUNK_SIZE=1000,
        RAG_CHUNK_OVERLAP=200,
    )


@pytest.mark.asyncio
async def test_ingestion_generates_and_persists_embeddings_and_transitions_ready(worker_settings):
    """Verify document pipeline extracts text, generates embeddings, persists them, and sets status to ready."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    pending_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="financial_report.pdf",
        content_hash="fin_hash_123",
        file_size_bytes=800,
        storage_path="workspaces/ws/financial_report.pdf",
        status="pending",
    )
    claimed_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="financial_report.pdf",
        content_hash="fin_hash_123",
        file_size_bytes=800,
        storage_path="workspaces/ws/financial_report.pdf",
        status="processing",
    )

    pdf_bytes = create_in_memory_pdf(["Page 1 financial statement.", "Page 2 cash flow report."])

    mock_session = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_file.return_value = pdf_bytes

    chunk_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_id=uuid.uuid4(),
        chunk_index=0,
        chunk_text="Page 1 financial statement.",
        embedding=None,
    )
    chunk_2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_id=uuid.uuid4(),
        chunk_index=1,
        chunk_text="Page 2 cash flow report.",
        embedding=None,
    )

    mock_persist_result = (
        [DocumentPage(id=chunk_1.page_id, document_id=doc_id, page_number=1, raw_text="...", char_count=30)],
        [chunk_1, chunk_2],
    )

    mock_embedding_service = MagicMock()
    mock_embedding_service.embed_texts = AsyncMock(return_value=[
        [0.1] * 768,
        [0.2] * 768,
    ])

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=pending_doc)), \
         patch("app.repositories.document_repo.atomic_claim_worker", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.repositories.document_repo.get_document_chunks", new=AsyncMock(return_value=[])), \
         patch("app.repositories.document_repo.persist_extracted_pages_and_chunks", new=AsyncMock(return_value=mock_persist_result)), \
         patch("app.repositories.document_repo.update_chunk_embeddings", new=AsyncMock(return_value=2)) as mock_update_embeddings, \
         patch("app.repositories.document_repo.mark_document_ready", new=AsyncMock()) as mock_mark_ready:

        success = await run_ingestion_pipeline(
            document_id=doc_id,
            workspace_id=ws_id,
            session=mock_session,
            storage=mock_storage,
            settings=worker_settings,
            embedding_service=mock_embedding_service,
        )

        assert success is True
        mock_embedding_service.embed_texts.assert_awaited_once_with([
            "Page 1 financial statement.",
            "Page 2 cash flow report.",
        ])
        mock_update_embeddings.assert_awaited_once()
        mock_mark_ready.assert_awaited_once_with(mock_session, ws_id, doc_id)


@pytest.mark.asyncio
async def test_ingestion_fails_if_embedding_service_fails(worker_settings):
    """Verify document transitions to failed and ready is never called if embeddings fail."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    claimed_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="report.pdf",
        content_hash="hash",
        file_size_bytes=500,
        storage_path="workspaces/ws/report.pdf",
        status="processing",
    )

    pdf_bytes = create_in_memory_pdf(["Page 1 content."])
    mock_session = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_file.return_value = pdf_bytes

    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_id=uuid.uuid4(),
        chunk_index=0,
        chunk_text="Page 1 content.",
    )
    mock_persist_result = ([], [chunk])

    mock_embedding_service = MagicMock()
    mock_embedding_service.embed_texts = AsyncMock(
        side_effect=EmbeddingGenerationError("Gemini API rate limit exceeded.")
    )

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.repositories.document_repo.get_document_chunks", new=AsyncMock(return_value=[])), \
         patch("app.repositories.document_repo.persist_extracted_pages_and_chunks", new=AsyncMock(return_value=mock_persist_result)), \
         patch("app.repositories.document_repo.mark_document_failed", new=AsyncMock()) as mock_mark_failed, \
         patch("app.repositories.document_repo.mark_document_ready", new=AsyncMock()) as mock_mark_ready:

        success = await run_ingestion_pipeline(
            document_id=doc_id,
            workspace_id=ws_id,
            session=mock_session,
            storage=mock_storage,
            settings=worker_settings,
            embedding_service=mock_embedding_service,
        )

        assert success is False
        mock_mark_failed.assert_awaited_once()
        err_msg = mock_mark_failed.call_args[0][3]
        assert "Embedding generation failed: Gemini API rate limit exceeded." in err_msg
        mock_mark_ready.assert_not_called()


@pytest.mark.asyncio
async def test_retry_resumes_unembedded_chunks_without_reextracting_pdf(worker_settings):
    """Verify retry of already-chunked document only embeds missing chunks without re-parsing PDF."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    claimed_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="existing_doc.pdf",
        content_hash="existing_hash",
        file_size_bytes=500,
        storage_path="workspaces/ws/existing.pdf",
        status="processing",
    )

    mock_session = AsyncMock()
    mock_storage = AsyncMock()

    # Document already has 2 chunks persisted
    chunk_1 = DocumentChunk(id=uuid.uuid4(), document_id=doc_id, chunk_index=0, chunk_text="Chunk 1", embedding=[0.1]*768)
    chunk_2 = DocumentChunk(id=uuid.uuid4(), document_id=doc_id, chunk_index=1, chunk_text="Chunk 2", embedding=None)

    existing_chunks = [chunk_1, chunk_2]
    unembedded_chunks = [chunk_2]  # Only chunk_2 needs embedding

    mock_embedding_service = MagicMock()
    mock_embedding_service.embed_texts = AsyncMock(return_value=[[0.2] * 768])

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.repositories.document_repo.get_document_chunks", new=AsyncMock(return_value=existing_chunks)), \
         patch("app.repositories.document_repo.get_unembedded_chunks", new=AsyncMock(return_value=unembedded_chunks)), \
         patch("app.repositories.document_repo.update_chunk_embeddings", new=AsyncMock(return_value=1)) as mock_update, \
         patch("app.repositories.document_repo.mark_document_ready", new=AsyncMock()) as mock_mark_ready:

        success = await run_ingestion_pipeline(
            document_id=doc_id,
            workspace_id=ws_id,
            session=mock_session,
            storage=mock_storage,
            settings=worker_settings,
            embedding_service=mock_embedding_service,
        )

        assert success is True
        # Verify storage was NOT accessed and PDF was NOT re-parsed
        mock_storage.get_file.assert_not_called()
        # Verify only unembedded chunk_2 was embedded
        mock_embedding_service.embed_texts.assert_awaited_once_with(["Chunk 2"])
        mock_update.assert_awaited_once()
        mock_mark_ready.assert_awaited_once()


@pytest.mark.asyncio
async def test_already_embedded_document_transitions_ready_without_reembedding(worker_settings):
    """Verify document where all chunks are already embedded transitions to ready immediately."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    claimed_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="complete.pdf",
        content_hash="complete_hash",
        file_size_bytes=500,
        storage_path="workspaces/ws/complete.pdf",
        status="processing",
    )

    mock_session = AsyncMock()
    mock_storage = AsyncMock()

    chunk_1 = DocumentChunk(id=uuid.uuid4(), document_id=doc_id, chunk_index=0, chunk_text="Chunk 1", embedding=[0.1]*768)
    existing_chunks = [chunk_1]

    mock_embedding_service = MagicMock()
    mock_embedding_service.embed_texts = AsyncMock()

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.repositories.document_repo.get_document_chunks", new=AsyncMock(return_value=existing_chunks)), \
         patch("app.repositories.document_repo.get_unembedded_chunks", new=AsyncMock(return_value=[])), \
         patch("app.repositories.document_repo.mark_document_ready", new=AsyncMock()) as mock_mark_ready:

        success = await run_ingestion_pipeline(
            document_id=doc_id,
            workspace_id=ws_id,
            session=mock_session,
            storage=mock_storage,
            settings=worker_settings,
            embedding_service=mock_embedding_service,
        )

        assert success is True
        mock_embedding_service.embed_texts.assert_not_called()
        mock_mark_ready.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_failure_during_vector_persistence_marks_document_failed(worker_settings):
    """Verify database exceptions during update_chunk_embeddings roll back and mark document failed."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    claimed_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="report.pdf",
        content_hash="hash",
        file_size_bytes=500,
        storage_path="workspaces/ws/report.pdf",
        status="processing",
    )

    pdf_bytes = create_in_memory_pdf(["Page 1 content."])
    mock_session = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_file.return_value = pdf_bytes

    chunk = DocumentChunk(id=uuid.uuid4(), document_id=doc_id, page_id=uuid.uuid4(), chunk_index=0, chunk_text="Page 1.")
    mock_persist_result = ([], [chunk])

    mock_embedding_service = MagicMock()
    mock_embedding_service.embed_texts = AsyncMock(return_value=[[0.1] * 768])

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.repositories.document_repo.get_document_chunks", new=AsyncMock(return_value=[])), \
         patch("app.repositories.document_repo.persist_extracted_pages_and_chunks", new=AsyncMock(return_value=mock_persist_result)), \
         patch("app.repositories.document_repo.update_chunk_embeddings", new=AsyncMock(side_effect=RuntimeError("Database connection lost"))), \
         patch("app.repositories.document_repo.mark_document_failed", new=AsyncMock()) as mock_mark_failed:

        success = await run_ingestion_pipeline(
            document_id=doc_id,
            workspace_id=ws_id,
            session=mock_session,
            storage=mock_storage,
            settings=worker_settings,
            embedding_service=mock_embedding_service,
        )

        assert success is False
        mock_session.rollback.assert_awaited_once()
        mock_mark_failed.assert_awaited_once()
        err_msg = mock_mark_failed.call_args[0][3]
        assert "Vector persistence error: Database connection lost" in err_msg
