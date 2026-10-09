"""Strategy-neutral state for an orchestration execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import ExecutionId, ExecutionStatus


@dataclass(slots=True)
class ExecutionState:
    """Mutable lifecycle state owned by the orchestration boundary."""

    execution_id: ExecutionId
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_step: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
