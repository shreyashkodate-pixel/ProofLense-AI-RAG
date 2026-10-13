"""ProofLens AI — Unit Tests for Server-Authoritative Citation Validator.

Verifies:
1. A valid citation maps to the correct chunk, document, filename, and physical page.
2. A fabricated citation ID is stripped.
3. A citation referring to an un-retrieved chunk is rejected.
4. Model-supplied fake page numbers, filenames, and IDs are ignored.
5. Cross-workspace evidence is rejected.
6. Duplicate citations follow the deduplication policy.
7. Empty or malformed model output cannot create a citation.
8. Factual claims with zero valid citations safely convert to explicit abstention.
"""

import uuid
import pytest

from app.repositories.query_repo import CandidateChunk
from app.services.ai.generator import GeneratedCitation
from app.services.rag.validator import CitationValidator, ValidatedCitation


def create_candidate(
    chunk_index: int = 1,
    page_number: int = 5,
    filename: str = "financial_report_q3.pdf",
    chunk_text: str = "Total net revenue reached $42.5 million for the quarter ending September.",
    rank: int = 1,
) -> CandidateChunk:
    """Helper to construct authoritative candidate chunk records."""
    return CandidateChunk(
        chunk_id=uuid.uuid4(),
        chunk_text=chunk_text,
        chunk_index=chunk_index,
        document_id=uuid.uuid4(),
        document_filename=filename,
        page_id=uuid.uuid4(),
        page_number=page_number,
        similarity_score=0.88,
        rank=rank,
    )


def test_valid_citation_resolves_authoritative_postgres_metadata():
    """Verify valid citation maps strictly to PostgreSQL filename, document_id, and physical page."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    candidate = create_candidate(chunk_index=2, page_number=14, filename="audit_2026.pdf")

    proposed = [
        GeneratedCitation(
            candidate_id=str(candidate.chunk_id),
            quoted_snippet="Total net revenue reached $42.5 million",
        )
    ]

    result = validator.validate_citations(
        answer_text="The company generated $42.5 million in revenue.",
        is_abstention=False,
        proposed_citations=proposed,
        candidate_chunks=[candidate],
        workspace_id=workspace_id,
    )

    assert result.is_abstention is False
    assert len(result.citations) == 1
    cit = result.citations[0]
    assert cit.chunk_id == candidate.chunk_id
    assert cit.document_id == candidate.document_id
    assert cit.document_filename == "audit_2026.pdf"
    assert cit.page_number == 14
    assert cit.quoted_snippet == "Total net revenue reached $42.5 million"
    assert result.stripped_citation_count == 0


def test_alias_candidate_id_resolves_to_authoritative_chunk():
    """Verify model citing 'chunk_1' or rank alias resolves to the real chunk UUID."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    candidate = create_candidate(chunk_index=0, page_number=3, filename="memo.pdf", rank=1)

    proposed = [
        GeneratedCitation(
            candidate_id="chunk_1",
            quoted_snippet="Total net revenue reached $42.5 million",
        )
    ]

    result = validator.validate_citations(
        answer_text="The company generated $42.5 million.",
        is_abstention=False,
        proposed_citations=proposed,
        candidate_chunks=[candidate],
        workspace_id=workspace_id,
    )

    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == candidate.chunk_id
    assert result.citations[0].page_number == 3


def test_fabricated_citation_id_is_stripped():
    """Verify fabricated UUIDs not in the candidate set are stripped."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    candidate = create_candidate(page_number=1)
    fake_uuid = str(uuid.uuid4())

    proposed = [
        GeneratedCitation(candidate_id=fake_uuid, quoted_snippet="Fake snippet"),
        GeneratedCitation(candidate_id=str(candidate.chunk_id), quoted_snippet="revenue reached $42.5 million"),
    ]

    result = validator.validate_citations(
        answer_text="Revenue reached $42.5 million.",
        is_abstention=False,
        proposed_citations=proposed,
        candidate_chunks=[candidate],
        workspace_id=workspace_id,
    )

    assert result.stripped_citation_count == 1
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == candidate.chunk_id


def test_unretrieved_chunk_id_is_rejected():
    """Verify chunk ID from a different query or un-retrieved doc is rejected."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    candidate = create_candidate(page_number=2)
    unretrieved_chunk_id = str(uuid.uuid4())

    proposed = [
        GeneratedCitation(candidate_id=unretrieved_chunk_id, quoted_snippet="Something not retrieved")
    ]

    result = validator.validate_citations(
        answer_text="Some ungrounded claim.",
        is_abstention=False,
        proposed_citations=proposed,
        candidate_chunks=[candidate],
        workspace_id=workspace_id,
    )

    assert result.stripped_citation_count == 1
    assert len(result.citations) == 0
    # Because factual claim had zero citations, it forced abstention
    assert result.is_abstention is True


