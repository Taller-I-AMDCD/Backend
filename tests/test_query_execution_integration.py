from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

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
from query_execution.demo import run_demo  # noqa: E402


class IntegrationTool:
    def __init__(self, identifier: str, behavior: str = "success") -> None:
        self._tool_id = ToolId(identifier)
        self._spec = ToolSpec(
            tool_id=self._tool_id,
            name=f"Integration tool {identifier}",
            description="Test-only integration tool",
        )
        self.behavior = behavior
        self.execution_count = 0

    @property
    def tool_id(self) -> ToolId:
        return self._tool_id

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.execution_count += 1
        if self.behavior == "parameters":
            raise InvalidParametersError("Invalid integration parameters")
        if self.behavior == "exception":
            raise RuntimeError("Integration tool failure")
        if request.execution_id is None:
            raise ValueError("execution_id required")
        result_tool_id = (
            ToolId("inconsistent")
            if self.behavior == "invalid-result"
            else self.tool_id
        )
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=result_tool_id,
            status=ToolExecutionStatus.SUCCESS,
            output={"value": request.parameters.get("value")},
        )


def build_executor(*tools: IntegrationTool) -> QueryExecutor:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    dispatcher = ToolDispatcher(registry)
    return QueryExecutor(dispatcher)


class QueryExecutionIntegrationTests(unittest.TestCase):
    def test_successful_end_to_end_flow(self) -> None:
        tool = IntegrationTool("echo")
        registry = ToolRegistry()
        registry.register(tool)
        dispatcher = ToolDispatcher(registry)
        executor = QueryExecutor(dispatcher)
        execution_id = ExecutionId("integration-success")
        request = ToolExecutionRequest(
            execution_id=execution_id,
            tool_id=tool.tool_id,
            parameters={"value": 4},
        )
        self.assertTrue(registry.contains(tool.tool_id))
        self.assertIs(dispatcher.resolve(request), tool)
        result = executor.execute(request)
        entries = executor.trace.for_execution(execution_id)
        self.assertEqual(result.status, ToolExecutionStatus.SUCCESS)
        self.assertEqual(result.output, {"value": 4})
        self.assertEqual(result.execution_id, execution_id)
        self.assertEqual(result.tool_id, tool.tool_id)
        self.assertEqual(tool.execution_count, 1)
        self.assertEqual(entries[0].event_type, QueryTraceEventType.EXECUTION_STARTED)
        self.assertEqual(entries[-1].event_type, QueryTraceEventType.EXECUTION_COMPLETED)
        self.assertGreaterEqual(entries[-1].metadata["duration_ms"], 0)

    def test_unknown_tool_is_controlled_without_fallback(self) -> None:
        fallback = IntegrationTool("fallback")
        executor = build_executor(fallback)
        result = executor.execute(
            ToolExecutionRequest(tool_id=ToolId("unknown"))
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "UNKNOWN_TOOL")  # type: ignore[union-attr]
        self.assertEqual(fallback.execution_count, 0)
        self.assertEqual(
            executor.trace.for_execution(result.execution_id)[-1].event_type,
            QueryTraceEventType.EXECUTION_FAILED,
        )

    def test_invalid_parameters_are_controlled_without_retry(self) -> None:
        tool = IntegrationTool("invalid", behavior="parameters")
        executor = build_executor(tool)
        result = executor.execute(ToolExecutionRequest(tool_id=tool.tool_id))
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "INVALID_PARAMETERS")  # type: ignore[union-attr]
        self.assertEqual(tool.execution_count, 1)
        self.assertEqual(
            executor.trace.for_execution(result.execution_id)[-1].event_type,
            QueryTraceEventType.EXECUTION_FAILED,
        )

    def test_unexpected_failure_is_controlled_without_retry(self) -> None:
        tool = IntegrationTool("exploding", behavior="exception")
        executor = build_executor(tool)
        result = executor.execute(ToolExecutionRequest(tool_id=tool.tool_id))
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "TOOL_EXECUTION_ERROR")  # type: ignore[union-attr]
        self.assertNotIn("Traceback", result.error.message)  # type: ignore[union-attr]
        self.assertEqual(tool.execution_count, 1)
        self.assertEqual(
            executor.trace.for_execution(result.execution_id)[-1].event_type,
            QueryTraceEventType.EXECUTION_FAILED,
        )

    def test_invalid_tool_result_is_controlled(self) -> None:
        tool = IntegrationTool("invalid-result", behavior="invalid-result")
        executor = build_executor(tool)
        result = executor.execute(ToolExecutionRequest(tool_id=tool.tool_id))
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "INVALID_TOOL_RESULT")  # type: ignore[union-attr]
        self.assertEqual(tool.execution_count, 1)

    def test_duplicate_execution_is_rejected_without_second_call(self) -> None:
        tool = IntegrationTool("duplicate")
        executor = build_executor(tool)
        request = ToolExecutionRequest(
            execution_id=ExecutionId("integration-duplicate"),
            tool_id=tool.tool_id,
        )
        first = executor.execute(request)
        second = executor.execute(request)
        self.assertEqual(first.status, ToolExecutionStatus.SUCCESS)
        self.assertEqual(second.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(second.error.code, "DUPLICATE_EXECUTION")  # type: ignore[union-attr]
        self.assertEqual(tool.execution_count, 1)
        self.assertEqual(
            executor.trace.for_execution(request.execution_id)[-1].event_type,
            QueryTraceEventType.EXECUTION_FAILED,
        )

    def test_multiple_tools_execute_only_the_requested_instance(self) -> None:
        first = IntegrationTool("first")
        second = IntegrationTool("second")
        executor = build_executor(first, second)
        first_result = executor.execute(
            ToolExecutionRequest(tool_id=first.tool_id, parameters={"value": 1})
        )
        second_result = executor.execute(
            ToolExecutionRequest(tool_id=second.tool_id, parameters={"value": 2})
        )
        self.assertEqual(first_result.tool_id, first.tool_id)
        self.assertEqual(second_result.tool_id, second.tool_id)
        self.assertEqual(first.execution_count, 1)
        self.assertEqual(second.execution_count, 1)

    def test_result_is_serializable_when_data_is_serializable(self) -> None:
        tool = IntegrationTool("serializable")
        result = build_executor(tool).execute(
            ToolExecutionRequest(tool_id=tool.tool_id, parameters={"value": 5})
        )
        serialized = json.dumps(asdict(result))
        self.assertIn('"status": "success"', serialized)


class DemoAndBoundaryTests(unittest.TestCase):
    def test_demo_runs_all_cases_without_traceback(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            run_demo()
        text = output.getvalue()
        for marker in (
            "HU-005 QUERY EXECUTION DEMO",
            "CASE 1",
            "CASE 2",
            "CASE 3",
            "CASE 4",
            "CASE 5",
            "Architecture selected: NO",
            "Unexpected traceback: NO",
            "Output: {'value': 8}",
            "Error code: UNKNOWN_TOOL",
            "Error code: INVALID_PARAMETERS",
            "Error code: TOOL_EXECUTION_ERROR",
            "Error code: DUPLICATE_EXECUTION",
            "Tool execution count: 1",
        ):
            self.assertIn(marker, text)

    def test_product_modules_remain_neutral_and_safe(self) -> None:
        source_files = list((SOURCE_ROOT / "query_execution").glob("*.py"))
        module_names = {path.stem for path in source_files}
        source_text = "\n".join(
            path.read_text(encoding="utf-8") for path in source_files
        )
        forbidden_modules = {
            "planner",
            "blackboard",
            "critic",
            "consensus",
            "supervisor",
        }
        self.assertTrue(forbidden_modules.isdisjoint(module_names))
        self.assertNotIn("from orchestration", source_text)
        self.assertNotIn("import orchestration", source_text)
        self.assertNotIn("from spikes", source_text)
        self.assertNotIn("import spikes", source_text)
        for marker in (
            "eval" + "(",
            "exec" + "(",
            "subprocess",
            "os.system",
            "shell=True",
            "importlib",
            "__import__" + "(",
        ):
            self.assertNotIn(marker, source_text)


if __name__ == "__main__":
    unittest.main()
