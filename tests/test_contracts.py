"""Unit tests for neutral orchestration contracts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from orchestration import (  # noqa: E402
    ComponentId,
    ComponentRequest,
    ComponentResult,
    ComponentStatus,
    ExecutionId,
    ExecutionStatus,
    OrchestrationRequest,
    OrchestrationResult,
)


class OrchestrationRequestTests(unittest.TestCase):
    def test_request_accepts_explicit_execution_id(self) -> None:
        request = OrchestrationRequest(execution_id=ExecutionId("execution-1"))

        self.assertEqual(request.execution_id, "execution-1")

    def test_request_allows_orchestrator_generated_execution_id(self) -> None:
        self.assertIsNone(OrchestrationRequest().execution_id)

    def test_request_defaults_are_not_shared(self) -> None:
        first = OrchestrationRequest()
        second = OrchestrationRequest()

        self.assertIsNot(first.metadata, second.metadata)
        self.assertIsNot(first.payload, second.payload)

    def test_request_preserves_payload_with_defensive_copy(self) -> None:
        payload = {"operation": "analyze"}
        request = OrchestrationRequest(payload=payload)
        payload["operation"] = "changed"

        self.assertEqual(request.payload["operation"], "analyze")

    def test_request_rejects_empty_execution_id(self) -> None:
        with self.assertRaises(ValueError):
            OrchestrationRequest(execution_id=ExecutionId(" "))


class ComponentContractTests(unittest.TestCase):
    def test_component_request_preserves_identifiers(self) -> None:
        request = ComponentRequest(
            execution_id=ExecutionId("execution-1"),
            component_id=ComponentId("component-1"),
        )

        self.assertEqual(request.execution_id, "execution-1")
        self.assertEqual(request.component_id, "component-1")

    def test_component_request_rejects_empty_component_id(self) -> None:
        with self.assertRaises(ValueError):
            ComponentRequest(
                execution_id=ExecutionId("execution-1"),
                component_id=ComponentId(""),
            )

    def test_component_result_represents_success(self) -> None:
        result = ComponentResult(
            component_id=ComponentId("component-1"),
            status=ComponentStatus.SUCCESS,
            output={"value": 42},
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.output["value"], 42)
        self.assertIsNone(result.error)

    def test_component_result_represents_failure(self) -> None:
        result = ComponentResult(
            component_id=ComponentId("component-1"),
            status=ComponentStatus.FAILURE,
            error="controlled failure",
        )

        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, "controlled failure")


class OrchestrationResultTests(unittest.TestCase):
    def test_result_preserves_status_and_output(self) -> None:
        result = OrchestrationResult(
            execution_id=ExecutionId("execution-1"),
            status=ExecutionStatus.COMPLETED,
            output={"summary": "complete"},
        )

        self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        self.assertEqual(result.output["summary"], "complete")

    def test_result_metadata_uses_defensive_copy(self) -> None:
        metadata = {"source": "external"}
        result = OrchestrationResult(
            execution_id=ExecutionId("execution-1"),
            status=ExecutionStatus.PENDING,
            metadata=metadata,
        )
        metadata["source"] = "changed"

        self.assertEqual(result.metadata["source"], "external")


if __name__ == "__main__":
    unittest.main()
