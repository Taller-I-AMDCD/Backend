"""Neutral contracts for controlled tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4


def _validate_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class ToolId:
    """Validated identifier for a tool exposed to the execution layer."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_identifier(self.value, "tool_id"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ExecutionId:
    """Stable identifier shared by a request and its eventual result."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_identifier(self.value, "execution_id"),
        )

    @classmethod
    def generate(cls) -> ExecutionId:
        return cls(str(uuid4()))

    def __str__(self) -> str:
        return self.value


class ToolExecutionStatus(str, Enum):
    """Outcome categories returned by the tool execution boundary."""

    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class ToolError:
    """Structured information for an expected execution failure."""

    code: str
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _validate_identifier(self.code, "error code"))
        object.__setattr__(
            self,
            "message",
            _validate_identifier(self.message, "error message"),
        )


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Static, architecture-neutral description of a registered tool."""

    tool_id: ToolId
    name: str
    description: str
    version: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_identifier(self.name, "tool name"))
        object.__setattr__(
            self,
            "description",
            _validate_identifier(self.description, "tool description"),
        )
        if self.version is not None:
            object.__setattr__(
                self,
                "version",
                _validate_identifier(self.version, "tool version"),
            )


@dataclass(frozen=True, slots=True)
class ToolExecutionRequest:
    """Request to invoke one explicitly identified tool."""

    tool_id: ToolId
    execution_id: ExecutionId | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", dict(self.parameters))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    """Structured success or failure produced by the execution boundary."""

    execution_id: ExecutionId
    tool_id: ToolId
    status: ToolExecutionStatus
    output: Any = None
    error: ToolError | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))
