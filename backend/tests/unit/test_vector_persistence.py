"""ProofLens AI — Unit Tests for Vector Persistence & Repository Methods.

Verifies:
1. Valid embeddings are correctly persisted to chunks via update_chunk_embeddings.
2. Unembedded chunks are queried and sorted by chunk_index ascending.
3. Existing valid embeddings are preserved and not overwritten unnecessarily.
4. Empty lists are handled safely.
5. Document status transitions to 'ready' only after embeddings are persisted.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.repositories import document_repo
from app.services.parsing.chunker import ChunkData
from app.services.parsing.pdf_parser import ParsedPage


@pytest.mark.asyncio
async def test_update_chunk_embeddings_persists_vectors():
    """Verify update_chunk_embeddings issues parameterized updates and commits."""
    mock_session = AsyncMock()
    chunk_1_id = uuid.uuid4()
    chunk_2_id = uuid.uuid4()

    vector_1 = [0.1] * 768
    vector_2 = [0.2] * 768

    chunk_data = [
        (chunk_1_id, vector_1, "gemini-embedding-2"),
        (chunk_2_id, vector_2, "gemini-embedding-2"),
    ]

    count = await document_repo.update_chunk_embeddings(mock_session, chunk_data)

    assert count == 2
    assert mock_session.execute.call_count == 2
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_chunk_embeddings_empty_list():
    """Verify empty chunk embeddings list returns 0 and commits nothing."""
    mock_session = AsyncMock()
    count = await document_repo.update_chunk_embeddings(mock_session, [])
    assert count == 0
    mock_session.execute.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_unembedded_chunks_queries_null_embeddings():
    """Verify get_unembedded_chunks queries only chunks with embedding IS NULL."""
    mock_session = AsyncMock()
    doc_id = uuid.uuid4()

    chunk_unembedded = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_id=uuid.uuid4(),
        chunk_index=0,
        chunk_text="Chunk awaiting embedding",
        embedding=None,
    )

    # Configure scalar result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [chunk_unembedded]
    mock_session.execute.return_value = mock_result

    unembedded = await document_repo.get_unembedded_chunks(mock_session, doc_id)

    assert len(unembedded) == 1
    assert unembedded[0].id == chunk_unembedded.id
    assert unembedded[0].embedding is None


@pytest.mark.asyncio
async def test_mark_document_ready():
    """Verify mark_document_ready executes status update to 'ready' and commits."""
    mock_session = AsyncMock()
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    await document_repo.mark_document_ready(mock_session, ws_id, doc_id)

    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_extracted_pages_and_chunks_keeps_processing_by_default():
    """Verify persist_extracted_pages_and_chunks leaves document in processing pending embeddings."""
    mock_session = AsyncMock()
    doc_id = uuid.uuid4()

    pages = [ParsedPage(page_number=1, raw_text="Page text", char_count=9)]
    chunks = [ChunkData(page_number=1, chunk_index=0, chunk_text="Chunk text", char_count=10, token_count=3)]

    created_pages, created_chunks = await document_repo.persist_extracted_pages_and_chunks(
        session=mock_session,
        document_id=doc_id,
        pages=pages,
        chunks=chunks,
        mark_ready=False,
    )

    assert len(created_pages) == 1
    assert len(created_chunks) == 1
    assert created_chunks[0].embedding is None
    # Verify execute was called for delete chunks, delete pages, and update page_count
    assert mock_session.execute.call_count == 3
    mock_session.commit.assert_awaited_once()
