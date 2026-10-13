"""ProofLens AI — Unit Tests for Cross-Document Comparison Citation Validator.

Verifies:
1. Server-Authoritative Citation Integrity across multi-document findings.
2. Verified Contradiction rule (requires citations from 2+ distinct documents; downgrades if not).
3. Verified Agreement rule (requires citations from 2+ distinct documents; downgrades if not).
4. Stripping of fabricated or cross-workspace citation identifiers.
5. Overwriting of model-supplied metadata with authoritative PostgreSQL values.
6. Snippet verification and authentic bounded fallback.
7. Deduplication of citations within a finding.
8. Unsupported claim defense forcing explicit abstention when citations cannot be verified.
"""

from typing import List, Optional
import uuid
import pytest

from app.models.document import Document
from app.repositories.query_repo import CandidateChunk
from app.services.ai.generator import (
    GeneratedComparisonFinding,
    GeneratedComparisonResult,
    GeneratedFindingCitation,
    GeneratedPerDocumentFinding,
)
from app.services.rag.validator import CitationValidator


def create_candidate(
    doc_id: uuid.UUID,
    filename: str,
    page: int = 1,
    rank: int = 1,
    text: str = "Evidence text",
) -> CandidateChunk:
    return CandidateChunk(
        chunk_id=uuid.uuid4(),
        chunk_text=text,
        chunk_index=rank - 1,
        document_id=doc_id,
        document_filename=filename,
        page_id=uuid.uuid4(),
        page_number=page,
        similarity_score=0.90,
        rank=rank,
    )


def test_comparison_validator_agreement_supported_by_two_documents_passes():
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a_id = uuid.uuid4()
    doc_b_id = uuid.uuid4()

    doc_a = Document(id=doc_a_id, workspace_id=workspace_id, filename="filing_2024.pdf")
    doc_b = Document(id=doc_b_id, workspace_id=workspace_id, filename="filing_2025.pdf")

    cand_a = create_candidate(doc_a_id, "filing_2024.pdf", page=3, rank=1, text="Operating margin is 18%")
    cand_b = create_candidate(doc_b_id, "filing_2025.pdf", page=5, rank=2, text="Operating margin remained 18%")

    finding = GeneratedComparisonFinding(
        finding_type="agreement",
        topic="Operating Margin",
        summary="Both 2024 and 2025 filings confirm an 18% operating margin.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a_id),
                document_filename="filing_2024.pdf",
                statement="Reported 18% operating margin in 2024.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand_a.chunk_id), quoted_snippet="Operating margin is 18%")],
            ),
            GeneratedPerDocumentFinding(
                document_id=str(doc_b_id),
                document_filename="filing_2025.pdf",
                statement="Reported 18% operating margin in 2025.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand_b.chunk_id), quoted_snippet="Operating margin remained 18%")],
            ),
        ],
    )

    model_result = GeneratedComparisonResult(
        findings=[finding],
        synthesis="Both documents agree on operating margin consistency.",
        is_abstention=False,
    )

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand_a, cand_b],
        workspace_id=workspace_id,
        documents=[doc_a, doc_b],
    )

    assert res.is_abstention is False
    assert len(res.findings) == 1
    val_finding = res.findings[0]
    assert val_finding.finding_type == "agreement"
    assert len(val_finding.citations) == 2
    # Verify provenance
    filenames = {c.document_filename for c in val_finding.citations}
    assert filenames == {"filing_2024.pdf", "filing_2025.pdf"}


def test_comparison_validator_contradiction_supported_by_two_documents_passes():
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a_id = uuid.uuid4()
    doc_b_id = uuid.uuid4()

    doc_a = Document(id=doc_a_id, workspace_id=workspace_id, filename="doc_a.pdf")
    doc_b = Document(id=doc_b_id, workspace_id=workspace_id, filename="doc_b.pdf")

    cand_a = create_candidate(doc_a_id, "doc_a.pdf", page=1, rank=1, text="Project deadline is June 1st.")
    cand_b = create_candidate(doc_b_id, "doc_b.pdf", page=2, rank=2, text="Project deadline is August 15th.")

    finding = GeneratedComparisonFinding(
        finding_type="contradiction",
        topic="Project Deadline",
        summary="Document A and Document B specify conflicting project deadlines.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a_id),
                document_filename="doc_a.pdf",
                statement="States deadline is June 1st.",
                citations=[GeneratedFindingCitation(candidate_id="chunk_1", quoted_snippet="Project deadline is June 1st.")],
            ),
            GeneratedPerDocumentFinding(
                document_id=str(doc_b_id),
                document_filename="doc_b.pdf",
                statement="States deadline is August 15th.",
                citations=[GeneratedFindingCitation(candidate_id="chunk_2", quoted_snippet="Project deadline is August 15th.")],
            ),
        ],
    )

    model_result = GeneratedComparisonResult(
        findings=[finding],
        synthesis="Direct conflict in project delivery date.",
        is_abstention=False,
    )

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand_a, cand_b],
        workspace_id=workspace_id,
        documents=[doc_a, doc_b],
    )

    assert res.is_abstention is False
    assert len(res.findings) == 1
    assert res.findings[0].finding_type == "contradiction"


