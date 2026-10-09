"""Unit tests for execution state and context lifecycle rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from orchestration import (  # noqa: E402
    ExecutionContext,
    ExecutionId,
    ExecutionState,
    ExecutionStatus,
    ExecutionTrace,
    InvalidStateTransitionError,
    OrchestrationError,
    OrchestrationRequest,
    Orchestrator,
)


class ExecutionStateTests(unittest.TestCase):
    def test_initial_state_is_pending(self) -> None:
        state = ExecutionState(execution_id=ExecutionId("execution-1"))

        self.assertEqual(state.status, ExecutionStatus.PENDING)

    def test_pending_can_transition_to_running(self) -> None:
        state = ExecutionState(execution_id=ExecutionId("execution-1"))

        state.transition_to(ExecutionStatus.RUNNING)

        self.assertEqual(state.status, ExecutionStatus.RUNNING)

    def test_running_can_transition_to_completed(self) -> None:
        state = self._running_state()

        state.transition_to(ExecutionStatus.COMPLETED)

        self.assertEqual(state.status, ExecutionStatus.COMPLETED)

    def test_running_can_transition_to_failed(self) -> None:
        state = self._running_state()

        state.transition_to(ExecutionStatus.FAILED)

        self.assertEqual(state.status, ExecutionStatus.FAILED)

    def test_pending_can_fail_during_initialization(self) -> None:
        state = ExecutionState(execution_id=ExecutionId("execution-1"))

        state.transition_to(ExecutionStatus.FAILED)

        self.assertEqual(state.status, ExecutionStatus.FAILED)

    def test_completed_state_cannot_be_reactivated(self) -> None:
        state = self._running_state()
        state.transition_to(ExecutionStatus.COMPLETED)

        with self.assertRaises(InvalidStateTransitionError):
            state.transition_to(ExecutionStatus.RUNNING)

    def test_failed_state_cannot_be_reactivated(self) -> None:
        state = self._running_state()
        state.transition_to(ExecutionStatus.FAILED)

        with self.assertRaises(InvalidStateTransitionError):
            state.transition_to(ExecutionStatus.RUNNING)

    def test_invalid_transition_uses_domain_error(self) -> None:
        state = ExecutionState(execution_id=ExecutionId("execution-1"))

        with self.assertRaises(InvalidStateTransitionError):
            state.transition_to(ExecutionStatus.COMPLETED)

    def test_invalid_transition_error_uses_common_base(self) -> None:
        self.assertTrue(
            issubclass(InvalidStateTransitionError, OrchestrationError)
        )

    def test_current_step_can_be_updated(self) -> None:
        state = ExecutionState(execution_id=ExecutionId("execution-1"))

        state.set_current_step("component-validation")

        self.assertEqual(state.current_step, "component-validation")

    def test_metadata_uses_defensive_copy(self) -> None:
        metadata = {"source": "external"}
        state = ExecutionState(
            execution_id=ExecutionId("execution-1"),
            metadata=metadata,
        )
        metadata["source"] = "changed"

        self.assertEqual(state.metadata["source"], "external")

    def test_metadata_defaults_are_not_shared(self) -> None:
        first = ExecutionState(execution_id=ExecutionId("execution-1"))
        second = ExecutionState(execution_id=ExecutionId("execution-2"))

        first.metadata["key"] = "value"

        self.assertNotIn("key", second.metadata)

    def test_execution_id_remains_stable_across_transitions(self) -> None:
        state = ExecutionState(execution_id=ExecutionId("execution-1"))

        state.transition_to(ExecutionStatus.RUNNING)
        state.transition_to(ExecutionStatus.COMPLETED)

        self.assertEqual(state.execution_id, "execution-1")

    @staticmethod
    def _running_state() -> ExecutionState:
        state = ExecutionState(execution_id=ExecutionId("execution-1"))
        state.transition_to(ExecutionStatus.RUNNING)
        return state


class ExecutionContextTests(unittest.TestCase):
    def test_context_groups_matching_request_and_state(self) -> None:
        execution_id = ExecutionId("execution-1")
        context = ExecutionContext(
            request=OrchestrationRequest(execution_id=execution_id),
            state=ExecutionState(execution_id=execution_id),
            trace=ExecutionTrace(execution_id),
            shared_data={"shared": "value"},
        )

        self.assertEqual(context.state.execution_id, execution_id)
        self.assertEqual(context.shared_data["shared"], "value")

    def test_context_rejects_mismatched_execution_ids(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionContext(
                request=OrchestrationRequest(
                    execution_id=ExecutionId("execution-1")
                ),
                state=ExecutionState(execution_id=ExecutionId("execution-2")),
                trace=ExecutionTrace(ExecutionId("execution-2")),
            )

    def test_context_rejects_mismatched_trace_execution_id(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionContext(
                request=OrchestrationRequest(),
                state=ExecutionState(execution_id=ExecutionId("execution-1")),
                trace=ExecutionTrace(ExecutionId("execution-2")),
            )

class OrchestratorIdentityTests(unittest.TestCase):
    def test_orchestrator_preserves_explicit_execution_id(self) -> None:
        orchestrator = Orchestrator()

        result = orchestrator.initialize(
            OrchestrationRequest(execution_id=ExecutionId("execution-1"))
        )

        self.assertEqual(result.execution_id, "execution-1")
        self.assertEqual(orchestrator.state.execution_id, "execution-1")

    def test_orchestrator_generates_and_preserves_execution_id(self) -> None:
        orchestrator = Orchestrator()

        result = orchestrator.initialize(OrchestrationRequest())

        self.assertTrue(result.execution_id)
        self.assertEqual(orchestrator.state.execution_id, result.execution_id)

    def test_orchestrator_preserves_metadata_without_aliasing_request(self) -> None:
        request = OrchestrationRequest(metadata={"source": "request"})
        orchestrator = Orchestrator()

        result = orchestrator.initialize(request)
        orchestrator.state.metadata["source"] = "state"

        self.assertEqual(request.metadata["source"], "request")
        self.assertEqual(result.metadata["source"], "request")


if __name__ == "__main__":
    unittest.main()
