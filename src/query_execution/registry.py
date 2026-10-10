"""Explicit registry of tools authorized for future execution."""

from __future__ import annotations

from .contracts import ToolId, ToolSpec
from .exceptions import DuplicateToolError, InvalidToolError, ToolNotFoundError
from .tool import Tool


class ToolRegistry:
    """Store and retrieve explicitly registered tools without executing them."""

    def __init__(self) -> None:
        self._tools: dict[ToolId, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a valid tool while preventing silent replacement."""

        if not isinstance(tool, Tool):
            raise InvalidToolError("Object does not satisfy the Tool protocol")
        if not isinstance(tool.tool_id, ToolId):
            raise InvalidToolError("Tool must expose a valid ToolId")
        if not isinstance(tool.spec, ToolSpec):
            raise InvalidToolError("Tool must expose a valid ToolSpec")
        if tool.tool_id != tool.spec.tool_id:
            raise InvalidToolError("Tool and ToolSpec identifiers must match")
        if tool.tool_id in self._tools:
            raise DuplicateToolError(tool.tool_id)
        self._tools[tool.tool_id] = tool

    def contains(self, tool_id: ToolId) -> bool:
        """Return whether a tool ID is explicitly registered."""

        return tool_id in self._tools

    def get(self, tool_id: ToolId) -> Tool:
        """Return the registered tool or raise a controlled lookup error."""

        try:
            return self._tools[tool_id]
        except KeyError as error:
            raise ToolNotFoundError(tool_id) from error

    def list_ids(self) -> tuple[ToolId, ...]:
        """Return registered IDs in stable registration order."""

        return tuple(self._tools)

    def unregister(self, tool_id: ToolId) -> Tool:
        """Remove and return a tool, preserving controlled unknown-ID handling."""

        tool = self.get(tool_id)
        del self._tools[tool_id]
        return tool

    def __len__(self) -> int:
        return len(self._tools)
