"""ProofLens AI — PDF Text Parser.

Extracts text on a physical page-by-page basis using pypdf, preserving exact
1-indexed page numbering, character counts, and flagging scanned/empty documents.
"""

import io
from dataclasses import dataclass
from typing import List
import pypdf
from pypdf.errors import PdfReadError


class PDFParsingError(Exception):
    """Raised when PDF extraction fails or document contains unextractable content."""
    pass


@dataclass(frozen=True)
class ParsedPage:
    """Represents a single extracted physical page."""
    page_number: int  # 1-indexed
    raw_text: str
    char_count: int


@dataclass(frozen=True)
class ParsedPDF:
    """Represents all extracted pages and metadata from a PDF."""
    pages: List[ParsedPage]
    total_pages: int
    total_char_count: int


def extract_pdf_pages(pdf_bytes: bytes) -> ParsedPDF:
    """Extract page-by-page text from raw PDF bytes.

    Args:
        pdf_bytes: Raw binary content of the PDF file.

    Returns:
        ParsedPDF with all pages, total page count, and character counts.

    Raises:
        PDFParsingError: If PDF is malformed, has 0 pages, or contains zero extractable text (scanned).
    """
    if not pdf_bytes:
        raise PDFParsingError("Cannot parse empty file: 0 bytes provided.")

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    except (PdfReadError, Exception) as exc:
        raise PDFParsingError(f"Malformed or unreadable PDF: {str(exc)}") from exc

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise PDFParsingError("PDF contains 0 pages.")

    parsed_pages: List[ParsedPage] = []
    total_chars = 0

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1  # 1-indexed physical page numbering
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:
            # If a specific page cannot be extracted, fallback to empty string
            page_text = ""

        # Remove null characters which PostgreSQL Text columns reject
        clean_text = page_text.replace("\x00", "")
        char_count = len(clean_text)
        total_chars += char_count

        parsed_pages.append(
            ParsedPage(
                page_number=page_num,
                raw_text=clean_text,
                char_count=char_count,
            )
        )

    # Scanned image detection: Check if any extractable non-whitespace text exists across all pages
    all_text = "".join(p.raw_text for p in parsed_pages).strip()
    if not all_text or total_chars == 0:
        raise PDFParsingError(
            "Document appears to be scanned or contains no extractable text (OCR not supported in MVP)"
        )

    return ParsedPDF(
        pages=parsed_pages,
        total_pages=total_pages,
        total_char_count=total_chars,
    )
