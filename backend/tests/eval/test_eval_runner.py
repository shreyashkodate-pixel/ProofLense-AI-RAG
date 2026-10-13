"""ProofLens AI — Evaluation Runner CLI & Offline Execution Tests.

Tests the CLI evaluation runner, offline deterministic execution mode, JSON report
generation, exit code behavior, and secret-safety guarantees.
"""

import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest

from app.services.evaluation.harness import EvaluationHarness
from app.services.evaluation.runner import main, run_evaluation
from app.services.evaluation.schemas import OverallEvaluationReport


@pytest.fixture
def temp_output_path(tmp_path: Path) -> Path:
    return tmp_path / "test_eval_report.json"


class TestEvaluationRunner:
    """Verifies programmatic and CLI execution of the evaluation runner."""

    def test_run_evaluation_offline_programmatic(self, temp_output_path: Path):
        """Programmatic run_evaluation must complete 25 cases and satisfy hard gates."""
        report = run_evaluation(
            output_path=temp_output_path,
            offline=True,
            enforce_hard_gate=True,
        )

        assert isinstance(report, OverallEvaluationReport)
        assert report.total_cases == 25
        assert report.total_passed == 25
        assert report.total_failed == 0
        assert report.hard_gate_passed is True
        assert report.execution_mode == "DETERMINISTIC_OFFLINE_FIXTURE"

        # Check all 6 core metrics
        assert report.metrics["structural_citation_integrity"].passed_target is True
        assert report.metrics["negative_abstention_accuracy"].passed_target is True
        assert report.metrics["factual_false_abstention_rate"].passed_target is True
        assert report.metrics["retrieval_recall_at_5"].passed_target is True
        assert report.metrics["comparison_quality"].passed_target is True
        assert report.metrics["adversarial_prompt_resistance"].passed_target is True

        # Check report file exists on disk and is valid JSON
        assert temp_output_path.exists()
        with open(temp_output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["benchmark_version"] == "1.0.0"
        assert len(data["case_results"]) == 25

    def test_live_mode_rejected_programmatically(self, temp_output_path: Path):
        """Programmatic run_evaluation and EvaluationHarness must reject offline=False."""
        expected_msg = (
            "Live evaluation against PostgreSQL/pgvector and Gemini is not yet provisioned; "
            "run with --offline."
        )

        # 1. run_evaluation rejection
        with pytest.raises(NotImplementedError) as exc_eval:
            run_evaluation(output_path=temp_output_path, offline=False)
        assert str(exc_eval.value) == expected_msg
        assert not temp_output_path.exists(), "Report file must not be created when live mode is rejected"

        # 2. EvaluationHarness rejection
        with pytest.raises(NotImplementedError) as exc_harness:
            EvaluationHarness(offline=False)
        assert str(exc_harness.value) == expected_msg

    def test_cli_rejects_live_mode_with_actionable_error(self, tmp_path: Path):
        """CLI with --live flag must fail with exit code 2 and never produce a LIVE report."""
        out_file = tmp_path / "live_report.json"
        cmd = [
            sys.executable,
            "-m",
            "app.services.evaluation.runner",
            "--live",
            "--output",
            str(out_file),
        ]

        backend_dir = Path(__file__).resolve().parent.parent.parent
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        )

        # Must exit with non-zero code (2)
        assert result.returncode == 2
        # Error must be actionable and explicit
        assert (
            "Live evaluation against PostgreSQL/pgvector and Gemini is not yet provisioned; run with --offline."
            in result.stderr
        )
        # Must never write a report to disk
        assert not out_file.exists()
        # Must never print a report summary claiming LIVE mode
        assert "LIVE" not in result.stdout
        assert "Hard Quality Gate: [PASSED]" not in result.stdout

    def test_json_report_zero_secret_leakage(self, temp_output_path: Path):
        """Report JSON content must contain zero secret keys, tokens, or passwords."""
        report = run_evaluation(
            output_path=temp_output_path,
            offline=True,
            enforce_hard_gate=True,
        )

        report_json_str = report.model_dump_json()

        # Secret Zero checks
        forbidden_patterns = [
            "AIza",
            "postgresql://",
            "postgres:",
            "service_role",
            "DEMO_ACCESS_TOKEN",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in report_json_str, f"Found secret leak pattern: {pattern}"

    def test_cli_module_execution_success(self, tmp_path: Path):
        """CLI module execution `python -m app.services.evaluation.runner` exits with code 0."""
        out_file = tmp_path / "cli_report.json"
        cmd = [
            sys.executable,
            "-m",
            "app.services.evaluation.runner",
            "--offline",
            "--output",
            str(out_file),
            "--hard-gate",
        ]

        # Execute from backend directory
        backend_dir = Path(__file__).resolve().parent.parent.parent
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"CLI runner failed with error: {result.stderr}"
        assert "ProofLens AI — Curated Regression Evaluation Summary" in result.stdout
        assert "Mode:            DETERMINISTIC_OFFLINE_FIXTURE" in result.stdout
        assert "Hard Quality Gate: [PASSED]" in result.stdout
        assert out_file.exists()

    def test_cli_module_execution_default_is_offline(self, tmp_path: Path):
        """CLI without explicit flags runs offline by default and exits with code 0."""
        out_file = tmp_path / "default_report.json"
        cmd = [
            sys.executable,
            "-m",
            "app.services.evaluation.runner",
            "--output",
            str(out_file),
        ]

        backend_dir = Path(__file__).resolve().parent.parent.parent
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"CLI runner failed with error: {result.stderr}"
        assert "Mode:            DETERMINISTIC_OFFLINE_FIXTURE" in result.stdout
        assert out_file.exists()
        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["execution_mode"] == "DETERMINISTIC_OFFLINE_FIXTURE"

    def test_cli_rejects_nonexistent_benchmark_file(self):
        """CLI must exit with non-zero status code when benchmark file does not exist."""
        cmd = [
            sys.executable,
            "-m",
            "app.services.evaluation.runner",
            "--benchmark",
            "/nonexistent/path/benchmark.json",
        ]
        backend_dir = Path(__file__).resolve().parent.parent.parent
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert "Benchmark file not found" in result.stderr or "FATAL" in result.stderr

    def test_cli_hard_gate_failure_exit_code(self, monkeypatch):
        """CLI must exit with code 1 when hard quality gate fails."""
        report = run_evaluation(offline=True)
        report_failing = report.model_copy(update={"hard_gate_passed": False})

        monkeypatch.setattr(sys, "argv", ["runner", "--offline", "--hard-gate"])
        with patch("app.services.evaluation.runner.run_evaluation", return_value=report_failing):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
