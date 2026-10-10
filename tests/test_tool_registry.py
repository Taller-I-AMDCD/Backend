from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from query_execution import (  # noqa: E402
    DuplicateToolError,
    InvalidToolError,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolId,
    ToolNotFoundError,
    ToolRegistry,
    ToolSpec,
)


class FakeTool:
    def __init__(self, identifier: str, *, spec_identifier: str | None = None) -> None:
        self._tool_id = ToolId(identifier)
        self._spec = ToolSpec(
            tool_id=ToolId(spec_identifier or identifier),
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


class IncompleteTool:
    tool_id = ToolId("incomplete")


class ToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()

    def test_registry_starts_empty(self) -> None:
        self.assertEqual(len(self.registry), 0)
        self.assertEqual(self.registry.list_ids(), ())

    def test_register_valid_tool(self) -> None:
        tool = FakeTool("echo")
        self.registry.register(tool)
        self.assertEqual(len(self.registry), 1)

    def test_contains_registered_tool(self) -> None:
        tool = FakeTool("echo")
        self.registry.register(tool)
        self.assertTrue(self.registry.contains(tool.tool_id))

    def test_get_returns_same_tool(self) -> None:
        tool = FakeTool("echo")
        self.registry.register(tool)
        self.assertIs(self.registry.get(tool.tool_id), tool)

    def test_list_ids_preserves_typed_registration_order(self) -> None:
        first = FakeTool("first")
        second = FakeTool("second")
        self.registry.register(first)
        self.registry.register(second)
        self.assertEqual(self.registry.list_ids(), (first.tool_id, second.tool_id))
        self.assertTrue(all(isinstance(item, ToolId) for item in self.registry.list_ids()))

    def test_distinct_tools_can_coexist(self) -> None:
        self.registry.register(FakeTool("first"))
        self.registry.register(FakeTool("second"))
        self.assertEqual(len(self.registry), 2)

    def test_duplicate_tool_is_rejected(self) -> None:
        self.registry.register(FakeTool("echo"))
        with self.assertRaises(DuplicateToolError):
            self.registry.register(FakeTool("echo"))

    def test_inconsistent_tool_and_spec_ids_are_rejected(self) -> None:
        with self.assertRaises(InvalidToolError):
            self.registry.register(FakeTool("echo", spec_identifier="different"))

    def test_incomplete_tool_is_rejected(self) -> None:
        with self.assertRaises(InvalidToolError):
            self.registry.register(IncompleteTool())  # type: ignore[arg-type]

    def test_get_unknown_tool_raises_controlled_error(self) -> None:
        with self.assertRaises(ToolNotFoundError):
            self.registry.get(ToolId("unknown"))

    def test_unregister_removes_and_returns_tool(self) -> None:
        tool = FakeTool("echo")
        self.registry.register(tool)
        self.assertIs(self.registry.unregister(tool.tool_id), tool)
        self.assertFalse(self.registry.contains(tool.tool_id))

    def test_register_does_not_execute_tool(self) -> None:
        tool = FakeTool("echo")
        self.registry.register(tool)
        self.assertEqual(tool.execution_count, 0)


if __name__ == "__main__":
    unittest.main()
