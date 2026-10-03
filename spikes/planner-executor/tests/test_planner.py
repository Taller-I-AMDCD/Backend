"""Tests for deterministic analytical planning decisions."""

from __future__ import annotations

import ast
import inspect
import json
from typing import Any, Mapping

import src.planner as planner_module
from src.planner import ASSOCIATION_THRESHOLD, Planner, ResearchState

TARGETS = ("X", "Y")
PAIR = {"x": "X", "y": "Y"}


def _history(tool: str, **parameters: Any) -> Mapping[str, Any]:
    return {"tool": tool, "parameters": parameters}


def _result(
    tool: str,
    result: Mapping[str, Any],
    **parameters: Any,
) -> Mapping[str, Any]:
    return {
        "status": "success",
        "tool": tool,
        "parameters": parameters,
        "result": result,
    }


def _state(
    *,
    numeric_columns: list[str],
    iteration: int = 0,
    history: list[Mapping[str, Any]] | None = None,
    results: list[Mapping[str, Any]] | None = None,
    max_iterations: int = 6,
) -> ResearchState:
    return ResearchState(
        objective="Evaluate the association between X and Y.",
        iteration=iteration,
        columns=list(numeric_columns),
        numeric_columns=numeric_columns,
        history=history or [],
        results=results or [],
        max_iterations=max_iterations,
        target_variables=TARGETS,
    )


def _strong_pearson_result() -> Mapping[str, Any]:
    return _result(
        "pearson_correlation",
        {"coefficient": 0.83, "sample_size": 500},
        **PAIR,
    )


def test_requests_profile_when_metadata_is_missing() -> None:
    decision = Planner().plan(_state(numeric_columns=[]))

    assert decision["status"] == "action"
    assert decision["tool"] == "profile_dataset"
    assert decision["parameters"] == {}


def test_skips_profile_when_metadata_is_available() -> None:
    decision = Planner().plan(_state(numeric_columns=["X", "Y"]))

    assert decision["status"] == "action"
    assert decision["tool"] != "profile_dataset"


def test_requests_pearson_as_initial_analysis() -> None:
    decision = Planner().plan(_state(numeric_columns=["X", "Y"]))

    assert decision["tool"] == "pearson_correlation"
    assert decision["parameters"] == PAIR


def test_requests_partial_correlation_for_strong_association_with_candidate() -> None:
    state = _state(
        numeric_columns=["X", "Y", "candidate_control"],
        iteration=1,
        history=[_history("pearson_correlation", **PAIR)],
        results=[_strong_pearson_result()],
    )

    decision = Planner().plan(state)

    assert decision["tool"] == "partial_correlation"
    assert decision["parameters"] == {
        "x": "X",
        "y": "Y",
        "control": "candidate_control",
    }


def test_without_third_variable_requests_outlier_contrast() -> None:
    state = _state(
        numeric_columns=["X", "Y"],
        iteration=1,
        history=[_history("pearson_correlation", **PAIR)],
        results=[_strong_pearson_result()],
    )

    decision = Planner().plan(state)

    assert decision["tool"] == "correlation_without_outliers"
    assert decision["parameters"] == PAIR


def test_requests_spearman_after_outlier_contrast() -> None:
    state = _state(
        numeric_columns=["X", "Y"],
        iteration=2,
        history=[
            _history("pearson_correlation", **PAIR),
            _history("correlation_without_outliers", **PAIR),
        ],
        results=[_strong_pearson_result()],
    )

    decision = Planner().plan(state)

    assert decision["tool"] == "spearman_correlation"


def test_does_not_generate_exact_duplicate_action() -> None:
    partial_parameters = {"x": "X", "y": "Y", "control": "control_a"}
    state = _state(
        numeric_columns=["control_a", "Y", "X"],
        iteration=2,
        history=[
            _history("pearson_correlation", **PAIR),
            _history("partial_correlation", **partial_parameters),
        ],
        results=[_strong_pearson_result()],
    )

    decision = Planner().plan(state)

    assert decision["tool"] == "correlation_without_outliers"


def test_stops_when_no_new_actions_exist() -> None:
    state = _state(
        numeric_columns=["X", "Y"],
        iteration=3,
        history=[
            _history("pearson_correlation", **PAIR),
            _history("correlation_without_outliers", **PAIR),
            _history("spearman_correlation", **PAIR),
        ],
        results=[_strong_pearson_result()],
    )

    decision = Planner().plan(state)

    assert decision == {
        "status": "stop",
        "iteration": 3,
        "reason": "NO_NEW_ACTIONS",
    }


def test_stops_at_max_iterations() -> None:
    state = _state(
        numeric_columns=["X", "Y"],
        iteration=4,
        max_iterations=4,
    )

    decision = Planner().plan(state)

    assert decision["status"] == "stop"
    assert decision["reason"] == "MAX_ITERATIONS"


def test_stops_when_initial_association_is_weak() -> None:
    weak_result = _result(
        "pearson_correlation",
        {"coefficient": ASSOCIATION_THRESHOLD - 0.1, "sample_size": 100},
        **PAIR,
    )
    state = _state(
        numeric_columns=["X", "Y", "control_a"],
        iteration=1,
        history=[_history("pearson_correlation", **PAIR)],
        results=[weak_result],
    )

    decision = Planner().plan(state)

    assert decision["status"] == "stop"
    assert decision["reason"] == "SUFFICIENT_EVIDENCE"


def test_decisions_are_json_serializable() -> None:
    action = Planner().plan(_state(numeric_columns=["X", "Y"]))
    stop = Planner().plan(
        _state(numeric_columns=["X", "Y"], iteration=1, max_iterations=1)
    )

    assert json.loads(json.dumps(action)) == action
    assert json.loads(json.dumps(stop)) == stop


def test_planner_does_not_import_or_call_analytical_runtime() -> None:
    source = inspect.getsource(planner_module)
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert imported_roots.isdisjoint({"pandas", "numpy", "tools", "executor"})
    assert called_names.isdisjoint(
        {
            "profile_dataset",
            "pearson_correlation",
            "spearman_correlation",
            "partial_correlation",
            "correlation_without_outliers",
        }
    )


def test_planner_does_not_load_csv_files() -> None:
    source = inspect.getsource(planner_module).lower()

    assert "read_csv" not in source
    assert ".csv" not in source


def test_planner_does_not_depend_on_dataset_names() -> None:
    source = inspect.getsource(planner_module)

    assert "consistent_relation" not in source
    assert "confounded_relation" not in source
    assert "outlier_relation" not in source
