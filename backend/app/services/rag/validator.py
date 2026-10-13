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
from app.services.ai.generator import GeneratedCitation


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
class CitationValidationResult:
    """Result of citation validation containing sanitized answer and verified citations."""

    answer_text: str
    is_abstention: bool
    citations: List[ValidatedCitation]
    stripped_citation_count: int


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


def get_citation_validator() -> CitationValidator:
    """Dependency factory for CitationValidator."""
    return CitationValidator()
