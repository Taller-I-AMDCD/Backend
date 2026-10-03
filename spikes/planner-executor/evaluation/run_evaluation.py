"""Run the reproducible final evaluation of the Planner–Executor spike."""

from __future__ import annotations

import ast
import csv
import json
import math
import platform
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.executor import Executor
from src.main import InputValidationError, load_and_validate_dataset
from src.orchestrator import DEFAULT_MAX_ITERATIONS, Orchestrator
from src.planner import ResearchState
from src.tools import TOOL_REGISTRY

ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
DATA_DIRECTORY = ROOT_DIRECTORY / "data"
DEFAULT_OUTPUT_DIRECTORY = ROOT_DIRECTORY / "results" / "evaluation"
WARMUP_RUNS = 3
MEASURED_RUNS = 20
EXPECTED_ROWS = 500

STRONG_ASSOCIATION_THRESHOLD = 0.70
CONFOUNDING_REDUCTION_RATIO = 0.30
OUTLIER_REDUCTION_RATIO = 0.50
STABLE_FILTERED_THRESHOLD = 0.70

REQUIRED_CSV_COLUMNS = [
    "scenario",
    "correct_behavior_detected",
    "iterations",
    "successful_executions",
    "failed_executions",
    "duplicate_actions_prevented",
    "tools_used",
    "stop_reason",
    "median_execution_ms",
    "p95_execution_ms",
    "pearson",
    "spearman",
    "partial_correlation",
    "original_correlation",
    "filtered_correlation",
    "removed_count",
    "absolute_change",
]


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario: str
    filename: str
    expected_behavior: str


SCENARIOS = (
    ScenarioDefinition(
        scenario="consistent_relation",
        filename="consistent_relation.csv",
        expected_behavior="The X-Y association remains strong across robustness checks.",
    ),
    ScenarioDefinition(
        scenario="confounded_relation",
        filename="confounded_relation.csv",
        expected_behavior=(
            "The X-Y association decreases substantially after controlling an "
            "additional numeric variable."
        ),
    ),
    ScenarioDefinition(
        scenario="outlier_relation",
        filename="outlier_relation.csv",
        expected_behavior=(
            "The X-Y association decreases substantially after removing detected "
            "extreme observations."
        ),
    ),
)


