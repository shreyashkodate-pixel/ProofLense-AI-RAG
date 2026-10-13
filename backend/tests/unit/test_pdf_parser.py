"""ProofLens AI — Unit Tests for PDF Parser.

Verifies page-by-page text extraction, 1-indexed physical page numbering,
character count accounting, scanned/zero-text document detection, and malformed file handling.
"""

import io
import pytest
import pypdf
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.services.parsing.pdf_parser import PDFParsingError, extract_pdf_pages


def create_in_memory_pdf(pages_text: list[str]) -> bytes:
    """Helper creating real in-memory PDF with text streams on each page."""
    writer = pypdf.PdfWriter()
    for text in pages_text:
        page = writer.add_blank_page(width=300, height=300)
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 50 250 Td ({text}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = stream

        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
        })

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_blank_pdf(num_pages: int = 1) -> bytes:
    """Helper creating a valid PDF with blank pages (zero extractable text)."""
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_extract_multi_page_pdf():
    """Verify multi-page PDF produces exact page count and 1-indexed page provenance."""
    sample_texts = [
        "First page content with financial figures.",
        "Second page detailing operations and quarterly results.",
        "Third page summarizing conclusions and audit opinions.",
    ]
    pdf_bytes = create_in_memory_pdf(sample_texts)

    parsed = extract_pdf_pages(pdf_bytes)

    assert parsed.total_pages == 3
    assert len(parsed.pages) == 3

    for idx, page in enumerate(parsed.pages):
        assert page.page_number == idx + 1  # 1-indexed physical page number
        assert page.raw_text == sample_texts[idx]
        assert page.char_count == len(sample_texts[idx])

    expected_total_chars = sum(len(t) for t in sample_texts)
    assert parsed.total_char_count == expected_total_chars


def test_scanned_or_zero_text_pdf_raises_error():
    """Verify blank or scanned PDFs fail with exact actionable MVP error message."""
    blank_pdf = create_blank_pdf(num_pages=3)

    with pytest.raises(PDFParsingError) as exc_info:
        extract_pdf_pages(blank_pdf)

    assert "Document appears to be scanned or contains no extractable text (OCR not supported in MVP)" in str(exc_info.value)


def test_whitespace_only_pdf_raises_error():
    """Verify PDFs with only spaces/whitespace fail with scanned document error."""
    whitespace_pdf = create_in_memory_pdf(["   \n\t  ", "    "])

    with pytest.raises(PDFParsingError) as exc_info:
        extract_pdf_pages(whitespace_pdf)

    assert "Document appears to be scanned or contains no extractable text (OCR not supported in MVP)" in str(exc_info.value)


def test_empty_bytes_raises_error():
    """Verify empty input raises PDFParsingError."""
    with pytest.raises(PDFParsingError) as exc_info:
        extract_pdf_pages(b"")

    assert "Cannot parse empty file: 0 bytes provided." in str(exc_info.value)


def test_malformed_pdf_raises_error():
    """Verify corrupt/non-PDF bytes raise PDFParsingError."""
    corrupt_bytes = b"%PDF-1.4 but corrupt and truncated content"

    with pytest.raises(PDFParsingError) as exc_info:
        extract_pdf_pages(corrupt_bytes)

    assert "Malformed or unreadable PDF" in str(exc_info.value)


def test_null_bytes_are_stripped():
    """Verify null bytes are stripped to prevent PostgreSQL string termination errors."""
    text_with_null = "Hello\x00World"
    pdf_bytes = create_in_memory_pdf([text_with_null])

    parsed = extract_pdf_pages(pdf_bytes)
    assert "\x00" not in parsed.pages[0].raw_text
    assert parsed.pages[0].raw_text == "HelloWorld"
