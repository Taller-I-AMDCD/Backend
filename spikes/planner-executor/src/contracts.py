"""Shared control-flow contracts for the evaluation spike."""

from enum import StrEnum


class StopReason(StrEnum):
    """Stable reasons for terminating an orchestration run."""

    NO_NEW_ACTIONS = "NO_NEW_ACTIONS"
    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    EXECUTION_ERROR = "EXECUTION_ERROR"