def run_evaluation(
    warmup_runs: int = WARMUP_RUNS,
    measured_runs: int = MEASURED_RUNS,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> dict[str, Any]:
    """Evaluate every scenario and return a JSON-compatible report."""
    if warmup_runs < 0 or measured_runs < 1:
        raise ValueError("Evaluation requires non-negative warm-ups and measured runs.")

    scenario_results = [
        _evaluate_scenario(definition, warmup_runs, measured_runs, max_iterations)
        for definition in SCENARIOS
    ]
    all_timings = [
        timing
        for scenario in scenario_results
        for timing in scenario["execution_times_ms"]
    ]
    execution_paths = {
        tuple(scenario["tools_used"]) for scenario in scenario_results
    }
    successful_scenarios = sum(
        bool(scenario["correct_behavior_detected"])
        for scenario in scenario_results
    )
    total_scenarios = len(scenario_results)

    return {
        "environment": _environment_metrics(warmup_runs, measured_runs),
        "protocol": {
            "target_x": "X",
            "target_y": "Y",
            "expected_rows_per_scenario": EXPECTED_ROWS,
            "warmup_runs": warmup_runs,
            "measured_runs": measured_runs,
            "max_iterations": max_iterations,
            "timing_scope": "In-memory Planner-Executor orchestration",
            "functional_reproducibility_required": True,
        },
        "scenarios": scenario_results,
        "global_metrics": {
            "total_scenarios": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "success_rate": successful_scenarios / total_scenarios * 100,
            "total_iterations": sum(
                scenario["total_iterations"] for scenario in scenario_results
            ),
            "mean_iterations_per_scenario": statistics.mean(
                scenario["total_iterations"] for scenario in scenario_results
            ),
            "min_iterations": min(
                scenario["total_iterations"] for scenario in scenario_results
            ),
            "max_iterations": max(
                scenario["total_iterations"] for scenario in scenario_results
            ),
            "total_tool_executions": sum(
                scenario["successful_executions"] for scenario in scenario_results
            ),
            "total_failed_executions": sum(
                scenario["failed_executions"] for scenario in scenario_results
            ),
            "total_duplicate_actions_prevented": sum(
                scenario["duplicate_actions_prevented"]
                for scenario in scenario_results
            ),
            "mean_execution_ms": statistics.mean(all_timings),
            "median_execution_ms": statistics.median(all_timings),
            "unique_execution_paths": len(execution_paths),
            "distinct_tools_used": len(
                {
                    tool
                    for scenario in scenario_results
                    for tool in scenario["tools_used"]
                }
            ),
            "execution_paths": {
                scenario["scenario"]: scenario["tools_used"]
                for scenario in scenario_results
            },
        },
        "control": _control_metrics(),
        "robustness": _robustness_metrics(),
        "structural_metrics": _structural_metrics(),
    }


def write_results(
    report: Mapping[str, Any],
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    """Write the official JSON and one-row-per-scenario CSV outputs."""
    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / "planner_executor_metrics.json"
    csv_path = output_directory / "planner_executor_scenarios.csv"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=REQUIRED_CSV_COLUMNS)
        writer.writeheader()
        for scenario in report["scenarios"]:
            statistics_result = scenario["statistics"]
            writer.writerow(
                {
                    "scenario": scenario["scenario"],
                    "correct_behavior_detected": scenario[
                        "correct_behavior_detected"
                    ],
                    "iterations": scenario["total_iterations"],
                    "successful_executions": scenario["successful_executions"],
                    "failed_executions": scenario["failed_executions"],
                    "duplicate_actions_prevented": scenario[
                        "duplicate_actions_prevented"
                    ],
                    "tools_used": " > ".join(scenario["tools_used"]),
                    "stop_reason": scenario["stop_reason"],
                    "median_execution_ms": scenario["timing"][
                        "median_execution_ms"
                    ],
                    "p95_execution_ms": scenario["timing"]["p95_execution_ms"],
                    "pearson": statistics_result.get("pearson", ""),
                    "spearman": statistics_result.get("spearman", ""),
                    "partial_correlation": statistics_result.get(
                        "partial_correlation", ""
                    ),
                    "original_correlation": statistics_result.get(
                        "original_correlation", ""
                    ),
                    "filtered_correlation": statistics_result.get(
                        "filtered_correlation", ""
                    ),
                    "removed_count": statistics_result.get("removed_count", ""),
                    "absolute_change": statistics_result.get("absolute_change", ""),
                }
            )
    return json_path, csv_path


def _evaluate_scenario(
    definition: ScenarioDefinition,
    warmup_runs: int,
    measured_runs: int,
    max_iterations: int,
) -> dict[str, Any]:
    dataset_path = DATA_DIRECTORY / definition.filename
    frame = load_and_validate_dataset(dataset_path, "X", "Y")
    reference_trace: dict[str, Any] | None = None

    for _ in range(warmup_runs):
        trace = Orchestrator().run(
            frame, definition.filename, "X", "Y", max_iterations=max_iterations
        )
        reference_trace = _require_same_trace(reference_trace, trace, definition.scenario)

    timings: list[float] = []
    for _ in range(measured_runs):
        started_at = time.perf_counter()
        trace = Orchestrator().run(
            frame, definition.filename, "X", "Y", max_iterations=max_iterations
        )
        timings.append((time.perf_counter() - started_at) * 1000)
        reference_trace = _require_same_trace(reference_trace, trace, definition.scenario)

    if reference_trace is None:
        raise RuntimeError(f"Scenario '{definition.scenario}' produced no trace.")

    statistical_results = _statistical_results(reference_trace)
    correct_behavior = _correct_behavior(
        definition.scenario,
        reference_trace,
        statistical_results,
    )
    final = reference_trace["final"]
    return {
        "scenario": definition.scenario,
        "rows": int(len(frame)),
        "expected_behavior": definition.expected_behavior,
        "correct_behavior_detected": correct_behavior,
        "functional_reproducibility": True,
        "total_iterations": final["total_iterations"],
        "successful_executions": final["successful_executions"],
        "failed_executions": final["failed_executions"],
        "duplicate_actions_prevented": final["duplicate_actions_prevented"],
        "tools_used": final["tools_used"],
        "stop_reason": final["stop_reason"],
        "trace_complete": _trace_is_complete(reference_trace),
        "statistics": statistical_results,
        "timing": _timing_metrics(timings),
        "execution_times_ms": timings,
    }


def _require_same_trace(
    reference: dict[str, Any] | None,
    candidate: dict[str, Any],
    scenario: str,
) -> dict[str, Any]:
    if reference is not None and candidate != reference:
        raise RuntimeError(
            f"Scenario '{scenario}' changed functionally between repetitions."
        )
    return candidate if reference is None else reference


def _statistical_results(trace: Mapping[str, Any]) -> dict[str, Any]:
    pearson = _tool_result(trace, "pearson_correlation")
    spearman = _tool_result(trace, "spearman_correlation")
    outlier = _tool_result(trace, "correlation_without_outliers")
    partial = _optional_tool_result(trace, "partial_correlation")
    results: dict[str, Any] = {
        "pearson": pearson["coefficient"],
        "spearman": spearman["coefficient"],
        "original_correlation": outlier["original_correlation"],
        "filtered_correlation": outlier["filtered_correlation"],
        "removed_count": outlier["removed_count"],
        "absolute_change": abs(
            outlier["original_correlation"] - outlier["filtered_correlation"]
        ),
    }
    if partial is not None:
        results["partial_correlation"] = partial["coefficient"]
        results["partial_absolute_change"] = abs(
            pearson["coefficient"] - partial["coefficient"]
        )
        denominator = abs(pearson["coefficient"])
        results["partial_relative_reduction"] = (
            1 - abs(partial["coefficient"]) / denominator
            if denominator > 0
            else None
        )
    return results


def _correct_behavior(
    scenario: str,
    trace: Mapping[str, Any],
    results: Mapping[str, Any],
) -> bool:
    completed = (
        trace["final"]["stop_reason"] == "NO_NEW_ACTIONS"
        and trace["final"]["failed_executions"] == 0
        and _trace_is_complete(trace)
    )
    if scenario == "consistent_relation":
        return bool(
            completed
            and abs(results["pearson"]) >= STRONG_ASSOCIATION_THRESHOLD
            and abs(results["spearman"]) >= STRONG_ASSOCIATION_THRESHOLD
            and abs(results["filtered_correlation"]) >= STABLE_FILTERED_THRESHOLD
        )
    if scenario == "confounded_relation":
        return bool(
            completed
            and "partial_correlation" in trace["final"]["tools_used"]
            and abs(results["pearson"]) >= STRONG_ASSOCIATION_THRESHOLD
            and abs(results["partial_correlation"])
            <= abs(results["pearson"]) * CONFOUNDING_REDUCTION_RATIO
        )
    if scenario == "outlier_relation":
        return bool(
            completed
            and "correlation_without_outliers" in trace["final"]["tools_used"]
            and results["removed_count"] > 0
            and abs(results["filtered_correlation"])
            <= abs(results["original_correlation"]) * OUTLIER_REDUCTION_RATIO
        )
    return False


def _tool_result(trace: Mapping[str, Any], tool: str) -> Mapping[str, Any]:
    result = _optional_tool_result(trace, tool)
    if result is None:
        raise RuntimeError(f"Required tool result is missing: {tool}")
    return result


def _optional_tool_result(
    trace: Mapping[str, Any], tool: str
) -> Mapping[str, Any] | None:
    for iteration in trace["iterations"]:
        if iteration["planner"]["tool"] == tool:
            result = iteration["executor"]["result"]
            return result if isinstance(result, Mapping) else None
    return None


def _trace_is_complete(trace: Mapping[str, Any]) -> bool:
    if not isinstance(trace.get("final"), Mapping):
        return False
    if "stop_reason" not in trace["final"]:
        return False
    for iteration in trace.get("iterations", []):
        planner = iteration.get("planner", {})
        executor = iteration.get("executor", {})
        if not {"action_id", "tool", "parameters", "reason"}.issubset(planner):
            return False
        if not {"status", "tool", "parameters", "result", "error"}.issubset(
            executor
        ):
            return False
    return True


def _timing_metrics(timings: list[float]) -> dict[str, float]:
    ordered = sorted(timings)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "min_execution_ms": min(ordered),
        "max_execution_ms": max(ordered),
        "mean_execution_ms": statistics.mean(ordered),
        "median_execution_ms": statistics.median(ordered),
        "p95_execution_ms": ordered[p95_index],
    }


