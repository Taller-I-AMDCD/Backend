"""Provisional supervision boundary for orchestration state."""

from __future__ import annotations

from .context import ExecutionContext
from .exceptions import OrchestrationError
from .state import ExecutionState
from .strategy import CoordinationDecision, CoordinationStrategy


class Supervisor:
    """Delegate decisions without embedding a coordination policy."""

    def __init__(self, strategy: CoordinationStrategy | None = None) -> None:
        self._strategy = strategy

    def contextualize(self, state: ExecutionState) -> ExecutionState:
        """Return state unchanged without imposing coordination semantics."""

        return state

    def decide(self, context: ExecutionContext) -> CoordinationDecision:
        """Delegate the next decision to the injected strategy."""

        if self._strategy is None:
            raise OrchestrationError("coordination strategy is not configured")
        return self._strategy.decide(context)
