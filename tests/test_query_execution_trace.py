from __future__ import annotations

import sys
import unittest
from datetime import timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from query_execution import (  # noqa: E402
    ExecutionId,
    QueryExecutionTrace,
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


class SuccessfulTool:
    def __init__(self, identifier: str = "success") -> None:
        self._tool_id = ToolId(identifier)
        self._spec = ToolSpec(
            tool_id=self._tool_id,
            name="Successful tool",
            description="Test-only tool",
        )

    @property
    def tool_id(self) -> ToolId:
        return self._tool_id

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        if request.execution_id is None:
            raise ValueError("execution_id required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=self.tool_id,
            status=ToolExecutionStatus.SUCCESS,
        )


class QueryExecutionTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.trace = QueryExecutionTrace()
        self.execution_id = ExecutionId("execution-1")
        self.tool_id = ToolId("tool-1")

    def test_trace_starts_empty(self) -> None:
        self.assertEqual(len(self.trace), 0)
        self.assertEqual(self.trace.entries, ())

    def test_first_sequence_is_one(self) -> None:
        entry = self.trace.record(
            self.execution_id,
            self.tool_id,
            QueryTraceEventType.EXECUTION_STARTED,
        )
        self.assertEqual(entry.sequence, 1)

    def test_sequence_is_incremental_and_ordered(self) -> None:
        for event_type in (
            QueryTraceEventType.EXECUTION_STARTED,
            QueryTraceEventType.TOOL_RESOLVED,
            QueryTraceEventType.TOOL_STARTED,
        ):
            self.trace.record(self.execution_id, self.tool_id, event_type)
        self.assertEqual([entry.sequence for entry in self.trace.entries], [1, 2, 3])

    def test_timestamp_is_timezone_aware_utc(self) -> None:
        entry = self.trace.record(
            self.execution_id,
            self.tool_id,
            QueryTraceEventType.EXECUTION_STARTED,
        )
        self.assertIsNotNone(entry.timestamp.tzinfo)
        self.assertEqual(entry.timestamp.utcoffset(), timezone.utc.utcoffset(None))

    def test_metadata_is_defensively_copied_and_immutable(self) -> None:
        metadata = {"status": "started"}
        entry = self.trace.record(
            self.execution_id,
            self.tool_id,
            QueryTraceEventType.EXECUTION_STARTED,
            metadata=metadata,
        )
        metadata["status"] = "changed"
        self.assertEqual(entry.metadata["status"], "started")
        with self.assertRaises(TypeError):
            entry.metadata["status"] = "changed"  # type: ignore[index]

    def test_entries_snapshot_cannot_change_internal_storage(self) -> None:
        self.trace.record(
            self.execution_id,
            self.tool_id,
            QueryTraceEventType.EXECUTION_STARTED,
        )
        snapshot = self.trace.entries
        self.assertIsInstance(snapshot, tuple)
        self.assertEqual(len(self.trace), 1)

    def test_identifiers_are_preserved(self) -> None:
        entry = self.trace.record(
            self.execution_id,
            self.tool_id,
            QueryTraceEventType.EXECUTION_STARTED,
        )
        self.assertEqual(entry.execution_id, self.execution_id)
        self.assertEqual(entry.tool_id, self.tool_id)

    def test_entries_can_be_filtered_by_execution(self) -> None:
        other_execution = ExecutionId("execution-2")
        self.trace.record(
            self.execution_id,
            self.tool_id,
            QueryTraceEventType.EXECUTION_STARTED,
        )
        self.trace.record(
            other_execution,
            self.tool_id,
            QueryTraceEventType.EXECUTION_STARTED,
        )
        self.assertEqual(len(self.trace.for_execution(self.execution_id)), 1)


class IntegratedTraceTests(unittest.TestCase):
    def test_success_has_expected_terminal_event_and_duration(self) -> None:
        registry = ToolRegistry()
        tool = SuccessfulTool()
        registry.register(tool)
        trace = QueryExecutionTrace()
        executor = QueryExecutor(ToolDispatcher(registry), trace=trace)
        result = executor.execute(ToolExecutionRequest(tool_id=tool.tool_id))
        entries = trace.for_execution(result.execution_id)
        self.assertEqual(
            [entry.event_type for entry in entries],
            [
                QueryTraceEventType.EXECUTION_STARTED,
                QueryTraceEventType.TOOL_RESOLVED,
                QueryTraceEventType.TOOL_STARTED,
                QueryTraceEventType.TOOL_SUCCEEDED,
                QueryTraceEventType.EXECUTION_COMPLETED,
            ],
        )
        self.assertIsInstance(entries[-1].metadata["duration_ms"], float)
        self.assertGreaterEqual(entries[-1].metadata["duration_ms"], 0)

    def test_unknown_tool_has_failed_terminal_event(self) -> None:
        trace = QueryExecutionTrace()
        executor = QueryExecutor(ToolDispatcher(ToolRegistry()), trace=trace)
        result = executor.execute(ToolExecutionRequest(tool_id=ToolId("unknown")))
        entries = trace.for_execution(result.execution_id)
        self.assertEqual(entries[-1].event_type, QueryTraceEventType.EXECUTION_FAILED)
        self.assertEqual(entries[-1].metadata["error_code"], "UNKNOWN_TOOL")


if __name__ == "__main__":
    unittest.main()
