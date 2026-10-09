"""Provisional entry point for strategy-neutral orchestration."""

from __future__ import annotations

from uuid import uuid4

from .contracts import ExecutionId, OrchestrationRequest, OrchestrationResult
from .context import ExecutionContext
from .state import ExecutionState
from .supervisor import Supervisor
from .trace import ExecutionTrace, TraceEventType


class Orchestrator:
    """Initialize executions while keeping coordination replaceable."""

    def __init__(self, supervisor: Supervisor | None = None) -> None:
        self._supervisor = supervisor or Supervisor()
        self._context: ExecutionContext | None = None

    @property
    def context(self) -> ExecutionContext | None:
        """Return the most recently initialized execution context."""

        return self._context

    @property
    def state(self) -> ExecutionState | None:
        """Return the most recently initialized execution state."""

        return self._context.state if self._context is not None else None

    def initialize(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Create a pending execution without routing or running components."""

        execution_id = request.execution_id or ExecutionId(str(uuid4()))
        trace = ExecutionTrace(execution_id)
        trace.record(
            TraceEventType.EXECUTION_STARTED,
            metadata=request.metadata,
        )
        state = ExecutionState(
            execution_id=execution_id,
            metadata=dict(request.metadata),
        )
        contextualized_state = self._supervisor.contextualize(state)
        self._context = ExecutionContext(
            request=request,
            state=contextualized_state,
            trace=trace,
        )

        return OrchestrationResult(
            execution_id=self._context.state.execution_id,
            status=self._context.state.status,
            metadata=self._context.state.metadata,
        )
