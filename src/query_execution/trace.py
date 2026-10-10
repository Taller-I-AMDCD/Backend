"""In-memory trace records for controlled tool executions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .contracts import ExecutionId, ToolId


class QueryTraceEventType(str, Enum):
    """Architecture-neutral events emitted by the query execution boundary."""

    EXECUTION_STARTED = "execution_started"
    TOOL_RESOLVED = "tool_resolved"
    TOOL_STARTED = "tool_started"
    TOOL_SUCCEEDED = "tool_succeeded"
    TOOL_FAILED = "tool_failed"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"


@dataclass(frozen=True, slots=True)
class QueryTraceEntry:
    """Immutable record of one event in an execution trace."""

    sequence: int
    execution_id: ExecutionId
    tool_id: ToolId
    event_type: QueryTraceEventType
    timestamp: datetime
    message: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


class QueryExecutionTrace:
    """Append-only, process-local trace for query execution events."""

    def __init__(self) -> None:
        self._entries: list[QueryTraceEntry] = []

    def record(
        self,
        execution_id: ExecutionId,
        tool_id: ToolId,
        event_type: QueryTraceEventType,
        *,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> QueryTraceEntry:
        """Append an immutable entry and assign its stable sequence number."""

        entry = QueryTraceEntry(
            sequence=len(self._entries) + 1,
            execution_id=execution_id,
            tool_id=tool_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            message=message,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> tuple[QueryTraceEntry, ...]:
        """Return an immutable snapshot of all entries in sequence order."""

        return tuple(self._entries)

    def for_execution(
        self,
        execution_id: ExecutionId,
    ) -> tuple[QueryTraceEntry, ...]:
        """Return entries associated with one execution identifier."""

        return tuple(
            entry for entry in self._entries if entry.execution_id == execution_id
        )

    def __len__(self) -> int:
        return len(self._entries)
