"""Controlled resolution of tool requests against an explicit registry."""

from __future__ import annotations

from .contracts import ToolExecutionRequest
from .registry import ToolRegistry
from .tool import Tool


class ToolDispatcher:
    """Resolve the exact requested tool without selecting or executing it."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> ToolRegistry:
        """Return the sole source used for tool resolution."""

        return self._registry

    def resolve(self, request: ToolExecutionRequest) -> Tool:
        """Resolve the request's tool ID exclusively through the registry."""

        return self._registry.get(request.tool_id)
