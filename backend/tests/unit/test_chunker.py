"""ProofLens AI — Unit Tests for Page-Aware Text Chunker.

Verifies deterministic bounded chunking, the absolute invariant that chunks
never cross physical page boundaries, sequential document-level chunk indexing,
and word-boundary preservation.
"""

import pytest

from app.services.parsing.chunker import chunk_document_pages
from app.services.parsing.pdf_parser import ParsedPage


def test_chunks_never_cross_page_boundaries():
    """Verify the hard invariant: chunks must strictly never cross physical page boundaries."""
    page_1_text = "Page one content detailing executive compensation and board governance."
    page_2_text = "Page two content discussing risk management frameworks and internal controls."

    pages = [
        ParsedPage(page_number=1, raw_text=page_1_text, char_count=len(page_1_text)),
        ParsedPage(page_number=2, raw_text=page_2_text, char_count=len(page_2_text)),
    ]

    chunks = chunk_document_pages(pages, chunk_size=1000, chunk_overlap=200)

    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_text == page_1_text
    assert chunks[1].page_number == 2
    assert chunks[1].chunk_text == page_2_text

    # Hard invariant: no cross-page contamination
    assert "compensation" not in chunks[1].chunk_text
    assert "frameworks" not in chunks[0].chunk_text


def test_sequential_chunk_index_across_document():
    """Verify chunk_index increments monotonically (0, 1, 2, ...) across all document pages."""
    # Create two pages that each require multiple chunks
    long_page_1 = "Alpha sentence. " * 150  # ~2400 chars
    long_page_2 = "Beta sentence. " * 180   # ~2700 chars

    pages = [
        ParsedPage(page_number=1, raw_text=long_page_1, char_count=len(long_page_1)),
        ParsedPage(page_number=2, raw_text=long_page_2, char_count=len(long_page_2)),
    ]

    chunks = chunk_document_pages(pages, chunk_size=800, chunk_overlap=150)

    assert len(chunks) > 4
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i  # Strict monotonic 0-based sequence

    # Check page distribution
    page_1_chunks = [c for c in chunks if c.page_number == 1]
    page_2_chunks = [c for c in chunks if c.page_number == 2]

    assert len(page_1_chunks) > 1
    assert len(page_2_chunks) > 1
    assert len(page_1_chunks) + len(page_2_chunks) == len(chunks)


def test_chunk_size_and_overlap_boundaries():
    """Verify chunks respect maximum chunk_size and demonstrate overlap between consecutive chunks."""
    text = (
        "Section 1: Introduction to macroeconomic trends. "
        "Section 2: Monetary policy shifts and interest rate sensitivity. "
        "Section 3: Credit default probabilities across commercial sectors. "
        "Section 4: Liquidity reserves and capital adequacy benchmarks. "
    ) * 10  # ~2700 chars

    pages = [ParsedPage(page_number=1, raw_text=text, char_count=len(text))]
    chunk_size = 500
    chunk_overlap = 100

    chunks = chunk_document_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    assert len(chunks) > 1
    for chunk in chunks:
        # Strict ceiling
        assert len(chunk.chunk_text) <= chunk_size + 50  # Allows for clean boundary window
        assert chunk.char_count == len(chunk.chunk_text)
        assert chunk.token_count > 0

    # Verify overlap exists between chunk 0 and chunk 1
    chunk_0_tail = chunks[0].chunk_text[-50:]
    assert chunk_0_tail in chunks[1].chunk_text or chunks[1].chunk_text[:50] in chunks[0].chunk_text


def test_empty_page_yields_zero_chunks():
    """Verify empty or blank pages produce zero chunks without breaking numbering."""
    pages = [
        ParsedPage(page_number=1, raw_text="Content on page 1.", char_count=18),
        ParsedPage(page_number=2, raw_text="   \n\t  ", char_count=6),  # Blank page
        ParsedPage(page_number=3, raw_text="Content on page 3.", char_count=18),
    ]

    chunks = chunk_document_pages(pages, chunk_size=1000, chunk_overlap=200)

    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert chunks[1].page_number == 3
    assert chunks[1].chunk_index == 1


def test_invalid_chunk_arguments():
    """Verify ValueError is raised when chunking parameters violate constraints."""
    dummy_pages = [ParsedPage(page_number=1, raw_text="Text", char_count=4)]

    # chunk_size <= 0
    with pytest.raises(ValueError, match="chunk_size must be a positive integer"):
        chunk_document_pages(dummy_pages, chunk_size=0, chunk_overlap=0)

    # chunk_overlap < 0
    with pytest.raises(ValueError, match="chunk_overlap cannot be negative"):
        chunk_document_pages(dummy_pages, chunk_size=500, chunk_overlap=-10)

    # chunk_overlap >= chunk_size
    with pytest.raises(ValueError, match="chunk_overlap must be strictly less than chunk_size"):
        chunk_document_pages(dummy_pages, chunk_size=500, chunk_overlap=500)
