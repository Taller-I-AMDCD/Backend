"""Generic context shared during one orchestration execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import OrchestrationRequest
from .state import ExecutionState
from .trace import ExecutionTrace


@dataclass(slots=True)
class ExecutionContext:
    """Group the original request, current state, and neutral shared data."""

    request: OrchestrationRequest
    state: ExecutionState
    trace: ExecutionTrace
    shared_data: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            self.request.execution_id is not None
            and self.request.execution_id != self.state.execution_id
        ):
            raise ValueError("request and state execution_id values must match")
        if self.trace.execution_id != self.state.execution_id:
            raise ValueError("trace and state execution_id values must match")
        self.shared_data = dict(self.shared_data)
