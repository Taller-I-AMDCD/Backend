"""Controlled execution boundary for explicitly requested tools."""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter

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
from .trace import QueryExecutionTrace, QueryTraceEventType

UNKNOWN_TOOL = "UNKNOWN_TOOL"
INVALID_PARAMETERS = "INVALID_PARAMETERS"
TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
INVALID_TOOL_RESULT = "INVALID_TOOL_RESULT"
DUPLICATE_EXECUTION = "DUPLICATE_EXECUTION"


class QueryExecutor:
    """Execute exactly the tool requested through a controlled dispatcher."""

    def __init__(
        self,
        dispatcher: ToolDispatcher,
        trace: QueryExecutionTrace | None = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._trace = trace if trace is not None else QueryExecutionTrace()
        self._used_execution_ids: set[ExecutionId] = set()

    @property
    def dispatcher(self) -> ToolDispatcher:
        """Return the dispatcher injected into this execution boundary."""

        return self._dispatcher

    @property
    def trace(self) -> QueryExecutionTrace:
        """Return this executor's process-local execution trace."""

        return self._trace

    def prepare_request(self, request: ToolExecutionRequest) -> ToolExecutionRequest:
        """Return an isolated request with a stable execution identifier."""

        execution_id = request.execution_id or ExecutionId.generate()
        return replace(request, execution_id=execution_id)

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Resolve and execute one requested tool, normalizing expected failures."""

        prepared = self.prepare_request(request)
        if prepared.execution_id is None:
            raise RuntimeError("Prepared requests must contain an execution_id")

        started_at = perf_counter()
        request_metadata = dict(prepared.metadata)
        self._trace.record(
            prepared.execution_id,
            prepared.tool_id,
            QueryTraceEventType.EXECUTION_STARTED,
        )

        if prepared.execution_id in self._used_execution_ids:
            return self._failure(
                prepared,
                DUPLICATE_EXECUTION,
                f"Execution '{prepared.execution_id}' has already been attempted",
                request_metadata,
                started_at,
                tool_failed=False,
            )
        self._used_execution_ids.add(prepared.execution_id)

        try:
            tool = self._dispatcher.resolve(prepared)
        except ToolNotFoundError as error:
            return self._failure(
                prepared,
                UNKNOWN_TOOL,
                str(error),
                request_metadata,
                started_at,
            )

        self._trace.record(
            prepared.execution_id,
            prepared.tool_id,
            QueryTraceEventType.TOOL_RESOLVED,
        )
        self._trace.record(
            prepared.execution_id,
            prepared.tool_id,
            QueryTraceEventType.TOOL_STARTED,
        )

        try:
            result = tool.execute(prepared)
        except InvalidParametersError as error:
            return self._failure(
                prepared,
                INVALID_PARAMETERS,
                str(error).strip() or "Tool parameters are invalid",
                request_metadata,
                started_at,
            )
        except Exception as error:
            return self._failure(
                prepared,
                TOOL_EXECUTION_ERROR,
                f"Tool execution failed: {error}",
                request_metadata,
                started_at,
            )

        try:
            self._validate_result(prepared, result)
        except InvalidToolResultError as error:
            return self._failure(
                prepared,
                INVALID_TOOL_RESULT,
                str(error),
                request_metadata,
                started_at,
            )

        normalized = replace(
            result,
            metadata={**request_metadata, **dict(result.metadata)},
        )
        self._record_result(normalized, started_at)
        return normalized

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

    def _failure(
        self,
        request: ToolExecutionRequest,
        code: str,
        message: str,
        metadata: dict[str, object],
        started_at: float,
        *,
        tool_failed: bool = True,
    ) -> ToolExecutionResult:
        if request.execution_id is None:
            raise RuntimeError("Prepared requests must contain an execution_id")
        result = ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            status=ToolExecutionStatus.FAILURE,
            error=ToolError(code=code, message=message),
            metadata=metadata,
        )
        if tool_failed:
            self._trace.record(
                request.execution_id,
                request.tool_id,
                QueryTraceEventType.TOOL_FAILED,
                message=message,
                metadata={"status": "failure", "error_code": code},
            )
        self._record_result(result, started_at, record_tool_failure=tool_failed)
        return result

    def _record_result(
        self,
        result: ToolExecutionResult,
        started_at: float,
        *,
        record_tool_failure: bool = True,
    ) -> None:
        duration_ms = max((perf_counter() - started_at) * 1000, 0.0)
        if result.status is ToolExecutionStatus.SUCCESS:
            self._trace.record(
                result.execution_id,
                result.tool_id,
                QueryTraceEventType.TOOL_SUCCEEDED,
                metadata={"status": "success"},
            )
            self._trace.record(
                result.execution_id,
                result.tool_id,
                QueryTraceEventType.EXECUTION_COMPLETED,
                metadata={"status": "success", "duration_ms": duration_ms},
            )
            return

        error_code = result.error.code if result.error is not None else "TOOL_FAILURE"
        error_message = result.error.message if result.error is not None else None
        existing_entries = self._trace.for_execution(result.execution_id)
        if record_tool_failure and (
            not existing_entries
            or existing_entries[-1].event_type is not QueryTraceEventType.TOOL_FAILED
        ):
            self._trace.record(
                result.execution_id,
                result.tool_id,
                QueryTraceEventType.TOOL_FAILED,
                message=error_message,
                metadata={"status": "failure", "error_code": error_code},
            )
        self._trace.record(
            result.execution_id,
            result.tool_id,
            QueryTraceEventType.EXECUTION_FAILED,
            message=error_message,
            metadata={
                "status": "failure",
                "error_code": error_code,
                "duration_ms": duration_ms,
            },
        )
