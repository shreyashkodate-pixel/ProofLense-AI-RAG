"""ProofLens AI — Unit Tests for Ingestion Worker & Persistence.

Verifies end-to-end ingestion pipeline execution, document lifecycle state transitions
(pending -> processing -> ready / failed), error handling, retry idempotency,
and atomic claim verification.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import Settings
from app.models.document import Document
from app.services.ingestion.worker import run_ingestion_pipeline
from app.services.parsing.chunker import ChunkData
from app.services.parsing.pdf_parser import ParsedPage
from tests.unit.test_pdf_parser import create_blank_pdf, create_in_memory_pdf


@pytest.fixture
def sample_settings():
    return Settings(
        ENVIRONMENT="test",
        RAG_CHUNK_SIZE=1000,
        RAG_CHUNK_OVERLAP=200,
    )


@pytest.mark.asyncio
async def test_run_ingestion_pipeline_success(sample_settings):
    """Verify valid multi-page PDF completes ingestion, transitions to 'ready', and persists data."""
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    pending_doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename="report.pdf",
        content_hash="abc123hash",
        file_size_bytes=1000,
        storage_path="workspaces/ws/report.pdf",
        status="pending",
    )

    claimed_doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename="report.pdf",
        content_hash="abc123hash",
        file_size_bytes=1000,
        storage_path="workspaces/ws/report.pdf",
        status="processing",
    )

    pdf_bytes = create_in_memory_pdf([
        "Page 1: Audit report introduction.",
        "Page 2: Balance sheet and revenue breakdown.",
    ])

    mock_session = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_file.return_value = pdf_bytes

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=pending_doc)), \
         patch("app.repositories.document_repo.atomic_claim_worker", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.repositories.document_repo.persist_extracted_pages_and_chunks", new=AsyncMock()) as mock_persist:

        success = await run_ingestion_pipeline(
            document_id=document_id,
            workspace_id=workspace_id,
            session=mock_session,
            storage=mock_storage,
            settings=sample_settings,
        )

        assert success is True
        mock_storage.get_file.assert_awaited_once_with("workspaces/ws/report.pdf")
        mock_persist.assert_awaited_once()

        # Verify pages passed to persistence
        args, kwargs = mock_persist.call_args
        assert kwargs["document_id"] == document_id
        assert len(kwargs["pages"]) == 2
        assert kwargs["pages"][0].page_number == 1
        assert kwargs["pages"][1].page_number == 2
        assert len(kwargs["chunks"]) >= 2


@pytest.mark.asyncio
async def test_run_ingestion_pipeline_scanned_pdf_fails(sample_settings):
    """Verify scanned/zero-text PDF fails with actionable message and transitions to 'failed'."""
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename="scanned.pdf",
        content_hash="scan_hash",
        file_size_bytes=500,
        storage_path="workspaces/ws/scanned.pdf",
        status="pending",
    )

    claimed_doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename="scanned.pdf",
        content_hash="scan_hash",
        file_size_bytes=500,
        storage_path="workspaces/ws/scanned.pdf",
        status="processing",
    )

    blank_pdf = create_blank_pdf(num_pages=2)
    mock_session = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_file.return_value = blank_pdf

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=doc)), \
         patch("app.repositories.document_repo.atomic_claim_worker", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.repositories.document_repo.mark_document_failed", new=AsyncMock()) as mock_mark_failed:

        success = await run_ingestion_pipeline(
            document_id=document_id,
            workspace_id=workspace_id,
            session=mock_session,
            storage=mock_storage,
            settings=sample_settings,
        )

        assert success is False
        mock_mark_failed.assert_awaited_once()
        err_msg = mock_mark_failed.call_args[0][3]
        assert "Document appears to be scanned or contains no extractable text (OCR not supported in MVP)" in err_msg


@pytest.mark.asyncio
async def test_run_ingestion_pipeline_corrupt_pdf_fails(sample_settings):
    """Verify malformed PDF transitions to 'failed' with descriptive error."""
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename="corrupt.pdf",
        content_hash="corrupt_hash",
        file_size_bytes=100,
        storage_path="workspaces/ws/corrupt.pdf",
        status="pending",
    )
    claimed_doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename="corrupt.pdf",
        content_hash="corrupt_hash",
        file_size_bytes=100,
        storage_path="workspaces/ws/corrupt.pdf",
        status="processing",
    )

    mock_session = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_file.return_value = b"corrupt-data-not-a-pdf"

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=doc)), \
         patch("app.repositories.document_repo.atomic_claim_worker", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.repositories.document_repo.mark_document_failed", new=AsyncMock()) as mock_mark_failed:

        success = await run_ingestion_pipeline(
            document_id=document_id,
            workspace_id=workspace_id,
            session=mock_session,
            storage=mock_storage,
            settings=sample_settings,
        )

        assert success is False
        mock_mark_failed.assert_awaited_once()
        err_msg = mock_mark_failed.call_args[0][3]
        assert "Malformed or unreadable PDF" in err_msg


@pytest.mark.asyncio
async def test_run_ingestion_pipeline_missing_storage_file(sample_settings):
    """Verify missing storage file transitions document to 'failed'."""
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename="missing.pdf",
        content_hash="missing_hash",
        file_size_bytes=100,
        storage_path="workspaces/ws/missing.pdf",
        status="pending",
    )
    claimed_doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename="missing.pdf",
        content_hash="missing_hash",
        file_size_bytes=100,
        storage_path="workspaces/ws/missing.pdf",
        status="processing",
    )

    mock_session = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_file.return_value = None  # File not found

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=doc)), \
         patch("app.repositories.document_repo.atomic_claim_worker", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.repositories.document_repo.mark_document_failed", new=AsyncMock()) as mock_mark_failed:

        success = await run_ingestion_pipeline(
            document_id=document_id,
            workspace_id=workspace_id,
            session=mock_session,
            storage=mock_storage,
            settings=sample_settings,
        )

        assert success is False
        mock_mark_failed.assert_awaited_once()
        err_msg = mock_mark_failed.call_args[0][3]
        assert "Physical file not found in storage" in err_msg


@pytest.mark.asyncio
async def test_run_ingestion_pipeline_skips_unclaimable_document(sample_settings):
    """Verify pipeline returns False when document cannot be claimed (e.g. concurrent race)."""
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename="busy.pdf",
        content_hash="busy_hash",
        file_size_bytes=100,
        storage_path="workspaces/ws/busy.pdf",
        status="pending",
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_storage = AsyncMock()

    # atomic_claim_worker returns None due to race
    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=doc)), \
         patch("app.repositories.document_repo.atomic_claim_worker", new=AsyncMock(return_value=None)):

        success = await run_ingestion_pipeline(
            document_id=document_id,
            workspace_id=workspace_id,
            session=mock_session,
            storage=mock_storage,
            settings=sample_settings,
        )

        assert success is False


@pytest.mark.asyncio
async def test_persist_extracted_pages_and_chunks_idempotency():
    """Verify persist_extracted_pages_and_chunks executes clean delete and inserts fresh records."""
    from app.repositories.document_repo import persist_extracted_pages_and_chunks

    doc_id = uuid.uuid4()
    pages = [
        ParsedPage(page_number=1, raw_text="Page 1", char_count=6),
        ParsedPage(page_number=2, raw_text="Page 2", char_count=6),
    ]
    chunks = [
        ChunkData(page_number=1, chunk_index=0, chunk_text="Page 1", char_count=6, token_count=2),
        ChunkData(page_number=2, chunk_index=1, chunk_text="Page 2", char_count=6, token_count=2),
    ]

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    created_pages, created_chunks = await persist_extracted_pages_and_chunks(
        session=mock_session,
        document_id=doc_id,
        pages=pages,
        chunks=chunks,
    )

    # Verified that 2 pages and 2 chunks were created
    assert len(created_pages) == 2
    assert len(created_chunks) == 2
    assert created_chunks[0].chunk_index == 0
    assert created_chunks[1].chunk_index == 1
    assert created_chunks[0].page_id == created_pages[0].id
    assert created_chunks[1].page_id == created_pages[1].id

    # Session operations
    assert mock_session.add.call_count == 4  # 2 pages + 2 chunks
    assert mock_session.execute.call_count == 3  # delete chunks, delete pages, update document
    mock_session.commit.assert_awaited_once()
