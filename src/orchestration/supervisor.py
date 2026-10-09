"""Provisional supervision boundary for orchestration state."""

from __future__ import annotations

from .state import ExecutionState


class Supervisor:
    """Expose a replaceable supervision hook without imposing a policy."""

    def contextualize(self, state: ExecutionState) -> ExecutionState:
        """Return the state unchanged until a coordination strategy is approved."""

        return state