def _environment_metrics(warmup_runs: int, measured_runs: int) -> dict[str, Any]:
    processor = platform.processor().strip()
    return {
        "python_version": platform.python_version(),
        "operating_system": platform.system(),
        "platform": platform.platform(),
        "processor": processor if processor else "unavailable",
        "warmup_runs": warmup_runs,
        "measured_runs": measured_runs,
    }


def _control_metrics() -> dict[str, Any]:
    response = Executor().execute(
        pd.DataFrame(),
        {"tool": "unsupported_tool", "parameters": {}},
    )
    return {
        "registered_tools_count": len(TOOL_REGISTRY),
        "arbitrary_tool_blocked": (
            response["status"] == "error"
            and response["error"] is not None
            and response["error"]["code"] == "UNKNOWN_TOOL"
        ),
    }


class _RepeatingPlanner:
    def plan(self, state: ResearchState) -> dict[str, Any]:
        return _evaluation_action(
            state, "pearson_correlation", {"x": "X", "y": "Y"}
        )


class _EndlessPlanner:
    def plan(self, state: ResearchState) -> dict[str, Any]:
        return _evaluation_action(
            state,
            "detect_outliers",
            {"column": "X", "multiplier": 1.5 + state.iteration / 10},
        )


class _UnknownToolPlanner:
    def plan(self, state: ResearchState) -> dict[str, Any]:
        return _evaluation_action(state, "unsupported_tool", {})


