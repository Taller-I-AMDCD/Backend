"""Demonstrate orchestration safeguards with controlled scenarios."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .executor import Executor
from .main import InputValidationError, load_and_validate_dataset
from .orchestrator import Orchestrator, save_trace
from .planner import ResearchState

ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIRECTORY / "data" / "consistent_relation.csv"
RESULTS_DIRECTORY = ROOT_DIRECTORY / "results"


def _action(state: ResearchState, tool: str, parameters: dict[str, Any]) -> dict[str, Any]:
    iteration = state.iteration + 1
    return {
        "status": "action",
        "action_id": f"action-{iteration:03d}",
        "iteration": iteration,
        "tool": tool,
        "parameters": parameters,
        "reason": "Demonstrate an orchestration safeguard.",
    }


class RepeatingPlanner:
    def plan(self, state: ResearchState) -> dict[str, Any]:
        return _action(state, "pearson_correlation", {"x": "X", "y": "Y"})


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


def main() -> None:
    frame = load_and_validate_dataset(DATASET_PATH, "X", "Y")
    normal = Orchestrator().run(frame, DATASET_PATH.name, "X", "Y")

    duplicate_executor = CountingExecutor()
    duplicate = Orchestrator(
        planner=RepeatingPlanner(), executor=duplicate_executor
    ).run(frame, "in_memory_duplicate", "X", "Y")

    configured_max_iterations = 3
    maximum = Orchestrator(planner=EndlessPlanner()).run(
        frame,
        "in_memory_maximum",
        "X",
        "Y",
        max_iterations=configured_max_iterations,
    )

    invalid_tool = Orchestrator(planner=UnknownToolPlanner()).run(
        frame, "in_memory_invalid_tool", "X", "Y"
    )
    save_trace(
        invalid_tool,
        RESULTS_DIRECTORY,
        "robustness_invalid_tool",
    )
    invalid_error = invalid_tool["iterations"][0]["executor"]["error"]

    target_error = ""
    try:
        load_and_validate_dataset(DATASET_PATH, "missing_column", "Y")
    except InputValidationError as error:
        target_error = f"{error.code}: {error}"

    print("=" * 40)
    print("ROBUSTNESS DEMO")
    print("=" * 40)
    print()
    print("CASE 1 - Normal execution")
    print("Status: completed")
    print(f"Stop reason: {normal['final']['stop_reason']}")
    print(f"Failed executions: {normal['final']['failed_executions']}")
    print()
    print("CASE 2 - Duplicate action protection")
    print(
        "Duplicate actions prevented: "
        f"{duplicate['final']['duplicate_actions_prevented']}"
    )
    print(f"Executor duplicate executions: {max(0, duplicate_executor.calls - 1)}")
    print(f"Stop reason: {duplicate['final']['stop_reason']}")
    print()
    print("CASE 3 - Maximum iterations")
    print(f"Configured max iterations: {configured_max_iterations}")
    print(f"Iterations executed: {maximum['final']['total_iterations']}")
    print(f"Stop reason: {maximum['final']['stop_reason']}")
    print()
    print("CASE 4 - Invalid tool")
    print("Tool: unsupported_tool")
    print(f"Executor error: {invalid_error['code']}")
    print(f"Failed executions: {invalid_tool['final']['failed_executions']}")
    print(f"Stop reason: {invalid_tool['final']['stop_reason']}")
    print()
    print("CASE 5 - Invalid target column")
    print("Target: missing_column")
    print(f"Handled: {'yes' if target_error else 'no'}")
    print(f"Error: {target_error}")


if __name__ == "__main__":
    main()
