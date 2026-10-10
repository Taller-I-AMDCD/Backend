from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from query_execution import (  # noqa: E402
    ExecutionId,
    ToolDispatcher,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolId,
    ToolNotFoundError,
    ToolRegistry,
    ToolSpec,
)


class FakeTool:
    def __init__(self, identifier: str) -> None:
        self._tool_id = ToolId(identifier)
        self._spec = ToolSpec(
            tool_id=self._tool_id,
            name=f"Tool {identifier}",
            description="Test-only tool",
        )
        self.execution_count = 0

    @property
    def tool_id(self) -> ToolId:
        return self._tool_id

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.execution_count += 1
        if request.execution_id is None:
            raise ValueError("execution_id required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=self.tool_id,
            status=ToolExecutionStatus.SUCCESS,
        )


class ToolDispatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.echo = FakeTool("echo")
        self.other = FakeTool("other")
        self.registry.register(self.echo)
        self.registry.register(self.other)
        self.dispatcher = ToolDispatcher(self.registry)

    def test_dispatcher_uses_supplied_registry(self) -> None:
        self.assertIs(self.dispatcher.registry, self.registry)

    def test_resolve_returns_exact_registered_tool(self) -> None:
        request = ToolExecutionRequest(tool_id=self.echo.tool_id)
        self.assertIs(self.dispatcher.resolve(request), self.echo)

    def test_resolve_preserves_execution_id(self) -> None:
        execution_id = ExecutionId("execution-1")
        request = ToolExecutionRequest(
            tool_id=self.echo.tool_id,
            execution_id=execution_id,
        )
        self.dispatcher.resolve(request)
        self.assertIs(request.execution_id, execution_id)

    def test_resolve_does_not_alter_parameters(self) -> None:
        request = ToolExecutionRequest(
            tool_id=self.echo.tool_id,
            parameters={"value": 2},
        )
        before = dict(request.parameters)
        self.dispatcher.resolve(request)
        self.assertEqual(request.parameters, before)

    def test_resolve_does_not_alter_metadata(self) -> None:
        request = ToolExecutionRequest(
            tool_id=self.echo.tool_id,
            metadata={"source": "test"},
        )
        before = dict(request.metadata)
        self.dispatcher.resolve(request)
        self.assertEqual(request.metadata, before)

    def test_unknown_tool_raises_controlled_error(self) -> None:
        request = ToolExecutionRequest(tool_id=ToolId("unknown"))
        with self.assertRaises(ToolNotFoundError):
            self.dispatcher.resolve(request)

    def test_dispatcher_does_not_select_another_tool(self) -> None:
        request = ToolExecutionRequest(tool_id=self.other.tool_id)
        self.assertIs(self.dispatcher.resolve(request), self.other)
        self.assertIsNot(self.dispatcher.resolve(request), self.echo)

    def test_dispatcher_does_not_execute_tools(self) -> None:
        request = ToolExecutionRequest(tool_id=self.echo.tool_id)
        self.dispatcher.resolve(request)
        self.assertEqual(self.echo.execution_count, 0)
        self.assertEqual(self.other.execution_count, 0)

    def test_unregistered_object_cannot_be_resolved(self) -> None:
        unregistered = FakeTool("unregistered")
        request = ToolExecutionRequest(tool_id=unregistered.tool_id)
        with self.assertRaises(ToolNotFoundError):
            self.dispatcher.resolve(request)


class DispatcherSecurityTests(unittest.TestCase):
    def test_product_code_has_no_arbitrary_resolution_mechanisms(self) -> None:
        source_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (SOURCE_ROOT / "query_execution").glob("*.py")
        )
        forbidden = (
            "eval" + "(",
            "exec" + "(",
            "subprocess",
            "os.system",
            "shell=True",
            "importlib",
            "globals" + "(",
            "locals" + "(",
            "__import__" + "(",
        )
        for marker in forbidden:
            self.assertNotIn(marker, source_text)


if __name__ == "__main__":
    unittest.main()
