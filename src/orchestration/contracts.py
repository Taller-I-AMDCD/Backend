"""Generic contracts shared by orchestration components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, NewType


ExecutionId = NewType("ExecutionId", str)
ComponentId = NewType("ComponentId", str)
Payload = Mapping[str, object]
Metadata = Mapping[str, object]


class ExecutionStatus(str, Enum):
    """Lifecycle states that do not assume a coordination strategy."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class OrchestrationRequest:
    """Input accepted by the orchestration boundary."""

    payload: Payload = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)
    execution_id: ExecutionId | None = None


@dataclass(frozen=True, slots=True)
class ComponentRequest:
    """Generic request that can be addressed to a registered component."""

    execution_id: ExecutionId
    component_id: ComponentId
    payload: Payload = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ComponentResult:
    """Generic outcome returned by a component."""

    component_id: ComponentId
    succeeded: bool
    data: Payload = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    """Snapshot returned by the provisional orchestration entry point."""

    execution_id: ExecutionId
    status: ExecutionStatus
    metadata: Metadata = field(default_factory=dict)
    component_results: tuple[ComponentResult, ...] = ()
    error: str | None = None
