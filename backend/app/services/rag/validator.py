"""ProofLens AI — Server-Authoritative Citation Validator.

Enforces Structural Citation Integrity per PRD and TECHNICAL-DESIGN.md Section 6.2:
1. Deterministic Server Invariant: 100% of citations returned to the API map to
   actual candidate chunks retrieved from PostgreSQL for the current query and workspace.
2. Ground-Truth Overwrite: Overwrites all model-supplied filenames, document IDs,
   and page numbers with authoritative values directly from PostgreSQL records.
3. Stripping of Hallucinations: Hallucinated, cross-workspace, or un-retrieved
   chunk IDs are strictly stripped.
4. Unsupported Claim Defense: If all citations for a factual claim are stripped,
   the answer is safely converted to an explicit abstention response.

Note on Limitation:
Structural Citation Integrity deterministically verifies source passage existence
and provenance in PostgreSQL. It does not mathematically prove semantic claim entailment
(which is evaluated empirically via benchmark suites).
"""

from dataclasses import dataclass
import uuid
from typing import Dict, List, Optional, Set

from app.core.logging import logger
from app.repositories.query_repo import CandidateChunk
from app.services.ai.generator import GeneratedCitation, GeneratedComparisonResult


@dataclass(frozen=True)
class ValidatedCitation:
    """Authoritative citation record verified against PostgreSQL candidate chunks."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str
    page_number: int
    quoted_snippet: str
    id: Optional[uuid.UUID] = None


@dataclass(frozen=True)
class ValidatedPerDocumentFinding:
    """Authoritative per-document evidence for a comparison finding."""

    document_id: uuid.UUID
    document_filename: str
    statement: str
    citations: List[ValidatedCitation]


@dataclass(frozen=True)
class ValidatedComparisonFinding:
    """Authoritative comparison finding with validated citations and classification."""

    finding_type: str
    topic: str
    summary: str
    per_document_evidence: List[ValidatedPerDocumentFinding]
    citations: List[ValidatedCitation]


@dataclass(frozen=True)
class CitationValidationResult:
    """Result of citation validation containing sanitized answer and verified citations."""

    answer_text: str
    is_abstention: bool
    citations: List[ValidatedCitation]
    stripped_citation_count: int


@dataclass(frozen=True)
class ComparisonValidationResult:
    """Result of cross-document comparison validation with verified findings and citations."""

    findings: List[ValidatedComparisonFinding]
    synthesis: str
    limitations: Optional[str]
    is_abstention: bool
    stripped_citation_count: int
    all_validated_citations: List[ValidatedCitation]



class CitationValidator:
    """Server-authoritative citation validation engine."""

    def validate_citations(
        self,
        answer_text: str,
        is_abstention: bool,
        proposed_citations: List[GeneratedCitation],
        candidate_chunks: List[CandidateChunk],
        workspace_id: uuid.UUID,
    ) -> CitationValidationResult:
        """Validate and resolve model-proposed citations against retrieved candidate chunks.

        Args:
            answer_text: Synthesized answer text from generation model.
            is_abstention: Whether model flagged insufficient evidence.
            proposed_citations: Citations proposed by generation model.
            candidate_chunks: Authoritative candidate chunks retrieved by server.
            workspace_id: Current workspace UUID scope.

        Returns:
            CitationValidationResult with guaranteed authentic citations.
        """
        # 1. Build lookup tables for authoritative candidate chunks
        lookup_by_uuid: Dict[str, CandidateChunk] = {
            str(c.chunk_id).lower(): c for c in candidate_chunks
        }
        lookup_by_alias: Dict[str, CandidateChunk] = {}
        for c in candidate_chunks:
            lookup_by_alias[f"chunk_{c.rank}".lower()] = c
            lookup_by_alias[f"evidence_{c.rank}".lower()] = c
            lookup_by_alias[str(c.rank)] = c

        validated_citations: List[ValidatedCitation] = []
        seen_chunk_ids: Set[uuid.UUID] = set()
        stripped_count = 0

        # 2. Inspect each proposed citation
        for prop in proposed_citations:
            raw_id = prop.candidate_id.strip().lower() if prop.candidate_id else ""
            if not raw_id:
                stripped_count += 1
                continue

            # Authoritative lookup in server-retrieved set
            candidate = lookup_by_uuid.get(raw_id) or lookup_by_alias.get(raw_id)

            if not candidate:
                stripped_count += 1
                logger.warning(
                    "Stripping hallucinated or un-retrieved citation identifier",
                    extra={"extra": {"raw_candidate_id": raw_id, "workspace_id": str(workspace_id)}},
                )
                continue

            # Deduplication: preserve single citation per unique chunk
            if candidate.chunk_id in seen_chunk_ids:
                continue

            # Verify quoted snippet against authoritative chunk text
            snippet = prop.quoted_snippet.strip() if prop.quoted_snippet else ""
            if not snippet or snippet not in candidate.chunk_text:
                # Fall back to an authentic bounded excerpt directly from chunk_text
                snippet = candidate.chunk_text[:300].strip()

            # Construct verified citation using ONLY PostgreSQL authoritative columns
            validated = ValidatedCitation(
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                document_filename=candidate.document_filename,
                page_number=candidate.page_number,
                quoted_snippet=snippet,
            )
            validated_citations.append(validated)
            seen_chunk_ids.add(candidate.chunk_id)

        # 3. Acceptance Invariant & Unsupported Claim Defense:
        # If the model produced a factual claim (not an abstention), but all citations were stripped
        # or zero citations were provided, abstain rather than serving an ungrounded hallucination.
        final_answer_text = answer_text
        final_is_abstention = is_abstention

        if not final_is_abstention and not validated_citations:
            logger.warning(
                "Factual answer contained zero valid citations after server-side validation. Forcing abstention.",
                extra={"extra": {"stripped_count": stripped_count, "workspace_id": str(workspace_id)}},
            )
            final_is_abstention = True
            final_answer_text = (
                "I am unable to confirm this answer because no verified citations from the workspace documents "
                "could be validated to support this claim."
            )

        return CitationValidationResult(
            answer_text=final_answer_text,
            is_abstention=final_is_abstention,
            citations=validated_citations,
            stripped_citation_count=stripped_count,
        )

    def validate_comparison_findings(
        self,
        model_result: GeneratedComparisonResult,
        candidate_chunks: List[CandidateChunk],
        workspace_id: uuid.UUID,
        documents: List[Any],
    ) -> ComparisonValidationResult:
        """Validate multi-document comparison findings against candidate chunks.

        Guarantees:
        1. 100% of citations resolve to authoritative candidate chunks retrieved for this comparison.
        2. Ground-truth metadata (document_id, document_filename, page_number) is populated directly
           from CandidateChunk records in PostgreSQL.
        3. Fabricated or cross-workspace citations are stripped.
        4. Verified contradiction rule: A 'contradiction' finding MUST have verified citations from
           at least 2 distinct documents. If not, the classification is downgraded to 'difference'
           or 'not_found'.
        5. Verified agreement rule: An 'agreement' finding MUST have verified citations from at least
           2 distinct documents. If not, it is downgraded to 'difference'.
        6. Unsupported claim defense: If the model claimed is_abstention=False but 0 valid citations
           were verified across all findings, force explicit abstention.
        """
        lookup_by_uuid: Dict[str, CandidateChunk] = {
            str(c.chunk_id).lower(): c for c in candidate_chunks
        }
        lookup_by_alias: Dict[str, CandidateChunk] = {}
        for c in candidate_chunks:
            lookup_by_alias[f"chunk_{c.rank}".lower()] = c
            lookup_by_alias[f"evidence_{c.rank}".lower()] = c
            lookup_by_alias[str(c.rank)] = c

        doc_map_by_id: Dict[str, Any] = {str(d.id).lower(): d for d in documents}
        doc_map_by_name: Dict[str, Any] = {d.filename.lower(): d for d in documents}

        validated_findings: List[ValidatedComparisonFinding] = []
        all_validated_citations: List[ValidatedCitation] = []
        seen_all_chunk_ids: Set[uuid.UUID] = set()
        stripped_count = 0

        for finding in model_result.findings:
            finding_validated_citations: List[ValidatedCitation] = []
            validated_per_doc_list: List[ValidatedPerDocumentFinding] = []
            finding_seen_chunks: Set[uuid.UUID] = set()

            for per_doc in finding.per_document_evidence:
                doc_citations: List[ValidatedCitation] = []

                # Resolve document record
                raw_doc_id = per_doc.document_id.strip().lower() if per_doc.document_id else ""
                matched_doc = doc_map_by_id.get(raw_doc_id) or doc_map_by_name.get(
                    per_doc.document_filename.strip().lower()
                )

                for prop_cit in per_doc.citations:
                    raw_id = prop_cit.candidate_id.strip().lower() if prop_cit.candidate_id else ""
                    if not raw_id:
                        stripped_count += 1
                        continue

                    candidate = lookup_by_uuid.get(raw_id) or lookup_by_alias.get(raw_id)
                    if not candidate:
                        stripped_count += 1
                        logger.warning(
                            "Stripping hallucinated candidate ID in comparison finding",
                            extra={"extra": {"raw_id": raw_id, "workspace_id": str(workspace_id)}},
                        )
                        continue

                    # Deduplication within finding
                    if candidate.chunk_id in finding_seen_chunks:
                        continue

                    snippet = prop_cit.quoted_snippet.strip() if prop_cit.quoted_snippet else ""
                    if not snippet or snippet not in candidate.chunk_text:
                        snippet = candidate.chunk_text[:300].strip()

                    val_cit = ValidatedCitation(
                        chunk_id=candidate.chunk_id,
                        document_id=candidate.document_id,
                        document_filename=candidate.document_filename,
                        page_number=candidate.page_number,
                        quoted_snippet=snippet,
                    )
                    doc_citations.append(val_cit)
                    finding_validated_citations.append(val_cit)
                    finding_seen_chunks.add(candidate.chunk_id)

                    if candidate.chunk_id not in seen_all_chunk_ids:
                        all_validated_citations.append(val_cit)
                        seen_all_chunk_ids.add(candidate.chunk_id)

                # Determine authoritative document identity for per_doc entry
                if matched_doc:
                    auth_doc_id = matched_doc.id
                    auth_doc_filename = matched_doc.filename
                elif doc_citations:
                    auth_doc_id = doc_citations[0].document_id
                    auth_doc_filename = doc_citations[0].document_filename
                else:
                    # Attempt safe, unambiguous inference from remaining unassigned authorized documents
                    assigned_doc_ids = {pd.document_id for pd in validated_per_doc_list}
                    unassigned_docs = [d for d in documents if d.id not in assigned_doc_ids]
                    if len(unassigned_docs) == 1:
                        auth_doc_id = unassigned_docs[0].id
                        auth_doc_filename = unassigned_docs[0].filename
                    else:
                        logger.warning(
                            "Omitting unresolvable per-document entry: document ID/filename not recognized and cannot be unambiguously inferred",
                            extra={
                                "extra": {
                                    "raw_doc_id": raw_doc_id,
                                    "raw_filename": per_doc.document_filename,
                                    "unassigned_count": len(unassigned_docs),
                                    "workspace_id": str(workspace_id),
                                }
                            },
                        )
                        continue

                validated_per_doc = ValidatedPerDocumentFinding(
                    document_id=auth_doc_id,
                    document_filename=auth_doc_filename,
                    statement=per_doc.statement.strip(),
                    citations=doc_citations,
                )
                validated_per_doc_list.append(validated_per_doc)

            # Enforce Contradiction / Agreement Verification Rule
            distinct_citing_docs = {c.document_id for c in finding_validated_citations}
            final_type = finding.finding_type.strip().lower()

            if final_type == "contradiction" and len(distinct_citing_docs) < 2:
                logger.info(
                    "Downgrading unverified contradiction: lacks verified citations from 2+ distinct documents",
                    extra={"extra": {"topic": finding.topic, "citing_docs_count": len(distinct_citing_docs)}},
                )
                final_type = "difference" if finding_validated_citations else "insufficient_evidence"

            elif final_type == "agreement" and len(distinct_citing_docs) < 2:
                logger.info(
                    "Downgrading unverified agreement: lacks verified citations from 2+ distinct documents",
                    extra={"extra": {"topic": finding.topic, "citing_docs_count": len(distinct_citing_docs)}},
                )
                final_type = "difference" if finding_validated_citations else "insufficient_evidence"

            if not finding_validated_citations and final_type not in ("not_found", "insufficient_evidence"):
                final_type = "insufficient_evidence"

            if not validated_per_doc_list:
                final_type = "insufficient_evidence"

            val_finding = ValidatedComparisonFinding(
                finding_type=final_type,
                topic=finding.topic.strip(),
                summary=finding.summary.strip(),
                per_document_evidence=validated_per_doc_list,
                citations=finding_validated_citations,
            )
            validated_findings.append(val_finding)

        # Acceptance Invariant & Unsupported Claim Defense
        final_is_abstention = model_result.is_abstention
        final_synthesis = model_result.synthesis
        final_limitations = model_result.limitations

        if not final_is_abstention and not all_validated_citations:
            logger.warning(
                "Comparison produced zero valid citations after server-side validation. Forcing abstention.",
                extra={"extra": {"stripped_count": stripped_count, "workspace_id": str(workspace_id)}},
            )
            final_is_abstention = True
            final_synthesis = (
                "I am unable to complete this comparison because no verified citations from the workspace documents "
                "could be validated to support these findings."
            )
            validated_findings = []

        return ComparisonValidationResult(
            findings=validated_findings,
            synthesis=final_synthesis,
            limitations=final_limitations,
            is_abstention=final_is_abstention,
            stripped_citation_count=stripped_count,
            all_validated_citations=all_validated_citations,
        )


def get_citation_validator() -> CitationValidator:
    """Dependency factory for CitationValidator."""
    return CitationValidator()