def _evaluation_action(
    state: ResearchState,
    tool: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    iteration = state.iteration + 1
    return {
        "status": "action",
        "action_id": f"action-{iteration:03d}",
        "iteration": iteration,
        "tool": tool,
        "parameters": parameters,
        "reason": "Verify an existing execution safeguard.",
    }


def _robustness_metrics() -> dict[str, bool]:
    frame = pd.DataFrame(
        {"X": [1.0, 2.0, 3.0, 4.0], "Y": [2.0, 4.0, 6.0, 8.0]}
    )
    duplicate = Orchestrator(planner=_RepeatingPlanner()).run(
        frame, "in_memory", "X", "Y"
    )
    maximum = Orchestrator(planner=_EndlessPlanner()).run(
        frame, "in_memory", "X", "Y", max_iterations=3
    )
    execution_error = Orchestrator(planner=_UnknownToolPlanner()).run(
        frame, "in_memory", "X", "Y"
    )
    input_validation = False
    try:
        load_and_validate_dataset(Path("__missing_evaluation_input__.csv"), "X", "Y")
    except InputValidationError as error:
        input_validation = error.code == "DATASET_NOT_FOUND"

    return {
        "duplicate_protection": (
            duplicate["final"]["duplicate_actions_prevented"] == 1
            and duplicate["final"]["successful_executions"] == 1
        ),
        "max_iteration_protection": (
            maximum["final"]["stop_reason"] == "MAX_ITERATIONS"
            and maximum["final"]["total_iterations"] == 3
        ),
        "execution_error_handling": (
            execution_error["final"]["stop_reason"] == "EXECUTION_ERROR"
            and execution_error["final"]["failed_executions"] == 1
        ),
        "input_validation": input_validation,
    }


def _structural_metrics() -> dict[str, int]:
    production_modules = sorted(
        path
        for path in (ROOT_DIRECTORY / "src").glob("*.py")
        if path.name != "__init__.py" and not path.name.startswith("demo_")
    )
    productive_loc = sum(_approximate_code_lines(path) for path in production_modules)
    test_functions = sum(
        _count_test_functions(path)
        for path in (ROOT_DIRECTORY / "tests").glob("test_*.py")
    )
    return {
        "productive_python_modules": len(production_modules),
        "approximate_productive_loc": productive_loc,
        "test_functions": test_functions,
        "registered_tools": len(TOOL_REGISTRY),
    }


def _approximate_code_lines(path: Path) -> int:
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _count_test_functions(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


def print_report(report: Mapping[str, Any], json_path: Path, csv_path: Path) -> None:
    print("=" * 69)
    print("PLANNER-EXECUTOR FINAL EVALUATION")
    print("=" * 69)
    print()
    print(
        f"{'Scenario':<20}{'Correct':<10}{'Iter.':<8}{'Exec.':<8}"
        f"{'Errors':<9}{'Median ms':<12}{'Stop'}"
    )
    print("-" * 69)
    for scenario in report["scenarios"]:
        correct = "YES" if scenario["correct_behavior_detected"] else "NO"
        print(
            f"{scenario['scenario']:<20}{correct:<10}"
            f"{scenario['total_iterations']:<8}"
            f"{scenario['successful_executions']:<8}"
            f"{scenario['failed_executions']:<9}"
            f"{scenario['timing']['median_execution_ms']:<12.3f}"
            f"{scenario['stop_reason']}"
        )
    print("-" * 69)

    global_metrics = report["global_metrics"]
    print(
        "Successful scenarios: "
        f"{global_metrics['successful_scenarios']} / {global_metrics['total_scenarios']}"
    )
    print(f"Success rate: {global_metrics['success_rate']:.1f}%")
    print(f"Failed executions: {global_metrics['total_failed_executions']}")
    print(
        "Duplicate actions prevented: "
        f"{global_metrics['total_duplicate_actions_prevented']}"
    )
    print(f"Unique execution paths: {global_metrics['unique_execution_paths']}")
    print()
    print("Robustness")
    print("-" * 10)
    for name, passed in report["robustness"].items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print()
    print("Environment")
    print("-" * 11)
    print(f"Python: {report['environment']['python_version']}")
    print(f"Platform: {report['environment']['platform']}")
    print()
    print("Results:")
    print(json_path.relative_to(ROOT_DIRECTORY).as_posix())
    print(csv_path.relative_to(ROOT_DIRECTORY).as_posix())


def main() -> None:
    report = run_evaluation()
    json_path, csv_path = write_results(report)
    print_report(report, json_path, csv_path)


if __name__ == "__main__":
    main()
