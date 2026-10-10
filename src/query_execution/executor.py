"""Controlled execution boundary for explicitly requested tools."""

from __future__ import annotations

from dataclasses import replace

from .contracts import (
    ExecutionId,
    ToolError,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
)
from .dispatcher import ToolDispatcher
from .exceptions import (
    InvalidParametersError,
    InvalidToolResultError,
    ToolNotFoundError,
)

UNKNOWN_TOOL = "UNKNOWN_TOOL"
INVALID_PARAMETERS = "INVALID_PARAMETERS"
TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
INVALID_TOOL_RESULT = "INVALID_TOOL_RESULT"


class QueryExecutor:
    """Execute exactly the tool requested through a controlled dispatcher."""

    def __init__(self, dispatcher: ToolDispatcher) -> None:
        self._dispatcher = dispatcher

    @property
    def dispatcher(self) -> ToolDispatcher:
        """Return the dispatcher injected into this execution boundary."""

        return self._dispatcher

    def prepare_request(self, request: ToolExecutionRequest) -> ToolExecutionRequest:
        """Return an isolated request with a stable execution identifier."""

        execution_id = request.execution_id or ExecutionId.generate()
        return replace(request, execution_id=execution_id)

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Resolve and execute one requested tool, normalizing expected failures."""

        prepared = self.prepare_request(request)
        request_metadata = dict(prepared.metadata)

        try:
            tool = self._dispatcher.resolve(prepared)
        except ToolNotFoundError as error:
            return self._failure(
                prepared,
                UNKNOWN_TOOL,
                str(error),
                request_metadata,
            )

        try:
            result = tool.execute(prepared)
        except InvalidParametersError as error:
            return self._failure(
                prepared,
                INVALID_PARAMETERS,
                str(error).strip() or "Tool parameters are invalid",
                request_metadata,
            )
        except Exception as error:
            return self._failure(
                prepared,
                TOOL_EXECUTION_ERROR,
                f"Tool execution failed: {error}",
                request_metadata,
            )

        try:
            self._validate_result(prepared, result)
        except InvalidToolResultError as error:
            return self._failure(
                prepared,
                INVALID_TOOL_RESULT,
                str(error),
                request_metadata,
            )

        return replace(
            result,
            metadata={**request_metadata, **dict(result.metadata)},
        )

    @staticmethod
    def _validate_result(
        request: ToolExecutionRequest,
        result: object,
    ) -> None:
        if not isinstance(result, ToolExecutionResult):
            raise InvalidToolResultError(
                "Tool must return a ToolExecutionResult instance"
            )
        if not isinstance(result.status, ToolExecutionStatus):
            raise InvalidToolResultError("Tool result status is not valid")
        if result.execution_id != request.execution_id:
            raise InvalidToolResultError(
                "Tool result execution_id does not match the request"
            )
        if result.tool_id != request.tool_id:
            raise InvalidToolResultError("Tool result tool_id does not match the request")

    @staticmethod
    def _failure(
        request: ToolExecutionRequest,
        code: str,
        message: str,
        metadata: dict[str, object],
    ) -> ToolExecutionResult:
        if request.execution_id is None:
            raise RuntimeError("Prepared requests must contain an execution_id")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            status=ToolExecutionStatus.FAILURE,
            error=ToolError(code=code, message=message),
            metadata=metadata,
        )
