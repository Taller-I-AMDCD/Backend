from __future__ import annotations

import json
import sys
import unittest
from dataclasses import asdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from query_execution import (  # noqa: E402
    ExecutionId,
    InvalidParametersError,
    QueryExecutor,
    ToolDispatcher,
    ToolError,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolId,
    ToolRegistry,
    ToolSpec,
)


class BaseFakeTool:
    def __init__(self, identifier: str) -> None:
        self._tool_id = ToolId(identifier)
        self._spec = ToolSpec(
            tool_id=self._tool_id,
            name=f"Tool {identifier}",
            description="Test-only tool",
        )
        self.requests: list[ToolExecutionRequest] = []

    @property
    def tool_id(self) -> ToolId:
        return self._tool_id

    @property
    def spec(self) -> ToolSpec:
        return self._spec


class EchoTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        if request.execution_id is None:
            raise ValueError("execution_id required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=self.tool_id,
            status=ToolExecutionStatus.SUCCESS,
            output={"parameters": dict(request.parameters)},
            metadata={"tool": "echo"},
        )


class InvalidParametersTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        raise InvalidParametersError("Parameter 'value' must be numeric")


class EmptyInvalidParametersTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        raise InvalidParametersError


class ExplodingTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        raise RuntimeError("controlled diagnostic")


class FailureTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        if request.execution_id is None:
            raise ValueError("execution_id required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=self.tool_id,
            status=ToolExecutionStatus.FAILURE,
            error=ToolError(code="TOOL_FAILURE", message="Expected failure"),
        )


class WrongToolIdTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        if request.execution_id is None:
            raise ValueError("execution_id required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=ToolId("different"),
            status=ToolExecutionStatus.SUCCESS,
        )


class WrongExecutionIdTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        return ToolExecutionResult(
            execution_id=ExecutionId("different"),
            tool_id=self.tool_id,
            status=ToolExecutionStatus.SUCCESS,
        )


class InvalidResultTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> Any:
        self.requests.append(request)
        return {"invalid": True}


class InvalidStatusTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        if request.execution_id is None:
            raise ValueError("execution_id required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=self.tool_id,
            status="unexpected",  # type: ignore[arg-type]
        )


class MutatingTool(BaseFakeTool):
    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        request.parameters["tool_added"] = True  # type: ignore[index]
        request.metadata["tool_added"] = True  # type: ignore[index]
        if request.execution_id is None:
            raise ValueError("execution_id required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=self.tool_id,
            status=ToolExecutionStatus.SUCCESS,
        )


def build_executor(*tools: BaseFakeTool) -> QueryExecutor:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return QueryExecutor(ToolDispatcher(registry))


class QueryExecutorSuccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.echo = EchoTool("echo")
        self.other = EchoTool("other")
        self.executor = build_executor(self.echo, self.other)

    def test_executor_receives_dispatcher(self) -> None:
        dispatcher = ToolDispatcher(ToolRegistry())
        self.assertIs(QueryExecutor(dispatcher).dispatcher, dispatcher)

    def test_execute_resolves_and_runs_requested_tool_once(self) -> None:
        result = self.executor.execute(ToolExecutionRequest(tool_id=self.echo.tool_id))
        self.assertEqual(result.status, ToolExecutionStatus.SUCCESS)
        self.assertEqual(len(self.echo.requests), 1)
        self.assertEqual(len(self.other.requests), 0)

    def test_explicit_execution_id_is_preserved(self) -> None:
        execution_id = ExecutionId("provided")
        result = self.executor.execute(
            ToolExecutionRequest(
                execution_id=execution_id,
                tool_id=self.echo.tool_id,
            )
        )
        self.assertEqual(result.execution_id, execution_id)
        self.assertEqual(self.echo.requests[0].execution_id, execution_id)

    def test_missing_execution_id_is_generated_and_shared(self) -> None:
        result = self.executor.execute(ToolExecutionRequest(tool_id=self.echo.tool_id))
        self.assertIsInstance(result.execution_id, ExecutionId)
        self.assertTrue(result.execution_id.value)
        self.assertEqual(result.execution_id, self.echo.requests[0].execution_id)

    def test_success_output_is_preserved(self) -> None:
        result = self.executor.execute(
            ToolExecutionRequest(
                tool_id=self.echo.tool_id,
                parameters={"value": 7},
            )
        )
        self.assertEqual(result.output, {"parameters": {"value": 7}})
        self.assertIsNone(result.error)

    def test_request_and_tool_metadata_are_preserved(self) -> None:
        result = self.executor.execute(
            ToolExecutionRequest(
                tool_id=self.echo.tool_id,
                metadata={"source": "caller"},
            )
        )
        self.assertEqual(result.metadata, {"source": "caller", "tool": "echo"})

    def test_tool_receives_exact_parameters(self) -> None:
        parameters = {"left": 2, "right": 3}
        self.executor.execute(
            ToolExecutionRequest(tool_id=self.echo.tool_id, parameters=parameters)
        )
        self.assertEqual(self.echo.requests[0].parameters, parameters)

    def test_tool_mutation_does_not_change_original_inputs_or_request(self) -> None:
        tool = MutatingTool("mutating")
        executor = build_executor(tool)
        parameters = {"value": 2}
        metadata = {"source": "caller"}
        request = ToolExecutionRequest(
            tool_id=tool.tool_id,
            parameters=parameters,
            metadata=metadata,
        )
        executor.execute(request)
        self.assertEqual(parameters, {"value": 2})
        self.assertEqual(metadata, {"source": "caller"})
        self.assertEqual(request.parameters, {"value": 2})
        self.assertEqual(request.metadata, {"source": "caller"})

    def test_result_is_serializable_when_payload_is_serializable(self) -> None:
        result = self.executor.execute(ToolExecutionRequest(tool_id=self.echo.tool_id))
        encoded = json.dumps(asdict(result))
        self.assertIn('"status": "success"', encoded)


