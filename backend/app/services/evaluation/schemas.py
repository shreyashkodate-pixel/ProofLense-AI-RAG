"""ProofLens AI — Evaluation Schemas and Validation Models.

Defines type-safe Pydantic models for the 25-case curated benchmark, individual evaluation
cases (Factual, Comparison, Negative), execution results, metric summaries, and the
reproducible JSON evaluation report.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class ExpectedPerDocumentEvidence(BaseModel):
    """Ground-truth evidence expectations for a single document in a comparison case."""

    expected_quote: str = Field(..., description="Expected verbatim quote from source document.")
    page_number: int = Field(..., ge=1, description="Physical 1-indexed page number.")


class BenchmarkCase(BaseModel):
    """Schema for a single curated evaluation benchmark case."""

    case_id: str = Field(..., description="Stable, unique case identifier (e.g. factual_01).")
    category: Literal["factual", "comparison", "negative"] = Field(
        ..., description="Evaluation category: factual, comparison, or negative."
    )
    question: str = Field(..., description="Natural language question under evaluation.")
    fixture_documents: List[str] = Field(
        ..., min_length=1, description="List of synthetic fixture documents required for case."
    )

    # Category A: Factual Grounded Queries
    expected_document: Optional[str] = Field(
        default=None, description="Expected primary document containing answer."
    )
    expected_page_number: Optional[int] = Field(
        default=None, ge=1, description="Expected physical page number (1-indexed)."
    )
    expected_target_chunk_id: Optional[str] = Field(
        default=None, description="Expected ground-truth chunk alias/ID."
    )
    expected_quote: Optional[str] = Field(
        default=None, description="Expected supporting quote text."
    )
    expected_answer_contains: Optional[List[str]] = Field(
        default=None, description="List of required factual keywords or strings in answer."
    )
    evaluation_rule: Optional[str] = Field(
        default=None, description="Deterministic evaluation rule statement."
    )

    # Category B: Cross-Document Comparisons
    expected_relationship: Optional[
        Literal["agreement", "contradiction", "difference", "not_found", "insufficient_evidence"]
    ] = Field(default=None, description="Expected primary comparative relationship.")
    expected_per_document_evidence: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None, description="Map of document filename to expected evidence quote and page."
    )
    expected_limitations: Optional[str] = Field(
        default=None, description="Expected limitation or scope discrepancy notes."
    )

    # Category C: Negative / Out-of-Scope Queries
    expected_abstention: Optional[bool] = Field(
        default=None, description="True if query must trigger explicit abstention."
    )
    abstention_reason: Optional[str] = Field(
        default=None, description="Concise reason why evidence is out of scope or absent."
    )

    @model_validator(mode="after")
    def validate_category_fields(self) -> "BenchmarkCase":
        """Validate category-specific schema invariants."""
        if self.category == "factual":
            if not self.expected_document:
                raise ValueError(f"Factual case '{self.case_id}' requires 'expected_document'.")
            if not self.expected_page_number:
                raise ValueError(f"Factual case '{self.case_id}' requires 'expected_page_number'.")
            if not self.expected_quote:
                raise ValueError(f"Factual case '{self.case_id}' requires 'expected_quote'.")
        elif self.category == "comparison":
            if len(self.fixture_documents) < 2:
                raise ValueError(
                    f"Comparison case '{self.case_id}' requires at least 2 fixture_documents."
                )
            if not self.expected_relationship:
                raise ValueError(
                    f"Comparison case '{self.case_id}' requires 'expected_relationship'."
                )
        elif self.category == "negative":
            if self.expected_abstention is not True:
                raise ValueError(
                    f"Negative case '{self.case_id}' requires expected_abstention=True."
                )
            if not self.abstention_reason:
                raise ValueError(
                    f"Negative case '{self.case_id}' requires 'abstention_reason'."
                )
        return self


class CuratedBenchmark(BaseModel):
    """Schema for the entire 25-case curated benchmark suite."""

    benchmark_version: str = Field(..., description="Semantic version of benchmark suite.")
    created_at: str = Field(..., description="ISO 8601 creation timestamp.")
    description: str = Field(..., description="Benchmark suite description.")
    target_corpus: List[str] = Field(..., min_length=1, description="List of corpus documents.")
    cases: List[BenchmarkCase] = Field(..., description="List of benchmark cases.")

    @model_validator(mode="after")
    def validate_suite_composition(self) -> "CuratedBenchmark":
        """Enforce PRD / Technical Design composition: exactly 25 cases (10 F, 5 C, 10 N)."""
        if len(self.cases) != 25:
            raise ValueError(
                f"Benchmark must contain exactly 25 cases, found {len(self.cases)}."
            )

        case_ids = [c.case_id for c in self.cases]
        if len(set(case_ids)) != len(case_ids):
            duplicates = [cid for cid in case_ids if case_ids.count(cid) > 1]
            raise ValueError(f"Duplicate case_ids detected: {set(duplicates)}.")

        factual_count = sum(1 for c in self.cases if c.category == "factual")
        comparison_count = sum(1 for c in self.cases if c.category == "comparison")
        negative_count = sum(1 for c in self.cases if c.category == "negative")

        if factual_count != 10:
            raise ValueError(f"Expected exactly 10 factual cases, found {factual_count}.")
        if comparison_count != 5:
            raise ValueError(f"Expected exactly 5 comparison cases, found {comparison_count}.")
        if negative_count != 10:
            raise ValueError(f"Expected exactly 10 negative cases, found {negative_count}.")

        return self


class StageLatency(BaseModel):
    """Stage-level execution latencies in milliseconds."""

    embedding_ms: float = 0.0
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    validation_ms: float = 0.0
    total_ms: float = 0.0


class CaseExecutionResult(BaseModel):
    """Detailed result for a single evaluated benchmark case."""

    case_id: str
    category: Literal["factual", "comparison", "negative"]
    passed: bool
    hit_at_5: Optional[bool] = None
    citation_integrity: Optional[bool] = None
    abstained: bool = False
    false_abstention: bool = False
    comparison_rubric_score: Optional[float] = None  # 0.0 to 5.0
    rubric_breakdown: Optional[Dict[str, bool]] = None
    failure_reason: Optional[str] = None
    stage_latencies: Optional[StageLatency] = None


class MetricSummaryItem(BaseModel):
    """Standardized representation of an objective metric with numerator and denominator."""

    metric_name: str
    target: str
    measured_value: float  # Percentage (0-100) or count
    numerator: int
    denominator: int
    sample_size: int
    passed_target: bool
    interpretation: str


class OverallEvaluationReport(BaseModel):
    """Standardized machine-readable evaluation report generated by the CLI runner."""

    benchmark_version: str
    timestamp: str
    execution_mode: Literal["DETERMINISTIC_OFFLINE_FIXTURE", "LIVE"]
    environment_info: Dict[str, Any]
    total_cases: int = 25
    total_passed: int
    total_failed: int
    hard_gate_passed: bool
    metrics: Dict[str, MetricSummaryItem]
    latency_p95: Dict[str, float]
    case_results: List[CaseExecutionResult]