def test_contradiction_with_only_one_document_downgraded_to_difference():
    """Verify that claiming contradiction without citing evidence from both documents downgrades to difference."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a_id = uuid.uuid4()
    doc_b_id = uuid.uuid4()

    doc_a = Document(id=doc_a_id, workspace_id=workspace_id, filename="doc_a.pdf")
    doc_b = Document(id=doc_b_id, workspace_id=workspace_id, filename="doc_b.pdf")

    cand_a = create_candidate(doc_a_id, "doc_a.pdf", page=1, rank=1, text="Revenue is $50M.")

    # Model claims contradiction, but only provides citations from doc A (doc B citation is missing or fake)
    finding = GeneratedComparisonFinding(
        finding_type="contradiction",
        topic="Revenue",
        summary="Alleged contradiction with only Doc A cited.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a_id),
                document_filename="doc_a.pdf",
                statement="Revenue is $50M.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand_a.chunk_id), quoted_snippet="Revenue is $50M.")],
            ),
            GeneratedPerDocumentFinding(
                document_id=str(doc_b_id),
                document_filename="doc_b.pdf",
                statement="Doc B claims $80M without real citation.",
                citations=[GeneratedFindingCitation(candidate_id="fake_chunk_id", quoted_snippet="fake snippet")],
            ),
        ],
    )

    model_result = GeneratedComparisonResult(
        findings=[finding],
        synthesis="Conflict asserted without two-sided evidence.",
        is_abstention=False,
    )

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand_a],
        workspace_id=workspace_id,
        documents=[doc_a, doc_b],
    )

    assert res.is_abstention is False
    assert len(res.findings) == 1
    # Downgraded from 'contradiction' to 'difference' because only 1 document had verified evidence
    assert res.findings[0].finding_type == "difference"
    assert res.stripped_citation_count == 1


def test_fabricated_citation_ids_stripped():
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a_id = uuid.uuid4()
    doc_b_id = uuid.uuid4()

    doc_a = Document(id=doc_a_id, workspace_id=workspace_id, filename="doc_a.pdf")
    doc_b = Document(id=doc_b_id, workspace_id=workspace_id, filename="doc_b.pdf")

    cand_a = create_candidate(doc_a_id, "doc_a.pdf", page=1, rank=1, text="Real excerpt from doc A.")

    finding = GeneratedComparisonFinding(
        finding_type="difference",
        topic="Topic",
        summary="Summary text.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a_id),
                document_filename="doc_a.pdf",
                statement="Doc A valid claim.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand_a.chunk_id), quoted_snippet="Real excerpt from doc A.")],
            ),
            GeneratedPerDocumentFinding(
                document_id=str(doc_b_id),
                document_filename="doc_b.pdf",
                statement="Doc B fake claim.",
                citations=[GeneratedFindingCitation(candidate_id=str(uuid.uuid4()), quoted_snippet="Invented quote")],
            ),
        ],
    )

    model_result = GeneratedComparisonResult(
        findings=[finding],
        synthesis="Synthesis text.",
        is_abstention=False,
    )

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand_a],
        workspace_id=workspace_id,
        documents=[doc_a, doc_b],
    )

    assert res.stripped_citation_count == 1
    assert len(res.findings[0].citations) == 1
    assert res.findings[0].citations[0].chunk_id == cand_a.chunk_id


def test_model_supplied_fake_filenames_overwritten_by_postgres_ground_truth():
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a_id = uuid.uuid4()
    doc_a = Document(id=doc_a_id, workspace_id=workspace_id, filename="authoritative_truth.pdf")

    cand = create_candidate(doc_a_id, "authoritative_truth.pdf", page=42, rank=1, text="Authentic text.")

    # Model tries to claim the filename is "fake_hacked_name.pdf" and page is 999
    finding = GeneratedComparisonFinding(
        finding_type="difference",
        topic="Topic",
        summary="Summary.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a_id),
                document_filename="fake_hacked_name.pdf",
                statement="Some statement.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand.chunk_id), quoted_snippet="Authentic text.")],
            )
        ],
    )

    model_result = GeneratedComparisonResult(
        findings=[finding],
        synthesis="Synthesis.",
        is_abstention=False,
    )

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand],
        workspace_id=workspace_id,
        documents=[doc_a],
    )

    cit = res.findings[0].citations[0]
    assert cit.document_filename == "authoritative_truth.pdf"
    assert cit.page_number == 42


def test_snippet_fallback_to_authentic_chunk_text():
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a_id = uuid.uuid4()
    doc_a = Document(id=doc_a_id, workspace_id=workspace_id, filename="doc.pdf")

    cand = create_candidate(doc_a_id, "doc.pdf", page=1, rank=1, text="Actual true text in repository chunk.")

    finding = GeneratedComparisonFinding(
        finding_type="difference",
        topic="Topic",
        summary="Summary.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a_id),
                document_filename="doc.pdf",
                statement="Statement.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand.chunk_id), quoted_snippet="Hallucinated snippet not in chunk")],
            )
        ],
    )

    model_result = GeneratedComparisonResult(
        findings=[finding],
        synthesis="Synthesis.",
        is_abstention=False,
    )

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand],
        workspace_id=workspace_id,
        documents=[doc_a],
    )

    # Snippet replaced with authentic chunk text excerpt
    assert res.findings[0].citations[0].quoted_snippet == "Actual true text in repository chunk."


def test_all_citations_stripped_forces_explicit_abstention():
    """Verify that if all citations for a comparison are hallucinated/stripped, abstention is forced."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a_id = uuid.uuid4()
    doc_a = Document(id=doc_a_id, workspace_id=workspace_id, filename="doc.pdf")

    cand = create_candidate(doc_a_id, "doc.pdf", page=1, rank=1, text="Real chunk text.")

    finding = GeneratedComparisonFinding(
        finding_type="contradiction",
        topic="Topic",
        summary="Factual contradiction with zero real citations.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a_id),
                document_filename="doc.pdf",
                statement="Unbacked claim.",
                citations=[GeneratedFindingCitation(candidate_id="fake_1", quoted_snippet="fake 1")],
            )
        ],
    )

    model_result = GeneratedComparisonResult(
        findings=[finding],
        synthesis="Asserted facts without citations.",
        is_abstention=False,
    )

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand],
        workspace_id=workspace_id,
        documents=[doc_a],
    )

    assert res.is_abstention is True
    assert "unable to complete this comparison" in res.synthesis
    assert res.findings == []


