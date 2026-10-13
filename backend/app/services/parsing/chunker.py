"""ProofLens AI — Page-Aware Text Chunker.

Implements deterministic, bounded text chunking strictly preserving physical page
provenance. Hard Invariant: Chunks must never cross physical page boundaries.
"""

from dataclasses import dataclass
from typing import List
from app.services.parsing.pdf_parser import ParsedPage


@dataclass(frozen=True)
class ChunkData:
    """Represents a bounded semantic text chunk with page provenance."""
    page_number: int  # 1-indexed
    chunk_index: int  # 0-indexed sequentially across document
    chunk_text: str
    char_count: int
    token_count: int


def estimate_token_count(text: str) -> int:
    """Estimate token count for a text snippet.

    Uses whitespace-based word count heuristic (or ~4 chars per token)
    suitable for preliminary chunk sizing prior to tokenizer integration.
    """
    if not text:
        return 0
    words = len(text.split())
    char_estimate = max(1, len(text) // 4)
    return max(words, char_estimate)


def chunk_document_pages(
    pages: List[ParsedPage],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[ChunkData]:
    """Chunk extracted pages into deterministic, bounded pieces.

    Hard Invariants:
    1. Chunks must NEVER span across two physical pages.
    2. Every chunk must maintain valid 1-indexed page_number and sequential chunk_index.
    3. Empty pages produce zero chunks.

    Args:
        pages: List of ParsedPage objects from the PDF parser.
        chunk_size: Maximum characters per chunk (default: 1000).
        chunk_overlap: Overlap between consecutive chunks within the same page (default: 200).

    Returns:
        List of ChunkData preserving page-level provenance.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be strictly less than chunk_size.")

    chunks: List[ChunkData] = []
    global_chunk_index = 0

    for page in pages:
        page_text = page.raw_text.strip()
        if not page_text:
            # Empty or whitespace-only page yields no chunks
            continue

        text_length = len(page_text)

        # Single chunk if entire page text fits within chunk_size
        if text_length <= chunk_size:
            chunks.append(
                ChunkData(
                    page_number=page.page_number,
                    chunk_index=global_chunk_index,
                    chunk_text=page_text,
                    char_count=text_length,
                    token_count=estimate_token_count(page_text),
                )
            )
            global_chunk_index += 1
            continue

        # Sliding window within this page only
        start = 0
        stride = chunk_size - chunk_overlap

        while start < text_length:
            end = min(start + chunk_size, text_length)
            slice_candidate = page_text[start:end]

            # If not at the end of page text, look for clean word boundary
            if end < text_length:
                # Search for space or newline in the last 25% of the window
                min_split_point = int(chunk_size * 0.75)
                relative_slice = slice_candidate[min_split_point:]
                last_space = max(relative_slice.rfind(" "), relative_slice.rfind("\n"))

                if last_space != -1:
                    actual_cut = min_split_point + last_space + 1
                    end = start + actual_cut

            chunk_text = page_text[start:end].strip()

            if chunk_text:
                chunks.append(
                    ChunkData(
                        page_number=page.page_number,
                        chunk_index=global_chunk_index,
                        chunk_text=chunk_text,
                        char_count=len(chunk_text),
                        token_count=estimate_token_count(chunk_text),
                    )
                )
                global_chunk_index += 1

            if end >= text_length:
                break

            # Advance start while guaranteeing strict forward progression
            next_start = end - chunk_overlap
            start = max(start + 1, next_start)

    return chunks
