"""Integration tests for the bounded, replaceable coordination flow."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from orchestration import (  # noqa: E402
    ComponentId,
    ComponentRegistry,
    ComponentRequest,
    ComponentResult,
    ComponentStatus,
    CoordinationAction,
    CoordinationDecision,
    ExecutionContext,
    ExecutionId,
    ExecutionStatus,
    OrchestrationRequest,
    Orchestrator,
    Supervisor,
    TraceEventType,
)


@dataclass
class FakeComponent:
    component_id: ComponentId
    result: ComponentResult | None = None
    exception: Exception | None = None
    calls: list[ComponentRequest] = field(default_factory=list)

    def handle(self, request: ComponentRequest) -> ComponentResult:
        self.calls.append(request)
        if self.exception is not None:
            raise self.exception
        return self.result or ComponentResult(
            component_id=self.component_id,
            status=ComponentStatus.SUCCESS,
            output={"value": self.component_id},
        )


class SequenceStrategy:
    def __init__(self, decisions: list[CoordinationDecision]) -> None:
        self._decisions = iter(decisions)
        self.calls = 0

    def decide(self, context: ExecutionContext) -> CoordinationDecision:
        self.calls += 1
        return next(self._decisions)


class RepeatingStrategy:
    def __init__(self, component_id: ComponentId) -> None:
        self._component_id = component_id

    def decide(self, context: ExecutionContext) -> CoordinationDecision:
        return CoordinationDecision(
            action=CoordinationAction.EXECUTE,
            component_id=self._component_id,
        )


def execute_decision(component_id: str) -> CoordinationDecision:
    return CoordinationDecision(
        action=CoordinationAction.EXECUTE,
        component_id=ComponentId(component_id),
        payload={"requested": component_id},
        metadata={"decision": component_id},
    )


def complete_decision() -> CoordinationDecision:
    return CoordinationDecision(
        action=CoordinationAction.COMPLETE,
        payload={"summary": "complete"},
    )


class OrchestrationFlowTests(unittest.TestCase):
    def test_immediate_complete_transitions_and_finishes(self) -> None:
        orchestrator = self._orchestrator([complete_decision()])

        result = orchestrator.run(OrchestrationRequest())

        self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        self.assertEqual(result.output["summary"], "complete")
        self.assertEqual(
            self._event_types(orchestrator),
            [
                TraceEventType.EXECUTION_STARTED,
                TraceEventType.STATE_CHANGED,
                TraceEventType.STATE_CHANGED,
                TraceEventType.EXECUTION_COMPLETED,
            ],
        )

    def test_registered_component_executes_once_with_correct_request(self) -> None:
        component = FakeComponent(ComponentId("component-1"))
        orchestrator = self._orchestrator(
            [execute_decision("component-1"), complete_decision()],
            components=[component],
        )

        result = orchestrator.run(
            OrchestrationRequest(
                execution_id=ExecutionId("execution-1"),
                metadata={"source": "request"},
            )
        )

        self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        self.assertEqual(len(component.calls), 1)
        self.assertEqual(component.calls[0].execution_id, "execution-1")
        self.assertEqual(component.calls[0].component_id, "component-1")
        self.assertEqual(component.calls[0].payload["requested"], "component-1")
        self.assertEqual(result.execution_id, "execution-1")
        self.assertEqual(result.metadata["source"], "request")

    def test_successful_component_output_and_trace_are_available(self) -> None:
        component = FakeComponent(ComponentId("component-1"))
        orchestrator = self._orchestrator(
            [execute_decision("component-1"), complete_decision()],
            components=[component],
        )

        result = orchestrator.run(OrchestrationRequest())

        outputs = result.output["component_outputs"]
        self.assertEqual(outputs[0]["component_id"], "component-1")
        self.assertEqual(outputs[0]["output"]["value"], "component-1")
        events = self._event_types(orchestrator)
        self.assertEqual(
            events,
            [
                TraceEventType.EXECUTION_STARTED,
                TraceEventType.STATE_CHANGED,
                TraceEventType.COMPONENT_SELECTED,
                TraceEventType.COMPONENT_STARTED,
                TraceEventType.COMPONENT_COMPLETED,
                TraceEventType.STATE_CHANGED,
                TraceEventType.EXECUTION_COMPLETED,
            ],
        )
        sequences = [entry.sequence for entry in orchestrator.context.trace.entries]
        self.assertEqual(sequences, list(range(1, len(sequences) + 1)))

    def test_two_components_execute_in_successive_steps(self) -> None:
        first = FakeComponent(ComponentId("component-1"))
        second = FakeComponent(ComponentId("component-2"))
        orchestrator = self._orchestrator(
            [
                execute_decision("component-1"),
                execute_decision("component-2"),
                complete_decision(),
            ],
            components=[first, second],
        )

        result = orchestrator.run(OrchestrationRequest())

        self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(len(second.calls), 1)
        self.assertEqual(orchestrator.state.current_step, "2")

    def test_fail_decision_returns_controlled_failure(self) -> None:
        orchestrator = self._orchestrator(
            [
                CoordinationDecision(
                    action=CoordinationAction.FAIL,
                    reason="controlled failure",
                )
            ]
        )

        result = orchestrator.run(OrchestrationRequest())

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(result.error, "controlled failure")
        self.assertEqual(
            self._event_types(orchestrator)[-1],
            TraceEventType.EXECUTION_FAILED,
        )

    def test_component_failure_returns_failed_result(self) -> None:
        component = FakeComponent(
            ComponentId("component-1"),
            result=ComponentResult(
                component_id=ComponentId("component-1"),
                status=ComponentStatus.FAILURE,
                error="component rejected request",
            ),
        )
        orchestrator = self._orchestrator(
            [execute_decision("component-1")],
            components=[component],
        )

        result = orchestrator.run(OrchestrationRequest())

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(result.error, "component rejected request")
        self.assertIn(
            TraceEventType.COMPONENT_FAILED,
            self._event_types(orchestrator),
        )

    def test_unknown_component_returns_failed_result(self) -> None:
        orchestrator = self._orchestrator([execute_decision("missing")])

        result = orchestrator.run(OrchestrationRequest())

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertIn("not registered", result.error)

    def test_unexpected_component_exception_is_controlled(self) -> None:
        component = FakeComponent(
            ComponentId("component-1"),
            exception=RuntimeError("unexpected condition"),
        )
        orchestrator = self._orchestrator(
            [execute_decision("component-1")],
            components=[component],
        )

        result = orchestrator.run(OrchestrationRequest())

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertIn("RuntimeError: unexpected condition", result.error)
        self.assertIn(
            TraceEventType.COMPONENT_FAILED,
            self._event_types(orchestrator),
        )

    def test_max_steps_stops_repeating_strategy(self) -> None:
        component = FakeComponent(ComponentId("component-1"))
        registry = ComponentRegistry()
        registry.register(component)
        orchestrator = Orchestrator(
            supervisor=Supervisor(RepeatingStrategy(component.component_id)),
            registry=registry,
            max_steps=2,
        )

        result = orchestrator.run(OrchestrationRequest())

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(len(component.calls), 2)
        self.assertIn("maximum component steps exceeded", result.error)

    def test_supervisor_delegates_without_executing_component(self) -> None:
        strategy = SequenceStrategy([execute_decision("component-1")])
        supervisor = Supervisor(strategy)
        orchestrator = self._orchestrator([complete_decision()])
        orchestrator.initialize(OrchestrationRequest())

        decision = supervisor.decide(orchestrator.context)

        self.assertEqual(decision.component_id, "component-1")
        self.assertEqual(strategy.calls, 1)

    def test_registry_exposes_no_routing_decision(self) -> None:
        registry = ComponentRegistry()

        self.assertFalse(hasattr(registry, "decide"))
        self.assertFalse(hasattr(registry, "route"))

    @staticmethod
    def _orchestrator(
        decisions: list[CoordinationDecision],
        components: list[FakeComponent] | None = None,
    ) -> Orchestrator:
        registry = ComponentRegistry()
        for component in components or []:
            registry.register(component)
        return Orchestrator(
            supervisor=Supervisor(SequenceStrategy(decisions)),
            registry=registry,
        )

    @staticmethod
    def _event_types(orchestrator: Orchestrator) -> list[TraceEventType]:
        return [entry.event_type for entry in orchestrator.context.trace.entries]


if __name__ == "__main__":
    unittest.main()