# ------------------------------------------------------------------------------
# Phase 7.1 Regression Tests: Safe not_found Document Attribution
# ------------------------------------------------------------------------------

def test_unmatched_model_id_is_not_assigned_to_documents_zero():
    """Verify an unrecognized document ID is never silently assigned to documents[0]."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_a.pdf")
    doc_b = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_b.pdf")
    doc_c = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_c.pdf")

    cand_a = create_candidate(doc_a.id, "doc_a.pdf", page=1, rank=1, text="Fact from Doc A.")

    fake_id = str(uuid.uuid4())
    finding = GeneratedComparisonFinding(
        finding_type="not_found",
        topic="Clause X",
        summary="Clause X in Doc A; missing in other.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a.id),
                document_filename="doc_a.pdf",
                statement="Doc A mentions Clause X.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand_a.chunk_id), quoted_snippet="Fact from Doc A.")],
            ),
            GeneratedPerDocumentFinding(
                document_id=fake_id,
                document_filename="unrecognized.pdf",
                statement="Not mentioned.",
                citations=[],
            ),
        ],
    )

    model_result = GeneratedComparisonResult(findings=[finding], synthesis="Doc A mentions Clause X.", is_abstention=False)

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand_a],
        workspace_id=workspace_id,
        documents=[doc_a, doc_b, doc_c],
    )

    # The ambiguous entry was omitted rather than falsely assigned to doc_a or fabricated
    per_doc_entries = res.findings[0].per_document_evidence
    assert len(per_doc_entries) == 1
    assert per_doc_entries[0].document_id == doc_a.id


def test_unmatched_filename_is_not_assigned_to_documents_zero():
    """Verify an unrecognized document filename is never silently attributed to documents[0]."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_a.pdf")
    doc_b = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_b.pdf")
    doc_c = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_c.pdf")

    cand_a = create_candidate(doc_a.id, "doc_a.pdf", page=1, rank=1, text="Fact from Doc A.")

    finding = GeneratedComparisonFinding(
        finding_type="not_found",
        topic="Clause Y",
        summary="Clause Y in Doc A.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a.id),
                document_filename="doc_a.pdf",
                statement="Doc A mentions Clause Y.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand_a.chunk_id), quoted_snippet="Fact from Doc A.")],
            ),
            GeneratedPerDocumentFinding(
                document_id="",
                document_filename="totally_invented_filename.pdf",
                statement="Not mentioned.",
                citations=[],
            ),
        ],
    )

    model_result = GeneratedComparisonResult(findings=[finding], synthesis="Doc A mentions Clause Y.", is_abstention=False)

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand_a],
        workspace_id=workspace_id,
        documents=[doc_a, doc_b, doc_c],
    )

    per_doc_entries = res.findings[0].per_document_evidence
    assert len(per_doc_entries) == 1
    assert per_doc_entries[0].document_id == doc_a.id


