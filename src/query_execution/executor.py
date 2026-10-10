"""Entry point for the future controlled tool execution workflow."""

from __future__ import annotations

from dataclasses import replace

from .contracts import ExecutionId, ToolExecutionRequest


class QueryExecutor:
    """Prepare execution requests without selecting or dispatching tools.

    Dispatch behavior is intentionally deferred. This class currently owns only
    the neutral responsibility of ensuring that a request has a stable execution
    identifier before it reaches the future dispatcher.
    """

    def prepare_request(self, request: ToolExecutionRequest) -> ToolExecutionRequest:
        """Return the request unchanged or add a newly generated execution ID."""

        if request.execution_id is not None:
            return request
        return replace(request, execution_id=ExecutionId.generate())
