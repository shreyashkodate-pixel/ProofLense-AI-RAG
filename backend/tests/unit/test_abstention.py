"""ProofLens AI — Unit Tests for Unified Evidence-Sufficiency Engine.

Verifies:
1. Deterministic vector sufficiency evaluation against RAG_MIN_SIMILARITY_THRESHOLD.
2. Filtering of candidate chunks below threshold.
3. Handling of empty candidate lists.
4. Canonical abstention messages for single Q&A and comparisons.
"""

import uuid
import pytest
from app.repositories.query_repo import CandidateChunk
from app.services.rag.abstention import (
    EvidenceSufficiencyEvaluator,
    STANDARD_ABSTENTION_MESSAGE,
    COMPARISON_ABSTENTION_MESSAGE,
)


def create_candidate(score: float, rank: int = 1) -> CandidateChunk:
    return CandidateChunk(
        chunk_id=uuid.uuid4(),
        chunk_text=f"Sample text for rank {rank}",
        chunk_index=rank - 1,
        document_id=uuid.uuid4(),
        document_filename="test.pdf",
        page_id=uuid.uuid4(),
        page_number=1,
        similarity_score=score,
        rank=rank,
    )


def test_vector_sufficiency_above_threshold_passes():
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    candidates = [create_candidate(0.75, rank=1), create_candidate(0.60, rank=2)]

    is_sufficient, top_score = evaluator.evaluate_vector_sufficiency(candidates)
    assert is_sufficient is True
    assert top_score == 0.75


def test_vector_sufficiency_below_threshold_fails():
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    candidates = [create_candidate(0.62, rank=1), create_candidate(0.55, rank=2)]

    is_sufficient, top_score = evaluator.evaluate_vector_sufficiency(candidates)
    assert is_sufficient is False
    assert top_score == 0.62


def test_vector_sufficiency_empty_candidates_fails():
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    is_sufficient, top_score = evaluator.evaluate_vector_sufficiency([])
    assert is_sufficient is False
    assert top_score is None


def test_filter_passing_chunks_preserves_only_chunks_above_threshold():
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    c1 = create_candidate(0.85, rank=1)
    c2 = create_candidate(0.66, rank=2)
    c3 = create_candidate(0.64, rank=3)
    c4 = create_candidate(0.40, rank=4)

    passing = evaluator.filter_passing_chunks([c1, c2, c3, c4])
    assert len(passing) == 2
    assert passing[0].chunk_id == c1.chunk_id
    assert passing[1].chunk_id == c2.chunk_id


def test_custom_threshold_override():
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    candidates = [create_candidate(0.70, rank=1)]

    # With higher custom threshold 0.80, 0.70 fails
    is_sufficient, top_score = evaluator.evaluate_vector_sufficiency(candidates, threshold=0.80)
    assert is_sufficient is False
    assert top_score == 0.70


def test_canonical_abstention_messages():
    evaluator = EvidenceSufficiencyEvaluator()
    assert evaluator.get_standard_abstention_text() == STANDARD_ABSTENTION_MESSAGE
    assert evaluator.get_comparison_abstention_text() == COMPARISON_ABSTENTION_MESSAGE
    assert "sufficient document evidence" in evaluator.get_standard_abstention_text()
    assert "selected documents" in evaluator.get_comparison_abstention_text()


# ------------------------------------------------------------------------------
# Phase 7.1 Regression Tests: Global Evidence Sufficiency
# ------------------------------------------------------------------------------

def test_first_candidate_below_threshold_later_above_threshold_is_sufficient():
    """Verify out-of-order candidates (e.g. from multi-document retrieval) correctly identify top score."""
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    candidates = [create_candidate(0.45, rank=1), create_candidate(0.88, rank=2)]
    is_sufficient, top_score = evaluator.evaluate_vector_sufficiency(candidates)
    assert is_sufficient is True
    assert top_score == 0.88


def test_all_candidates_below_threshold_is_insufficient():
    """Verify that when all candidates are below threshold, evidence is insufficient."""
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    candidates = [create_candidate(0.30, rank=1), create_candidate(0.50, rank=2), create_candidate(0.64, rank=3)]
    is_sufficient, top_score = evaluator.evaluate_vector_sufficiency(candidates)
    assert is_sufficient is False
    assert top_score == 0.64


def test_exact_threshold_boundary_is_sufficient():
    """Verify boundary behavior: score exactly equal to 0.65 is sufficient."""
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    candidates = [create_candidate(0.65, rank=1)]
    is_sufficient, top_score = evaluator.evaluate_vector_sufficiency(candidates)
    assert is_sufficient is True
    assert top_score == 0.65


def test_empty_candidates_deterministic_insufficient():
    """Verify empty candidates returns False and None."""
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    is_sufficient, top_score = evaluator.evaluate_vector_sufficiency([])
    assert is_sufficient is False
    assert top_score is None


def test_reversing_candidate_order_preserves_sufficiency():
    """Verify candidate list ordering has zero effect on sufficiency determination."""
    evaluator = EvidenceSufficiencyEvaluator(default_threshold=0.65)
    c1 = create_candidate(0.40, rank=1)
    c2 = create_candidate(0.90, rank=2)

    suff_a, score_a = evaluator.evaluate_vector_sufficiency([c1, c2])
    suff_b, score_b = evaluator.evaluate_vector_sufficiency([c2, c1])

    assert suff_a is True and suff_b is True
    assert score_a == 0.90 and score_b == 0.90