class QueryExecutorFailureTests(unittest.TestCase):
    def test_unknown_tool_returns_structured_failure(self) -> None:
        executor = build_executor()
        result = executor.execute(ToolExecutionRequest(tool_id=ToolId("unknown")))
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "UNKNOWN_TOOL")  # type: ignore[union-attr]
        self.assertNotIn("Traceback", result.error.message)  # type: ignore[union-attr]

    def test_unknown_tool_does_not_execute_fallback(self) -> None:
        fallback = EchoTool("fallback")
        result = build_executor(fallback).execute(
            ToolExecutionRequest(tool_id=ToolId("unknown"))
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(len(fallback.requests), 0)

    def test_invalid_parameters_returns_structured_failure(self) -> None:
        tool = InvalidParametersTool("invalid-parameters")
        result = build_executor(tool).execute(
            ToolExecutionRequest(tool_id=tool.tool_id)
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "INVALID_PARAMETERS")  # type: ignore[union-attr]

    def test_empty_invalid_parameters_error_uses_safe_message(self) -> None:
        tool = EmptyInvalidParametersTool("empty-invalid-parameters")
        result = build_executor(tool).execute(
            ToolExecutionRequest(tool_id=tool.tool_id)
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(
            result.error.message,  # type: ignore[union-attr]
            "Tool parameters are invalid",
        )

    def test_unexpected_tool_exception_is_contained(self) -> None:
        tool = ExplodingTool("exploding")
        result = build_executor(tool).execute(
            ToolExecutionRequest(tool_id=tool.tool_id)
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "TOOL_EXECUTION_ERROR")  # type: ignore[union-attr]
        self.assertIn("controlled diagnostic", result.error.message)  # type: ignore[union-attr]
        self.assertNotIn("Traceback", result.error.message)  # type: ignore[union-attr]

    def test_failure_returned_by_tool_is_preserved(self) -> None:
        tool = FailureTool("failure")
        result = build_executor(tool).execute(
            ToolExecutionRequest(tool_id=tool.tool_id)
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "TOOL_FAILURE")  # type: ignore[union-attr]

    def test_inconsistent_tool_id_is_rejected(self) -> None:
        tool = WrongToolIdTool("wrong-tool-id")
        result = build_executor(tool).execute(
            ToolExecutionRequest(tool_id=tool.tool_id)
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "INVALID_TOOL_RESULT")  # type: ignore[union-attr]

    def test_inconsistent_execution_id_is_rejected(self) -> None:
        tool = WrongExecutionIdTool("wrong-execution-id")
        result = build_executor(tool).execute(
            ToolExecutionRequest(tool_id=tool.tool_id)
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "INVALID_TOOL_RESULT")  # type: ignore[union-attr]

    def test_invalid_result_type_is_rejected(self) -> None:
        tool = InvalidResultTool("invalid-result")
        result = build_executor(tool).execute(
            ToolExecutionRequest(tool_id=tool.tool_id)
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "INVALID_TOOL_RESULT")  # type: ignore[union-attr]

    def test_invalid_result_status_is_rejected(self) -> None:
        tool = InvalidStatusTool("invalid-status")
        result = build_executor(tool).execute(
            ToolExecutionRequest(tool_id=tool.tool_id)
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error.code, "INVALID_TOOL_RESULT")  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