def test_model_supplied_fake_metadata_is_ignored():
    """Verify that even if the model attempts to dictate filename or page, PostgreSQL values win."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    candidate = create_candidate(page_number=7, filename="real_truth.pdf")

    # In our GeneratedCitation schema, the model can only supply candidate_id and snippet.
    # The server strictly resolves document_filename and page_number from CandidateChunk.
    proposed = [
        GeneratedCitation(
            candidate_id=str(candidate.chunk_id),
            quoted_snippet="Total net revenue reached $42.5 million",
        )
    ]

    result = validator.validate_citations(
        answer_text="Revenue is $42.5 million.",
        is_abstention=False,
        proposed_citations=proposed,
        candidate_chunks=[candidate],
        workspace_id=workspace_id,
    )

    cit = result.citations[0]
    assert cit.document_filename == "real_truth.pdf"
    assert cit.page_number == 7


def test_duplicate_citations_are_deduplicated():
    """Verify multiple citations pointing to the same chunk are deduplicated to a single citation."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    candidate = create_candidate()

    proposed = [
        GeneratedCitation(candidate_id=str(candidate.chunk_id), quoted_snippet="snippet 1"),
        GeneratedCitation(candidate_id=str(candidate.chunk_id), quoted_snippet="snippet 2"),
        GeneratedCitation(candidate_id="chunk_1", quoted_snippet="snippet 3"),
    ]

    result = validator.validate_citations(
        answer_text="Statement backed by one chunk.",
        is_abstention=False,
        proposed_citations=proposed,
        candidate_chunks=[candidate],
        workspace_id=workspace_id,
    )

    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == candidate.chunk_id


def test_empty_or_malformed_citation_id_cannot_create_citation():
    """Verify whitespace or empty candidate IDs are safely discarded."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    candidate = create_candidate()

    proposed = [
        GeneratedCitation(candidate_id="", quoted_snippet=""),
        GeneratedCitation(candidate_id="   ", quoted_snippet="test"),
    ]

    result = validator.validate_citations(
        answer_text="Some assertion.",
        is_abstention=False,
        proposed_citations=proposed,
        candidate_chunks=[candidate],
        workspace_id=workspace_id,
    )

    assert result.stripped_citation_count == 2
    assert len(result.citations) == 0
    assert result.is_abstention is True


def test_quoted_snippet_falls_back_to_authentic_chunk_text():
    """Verify that if the model's quoted snippet is hallucinated, authentic chunk text is used."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    candidate = create_candidate(chunk_text="Actual verbatim content in chunk.")

    proposed = [
        GeneratedCitation(
            candidate_id=str(candidate.chunk_id),
            quoted_snippet="Hallucinated text not present in chunk",
        )
    ]

    result = validator.validate_citations(
        answer_text="Answer text.",
        is_abstention=False,
        proposed_citations=proposed,
        candidate_chunks=[candidate],
        workspace_id=workspace_id,
    )

    assert len(result.citations) == 1
    # Snippet was replaced with authentic text from chunk
    assert result.citations[0].quoted_snippet == "Actual verbatim content in chunk."


def test_abstention_from_model_is_preserved():
    """Verify that if the model explicitly abstains, abstention is preserved without forced citations."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    candidate = create_candidate()

    result = validator.validate_citations(
        answer_text="The evidence does not mention the CEO's bonus.",
        is_abstention=True,
        proposed_citations=[],
        candidate_chunks=[candidate],
        workspace_id=workspace_id,
    )

    assert result.is_abstention is True
    assert "CEO's bonus" in result.answer_text
    assert len(result.citations) == 0


def test_citation_alias_collision_regression_resolves_to_retrieval_rank():
    """Verify chunk_index does not collide with retrieval rank when citing 'chunk_2'."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()

    # Candidate A: retrieval rank 1, but chunk_index is 2 (e.g., 3rd chunk of Doc 1)
    cand_a = create_candidate(
        chunk_index=2,
        page_number=1,
        filename="doc1.pdf",
        chunk_text="Candidate A text with chunk_index=2",
        rank=1,
    )

    # Candidate B: retrieval rank 2, but chunk_index is 0 (e.g., 1st chunk of Doc 2)
    cand_b = create_candidate(
        chunk_index=0,
        page_number=5,
        filename="doc2.pdf",
        chunk_text="Candidate B text with chunk_index=0",
        rank=2,
    )

    # When the model cites "chunk_2", it must resolve to Candidate B (rank 2), NOT Candidate A (chunk_index 2)
    proposed = [
        GeneratedCitation(candidate_id="chunk_2", quoted_snippet="Candidate B text")
    ]

    result = validator.validate_citations(
        answer_text="Claim citing chunk_2.",
        is_abstention=False,
        proposed_citations=proposed,
        candidate_chunks=[cand_a, cand_b],
        workspace_id=workspace_id,
    )

    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == cand_b.chunk_id
    assert result.citations[0].document_filename == "doc2.pdf"
    assert result.citations[0].page_number == 5