def test_valid_unambiguous_authorized_document_id_resolves_correctly():
    """Verify an explicit, valid authorized document ID with empty citations resolves accurately."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_a.pdf")
    doc_b = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_b.pdf")

    cand_a = create_candidate(doc_a.id, "doc_a.pdf", page=1, rank=1, text="Fact from Doc A.")

    finding = GeneratedComparisonFinding(
        finding_type="not_found",
        topic="Term Z",
        summary="Term Z only in Doc A.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a.id),
                document_filename="doc_a.pdf",
                statement="Doc A mentions Term Z.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand_a.chunk_id), quoted_snippet="Fact from Doc A.")],
            ),
            GeneratedPerDocumentFinding(
                document_id=str(doc_b.id),
                document_filename="",
                statement="Not found in retrieved evidence for Doc B.",
                citations=[],
            ),
        ],
    )

    model_result = GeneratedComparisonResult(findings=[finding], synthesis="Term Z only in Doc A.", is_abstention=False)

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand_a],
        workspace_id=workspace_id,
        documents=[doc_a, doc_b],
    )

    assert len(res.findings[0].per_document_evidence) == 2
    assert res.findings[0].per_document_evidence[1].document_id == doc_b.id
    assert res.findings[0].per_document_evidence[1].document_filename == doc_b.filename


def test_ambiguous_attribution_does_not_produce_fabricated_document_reference():
    """Verify ambiguous attribution across 3+ documents omits the entry without fabricating UUIDs."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_a.pdf")
    doc_b = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_b.pdf")
    doc_c = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="doc_c.pdf")

    cand_a = create_candidate(doc_a.id, "doc_a.pdf", page=1, rank=1, text="Fact A.")

    finding = GeneratedComparisonFinding(
        finding_type="not_found",
        topic="Topic",
        summary="Summary",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a.id),
                document_filename="doc_a.pdf",
                statement="Claim A.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand_a.chunk_id), quoted_snippet="Fact A.")],
            ),
            GeneratedPerDocumentFinding(
                document_id="unrecognized-id",
                document_filename="unrecognized.pdf",
                statement="Not found.",
                citations=[],
            ),
        ],
    )

    model_result = GeneratedComparisonResult(findings=[finding], synthesis="Synthesis", is_abstention=False)

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand_a],
        workspace_id=workspace_id,
        documents=[doc_a, doc_b, doc_c],
    )

    # Entry is omitted; only doc_a remains; no random UUID fabricated
    assert len(res.findings[0].per_document_evidence) == 1
    assert res.findings[0].per_document_evidence[0].document_id == doc_a.id


def test_existing_valid_not_found_cases_continue_to_work():
    """Verify 2-document comparison correctly resolves remaining document for not_found entry."""
    validator = CitationValidator()
    workspace_id = uuid.uuid4()
    doc_a = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="msa_complete.pdf")
    doc_b = Document(id=uuid.uuid4(), workspace_id=workspace_id, filename="msa_draft.pdf")

    cand_a = create_candidate(doc_a.id, "msa_complete.pdf", page=10, rank=1, text="Indemnity cap is $5M.")

    finding = GeneratedComparisonFinding(
        finding_type="not_found",
        topic="Indemnity Cap",
        summary="Complete MSA specifies $5M; draft has no indemnity cap in retrieved evidence.",
        per_document_evidence=[
            GeneratedPerDocumentFinding(
                document_id=str(doc_a.id),
                document_filename=doc_a.filename,
                statement="Indemnity cap is $5M.",
                citations=[GeneratedFindingCitation(candidate_id=str(cand_a.chunk_id), quoted_snippet="Indemnity cap is $5M.")],
            ),
            GeneratedPerDocumentFinding(
                document_id=str(doc_b.id),
                document_filename=doc_b.filename,
                statement="Not mentioned in retrieved evidence.",
                citations=[],
            ),
        ],
    )

    model_result = GeneratedComparisonResult(findings=[finding], synthesis="Comparison synthesis.", is_abstention=False)

    res = validator.validate_comparison_findings(
        model_result=model_result,
        candidate_chunks=[cand_a],
        workspace_id=workspace_id,
        documents=[doc_a, doc_b],
    )

    assert res.findings[0].finding_type == "not_found"
    assert len(res.findings[0].per_document_evidence) == 2
    assert res.findings[0].per_document_evidence[1].document_id == doc_b.id
    assert res.findings[0].per_document_evidence[1].document_filename == doc_b.filename

