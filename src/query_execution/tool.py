"""Structural contract implemented by controlled tools."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import ToolExecutionRequest, ToolExecutionResult, ToolId, ToolSpec


@runtime_checkable
class Tool(Protocol):
    """A tool that can handle a typed execution request.

    Implementations satisfy this protocol structurally and do not need to inherit
    from a framework base class.
    """

    @property
    def tool_id(self) -> ToolId:
        """Return the stable identifier used by a future registry."""

    @property
    def spec(self) -> ToolSpec:
        """Return static descriptive metadata for the tool."""

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute an already validated request for this tool."""
