"""ProofLens AI — Evaluation Metrics & Quality Rubric Unit Tests.

Tests the mathematical and rubric-based metric calculations for:
1. Structural Citation Integrity
2. Negative-Set Abstention Accuracy
3. Factual-Set False-Abstention Rate
4. Retrieval Recall@5
5. Comparison Quality Rubric (5-point rubric)
6. Stage Latency Percentiles (P95)
"""

import pytest

from app.services.evaluation.metrics import (
    calculate_percentile,
    compute_evaluation_metrics,
    compute_stage_latencies_p95,
    score_comparison_rubric,
)
from app.services.evaluation.schemas import CaseExecutionResult, StageLatency


class TestEvaluationMetrics:
    """Verifies precision and edge-case behavior of metric calculations."""

    def test_percentile_calculation_nearest_rank(self):
        """Validates nearest-rank percentile calculation across known arrays."""
        # Single element
        assert calculate_percentile([100.0], 95.0) == 100.0
        # Empty array
        assert calculate_percentile([], 95.0) == 0.0
        # 10 sorted elements: [10, 20, ..., 100]
        data = [float(i * 10) for i in range(1, 11)]
        p95 = calculate_percentile(data, 95.0)
        assert 90.0 <= p95 <= 100.0

    def test_comparison_rubric_scoring(self):
        """Verifies 5-point comparison rubric and 80% passing threshold."""
        # 5/5 criteria passed
        res_5 = score_comparison_rubric(
            documents_identified=True,
            evidence_accurate=True,
            citations_valid=True,
            classification_correct=True,
            limitations_handled=True,
        )
        assert res_5["score"] == 5
        assert res_5["passed"] is True

        # 4/5 criteria passed (80% -> passes)
        res_4 = score_comparison_rubric(
            documents_identified=True,
            evidence_accurate=True,
            citations_valid=True,
            classification_correct=True,
            limitations_handled=False,
        )
        assert res_4["score"] == 4
        assert res_4["passed"] is True

        # 3/5 criteria passed (60% -> fails)
        res_3 = score_comparison_rubric(
            documents_identified=True,
            evidence_accurate=False,
            citations_valid=False,
            classification_correct=True,
            limitations_handled=True,
        )
        assert res_3["score"] == 3
        assert res_3["passed"] is False

    def test_compute_metrics_perfect_suite(self):
        """Validates metric calculations when all cases pass."""
        results = []
        # 10 Factual: hit_at_5=True, citation_integrity=True, false_abstention=False
        for i in range(10):
            results.append(
                CaseExecutionResult(
                    case_id=f"factual_{i}",
                    category="factual",
                    passed=True,
                    hit_at_5=True,
                    citation_integrity=True,
                    abstained=False,
                    false_abstention=False,
                )
            )
        # 5 Comparison: rubric score 5.0
        for i in range(5):
            results.append(
                CaseExecutionResult(
                    case_id=f"comparison_{i}",
                    category="comparison",
                    passed=True,
                    citation_integrity=True,
                    comparison_rubric_score=5.0,
                )
            )
        # 10 Negative: abstained=True
        for i in range(10):
            results.append(
                CaseExecutionResult(
                    case_id=f"negative_{i}",
                    category="negative",
                    passed=True,
                    abstained=True,
                    false_abstention=False,
                )
            )

        metrics = compute_evaluation_metrics(results, adversarial_passed=10, adversarial_total=10)

        assert metrics["structural_citation_integrity"].measured_value == 100.0
        assert metrics["structural_citation_integrity"].passed_target is True

        assert metrics["negative_abstention_accuracy"].measured_value == 100.0
        assert metrics["negative_abstention_accuracy"].passed_target is True

        assert metrics["factual_false_abstention_rate"].measured_value == 0.0
        assert metrics["factual_false_abstention_rate"].passed_target is True

        assert metrics["retrieval_recall_at_5"].measured_value == 100.0
        assert metrics["retrieval_recall_at_5"].passed_target is True

        assert metrics["comparison_quality"].measured_value == 100.0
        assert metrics["comparison_quality"].passed_target is True

        assert metrics["adversarial_prompt_resistance"].measured_value == 100.0
        assert metrics["adversarial_prompt_resistance"].passed_target is True

    def test_compute_metrics_degraded_failures(self):
        """Validates metric calculations when targets fail."""
        results = []
        # 10 Factual: 2 hit_at_5 failures (8/10 = 80% < 85%)
        for i in range(10):
            hit = i < 8
            results.append(
                CaseExecutionResult(
                    case_id=f"factual_{i}",
                    category="factual",
                    passed=hit,
                    hit_at_5=hit,
                    citation_integrity=True,
                    false_abstention=(i >= 8),  # 2 false abstentions (20% > 10%)
                )
            )
        # 5 Comparison: 2 failures (3/5 = 60% < 80%)
        for i in range(5):
            score = 5.0 if i < 3 else 3.0
            results.append(
                CaseExecutionResult(
                    case_id=f"comparison_{i}",
                    category="comparison",
                    passed=(score >= 4.0),
                    citation_integrity=True,
                    comparison_rubric_score=score,
                )
            )
        # 10 Negative: 2 failures (8/10 = 80% < 90%)
        for i in range(10):
            abstained = i < 8
            results.append(
                CaseExecutionResult(
                    case_id=f"negative_{i}",
                    category="negative",
                    passed=abstained,
                    abstained=abstained,
                )
            )

        metrics = compute_evaluation_metrics(results)

        assert metrics["retrieval_recall_at_5"].measured_value == 80.0
        assert metrics["retrieval_recall_at_5"].passed_target is False

        assert metrics["factual_false_abstention_rate"].measured_value == 20.0
        assert metrics["factual_false_abstention_rate"].passed_target is False

        assert metrics["comparison_quality"].measured_value == 60.0
        assert metrics["comparison_quality"].passed_target is False

        assert metrics["negative_abstention_accuracy"].measured_value == 80.0
        assert metrics["negative_abstention_accuracy"].passed_target is False

    def test_compute_stage_latencies_p95(self):
        """Validates stage latency aggregation and P95 calculation."""
        results = []
        for i in range(10):
            results.append(
                CaseExecutionResult(
                    case_id=f"case_{i}",
                    category="factual",
                    passed=True,
                    stage_latencies=StageLatency(
                        embedding_ms=2.0 + i,
                        retrieval_ms=1.0 + i,
                        generation_ms=10.0 + i,
                        validation_ms=0.5 + (i * 0.1),
                        total_ms=15.0 + (i * 2.0),
                    ),
                )
            )

        p95 = compute_stage_latencies_p95(results)
        assert p95["embedding_p95_ms"] > 0
        assert p95["retrieval_p95_ms"] > 0
        assert p95["generation_p95_ms"] > 0
        assert p95["validation_p95_ms"] > 0
        assert p95["total_p95_ms"] > 0
        assert p95["total_p95_ms"] < 2500.0  # Well within target
