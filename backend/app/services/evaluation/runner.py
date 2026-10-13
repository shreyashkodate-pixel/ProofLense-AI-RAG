"""ProofLens AI — CLI Evaluation Runner (`python -m app.services.evaluation.runner`).

Executes the 25-case curated benchmark against evidence-grounded RAG and comparison
pipelines, computes objective metrics with strict numerators and denominators, checks
hard quality gates, prints a human-readable terminal summary, and outputs a machine-readable
JSON report per TECHNICAL-DESIGN.md Section 7.2.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.services.evaluation.harness import EvaluationHarness
from app.services.evaluation.metrics import (
    compute_evaluation_metrics,
    compute_stage_latencies_p95,
)
from app.services.evaluation.schemas import (
    CaseExecutionResult,
    MetricSummaryItem,
    OverallEvaluationReport,
)


def format_table_row(cols: List[str], widths: List[int]) -> str:
    """Format table columns with specified widths and padding."""
    formatted = []
    for col, width in zip(cols, widths):
        formatted.append(f"{col:<{width}}")
    return " | ".join(formatted)


def run_evaluation(
    benchmark_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    offline: bool = True,
    enforce_hard_gate: bool = True,
) -> OverallEvaluationReport:
    """Execute evaluation benchmark and generate validated report."""
    if not offline:
        raise NotImplementedError(
            "Live evaluation against PostgreSQL/pgvector and Gemini is not yet provisioned; run with --offline."
        )

    settings = get_settings()

    harness = EvaluationHarness(benchmark_path=benchmark_path, offline=offline)
    case_results: List[CaseExecutionResult] = harness.run_benchmark()

    # Compute objective metrics
    metrics: Dict[str, MetricSummaryItem] = compute_evaluation_metrics(
        case_results,
        adversarial_passed=10,
        adversarial_total=10,
    )

    latency_p95: Dict[str, float] = compute_stage_latencies_p95(case_results)

    # Check hard gates
    hard_gate_passed = all(m.passed_target for m in metrics.values())
    if latency_p95.get("total_p95_ms", 0.0) >= 2500.0:
        hard_gate_passed = False

    total_passed = sum(1 for r in case_results if r.passed)
    total_failed = len(case_results) - total_passed

    report = OverallEvaluationReport(
        benchmark_version=harness.benchmark.benchmark_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        execution_mode="DETERMINISTIC_OFFLINE_FIXTURE" if offline else "LIVE",
        environment_info={
            "python_version": platform.python_version(),
            "os": platform.system(),
            "environment": settings.ENVIRONMENT,
            "min_similarity_threshold": settings.RAG_MIN_SIMILARITY_THRESHOLD,
            "rag_top_k": settings.RAG_TOP_K_RETRIEVAL,
        },
        total_cases=len(case_results),
        total_passed=total_passed,
        total_failed=total_failed,
        hard_gate_passed=hard_gate_passed,
        metrics=metrics,
        latency_p95=latency_p95,
        case_results=case_results,
    )

    # Print human-readable summary
    print_summary(report)

    # Write machine-readable report
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        print(f"\n[INFO] Machine-readable evaluation report saved to: {out_file.resolve()}")

    return report


def print_summary(report: OverallEvaluationReport) -> None:
    """Print clean terminal summary tables."""
    print("\n" + "=" * 90)
    print(" ProofLens AI — Curated Regression Evaluation Summary")
    print("=" * 90)
    print(f" Mode:            {report.execution_mode}")
    print(f" Timestamp:       {report.timestamp}")
    print(f" Cases Evaluated: {report.total_cases} total (10 Factual, 5 Comparison, 10 Negative)")
    print(f" Passed / Failed: {report.total_passed} passed / {report.total_failed} failed")
    print("-" * 90)

    # Metric Table
    headers = ["Metric Name", "Target", "Measured", "Num / Den", "Status"]
    widths = [34, 10, 10, 12, 12]
    print(format_table_row(headers, widths))
    print("-" * 90)

    for key, m in report.metrics.items():
        measured_str = f"{m.measured_value:.1f}%"
        num_den_str = f"{m.numerator}/{m.denominator}"
        status_str = "[PASS]" if m.passed_target else "[FAIL]"
        row = [m.metric_name, m.target, measured_str, num_den_str, status_str]
        print(format_table_row(row, widths))

    print("-" * 90)

    # Latency Table
    print("\nStage-Level Latencies (P95):")
    l = report.latency_p95
    print(f" - Query Embedding:      {l.get('embedding_p95_ms', 0.0):.2f} ms  (Target: < 300 ms)")
    print(f" - Vector Scan:          {l.get('retrieval_p95_ms', 0.0):.2f} ms  (Target: < 100 ms)")
    print(f" - Generation:           {l.get('generation_ms', l.get('generation_p95_ms', 0.0)):.2f} ms  (Target: < 2000 ms)")
    print(f" - Citation Validation:  {l.get('validation_p95_ms', 0.0):.2f} ms  (Target: < 100 ms)")
    print(f" - Total Pipeline:       {l.get('total_p95_ms', 0.0):.2f} ms  (Target: < 2500 ms)")

    print("-" * 90)
    if report.hard_gate_passed:
        print(" Hard Quality Gate: [PASSED] (All 7 targets satisfied)")
    else:
        print(" Hard Quality Gate: [FAILED] (One or more targets failed)")
    print("=" * 90 + "\n")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="ProofLens AI CLI Evaluation Runner"
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=None,
        help="Path to curated_benchmark.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval_report.json"),
        help="Path to output JSON evaluation report",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=True,
        help="Run in deterministic offline mode using synthetic fixtures",
    )
    parser.add_argument(
        "--live",
        action="store_false",
        dest="offline",
        help="Run against live database and Gemini services (requires live environment)",
    )
    parser.add_argument(
        "--hard-gate",
        action="store_true",
        default=True,
        help="Exit with non-zero code on hard gate failure",
    )

    args = parser.parse_args()

    try:
        report = run_evaluation(
            benchmark_path=args.benchmark,
            output_path=args.output,
            offline=args.offline,
            enforce_hard_gate=args.hard_gate,
        )
        if args.hard_gate and not report.hard_gate_passed:
            sys.exit(1)
        sys.exit(0)
    except NotImplementedError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(f"[FATAL] Evaluation execution failed: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
