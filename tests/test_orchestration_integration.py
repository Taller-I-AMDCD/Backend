"""Final integration and neutrality tests for the provisional scaffold."""

from __future__ import annotations

import ast
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
MODULE_ROOT = SOURCE_ROOT / "orchestration"
sys.path.insert(0, str(SOURCE_ROOT))

import orchestration  # noqa: E402
from orchestration import (  # noqa: E402
    ComponentRegistry,
    ExecutionStatus,
    Supervisor,
    TraceEventType,
)
from orchestration.demo import (  # noqa: E402
    main as demo_main,
    run_failure_case,
    run_max_steps_case,
    run_success_case,
)


class FinalFlowIntegrationTests(unittest.TestCase):
    def test_successful_demo_executes_two_components_once(self) -> None:
        outcome = run_success_case()

        self.assertEqual(
            outcome.executed_components,
            ("demo-component-a", "demo-component-b"),
        )
        self.assertEqual(outcome.steps, 2)

    def test_successful_demo_completes_and_preserves_outputs(self) -> None:
        outcome = run_success_case()

        self.assertEqual(outcome.result.status, ExecutionStatus.COMPLETED)
        self.assertEqual(outcome.result.output["final_value"], 8)
        outputs = outcome.result.output["component_outputs"]
        self.assertEqual([item["output"]["value"] for item in outputs], [4, 8])

    def test_successful_trace_is_complete_and_incremental(self) -> None:
        outcome = run_success_case()
        event_types = [entry.event_type for entry in outcome.trace_entries]

        self.assertEqual(event_types[0], TraceEventType.EXECUTION_STARTED)
        self.assertEqual(event_types[-1], TraceEventType.EXECUTION_COMPLETED)
        self.assertEqual(event_types.count(TraceEventType.COMPONENT_SELECTED), 2)
        self.assertEqual(event_types.count(TraceEventType.COMPONENT_STARTED), 2)
        self.assertEqual(event_types.count(TraceEventType.COMPONENT_COMPLETED), 2)
        self.assertEqual(
            [entry.sequence for entry in outcome.trace_entries],
            list(range(1, len(outcome.trace_entries) + 1)),
        )

    def test_execution_id_is_stable_across_trace(self) -> None:
        outcome = run_success_case()

        self.assertTrue(outcome.result.execution_id)
        self.assertTrue(
            all(
                entry.execution_id == outcome.result.execution_id
                for entry in outcome.trace_entries
            )
        )

    def test_complete_does_not_execute_additional_components(self) -> None:
        outcome = run_success_case()

        self.assertEqual(len(outcome.executed_components), 2)
        self.assertEqual(outcome.steps, 2)

    def test_controlled_failure_is_terminal_and_traced(self) -> None:
        outcome = run_failure_case()

        self.assertEqual(outcome.result.status, ExecutionStatus.FAILED)
        self.assertIn("not registered", outcome.result.error)
        self.assertEqual(
            outcome.trace_entries[-1].event_type,
            TraceEventType.EXECUTION_FAILED,
        )

    def test_max_steps_limits_repeating_demo(self) -> None:
        outcome = run_max_steps_case(max_steps=3)

        self.assertEqual(outcome.steps, 3)
        self.assertEqual(outcome.result.status, ExecutionStatus.FAILED)
        self.assertIn("maximum component steps exceeded: 3", outcome.result.error)
        self.assertEqual(
            outcome.trace_entries[-1].event_type,
            TraceEventType.EXECUTION_FAILED,
        )

    def test_demo_metadata_is_preserved(self) -> None:
        outcome = run_success_case()

        self.assertEqual(outcome.result.metadata["case"], "successful-flow")

    def test_final_result_is_json_serializable_for_demo_data(self) -> None:
        outcome = run_success_case()

        serialized = json.dumps(asdict(outcome.result))

        self.assertIn("completed", serialized)
        self.assertIn("final_value", serialized)

    def test_demo_prints_all_three_cases_without_traceback(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            demo_main()

        text = output.getvalue()
        self.assertIn("CASE 1 - Successful flow", text)
        self.assertIn("CASE 2 - Controlled failure", text)
        self.assertIn("CASE 3 - Max steps protection", text)
        self.assertIn("Architecture selected: NO", text)
        self.assertNotIn("Traceback", text)


class FinalNeutralityTests(unittest.TestCase):
    def test_registry_and_supervisor_expose_no_routing_method(self) -> None:
        self.assertFalse(hasattr(ComponentRegistry(), "route"))
        self.assertFalse(hasattr(ComponentRegistry(), "decide"))
        self.assertFalse(hasattr(Supervisor(), "route"))

    def test_demo_strategies_are_not_exported_by_core_package(self) -> None:
        self.assertNotIn("DemoSequenceStrategy", orchestration.__all__)
        self.assertNotIn("DemoRepeatingStrategy", orchestration.__all__)

    def test_core_modules_do_not_import_demo(self) -> None:
        for source_file in MODULE_ROOT.glob("*.py"):
            if source_file.name == "demo.py":
                continue
            imports = self._imported_roots(source_file)
            self.assertNotIn("demo", imports, source_file.name)

    def test_productive_modules_do_not_import_spikes(self) -> None:
        for source_file in MODULE_ROOT.glob("*.py"):
            imports = self._imported_roots(source_file)
            self.assertNotIn("spikes", imports, source_file.name)

    def test_candidate_specific_modules_do_not_exist(self) -> None:
        for module_name in (
            "planner.py",
            "executor.py",
            "blackboard.py",
            "critic.py",
            "consensus.py",
        ):
            self.assertFalse((MODULE_ROOT / module_name).exists())

    @staticmethod
    def _imported_roots(source_file: Path) -> set[str]:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        return roots


if __name__ == "__main__":
    unittest.main()
