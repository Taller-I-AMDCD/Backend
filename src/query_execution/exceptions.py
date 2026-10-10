"""Domain exceptions for controlled query execution infrastructure."""

from __future__ import annotations

from .contracts import ToolId


class QueryExecutionError(Exception):
    """Base exception for query execution infrastructure errors."""


class DuplicateToolError(QueryExecutionError):
    """Raised when a registry already contains the requested tool ID."""

    def __init__(self, tool_id: ToolId) -> None:
        self.tool_id = tool_id
        super().__init__(f"Tool '{tool_id}' is already registered")


class ToolNotFoundError(QueryExecutionError):
    """Raised when an explicitly requested tool is not registered."""

    def __init__(self, tool_id: ToolId) -> None:
        self.tool_id = tool_id
        super().__init__(f"Tool '{tool_id}' is not registered")


class InvalidToolError(QueryExecutionError):
    """Raised when an object does not satisfy the tool contract."""
