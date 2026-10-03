"""Command-line entry point for an integrated Planner–Executor run."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .orchestrator import DEFAULT_MAX_ITERATIONS, Orchestrator, save_trace

RESULTS_DIRECTORY = Path(__file__).resolve().parents[1] / "results"


def parse_arguments() -> argparse.Namespace:
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
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.max_iterations < 1:
        raise SystemExit("--max-iterations must be at least 1.")

    frame = pd.read_csv(arguments.dataset)
    trace = Orchestrator().run(
        frame=frame,
        dataset=arguments.dataset.as_posix(),
        target_x=arguments.x,
        target_y=arguments.y,
        max_iterations=arguments.max_iterations,
    )
    output_path = save_trace(trace, RESULTS_DIRECTORY, arguments.dataset.stem)
    print_trace(trace, output_path)


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
    main()
