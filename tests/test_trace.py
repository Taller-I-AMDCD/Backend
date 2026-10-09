"""Unit tests for generic in-memory execution tracing."""

from __future__ import annotations

import sys
import unittest
from datetime import timezone
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from orchestration import (  # noqa: E402
    ComponentId,
    ExecutionId,
    ExecutionTrace,
    OrchestrationRequest,
    Orchestrator,
    Supervisor,
    TraceEventType,
)


class ExecutionTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.execution_id = ExecutionId("execution-1")
        self.trace = ExecutionTrace(self.execution_id)

    def test_trace_preserves_execution_id_and_starts_empty(self) -> None:
        self.assertEqual(self.trace.execution_id, self.execution_id)
        self.assertEqual(len(self.trace), 0)
        self.assertEqual(self.trace.entries, ())

    def test_record_adds_entry_with_sequence_starting_at_one(self) -> None:
        entry = self.trace.record(TraceEventType.EXECUTION_STARTED)

        self.assertEqual(entry.sequence, 1)
        self.assertEqual(len(self.trace), 1)

    def test_sequence_increments_and_order_is_preserved(self) -> None:
        first = self.trace.record(TraceEventType.EXECUTION_STARTED)
        second = self.trace.record(TraceEventType.STATE_CHANGED)

        self.assertEqual((first.sequence, second.sequence), (1, 2))
        self.assertEqual(self.trace.entries, (first, second))

    def test_metadata_mutation_does_not_change_internal_entry(self) -> None:
        metadata = {"source": "external"}
        entry = self.trace.record(
            TraceEventType.STATE_CHANGED,
            metadata=metadata,
        )
        metadata["source"] = "changed"

        self.assertEqual(entry.metadata["source"], "external")
        entry.metadata["source"] = "mutation"
        self.assertEqual(
            self.trace.entries[0].metadata["source"],
            "external",
        )

    def test_timestamp_is_timezone_aware_utc(self) -> None:
        entry = self.trace.record(TraceEventType.EXECUTION_STARTED)

        self.assertIsNotNone(entry.timestamp.tzinfo)
        self.assertEqual(entry.timestamp.utcoffset(), timezone.utc.utcoffset(None))

    def test_entries_collection_cannot_mutate_internal_storage(self) -> None:
        first = self.trace.record(TraceEventType.EXECUTION_STARTED)
        external_entries = self.trace.entries + (first,)

        self.assertEqual(len(external_entries), 2)
        self.assertEqual(len(self.trace), 1)

    def test_multiple_event_types_and_optional_component_are_supported(self) -> None:
        self.trace.record(TraceEventType.EXECUTION_STARTED)
        entry = self.trace.record(
            TraceEventType.COMPONENT_STARTED,
            component_id=ComponentId("component-1"),
        )

        self.assertEqual(entry.event_type, TraceEventType.COMPONENT_STARTED)
        self.assertEqual(entry.component_id, "component-1")


class OrchestratorTraceTests(unittest.TestCase):
    def test_orchestrator_creates_trace_with_same_execution_id(self) -> None:
        orchestrator = Orchestrator()
        result = orchestrator.initialize(OrchestrationRequest())

        self.assertIsNotNone(orchestrator.context)
        self.assertEqual(orchestrator.context.trace.execution_id, result.execution_id)

    def test_initialization_records_execution_started(self) -> None:
        orchestrator = Orchestrator()
        orchestrator.initialize(OrchestrationRequest())

        entries = orchestrator.context.trace.entries
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].event_type, TraceEventType.EXECUTION_STARTED)

    def test_initialization_trace_metadata_does_not_alias_request(self) -> None:
        request = OrchestrationRequest(metadata={"source": "request"})
        orchestrator = Orchestrator()
        orchestrator.initialize(request)

        entry = orchestrator.context.trace.entries[0]
        self.assertEqual(entry.metadata["source"], "request")
        self.assertIsNot(entry.metadata, request.metadata)

    def test_supervisor_exposes_no_routing_methods(self) -> None:
        supervisor = Supervisor()

        self.assertFalse(hasattr(supervisor, "route"))
        self.assertFalse(hasattr(supervisor, "select_component"))


if __name__ == "__main__":
    unittest.main()
