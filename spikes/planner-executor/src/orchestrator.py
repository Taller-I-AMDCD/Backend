"""Traceable orchestration loop connecting the Planner and Executor."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

from .executor import Executor
from .planner import Planner, ResearchState

DEFAULT_MAX_ITERATIONS = 8


class Orchestrator:
    """Maintain state and trace execution without making analytical decisions."""

    def __init__(
        self,
        planner: Planner | None = None,
        executor: Executor | None = None,
    ) -> None:
        self._planner = planner or Planner()
        self._executor = executor or Executor()

    def run(
        self,
        frame: pd.DataFrame,
        dataset: str,
        target_x: str,
        target_y: str,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> dict[str, Any]:
        """Execute plans sequentially until the Planner or an execution error stops."""
        state = ResearchState(
            objective=f"Evaluate the association between {target_x} and {target_y}.",
            iteration=0,
            columns=[],
            numeric_columns=[],
            history=[],
            results=[],
            max_iterations=max_iterations,
            target_variables=(target_x, target_y),
        )
        iterations: list[dict[str, Any]] = []
        successful_executions = 0
        failed_executions = 0
        stop_reason = "NO_NEW_ACTIONS"

        while True:
            decision = self._planner.plan(state)
            if decision["status"] == "stop":
                stop_reason = decision["reason"]
                break

            response = self._executor.execute(
                frame,
                {
                    "tool": decision["tool"],
                    "parameters": decision["parameters"],
                },
            )
            history_entry = {
                "action_id": decision["action_id"],
                "iteration": decision["iteration"],
                "tool": decision["tool"],
                "parameters": decision["parameters"],
                "reason": decision["reason"],
            }
            result_entry = {
                "action_id": decision["action_id"],
                "iteration": decision["iteration"],
                "tool": response["tool"],
                "parameters": response["parameters"],
                "status": response["status"],
                "result": response["result"],
                "error": response["error"],
            }

            columns = list(state.columns)
            numeric_columns = list(state.numeric_columns)
            if decision["tool"] == "profile_dataset" and response["status"] == "success":
                columns, numeric_columns = self._profile_metadata(response["result"])

            state = replace(
                state,
                iteration=decision["iteration"],
                columns=columns,
                numeric_columns=numeric_columns,
                history=[*state.history, history_entry],
                results=[*state.results, result_entry],
            )
            iterations.append(
                {
                    "iteration": decision["iteration"],
                    "planner": {
                        "action_id": decision["action_id"],
                        "tool": decision["tool"],
                        "parameters": decision["parameters"],
                        "reason": decision["reason"],
                    },
                    "executor": response,
                    "state": {
                        "iteration": state.iteration,
                        "columns": state.columns,
                        "numeric_columns": state.numeric_columns,
                        "history_size": len(state.history),
                        "results_size": len(state.results),
                    },
                }
            )

            if response["status"] == "success":
                successful_executions += 1
            else:
                failed_executions += 1
                stop_reason = "EXECUTION_ERROR"
                break

        return {
            "dataset": dataset,
            "objective": state.objective,
            "target_variables": {"x": target_x, "y": target_y},
            "iterations": iterations,
            "final": {
                "stop_reason": stop_reason,
                "total_iterations": len(iterations),
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "tools_used": [
                    iteration["planner"]["tool"] for iteration in iterations
                ],
            },
        }

    @staticmethod
    def _profile_metadata(
        result: Mapping[str, Any] | None,
    ) -> tuple[list[str], list[str]]:
        if result is None:
            return [], []
        raw_columns = result.get("columns")
        raw_numeric_columns = result.get("numeric_columns")
        columns = (
            list(raw_columns)
            if isinstance(raw_columns, list)
            and all(isinstance(column, str) for column in raw_columns)
            else []
        )
        numeric_columns = (
            list(raw_numeric_columns)
            if isinstance(raw_numeric_columns, list)
            and all(isinstance(column, str) for column in raw_numeric_columns)
            else []
        )
        return columns, numeric_columns


def save_trace(
    trace: Mapping[str, Any],
    output_directory: Path,
    run_name: str,
) -> Path:
    """Persist one technical execution trace using a deterministic filename."""
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f"{run_name}_run.json"
    output_path.write_text(
        json.dumps(trace, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path
