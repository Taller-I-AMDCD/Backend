"""Provisional entry point for strategy-neutral orchestration."""

from __future__ import annotations

from uuid import uuid4

from .contracts import ExecutionId, OrchestrationRequest, OrchestrationResult
from .state import ExecutionState
from .supervisor import Supervisor


class Orchestrator:
    """Initialize executions while keeping coordination replaceable."""

    def __init__(self, supervisor: Supervisor | None = None) -> None:
        self._supervisor = supervisor or Supervisor()
        self._state: ExecutionState | None = None

    @property
    def state(self) -> ExecutionState | None:
        """Return the most recently initialized execution state."""

        return self._state

    def initialize(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Create a pending execution without routing or running components."""

        execution_id = request.execution_id or ExecutionId(str(uuid4()))
        state = ExecutionState(
            execution_id=execution_id,
            metadata=dict(request.metadata),
        )
        self._state = self._supervisor.contextualize(state)

        return OrchestrationResult(
            execution_id=self._state.execution_id,
            status=self._state.status,
            metadata=dict(self._state.metadata),
        )
