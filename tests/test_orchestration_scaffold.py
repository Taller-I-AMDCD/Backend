"""Tests for the provisional, strategy-neutral orchestration scaffold."""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from orchestration import (  # noqa: E402
    ComponentId,
    ComponentResult,
    ComponentStatus,
    ExecutionId,
    ExecutionState,
    ExecutionStatus,
    OrchestrationRequest,
    OrchestrationResult,
    Orchestrator,
    Supervisor,
)


class ContractTests(unittest.TestCase):
    def test_request_can_be_created(self) -> None:
        request = OrchestrationRequest(
            payload={"dataset": "sample"},
            metadata={"source": "test"},
        )

        self.assertEqual(request.payload["dataset"], "sample")
        self.assertEqual(request.metadata["source"], "test")

    def test_result_can_be_created(self) -> None:
        result = OrchestrationResult(
            execution_id=ExecutionId("execution-1"),
            status=ExecutionStatus.COMPLETED,
            component_results=(
                ComponentResult(
                    component_id=ComponentId("component-1"),
                    status=ComponentStatus.SUCCESS,
                ),
            ),
        )

        self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        self.assertTrue(result.component_results[0].succeeded)


class StateTests(unittest.TestCase):
    def test_execution_state_starts_pending(self) -> None:
        state = ExecutionState(execution_id=ExecutionId("execution-1"))

        self.assertEqual(state.status, ExecutionStatus.PENDING)
        self.assertIsNone(state.current_step)

    def test_execution_state_preserves_metadata(self) -> None:
        state = ExecutionState(
            execution_id=ExecutionId("execution-1"),
            metadata={"correlation_id": "request-1"},
        )

        self.assertEqual(state.metadata["correlation_id"], "request-1")


class BoundaryTests(unittest.TestCase):
    def test_supervisor_can_be_initialized(self) -> None:
        self.assertIsInstance(Supervisor(), Supervisor)

    def test_orchestrator_can_be_initialized(self) -> None:
        self.assertIsNone(Orchestrator().state)

    def test_orchestrator_initializes_state_and_preserves_metadata(self) -> None:
        orchestrator = Orchestrator()
        result = orchestrator.initialize(
            OrchestrationRequest(metadata={"tenant": "research"})
        )

        self.assertEqual(result.status, ExecutionStatus.PENDING)
        self.assertEqual(result.metadata["tenant"], "research")
        self.assertIsNotNone(orchestrator.state)
        self.assertEqual(orchestrator.state.execution_id, result.execution_id)


class IndependenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.imported_roots: set[str] = set()
        for source_file in (SOURCE_ROOT / "orchestration").glob("*.py"):
            tree = ast.parse(source_file.read_text(encoding="utf-8"))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    cls.imported_roots.update(
                        alias.name.split(".")[0] for alias in node.names
                    )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    cls.imported_roots.add(node.module.split(".")[0])

    def test_orchestrator_has_no_planner_dependency(self) -> None:
        self.assertNotIn("planner", self.imported_roots)

    def test_orchestrator_has_no_blackboard_dependency(self) -> None:
        self.assertNotIn("blackboard", self.imported_roots)

    def test_orchestrator_has_no_critic_dependency(self) -> None:
        self.assertNotIn("critic", self.imported_roots)

    def test_productive_modules_have_no_spike_imports(self) -> None:
        self.assertNotIn("spikes", self.imported_roots)

    def test_candidate_specific_modules_do_not_exist(self) -> None:
        module_directory = SOURCE_ROOT / "orchestration"

        for module_name in (
            "planner.py",
            "executor.py",
            "blackboard.py",
            "critic.py",
            "consensus.py",
        ):
            self.assertFalse((module_directory / module_name).exists())

if __name__ == "__main__":
    unittest.main()
