"""Generic contracts shared by orchestration components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, NewType

from .exceptions import InvalidIdentifierError


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


class ComponentStatus(str, Enum):
    """Outcome states shared by all future component types."""

    SUCCESS = "success"
    FAILURE = "failure"


def _require_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidIdentifierError(f"{field_name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class OrchestrationRequest:
    """Input accepted by the orchestration boundary."""

    payload: Payload = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)
    execution_id: ExecutionId | None = None

    def __post_init__(self) -> None:
        if self.execution_id is not None:
            _require_identifier(self.execution_id, "execution_id")
        object.__setattr__(self, "payload", dict(self.payload))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class ComponentRequest:
    """Generic request that can be addressed to a registered component."""

    execution_id: ExecutionId
    component_id: ComponentId
    payload: Payload = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_identifier(self.execution_id, "execution_id")
        _require_identifier(self.component_id, "component_id")
        object.__setattr__(self, "payload", dict(self.payload))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class ComponentResult:
    """Generic outcome returned by a component."""

    component_id: ComponentId
    status: ComponentStatus
    output: Payload = field(default_factory=dict)
    error: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_identifier(self.component_id, "component_id")
        object.__setattr__(self, "output", dict(self.output))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def succeeded(self) -> bool:
        """Report success without forcing callers to compare enum values."""

        return self.status is ComponentStatus.SUCCESS


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    """Snapshot returned by the provisional orchestration entry point."""

    execution_id: ExecutionId
    status: ExecutionStatus
    output: Payload = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)
    component_results: tuple[ComponentResult, ...] = ()
    error: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.execution_id, "execution_id")
        object.__setattr__(self, "output", dict(self.output))
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "component_results", tuple(self.component_results))
