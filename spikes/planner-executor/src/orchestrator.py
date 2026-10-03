"""Traceable orchestration loop connecting the Planner and Executor."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

from .contracts import StopReason
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
        duplicate_actions_prevented = 0
        stop_reason = StopReason.NO_NEW_ACTIONS.value
        executed_action_identities: set[str] = set()
        tools_used: list[str] = []

        while True:
            if len(iterations) >= max_iterations:
                stop_reason = StopReason.MAX_ITERATIONS.value
                break

            decision = self._planner.plan(state)
            if decision["status"] == "stop":
                stop_reason = decision["reason"]
                break

            iteration_number = len(iterations) + 1
            action_identity = self._action_identity(
                decision["tool"], decision["parameters"]
            )
            if action_identity in executed_action_identities:
                duplicate_actions_prevented += 1
                iterations.append(
                    {
                        "iteration": iteration_number,
                        "planner": {
                            "action_id": decision["action_id"],
                            "tool": decision["tool"],
                            "parameters": decision["parameters"],
                            "reason": decision["reason"],
                        },
                        "executor": {
                            "status": "skipped",
                            "tool": decision["tool"],
                            "parameters": decision["parameters"],
                            "result": None,
                            "error": {
                                "code": "DUPLICATE_ACTION",
                                "message": "Duplicate action blocked before execution.",
                            },
                        },
                        "state": self._state_snapshot(state),
                    }
                )
                stop_reason = StopReason.NO_NEW_ACTIONS.value
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
                "iteration": iteration_number,
                "tool": decision["tool"],
                "parameters": decision["parameters"],
                "reason": decision["reason"],
            }
            result_entry = {
                "action_id": decision["action_id"],
                "iteration": iteration_number,
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
                iteration=iteration_number,
                columns=columns,
                numeric_columns=numeric_columns,
                history=[*state.history, history_entry],
                results=[*state.results, result_entry],
            )
            iterations.append(
                {
                    "iteration": iteration_number,
                    "planner": {
                        "action_id": decision["action_id"],
                        "tool": decision["tool"],
                        "parameters": decision["parameters"],
                        "reason": decision["reason"],
                    },
                    "executor": response,
                    "state": self._state_snapshot(state),
                }
            )
            executed_action_identities.add(action_identity)

            if response["status"] == "success":
                successful_executions += 1
                tools_used.append(decision["tool"])
            else:
                failed_executions += 1
                stop_reason = StopReason.EXECUTION_ERROR.value
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
                "duplicate_actions_prevented": duplicate_actions_prevented,
                "tools_used": tools_used,
            },
        }

    @staticmethod
    def _action_identity(tool: str, parameters: Mapping[str, Any]) -> str:
        normalized_parameters = json.dumps(
            parameters,
            sort_keys=True,
            separators=(",", ":"),
            default=repr,
        )
        return f"{tool}:{normalized_parameters}"

    @staticmethod
    def _state_snapshot(state: ResearchState) -> dict[str, Any]:
        return {
            "iteration": state.iteration,
            "columns": state.columns,
            "numeric_columns": state.numeric_columns,
            "history_size": len(state.history),
            "results_size": len(state.results),
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
