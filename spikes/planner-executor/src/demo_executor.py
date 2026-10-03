"""Terminal demonstration of the controlled analytical Executor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .executor import ExecutionResponse, Executor

DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"


def _execute(
    executor: Executor,
    dataset_name: str,
    tool: str,
    parameters: dict[str, Any],
) -> ExecutionResponse:
    frame = pd.read_csv(DATA_DIRECTORY / f"{dataset_name}.csv")
    return executor.execute(frame, {"tool": tool, "parameters": parameters})


def _coefficient(response: ExecutionResponse) -> float:
    result = response["result"]
    if result is None:
        raise RuntimeError("The demonstration expected a successful result.")
    return float(result["coefficient"])


def main() -> None:
    executor = Executor()

    consistent = _execute(
        executor,
        "consistent_relation",
        "pearson_correlation",
        {"x": "X", "y": "Y"},
    )
    confounded = _execute(
        executor,
        "confounded_relation",
        "pearson_correlation",
        {"x": "X", "y": "Y"},
    )
    partial = _execute(
        executor,
        "confounded_relation",
        "partial_correlation",
        {"x": "X", "y": "Y", "control": "Z"},
    )
    outliers = _execute(
        executor,
        "outlier_relation",
        "correlation_without_outliers",
        {"x": "X", "y": "Y"},
    )
    invalid = executor.execute(
        pd.DataFrame(),
        {"tool": "unsupported_tool", "parameters": {}},
    )

    outlier_result = outliers["result"]
    invalid_error = invalid["error"]
    if outlier_result is None or invalid_error is None:
        raise RuntimeError("The demonstration received an unexpected response.")

    print("=" * 40)
    print("EXECUTOR DEMO")
    print("=" * 40)
    _print_correlation("consistent_relation", "pearson_correlation", consistent)
    _print_correlation("confounded_relation", "pearson_correlation", confounded)

    print("Scenario: confounded_relation")
    print("Tool: partial_correlation")
    print("Control: Z")
    print(f"Status: {partial['status']}")
    print(f"Coefficient: {_coefficient(partial):.4f}")
    print()

    print("Scenario: outlier_relation")
    print("Tool: correlation_without_outliers")
    print(f"Status: {outliers['status']}")
    print(f"Original correlation: {outlier_result['original_correlation']:.4f}")
    print(f"Filtered correlation: {outlier_result['filtered_correlation']:.4f}")
    print(f"Removed observations: {outlier_result['removed_count']}")
    print()

    print("Invalid tool test")
    print("Tool: unsupported_tool")
    print(f"Status: {invalid['status']}")
    print(f"Error code: {invalid_error['code']}")


def _print_correlation(
    scenario: str,
    tool: str,
    response: ExecutionResponse,
) -> None:
    print(f"Scenario: {scenario}")
    print(f"Tool: {tool}")
    print(f"Status: {response['status']}")
    print(f"Coefficient: {_coefficient(response):.4f}")
    print()


if __name__ == "__main__":
    main()
