"""Integration tests for the traceable Planner–Executor loop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.orchestrator import Orchestrator

DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def consistent_trace() -> dict[str, Any]:
    frame = pd.read_csv(DATA_DIRECTORY / "consistent_relation.csv")
    return Orchestrator().run(frame, "synthetic_input.csv", "X", "Y")


@pytest.fixture(scope="module")
def confounded_trace() -> dict[str, Any]:
    frame = pd.read_csv(DATA_DIRECTORY / "confounded_relation.csv")
    return Orchestrator().run(frame, "synthetic_input.csv", "X", "Y")


def _entry(trace: dict[str, Any], tool: str) -> dict[str, Any]:
    return next(
        iteration
        for iteration in trace["iterations"]
        if iteration["planner"]["tool"] == tool
    )


def test_planner_and_executor_complete_cycle(consistent_trace: dict[str, Any]) -> None:
    assert consistent_trace["final"]["stop_reason"] == "NO_NEW_ACTIONS"
    assert consistent_trace["final"]["failed_executions"] == 0


def test_first_action_is_profile_dataset(consistent_trace: dict[str, Any]) -> None:
    assert consistent_trace["iterations"][0]["planner"]["tool"] == "profile_dataset"


def test_profile_result_updates_state_metadata(consistent_trace: dict[str, Any]) -> None:
    first_state = consistent_trace["iterations"][0]["state"]

    assert first_state["columns"] == ["X", "Y"]
    assert first_state["numeric_columns"] == ["X", "Y"]


def test_planner_requests_pearson_after_profile(consistent_trace: dict[str, Any]) -> None:
    assert consistent_trace["iterations"][1]["planner"]["tool"] == "pearson_correlation"


def test_pearson_execution_is_recorded(consistent_trace: dict[str, Any]) -> None:
    pearson = _entry(consistent_trace, "pearson_correlation")

    assert pearson["executor"]["status"] == "success"
    assert pearson["executor"]["result"]["coefficient"] > 0.8
    assert pearson["state"]["history_size"] == 2
    assert pearson["state"]["results_size"] == 2


def test_pearson_result_drives_subsequent_decision(
    consistent_trace: dict[str, Any],
) -> None:
    tools = consistent_trace["final"]["tools_used"]
    pearson_position = tools.index("pearson_correlation")

    assert tools[pearson_position + 1] == "correlation_without_outliers"


def test_third_numeric_variable_reaches_partial_correlation(
    confounded_trace: dict[str, Any],
) -> None:
    pearson = _entry(confounded_trace, "pearson_correlation")
    partial = _entry(confounded_trace, "partial_correlation")
    pearson_coefficient = abs(pearson["executor"]["result"]["coefficient"])
    partial_coefficient = abs(partial["executor"]["result"]["coefficient"])

    assert pearson_coefficient > 0.7
    assert partial_coefficient < 0.2
    assert partial_coefficient < pearson_coefficient * 0.3


def test_history_prevents_duplicate_actions(confounded_trace: dict[str, Any]) -> None:
    identities = [
        (
            iteration["planner"]["tool"],
            json.dumps(iteration["planner"]["parameters"], sort_keys=True),
        )
        for iteration in confounded_trace["iterations"]
    ]

    assert len(identities) == len(set(identities))


def test_every_iteration_has_planner_executor_and_state_trace(
    confounded_trace: dict[str, Any],
) -> None:
    for expected_iteration, entry in enumerate(
        confounded_trace["iterations"], start=1
    ):
        assert entry["iteration"] == expected_iteration
        assert set(entry) == {"iteration", "planner", "executor", "state"}
        assert entry["planner"]["action_id"] == f"action-{expected_iteration:03d}"


def test_flow_ends_with_stop_decision(confounded_trace: dict[str, Any]) -> None:
    assert confounded_trace["final"]["stop_reason"] == "NO_NEW_ACTIONS"


def test_total_iterations_matches_trace(confounded_trace: dict[str, Any]) -> None:
    assert confounded_trace["final"]["total_iterations"] == len(
        confounded_trace["iterations"]
    )


def test_successful_executions_are_counted(confounded_trace: dict[str, Any]) -> None:
    assert confounded_trace["final"]["successful_executions"] == len(
        confounded_trace["iterations"]
    )
    assert confounded_trace["final"]["failed_executions"] == 0


def test_executor_error_is_traced_and_stops_flow() -> None:
    class FailingExecutor:
        def execute(
            self,
            frame: pd.DataFrame,
            request: dict[str, Any],
        ) -> dict[str, Any]:
            return {
                "status": "error",
                "tool": request["tool"],
                "parameters": request["parameters"],
                "result": None,
                "error": {"code": "EXECUTION_ERROR", "message": "Controlled failure."},
            }

    frame = pd.DataFrame({"X": [1, 2, 3], "Y": [2, 4, 6]})
    trace = Orchestrator(executor=FailingExecutor()).run(
        frame, "synthetic_input.csv", "X", "Y"
    )

    assert trace["final"]["stop_reason"] == "EXECUTION_ERROR"
    assert trace["final"]["successful_executions"] == 0
    assert trace["final"]["failed_executions"] == 1
    assert trace["iterations"][0]["executor"]["error"]["code"] == "EXECUTION_ERROR"


def test_complete_trace_is_json_serializable(confounded_trace: dict[str, Any]) -> None:
    serialized = json.dumps(confounded_trace)

    assert json.loads(serialized) == confounded_trace


def test_cycle_respects_max_iterations() -> None:
    frame = pd.read_csv(DATA_DIRECTORY / "confounded_relation.csv")
    trace = Orchestrator().run(
        frame,
        "synthetic_input.csv",
        "X",
        "Y",
        max_iterations=2,
    )

    assert trace["final"]["stop_reason"] == "MAX_ITERATIONS"
    assert trace["final"]["total_iterations"] == 2
    assert len(trace["iterations"]) == 2
