from __future__ import annotations

import sys
import unittest
from pathlib import Path
from uuid import UUID

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from query_execution import (  # noqa: E402
    ExecutionId,
    QueryExecutor,
    Tool,
    ToolError,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolId,
    ToolSpec,
)


class FakeTool:
    def __init__(self) -> None:
        self._tool_id = ToolId("fake-tool")
        self._spec = ToolSpec(
            tool_id=self._tool_id,
            name="Fake tool",
            description="Test-only structural implementation",
        )

    @property
    def tool_id(self) -> ToolId:
        return self._tool_id

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        if request.execution_id is None:
            raise ValueError("prepared request required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            status=ToolExecutionStatus.SUCCESS,
            output={"received": dict(request.parameters)},
        )


class IdentifierTests(unittest.TestCase):
    def test_tool_id_accepts_non_empty_value(self) -> None:
        self.assertEqual(ToolId("profile").value, "profile")

    def test_tool_id_rejects_empty_value(self) -> None:
        with self.assertRaises(ValueError):
            ToolId("  ")

    def test_execution_id_accepts_non_empty_value(self) -> None:
        self.assertEqual(ExecutionId("execution-1").value, "execution-1")

    def test_execution_id_rejects_empty_value(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionId("")

    def test_generated_execution_id_is_uuid(self) -> None:
        generated = ExecutionId.generate()
        self.assertEqual(str(UUID(generated.value)), generated.value)


class ContractTests(unittest.TestCase):
    def test_request_preserves_tool_and_parameters(self) -> None:
        request = ToolExecutionRequest(
            tool_id=ToolId("profile"),
            parameters={"column": "X"},
        )
        self.assertEqual(request.tool_id, ToolId("profile"))
        self.assertEqual(request.parameters, {"column": "X"})

    def test_request_allows_deferred_execution_id(self) -> None:
        request = ToolExecutionRequest(tool_id=ToolId("profile"))
        self.assertIsNone(request.execution_id)

    def test_request_defaults_are_not_shared(self) -> None:
        first = ToolExecutionRequest(tool_id=ToolId("first"))
        second = ToolExecutionRequest(tool_id=ToolId("second"))
        self.assertIsNot(first.parameters, second.parameters)
        self.assertIsNot(first.metadata, second.metadata)

    def test_request_copies_input_mappings(self) -> None:
        parameters = {"column": "X"}
        metadata = {"source": "test"}
        request = ToolExecutionRequest(
            tool_id=ToolId("profile"),
            parameters=parameters,
            metadata=metadata,
        )
        parameters["column"] = "Y"
        metadata["source"] = "changed"
        self.assertEqual(request.parameters, {"column": "X"})
        self.assertEqual(request.metadata, {"source": "test"})

    def test_success_result(self) -> None:
        result = ToolExecutionResult(
            execution_id=ExecutionId("execution-1"),
            tool_id=ToolId("profile"),
            status=ToolExecutionStatus.SUCCESS,
            output={"rows": 10},
        )
        self.assertEqual(result.status, ToolExecutionStatus.SUCCESS)
        self.assertEqual(result.output, {"rows": 10})
        self.assertIsNone(result.error)

    def test_failure_result_with_structured_error(self) -> None:
        error = ToolError(code="UNKNOWN_TOOL", message="Tool is not registered")
        result = ToolExecutionResult(
            execution_id=ExecutionId("execution-2"),
            tool_id=ToolId("missing"),
            status=ToolExecutionStatus.FAILURE,
            error=error,
        )
        self.assertEqual(result.status, ToolExecutionStatus.FAILURE)
        self.assertEqual(result.error, error)

    def test_result_metadata_is_copied(self) -> None:
        metadata = {"source": "test"}
        result = ToolExecutionResult(
            execution_id=ExecutionId("execution-3"),
            tool_id=ToolId("profile"),
            status=ToolExecutionStatus.SUCCESS,
            metadata=metadata,
        )
        metadata["source"] = "changed"
        self.assertEqual(result.metadata, {"source": "test"})

    def test_tool_error_preserves_code_and_message(self) -> None:
        error = ToolError(code="INVALID_PARAMETERS", message="Missing column")
        self.assertEqual(error.code, "INVALID_PARAMETERS")
        self.assertEqual(error.message, "Missing column")

    def test_tool_spec_preserves_descriptive_fields(self) -> None:
        spec = ToolSpec(
            tool_id=ToolId("profile"),
            name="Dataset profile",
            description="Returns structural metadata",
            version="1.0",
        )
        self.assertEqual(spec.tool_id, ToolId("profile"))
        self.assertEqual(spec.version, "1.0")


class ToolAndExecutorTests(unittest.TestCase):
    def test_fake_tool_satisfies_protocol_without_inheritance(self) -> None:
        self.assertIsInstance(FakeTool(), Tool)

    def test_query_executor_can_be_initialized(self) -> None:
        self.assertIsInstance(QueryExecutor(), QueryExecutor)

    def test_executor_generates_execution_id(self) -> None:
        prepared = QueryExecutor().prepare_request(
            ToolExecutionRequest(tool_id=ToolId("profile"))
        )
        self.assertIsInstance(prepared.execution_id, ExecutionId)

    def test_executor_preserves_explicit_execution_id(self) -> None:
        execution_id = ExecutionId("provided-id")
        request = ToolExecutionRequest(
            tool_id=ToolId("profile"),
            execution_id=execution_id,
        )
        self.assertIs(QueryExecutor().prepare_request(request), request)

    def test_executor_does_not_execute_tool(self) -> None:
        tool = FakeTool()
        request = ToolExecutionRequest(tool_id=tool.tool_id)
        prepared = QueryExecutor().prepare_request(request)
        self.assertIsNotNone(prepared.execution_id)


class IsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_files = list((SOURCE_ROOT / "query_execution").glob("*.py"))
        self.source_text = "\n".join(
            path.read_text(encoding="utf-8") for path in self.source_files
        )

    def test_no_imports_from_experimental_or_orchestration_modules(self) -> None:
        self.assertNotIn("from spikes", self.source_text)
        self.assertNotIn("import spikes", self.source_text)
        self.assertNotIn("from orchestration", self.source_text)
        self.assertNotIn("import orchestration", self.source_text)

    def test_no_architecture_specific_modules_exist(self) -> None:
        module_names = {path.stem for path in self.source_files}
        self.assertTrue({"planner", "blackboard", "critic"}.isdisjoint(module_names))

    def test_no_productive_analytical_tools_exist(self) -> None:
        module_names = {path.stem for path in self.source_files}
        analytical_modules = {"pearson", "spearman", "outliers", "subgroups"}
        self.assertTrue(analytical_modules.isdisjoint(module_names))

    def test_no_arbitrary_execution_mechanisms(self) -> None:
        forbidden = (
            "eval" + "(",
            "exec" + "(",
            "subprocess",
            "os.system",
            "shell=True",
            "__import__" + "(",
        )
        for marker in forbidden:
            self.assertNotIn(marker, self.source_text)


if __name__ == "__main__":
    unittest.main()
