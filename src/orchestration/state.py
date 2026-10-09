"""Strategy-neutral state for an orchestration execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import ExecutionId, ExecutionStatus
from .exceptions import InvalidIdentifierError, InvalidStateTransitionError


_VALID_TRANSITIONS: dict[ExecutionStatus, frozenset[ExecutionStatus]] = {
    ExecutionStatus.PENDING: frozenset(
        {ExecutionStatus.RUNNING, ExecutionStatus.FAILED}
    ),
    ExecutionStatus.RUNNING: frozenset(
        {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED}
    ),
    ExecutionStatus.COMPLETED: frozenset(),
    ExecutionStatus.FAILED: frozenset(),
}


@dataclass(slots=True)
class ExecutionState:
    """Mutable lifecycle state owned by the orchestration boundary."""

    execution_id: ExecutionId
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_step: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.execution_id, str) or not self.execution_id.strip():
            raise InvalidIdentifierError("execution_id must be a non-empty string")
        self.metadata = dict(self.metadata)
        self.set_current_step(self.current_step)

    def transition_to(self, status: ExecutionStatus) -> None:
        """Apply an allowed lifecycle transition or reject it explicitly."""

        if status not in _VALID_TRANSITIONS[self.status]:
            raise InvalidStateTransitionError(
                f"invalid execution status transition: "
                f"{self.status.value} -> {status.value}"
            )
        self.status = status

    def set_current_step(self, step: str | None) -> None:
        """Set a strategy-neutral step identifier for the current execution."""

        if step is not None and (not isinstance(step, str) or not step.strip()):
            raise ValueError("current_step must be None or a non-empty string")
        self.current_step = step
