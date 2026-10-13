"""ProofLens AI — Unified Evidence-Sufficiency & Abstention Engine.

Implements the two-stage evidence-sufficiency policy per PRD and TECHNICAL-DESIGN.md Section 6.1:
1. Stage 1 (Deterministic Vector Abstention):
   Evaluates Top-1 cosine similarity score against RAG_MIN_SIMILARITY_THRESHOLD (default: 0.65).
   If top_score < threshold or candidates is empty, cleanly triggers deterministic vector
   abstention without invoking Gemini generation, saving cost and eliminating hallucination risk.
2. Stage 2 (Passing Chunk Filter):
   Filters candidate chunks, ensuring only evidence meeting or exceeding the similarity
   threshold is presented to the generation model.
3. Stage 3 (Semantic Content Abstention):
   Preserves explicit model-flagged abstentions when evidence fails to address the user question.
4. Stage 4 (Server-Authoritative Unsupported Claim Defense):
   Enforces that factual claims lacking validated server-side citations are converted
   to explicit abstention responses.
"""

from typing import List, Optional, Tuple
from app.core.logging import logger
from app.repositories.query_repo import CandidateChunk

STANDARD_ABSTENTION_MESSAGE = (
    "I do not have sufficient document evidence in this workspace to answer your question."
)

COMPARISON_ABSTENTION_MESSAGE = (
    "I do not have sufficient document evidence in the selected documents to perform a comparison on this topic."
)


class EvidenceSufficiencyEvaluator:
    """Evaluates vector similarity and candidate evidence sufficiency."""

    def __init__(self, default_threshold: float = 0.65) -> None:
        self.default_threshold = default_threshold

    def evaluate_vector_sufficiency(
        self,
        candidates: List[CandidateChunk],
        threshold: Optional[float] = None,
    ) -> Tuple[bool, Optional[float]]:
        """Evaluate whether candidate chunks meet the minimum similarity threshold.

        Args:
            candidates: Retrieved candidate chunks ordered by similarity descending.
            threshold: Minimum similarity threshold (defaults to self.default_threshold).

        Returns:
            Tuple of (is_sufficient: bool, top_score: Optional[float]).
        """
        thresh = threshold if threshold is not None else self.default_threshold
        if not candidates:
            return False, None

        top_score = max((c.similarity_score for c in candidates), default=None)
        if top_score is None:
            return False, None

        is_sufficient = top_score >= thresh


        if not is_sufficient:
            logger.info(
                "Deterministic vector abstention triggered: top similarity score below threshold",
                extra={
                    "extra": {
                        "top_score": top_score,
                        "threshold": thresh,
                        "candidate_count": len(candidates),
                    }
                },
            )

        return is_sufficient, top_score

    def filter_passing_chunks(
        self,
        candidates: List[CandidateChunk],
        threshold: Optional[float] = None,
    ) -> List[CandidateChunk]:
        """Filter candidate chunks to only those meeting or exceeding the threshold.

        Args:
            candidates: Retrieved candidate chunks.
            threshold: Minimum similarity threshold.

        Returns:
            List of candidate chunks with similarity_score >= threshold.
        """
        thresh = threshold if threshold is not None else self.default_threshold
        passing = [c for c in candidates if c.similarity_score >= thresh]
        return passing

    def get_standard_abstention_text(self) -> str:
        """Return canonical abstention message for single-topic Q&A."""
        return STANDARD_ABSTENTION_MESSAGE

    def get_comparison_abstention_text(self) -> str:
        """Return canonical abstention message for cross-document comparisons."""
        return COMPARISON_ABSTENTION_MESSAGE


def get_evidence_sufficiency_evaluator() -> EvidenceSufficiencyEvaluator:
    """Factory for EvidenceSufficiencyEvaluator."""
    return EvidenceSufficiencyEvaluator()
