"""Command-line entry point for an integrated Planner–Executor run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
from pandas.api.types import is_numeric_dtype

from .orchestrator import DEFAULT_MAX_ITERATIONS, Orchestrator, save_trace

RESULTS_DIRECTORY = Path(__file__).resolve().parents[1] / "results"


class InputValidationError(ValueError):
    """Represent an expected user-facing dataset or target validation error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Planner–Executor analytical evaluation loop."
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--x", required=True)
    parser.add_argument("--y", required=True)
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(arguments)
    if arguments.max_iterations < 1:
        print("Input error [INVALID_PARAMETERS]: --max-iterations must be at least 1.", file=sys.stderr)
        return 2

    try:
        frame = load_and_validate_dataset(arguments.dataset, arguments.x, arguments.y)
    except InputValidationError as error:
        print(f"Input error [{error.code}]: {error}", file=sys.stderr)
        return 2

    trace = Orchestrator().run(
        frame=frame,
        dataset=arguments.dataset.as_posix(),
        target_x=arguments.x,
        target_y=arguments.y,
        max_iterations=arguments.max_iterations,
    )
    output_path = save_trace(trace, RESULTS_DIRECTORY, arguments.dataset.stem)
    print_trace(trace, output_path)
    return 0


def load_and_validate_dataset(dataset: Path, target_x: str, target_y: str) -> pd.DataFrame:
    """Load a CSV and reject expected input problems before orchestration."""
    if not dataset.is_file():
        raise InputValidationError(
            "DATASET_NOT_FOUND",
            f"Dataset file does not exist: {dataset}",
        )
    if target_x == target_y:
        raise InputValidationError(
            "INVALID_TARGETS",
            "Target columns X and Y must be different.",
        )
    try:
        frame = pd.read_csv(dataset)
    except pd.errors.EmptyDataError as error:
        raise InputValidationError("EMPTY_DATASET", "Dataset is empty.") from error
    if frame.empty:
        raise InputValidationError("EMPTY_DATASET", "Dataset contains no rows.")

    missing_columns = [
        column for column in (target_x, target_y) if column not in frame.columns
    ]
    if missing_columns:
        raise InputValidationError(
            "COLUMN_NOT_FOUND",
            f"Target column not found: {', '.join(missing_columns)}.",
        )
    non_numeric_columns = [
        column
        for column in (target_x, target_y)
        if not is_numeric_dtype(frame[column])
    ]
    if non_numeric_columns:
        raise InputValidationError(
            "NON_NUMERIC_COLUMN",
            f"Target column must be numeric: {', '.join(non_numeric_columns)}.",
        )
    return frame


def print_trace(trace: Mapping[str, Any], output_path: Path) -> None:
    """Render a compact terminal view without changing the recorded trace."""
    targets = trace["target_variables"]
    print("=" * 40)
    print("PLANNER-EXECUTOR RUN")
    print("=" * 40)
    print(f"Dataset: {Path(str(trace['dataset'])).name}")
    print(f"Target: {targets['x']} <-> {targets['y']}")

    for entry in trace["iterations"]:
        planner = entry["planner"]
        executor = entry["executor"]
        print()
        print("-" * 40)
        print(f"ITERATION {entry['iteration']}")
        print("-" * 40)
        print("Planner:")
        print(f"Tool: {planner['tool']}")
        if planner["parameters"]:
            parameters = ", ".join(
                f"{key}={value}" for key, value in planner["parameters"].items()
            )
            print(f"Parameters: {parameters}")
        print(f"Reason: {planner['reason']}")
        print()
        print("Executor:")
        print(f"Status: {executor['status']}")
        _print_result(executor["result"])
        if executor["error"] is not None:
            print(f"Error: {executor['error']['code']} - {executor['error']['message']}")

    final = trace["final"]
    print()
    print("=" * 40)
    print("FINAL")
    print("=" * 40)
    print(f"Stop reason: {final['stop_reason']}")
    print(f"Iterations: {final['total_iterations']}")
    print(f"Successful executions: {final['successful_executions']}")
    print(f"Failed executions: {final['failed_executions']}")
    print(f"Duplicate actions prevented: {final['duplicate_actions_prevented']}")
    print(f"Tools used: {', '.join(final['tools_used'])}")
    print(f"Trace: {output_path}")


def _print_result(result: Mapping[str, Any] | None) -> None:
    if result is None:
        return
    if "row_count" in result:
        print(f"Rows: {result['row_count']}")
        print(f"Numeric columns: {', '.join(result['numeric_columns'])}")
    if "coefficient" in result:
        print(f"Coefficient: {result['coefficient']:.4f}")
    if "original_correlation" in result:
        print(f"Original correlation: {result['original_correlation']:.4f}")
        print(f"Filtered correlation: {result['filtered_correlation']:.4f}")
        print(f"Removed observations: {result['removed_count']}")


if __name__ == "__main__":
    raise SystemExit(main())
