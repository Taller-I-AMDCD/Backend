"""In-memory execution tracing for orchestration infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping

from .contracts import ComponentId, ExecutionId
from .exceptions import InvalidIdentifierError


class TraceEventType(str, Enum):
    """Neutral events that may occur during an orchestration execution."""

    EXECUTION_STARTED = "execution_started"
    STATE_CHANGED = "state_changed"
    COMPONENT_SELECTED = "component_selected"
    COMPONENT_STARTED = "component_started"
    COMPONENT_COMPLETED = "component_completed"
    COMPONENT_FAILED = "component_failed"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"


@dataclass(frozen=True, slots=True)
class TraceEntry:
    """Immutable record of one ordered orchestration event."""

    execution_id: ExecutionId
    sequence: int
    event_type: TraceEventType
    component_id: ComponentId | None = None
    message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _validate_identifier(self.execution_id, "execution_id")
        if self.component_id is not None:
            _validate_identifier(self.component_id, "component_id")
        if self.sequence < 1:
            raise ValueError("sequence must be greater than zero")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        object.__setattr__(self, "metadata", dict(self.metadata))


class ExecutionTrace:
    """Collect immutable trace entries for one execution in sequence order."""

    def __init__(self, execution_id: ExecutionId) -> None:
        _validate_identifier(execution_id, "execution_id")
        self._execution_id = execution_id
        self._entries: list[TraceEntry] = []

    @property
    def execution_id(self) -> ExecutionId:
        return self._execution_id

    @property
    def entries(self) -> tuple[TraceEntry, ...]:
        """Return detached copies of the entries collected so far."""

        return tuple(_copy_entry(entry) for entry in self._entries)

    def record(
        self,
        event_type: TraceEventType,
        *,
        component_id: ComponentId | None = None,
        message: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> TraceEntry:
        entry = TraceEntry(
            execution_id=self.execution_id,
            sequence=len(self._entries) + 1,
            event_type=event_type,
            component_id=component_id,
            message=message,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        return _copy_entry(entry)

    def __len__(self) -> int:
        return len(self._entries)


def _validate_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidIdentifierError(f"{field_name} must be a non-empty string")


def _copy_entry(entry: TraceEntry) -> TraceEntry:
    return TraceEntry(
        execution_id=entry.execution_id,
        sequence=entry.sequence,
        event_type=entry.event_type,
        component_id=entry.component_id,
        message=entry.message,
        metadata=entry.metadata,
        timestamp=entry.timestamp,
    )
