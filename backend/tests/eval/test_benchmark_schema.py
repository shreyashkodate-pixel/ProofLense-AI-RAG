"""ProofLens AI — Benchmark Schema & Suite Composition Unit Tests.

Validates that `curated_benchmark.json` strictly adheres to PRD and Technical Design
specifications: exactly 25 cases, 10 Factual, 5 Comparison, 10 Negative, unique IDs,
and valid category-specific fields.
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.services.evaluation.schemas import BenchmarkCase, CuratedBenchmark


@pytest.fixture
def benchmark_path() -> Path:
    return Path(__file__).resolve().parent / "curated_benchmark.json"


@pytest.fixture
def benchmark_data(benchmark_path: Path) -> dict:
    with open(benchmark_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestBenchmarkSchema:
    """Verifies schema invariants and composition of the curated benchmark."""

    def test_curated_benchmark_loads_and_validates(self, benchmark_data: dict):
        """Benchmark file must deserialize cleanly into CuratedBenchmark model."""
        benchmark = CuratedBenchmark.model_validate(benchmark_data)
        assert benchmark.benchmark_version == "1.0.0"
        assert len(benchmark.cases) == 25

    def test_category_distribution_invariant(self, benchmark_data: dict):
        """Suite must contain exactly 10 Factual, 5 Comparison, and 10 Negative cases."""
        benchmark = CuratedBenchmark.model_validate(benchmark_data)
        factual = [c for c in benchmark.cases if c.category == "factual"]
        comparison = [c for c in benchmark.cases if c.category == "comparison"]
        negative = [c for c in benchmark.cases if c.category == "negative"]

        assert len(factual) == 10
        assert len(comparison) == 5
        assert len(negative) == 10

    def test_case_ids_are_globally_unique(self, benchmark_data: dict):
        """All 25 case IDs must be unique."""
        benchmark = CuratedBenchmark.model_validate(benchmark_data)
        ids = [c.case_id for c in benchmark.cases]
        assert len(ids) == len(set(ids))

    def test_factual_case_fields_present(self, benchmark_data: dict):
        """Every factual case must include expected document, page, and quote."""
        benchmark = CuratedBenchmark.model_validate(benchmark_data)
        for case in benchmark.cases:
            if case.category == "factual":
                assert case.expected_document is not None
                assert case.expected_page_number is not None and case.expected_page_number >= 1
                assert case.expected_quote is not None and len(case.expected_quote) > 0
                assert case.expected_target_chunk_id is not None

    def test_comparison_case_fields_present(self, benchmark_data: dict):
        """Every comparison case must reference >= 2 documents and define relationship."""
        benchmark = CuratedBenchmark.model_validate(benchmark_data)
        for case in benchmark.cases:
            if case.category == "comparison":
                assert len(case.fixture_documents) >= 2
                assert case.expected_relationship in (
                    "agreement",
                    "contradiction",
                    "difference",
                    "not_found",
                    "insufficient_evidence",
                )

    def test_negative_case_fields_present(self, benchmark_data: dict):
        """Every negative case must require expected_abstention=True and abstention_reason."""
        benchmark = CuratedBenchmark.model_validate(benchmark_data)
        for case in benchmark.cases:
            if case.category == "negative":
                assert case.expected_abstention is True
                assert case.abstention_reason is not None and len(case.abstention_reason) > 5

    def test_rejects_missing_case_count(self, benchmark_data: dict):
        """Model must reject benchmarks with fewer than 25 cases."""
        mutated = dict(benchmark_data)
        mutated["cases"] = mutated["cases"][:-1]  # 24 cases
        with pytest.raises(ValidationError) as exc:
            CuratedBenchmark.model_validate(mutated)
        assert "exactly 25 cases" in str(exc.value)

    def test_rejects_duplicate_case_ids(self, benchmark_data: dict):
        """Model must reject duplicate case_id entries."""
        mutated = dict(benchmark_data)
        dup_case = dict(mutated["cases"][0])
        dup_case["case_id"] = mutated["cases"][1]["case_id"]
        mutated["cases"][0] = dup_case
        with pytest.raises(ValidationError) as exc:
            CuratedBenchmark.model_validate(mutated)
        assert "Duplicate case_ids" in str(exc.value)

    def test_rejects_malformed_factual_case(self):
        """Factual case missing expected_page_number must fail validation."""
        with pytest.raises(ValidationError):
            BenchmarkCase(
                case_id="factual_err",
                category="factual",
                question="What is revenue?",
                fixture_documents=["doc.pdf"],
                expected_document="doc.pdf",
                # Missing expected_page_number and expected_quote
            )
