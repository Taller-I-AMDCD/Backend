"""Tests for the final Planner–Executor evaluation infrastructure."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.run_evaluation import REQUIRED_CSV_COLUMNS, run_evaluation, write_results


@pytest.fixture(scope="module")
def evaluation_report() -> dict[str, Any]:
    return run_evaluation(warmup_runs=1, measured_runs=2)


def test_evaluator_runs_all_defined_scenarios(
    evaluation_report: dict[str, Any],
) -> None:
    assert {scenario["scenario"] for scenario in evaluation_report["scenarios"]} == {
        "consistent_relation",
        "confounded_relation",
        "outlier_relation",
    }


def test_evaluator_returns_exactly_three_scenarios(
    evaluation_report: dict[str, Any],
) -> None:
    assert len(evaluation_report["scenarios"]) == 3


def test_success_rate_is_calculated_from_results(
    evaluation_report: dict[str, Any],
) -> None:
    successful = sum(
        scenario["correct_behavior_detected"]
        for scenario in evaluation_report["scenarios"]
    )
    expected_rate = successful / len(evaluation_report["scenarios"]) * 100

    assert evaluation_report["global_metrics"]["success_rate"] == expected_rate


def test_timing_metrics_are_non_negative(evaluation_report: dict[str, Any]) -> None:
    for scenario in evaluation_report["scenarios"]:
        assert all(value >= 0 for value in scenario["timing"].values())
        assert all(value >= 0 for value in scenario["execution_times_ms"])


def test_median_and_p95_are_recorded(evaluation_report: dict[str, Any]) -> None:
    for scenario in evaluation_report["scenarios"]:
        assert "median_execution_ms" in scenario["timing"]
        assert "p95_execution_ms" in scenario["timing"]
        assert scenario["timing"]["p95_execution_ms"] >= scenario["timing"][
            "median_execution_ms"
        ]


def test_tools_used_are_recorded(evaluation_report: dict[str, Any]) -> None:
    for scenario in evaluation_report["scenarios"]:
        assert scenario["tools_used"]
        assert scenario["tools_used"][0] == "profile_dataset"


def test_execution_paths_are_recorded(evaluation_report: dict[str, Any]) -> None:
    paths = evaluation_report["global_metrics"]["execution_paths"]

    assert set(paths) == {
        "consistent_relation",
        "confounded_relation",
        "outlier_relation",
    }
    assert "partial_correlation" in paths["confounded_relation"]


def test_unique_execution_paths_are_calculated(
    evaluation_report: dict[str, Any],
) -> None:
    paths = evaluation_report["global_metrics"]["execution_paths"].values()
    expected_unique_paths = len({tuple(path) for path in paths})

    assert evaluation_report["global_metrics"][
        "unique_execution_paths"
    ] == expected_unique_paths
    assert expected_unique_paths >= 2


def test_trace_completeness_is_validated(evaluation_report: dict[str, Any]) -> None:
    assert all(
        scenario["trace_complete"] for scenario in evaluation_report["scenarios"]
    )


def test_global_metrics_match_scenario_metrics(
    evaluation_report: dict[str, Any],
) -> None:
    scenarios = evaluation_report["scenarios"]
    global_metrics = evaluation_report["global_metrics"]

    assert global_metrics["total_iterations"] == sum(
        scenario["total_iterations"] for scenario in scenarios
    )
    assert global_metrics["total_tool_executions"] == sum(
        scenario["successful_executions"] for scenario in scenarios
    )
    assert global_metrics["total_failed_executions"] == sum(
        scenario["failed_executions"] for scenario in scenarios
    )


def test_evaluation_report_is_json_serializable(
    evaluation_report: dict[str, Any],
) -> None:
    assert json.loads(json.dumps(evaluation_report)) == evaluation_report


def test_csv_contains_required_columns_and_rows(
    evaluation_report: dict[str, Any],
    tmp_path: Path,
) -> None:
    _, csv_path = write_results(evaluation_report, tmp_path)

    with csv_path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == REQUIRED_CSV_COLUMNS
    assert len(rows) == 3


def test_structural_metrics_are_non_negative(
    evaluation_report: dict[str, Any],
) -> None:
    metrics = evaluation_report["structural_metrics"]

    assert metrics["productive_python_modules"] > 0
    assert metrics["approximate_productive_loc"] > 0
    assert metrics["test_functions"] > 0
    assert metrics["registered_tools"] > 0


def test_statistical_behavior_remains_consistent(
    evaluation_report: dict[str, Any],
) -> None:
    scenarios = {
        scenario["scenario"]: scenario
        for scenario in evaluation_report["scenarios"]
    }
    consistent = scenarios["consistent_relation"]["statistics"]
    confounded = scenarios["confounded_relation"]["statistics"]
    outlier = scenarios["outlier_relation"]["statistics"]

    assert consistent["pearson"] > 0.8
    assert consistent["filtered_correlation"] > 0.8
    assert consistent["spearman"] > 0.8
    assert abs(confounded["partial_correlation"]) < abs(confounded["pearson"]) * 0.3
    assert abs(outlier["filtered_correlation"]) < abs(
        outlier["original_correlation"]
    ) * 0.5
    assert all(
        scenario["correct_behavior_detected"]
        for scenario in evaluation_report["scenarios"]
    )
