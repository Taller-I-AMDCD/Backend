"""Deterministic rule-based planner for analytical evaluation actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, TypedDict

ASSOCIATION_THRESHOLD = 0.5

PROFILE_TOOL = "profile_dataset"
PEARSON_TOOL = "pearson_correlation"
PARTIAL_TOOL = "partial_correlation"
OUTLIER_TOOL = "correlation_without_outliers"
SPEARMAN_TOOL = "spearman_correlation"


class ActionDecision(TypedDict):
    status: Literal["action"]
    action_id: str
    iteration: int
    tool: str
    parameters: dict[str, Any]
    reason: str


class StopDecision(TypedDict):
    status: Literal["stop"]
    iteration: int
    reason: str


PlannerDecision = ActionDecision | StopDecision


@dataclass(frozen=True)
class ResearchState:
    """Input contract containing context but no executable analytical objects."""

    objective: str
    iteration: int
    columns: list[str]
    numeric_columns: list[str]
    history: list[Mapping[str, Any]] = field(default_factory=list)
    results: list[Mapping[str, Any]] = field(default_factory=list)
    max_iterations: int = 6
    target_variables: tuple[str, str] | None = None


class Planner:
    """Select the next analytical request from state using ordered rules."""

    def plan(self, state: ResearchState) -> PlannerDecision:
        """Return one structured action or an explicit stop decision."""
        if state.iteration >= state.max_iterations:
            return self._stop(state, "MAX_ITERATIONS")

        numeric_columns = self._effective_numeric_columns(state)
        if not numeric_columns:
            if not self._was_requested(state, PROFILE_TOOL, {}):
                return self._action(
                    state,
                    PROFILE_TOOL,
                    {},
                    "Obtain the initial dataset structure before selecting "
                    "statistical analyses.",
                )
            return self._stop(state, "NO_NEW_ACTIONS")

        targets = self._target_pair(state, numeric_columns)
        if targets is None:
            return self._stop(state, "NO_NEW_ACTIONS")
        x, y = targets
        pair_parameters = {"x": x, "y": y}

        if not self._was_requested(state, PEARSON_TOOL, pair_parameters):
            return self._action(
                state,
                PEARSON_TOOL,
                pair_parameters,
                "Establish the initial association magnitude between the target "
                "variables.",
            )

        pearson_result = self._find_result(state, PEARSON_TOOL, pair_parameters)
        coefficient = self._coefficient(pearson_result)
        if coefficient is None:
            return self._stop(state, "NO_NEW_ACTIONS")
        if abs(coefficient) < ASSOCIATION_THRESHOLD:
            return self._stop(state, "SUFFICIENT_EVIDENCE")

        candidates = sorted(set(numeric_columns) - {x, y})
        if candidates:
            partial_parameters = {"x": x, "y": y, "control": candidates[0]}
            if not self._was_requested(state, PARTIAL_TOOL, partial_parameters):
                return self._action(
                    state,
                    PARTIAL_TOOL,
                    partial_parameters,
                    "The initial association is relevant and an additional numeric "
                    "variable should be evaluated as a potential confounder.",
                )

        if not self._was_requested(state, OUTLIER_TOOL, pair_parameters):
            return self._action(
                state,
                OUTLIER_TOOL,
                pair_parameters,
                "Check whether the observed association depends on extreme "
                "observations.",
            )

        if not self._was_requested(state, SPEARMAN_TOOL, pair_parameters):
            return self._action(
                state,
                SPEARMAN_TOOL,
                pair_parameters,
                "Contrast association stability using a rank-based metric.",
            )

        return self._stop(state, "NO_NEW_ACTIONS")

    @staticmethod
    def _effective_numeric_columns(state: ResearchState) -> list[str]:
        if state.numeric_columns:
            return list(state.numeric_columns)

        profile_result = Planner._find_result(state, PROFILE_TOOL, {})
        if profile_result is None:
            return []
        columns = profile_result.get("numeric_columns")
        if not isinstance(columns, list) or not all(
            isinstance(column, str) for column in columns
        ):
            return []
        return list(columns)

    @staticmethod
    def _target_pair(
        state: ResearchState,
        numeric_columns: list[str],
    ) -> tuple[str, str] | None:
        if state.target_variables is None:
            return None
        x, y = state.target_variables
        if x == y or x not in numeric_columns or y not in numeric_columns:
            return None
        return x, y

    @staticmethod
    def _was_requested(
        state: ResearchState,
        tool: str,
        parameters: Mapping[str, Any],
    ) -> bool:
        identity = Planner._action_identity(tool, parameters)
        return any(
            Planner._action_identity(
                str(entry.get("tool", "")),
                Planner._parameters(entry),
            )
            == identity
            for entry in state.history
        )

    @staticmethod
    def _find_result(
        state: ResearchState,
        tool: str,
        parameters: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        identity = Planner._action_identity(tool, parameters)
        for entry in reversed(state.results):
            if entry.get("status") not in (None, "success"):
                continue
            entry_identity = Planner._action_identity(
                str(entry.get("tool", "")),
                Planner._parameters(entry),
            )
            result = entry.get("result")
            if entry_identity == identity and isinstance(result, Mapping):
                return result
        return None

    @staticmethod
    def _parameters(entry: Mapping[str, Any]) -> Mapping[str, Any]:
        parameters = entry.get("parameters", {})
        return parameters if isinstance(parameters, Mapping) else {}

    @staticmethod
    def _action_identity(
        tool: str,
        parameters: Mapping[str, Any],
    ) -> tuple[str, tuple[tuple[str, str], ...]]:
        normalized = tuple(
            sorted((str(key), repr(value)) for key, value in parameters.items())
        )
        return tool, normalized

    @staticmethod
    def _coefficient(result: Mapping[str, Any] | None) -> float | None:
        if result is None:
            return None
        value = result.get("coefficient")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    @staticmethod
    def _action(
        state: ResearchState,
        tool: str,
        parameters: dict[str, Any],
        reason: str,
    ) -> ActionDecision:
        next_iteration = state.iteration + 1
        return {
            "status": "action",
            "action_id": f"action-{next_iteration:03d}",
            "iteration": next_iteration,
            "tool": tool,
            "parameters": parameters,
            "reason": reason,
        }

    @staticmethod
    def _stop(state: ResearchState, reason: str) -> StopDecision:
        return {"status": "stop", "iteration": state.iteration, "reason": reason}
