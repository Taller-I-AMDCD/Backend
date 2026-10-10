from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from query_execution import (  # noqa: E402
    ExecutionId,
    InvalidParametersError,
    QueryExecutor,
    QueryTraceEventType,
    ToolDispatcher,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolId,
    ToolRegistry,
    ToolSpec,
)


class CountingTool:
    def __init__(self, identifier: str = "counting", *, failure: str | None = None) -> None:
        self._tool_id = ToolId(identifier)
        self._spec = ToolSpec(
            tool_id=self._tool_id,
            name="Counting tool",
            description="Test-only tool",
        )
        self.failure = failure
        self.execution_count = 0

    @property
    def tool_id(self) -> ToolId:
        return self._tool_id

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.execution_count += 1
        if self.failure == "parameters":
            raise InvalidParametersError("Invalid test parameter")
        if self.failure == "exception":
            raise RuntimeError("test failure")
        if request.execution_id is None:
            raise ValueError("execution_id required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=self.tool_id,
            status=ToolExecutionStatus.SUCCESS,
        )


def build_executor(*tools: CountingTool) -> QueryExecutor:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return QueryExecutor(ToolDispatcher(registry))


class DuplicateExecutionTests(unittest.TestCase):
    def test_first_id_is_accepted_and_second_is_rejected(self) -> None:
        tool = CountingTool()
        executor = build_executor(tool)
        request = ToolExecutionRequest(
            execution_id=ExecutionId("same-id"),
            tool_id=tool.tool_id,
        )
        first = executor.execute(request)
        second = executor.execute(request)
        self.assertEqual(first.status, ToolExecutionStatus.SUCCESS)
        self.assertEqual(second.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(second.error.code, "DUPLICATE_EXECUTION")  # type: ignore[union-attr]
        self.assertEqual(tool.execution_count, 1)

    def test_duplicate_is_traced_without_traceback(self) -> None:
        tool = CountingTool()
        executor = build_executor(tool)
        request = ToolExecutionRequest(
            execution_id=ExecutionId("same-id"),
            tool_id=tool.tool_id,
        )
        executor.execute(request)
        duplicate = executor.execute(request)
        entries = executor.trace.for_execution(ExecutionId("same-id"))
        self.assertEqual(entries[-1].event_type, QueryTraceEventType.EXECUTION_FAILED)
        self.assertEqual(entries[-1].metadata["error_code"], "DUPLICATE_EXECUTION")
        self.assertNotIn("Traceback", duplicate.error.message)  # type: ignore[union-attr]

    def test_different_ids_are_executed(self) -> None:
        tool = CountingTool()
        executor = build_executor(tool)
        for value in ("first-id", "second-id"):
            result = executor.execute(
                ToolExecutionRequest(
                    execution_id=ExecutionId(value),
                    tool_id=tool.tool_id,
                )
            )
            self.assertEqual(result.status, ToolExecutionStatus.SUCCESS)
        self.assertEqual(tool.execution_count, 2)

    def test_automatic_ids_are_distinct(self) -> None:
        tool = CountingTool()
        executor = build_executor(tool)
        first = executor.execute(ToolExecutionRequest(tool_id=tool.tool_id))
        second = executor.execute(ToolExecutionRequest(tool_id=tool.tool_id))
        self.assertNotEqual(first.execution_id, second.execution_id)
        self.assertEqual(tool.execution_count, 2)

    def test_failed_execution_consumes_id(self) -> None:
        tool = CountingTool(failure="parameters")
        executor = build_executor(tool)
        request = ToolExecutionRequest(
            execution_id=ExecutionId("failed-id"),
            tool_id=tool.tool_id,
        )
        first = executor.execute(request)
        second = executor.execute(request)
        self.assertEqual(first.error.code, "INVALID_PARAMETERS")  # type: ignore[union-attr]
        self.assertEqual(second.error.code, "DUPLICATE_EXECUTION")  # type: ignore[union-attr]
        self.assertEqual(tool.execution_count, 1)

    def test_unknown_tool_consumes_id_without_fallback(self) -> None:
        fallback = CountingTool("fallback")
        executor = build_executor(fallback)
        request = ToolExecutionRequest(
            execution_id=ExecutionId("unknown-id"),
            tool_id=ToolId("unknown"),
        )
        first = executor.execute(request)
        second = executor.execute(request)
        self.assertEqual(first.error.code, "UNKNOWN_TOOL")  # type: ignore[union-attr]
        self.assertEqual(second.error.code, "DUPLICATE_EXECUTION")  # type: ignore[union-attr]
        self.assertEqual(fallback.execution_count, 0)


class FailureTraceTests(unittest.TestCase):
    def test_invalid_parameters_has_terminal_failure_trace(self) -> None:
        tool = CountingTool(failure="parameters")
        executor = build_executor(tool)
        result = executor.execute(ToolExecutionRequest(tool_id=tool.tool_id))
        entries = executor.trace.for_execution(result.execution_id)
        self.assertEqual(entries[-1].event_type, QueryTraceEventType.EXECUTION_FAILED)
        self.assertEqual(entries[-1].metadata["error_code"], "INVALID_PARAMETERS")
        self.assertEqual(tool.execution_count, 1)

    def test_tool_exception_has_terminal_failure_trace_and_stable_id(self) -> None:
        tool = CountingTool(failure="exception")
        executor = build_executor(tool)
        execution_id = ExecutionId("exception-id")
        result = executor.execute(
            ToolExecutionRequest(execution_id=execution_id, tool_id=tool.tool_id)
        )
        entries = executor.trace.for_execution(execution_id)
        self.assertEqual(result.execution_id, execution_id)
        self.assertEqual(result.error.code, "TOOL_EXECUTION_ERROR")  # type: ignore[union-attr]
        self.assertEqual(entries[-1].event_type, QueryTraceEventType.EXECUTION_FAILED)
        self.assertGreaterEqual(entries[-1].metadata["duration_ms"], 0)
        self.assertNotIn("Traceback", result.error.message)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
