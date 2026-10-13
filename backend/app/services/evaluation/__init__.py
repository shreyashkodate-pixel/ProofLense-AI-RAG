"""ProofLens AI — Evaluation Services Package."""

from app.services.evaluation.harness import EvaluationHarness
from app.services.evaluation.metrics import (
    compute_evaluation_metrics,
    compute_stage_latencies_p95,
    score_comparison_rubric,
)
from app.services.evaluation.schemas import (
    BenchmarkCase,
    CaseExecutionResult,
    CuratedBenchmark,
    OverallEvaluationReport,
)

__all__ = [
    "EvaluationHarness",
    "CuratedBenchmark",
    "BenchmarkCase",
    "CaseExecutionResult",
    "OverallEvaluationReport",
    "compute_evaluation_metrics",
    "compute_stage_latencies_p95",
    "score_comparison_rubric",
]
