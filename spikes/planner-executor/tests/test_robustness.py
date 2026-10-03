"""Robustness tests for orchestration safeguards and CLI validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.executor import Executor
from src.main import InputValidationError, load_and_validate_dataset, main
from src.orchestrator import Orchestrator, save_trace
from src.planner import Planner, ResearchState


def _action(state: ResearchState, tool: str, parameters: dict[str, Any]) -> dict[str, Any]:
    iteration = state.iteration + 1
    return {
        "status": "action",
        "action_id": f"action-{iteration:03d}",
        "iteration": iteration,
        "tool": tool,
        "parameters": parameters,
        "reason": "Test orchestration safeguard.",
    }


class RepeatingPlanner:
    def __init__(self) -> None:
        self.calls = 0

    def plan(self, state: ResearchState) -> dict[str, Any]:
        self.calls += 1
        parameters = (
            {"x": "X", "y": "Y"}
            if self.calls == 1
            else {"y": "Y", "x": "X"}
        )
        return _action(state, "pearson_correlation", parameters)


class EndlessPlanner:
    def plan(self, state: ResearchState) -> dict[str, Any]:
        return _action(
            state,
            "detect_outliers",
            {"column": "X", "multiplier": 1.5 + state.iteration / 10},
        )


class UnknownToolPlanner:
    def plan(self, state: ResearchState) -> dict[str, Any]:
        return _action(state, "unsupported_tool", {})


class InvalidParametersPlanner:
    def plan(self, state: ResearchState) -> dict[str, Any]:
        return _action(state, "pearson_correlation", {"x": "X"})


class ProfileThenUnknownPlanner:
    def plan(self, state: ResearchState) -> dict[str, Any]:
        if state.iteration == 0:
            return _action(state, "profile_dataset", {})
        return _action(state, "unsupported_tool", {})


class CountingExecutor:
    def __init__(self) -> None:
        self.calls = 0
        self._executor = Executor()

    def execute(
        self,
        frame: pd.DataFrame,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls += 1
        return self._executor.execute(frame, request)


@pytest.fixture
def numeric_frame() -> pd.DataFrame:
    return pd.DataFrame({"X": [1.0, 2.0, 3.0, 4.0], "Y": [2.0, 4.0, 6.0, 8.0]})


def test_planner_stops_at_max_iterations() -> None:
    state = ResearchState(
        objective="Evaluate X and Y.",
        iteration=3,
        columns=["X", "Y"],
        numeric_columns=["X", "Y"],
        max_iterations=3,
        target_variables=("X", "Y"),
    )

    decision = Planner().plan(state)

    assert decision["status"] == "stop"
    assert decision["reason"] == "MAX_ITERATIONS"


def test_orchestrator_defensively_stops_endless_planner(
    numeric_frame: pd.DataFrame,
) -> None:
    trace = Orchestrator(planner=EndlessPlanner()).run(
        numeric_frame, "in_memory", "X", "Y", max_iterations=3
    )

    assert trace["final"]["stop_reason"] == "MAX_ITERATIONS"
    assert trace["final"]["total_iterations"] == 3


def test_duplicate_action_is_detected(numeric_frame: pd.DataFrame) -> None:
    trace = Orchestrator(planner=RepeatingPlanner()).run(
        numeric_frame, "in_memory", "X", "Y"
    )

    assert trace["iterations"][-1]["executor"]["error"]["code"] == "DUPLICATE_ACTION"


def test_duplicate_action_is_not_executed_twice(numeric_frame: pd.DataFrame) -> None:
    executor = CountingExecutor()
    Orchestrator(planner=RepeatingPlanner(), executor=executor).run(
        numeric_frame, "in_memory", "X", "Y"
    )

    assert executor.calls == 1


def test_duplicate_counter_is_incremented(numeric_frame: pd.DataFrame) -> None:
    trace = Orchestrator(planner=RepeatingPlanner()).run(
        numeric_frame, "in_memory", "X", "Y"
    )

    assert trace["final"]["duplicate_actions_prevented"] == 1
    assert trace["final"]["stop_reason"] == "NO_NEW_ACTIONS"


def test_unknown_tool_is_controlled(numeric_frame: pd.DataFrame) -> None:
    trace = Orchestrator(planner=UnknownToolPlanner()).run(
        numeric_frame, "in_memory", "X", "Y"
    )

    assert trace["iterations"][0]["executor"]["error"]["code"] == "UNKNOWN_TOOL"
    assert trace["final"]["stop_reason"] == "EXECUTION_ERROR"


def test_invalid_parameters_are_controlled(numeric_frame: pd.DataFrame) -> None:
    trace = Orchestrator(planner=InvalidParametersPlanner()).run(
        numeric_frame, "in_memory", "X", "Y"
    )

    assert trace["iterations"][0]["executor"]["error"]["code"] == "INVALID_PARAMETERS"
    assert trace["final"]["stop_reason"] == "EXECUTION_ERROR"


def test_failed_execution_counter_is_incremented(numeric_frame: pd.DataFrame) -> None:
    trace = Orchestrator(planner=UnknownToolPlanner()).run(
        numeric_frame, "in_memory", "X", "Y"
    )

    assert trace["final"]["failed_executions"] == 1
    assert trace["final"]["successful_executions"] == 0


def test_trace_preserves_prior_success_before_error(numeric_frame: pd.DataFrame) -> None:
    trace = Orchestrator(planner=ProfileThenUnknownPlanner()).run(
        numeric_frame, "in_memory", "X", "Y"
    )

    assert len(trace["iterations"]) == 2
    assert trace["iterations"][0]["executor"]["status"] == "success"
    assert trace["iterations"][1]["executor"]["error"]["code"] == "UNKNOWN_TOOL"
    assert trace["final"]["successful_executions"] == 1
    assert trace["final"]["failed_executions"] == 1


def test_failed_trace_is_serializable_and_persisted(
    numeric_frame: pd.DataFrame,
    tmp_path: Path,
) -> None:
    trace = Orchestrator(planner=UnknownToolPlanner()).run(
        numeric_frame, "in_memory", "X", "Y"
    )
    output_path = save_trace(trace, tmp_path, "failed")
    loaded = json.loads(output_path.read_text(encoding="utf-8"))

    assert loaded == trace
    assert loaded["final"]["stop_reason"] == "EXECUTION_ERROR"


def test_missing_dataset_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError) as error:
        load_and_validate_dataset(tmp_path / "missing.csv", "X", "Y")

    assert error.value.code == "DATASET_NOT_FOUND"


def test_empty_dataset_is_rejected(tmp_path: Path) -> None:
    dataset = tmp_path / "empty.csv"
    dataset.write_text("", encoding="utf-8")

    with pytest.raises(InputValidationError) as error:
        load_and_validate_dataset(dataset, "X", "Y")

    assert error.value.code == "EMPTY_DATASET"


def test_missing_x_target_is_rejected(tmp_path: Path) -> None:
    dataset = tmp_path / "data.csv"
    pd.DataFrame({"Y": [1, 2, 3]}).to_csv(dataset, index=False)

    with pytest.raises(InputValidationError) as error:
        load_and_validate_dataset(dataset, "X", "Y")

    assert error.value.code == "COLUMN_NOT_FOUND"
    assert "X" in str(error.value)


def test_missing_y_target_is_rejected(tmp_path: Path) -> None:
    dataset = tmp_path / "data.csv"
    pd.DataFrame({"X": [1, 2, 3]}).to_csv(dataset, index=False)

    with pytest.raises(InputValidationError) as error:
        load_and_validate_dataset(dataset, "X", "Y")

    assert error.value.code == "COLUMN_NOT_FOUND"
    assert "Y" in str(error.value)


@pytest.mark.parametrize("text_column", ["X", "Y"])
def test_non_numeric_target_is_rejected(tmp_path: Path, text_column: str) -> None:
    frame = pd.DataFrame({"X": [1, 2, 3], "Y": [2, 4, 6]})
    frame[text_column] = ["a", "b", "c"]
    dataset = tmp_path / "data.csv"
    frame.to_csv(dataset, index=False)

    with pytest.raises(InputValidationError) as error:
        load_and_validate_dataset(dataset, "X", "Y")

    assert error.value.code == "NON_NUMERIC_COLUMN"
    assert text_column in str(error.value)


def test_identical_targets_are_rejected(tmp_path: Path) -> None:
    dataset = tmp_path / "data.csv"
    pd.DataFrame({"X": [1, 2, 3]}).to_csv(dataset, index=False)

    with pytest.raises(InputValidationError) as error:
        load_and_validate_dataset(dataset, "X", "X")

    assert error.value.code == "INVALID_TARGETS"


def test_successful_executions_exclude_duplicate(numeric_frame: pd.DataFrame) -> None:
    trace = Orchestrator(planner=RepeatingPlanner()).run(
        numeric_frame, "in_memory", "X", "Y"
    )

    assert trace["final"]["successful_executions"] == 1
    assert trace["final"]["tools_used"] == ["pearson_correlation"]


def test_total_iterations_includes_blocked_attempt(numeric_frame: pd.DataFrame) -> None:
    trace = Orchestrator(planner=RepeatingPlanner()).run(
        numeric_frame, "in_memory", "X", "Y"
    )

    assert trace["final"]["total_iterations"] == 2
    assert len(trace["iterations"]) == 2


def test_cli_returns_nonzero_without_traceback_for_expected_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        ["--dataset", str(tmp_path / "missing.csv"), "--x", "X", "--y", "Y"]
    )
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "DATASET_NOT_FOUND" in captured.err
    assert "Traceback" not in captured.err
