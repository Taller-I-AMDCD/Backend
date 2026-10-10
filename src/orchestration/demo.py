"""Reproducible demonstration of the provisional orchestration scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import (
    ComponentId,
    ComponentRequest,
    ComponentResult,
    ComponentStatus,
    ExecutionStatus,
    OrchestrationRequest,
    OrchestrationResult,
)
from .context import ExecutionContext
from .orchestrator import Orchestrator
from .registry import ComponentRegistry
from .strategy import CoordinationAction, CoordinationDecision
from .supervisor import Supervisor
from .trace import TraceEntry


@dataclass
class DemoMultiplyComponent:
    """Multiply an input value for demonstration purposes only."""

    component_id: ComponentId
    factor: int
    calls: list[ComponentRequest] = field(default_factory=list)

    def handle(self, request: ComponentRequest) -> ComponentResult:
        self.calls.append(request)
        value = int(request.payload["value"])
        return ComponentResult(
            component_id=self.component_id,
            status=ComponentStatus.SUCCESS,
            output={"value": value * self.factor},
        )


class DemoSequenceStrategy:
    """Drive two known demo components; not a production coordination policy."""

    def decide(self, context: ExecutionContext) -> CoordinationDecision:
        step = context.state.current_step
        if step is None:
            return CoordinationDecision(
                action=CoordinationAction.EXECUTE,
                component_id=ComponentId("demo-component-a"),
                payload=context.request.payload,
                reason="Run the first demonstration transformation.",
            )
        previous_value = _latest_value(context)
        if step == "1":
            return CoordinationDecision(
                action=CoordinationAction.EXECUTE,
                component_id=ComponentId("demo-component-b"),
                payload={"value": previous_value},
                reason="Run the second demonstration transformation.",
            )
        return CoordinationDecision(
            action=CoordinationAction.COMPLETE,
            payload={"final_value": previous_value},
            reason="The demonstration sequence is complete.",
        )


class DemoMissingComponentStrategy:
    """Request an absent component to demonstrate controlled failure."""

    def decide(self, context: ExecutionContext) -> CoordinationDecision:
        return CoordinationDecision(
            action=CoordinationAction.EXECUTE,
            component_id=ComponentId("missing-demo-component"),
            reason="Demonstrate controlled lookup failure.",
        )


class DemoRepeatingStrategy:
    """Repeat a demo component to demonstrate the defensive step limit."""

    def decide(self, context: ExecutionContext) -> CoordinationDecision:
        return CoordinationDecision(
            action=CoordinationAction.EXECUTE,
            component_id=ComponentId("repeating-demo-component"),
            payload={"value": 1},
            reason="Demonstrate max_steps protection.",
        )


@dataclass(frozen=True, slots=True)
class DemoOutcome:
    """Data captured from one reproducible demonstration case."""

    result: OrchestrationResult
    trace_entries: tuple[TraceEntry, ...]
    executed_components: tuple[ComponentId, ...]
    steps: int


def run_success_case() -> DemoOutcome:
    first = DemoMultiplyComponent(ComponentId("demo-component-a"), factor=2)
    second = DemoMultiplyComponent(ComponentId("demo-component-b"), factor=2)
    registry = ComponentRegistry()
    registry.register(first)
    registry.register(second)
    orchestrator = Orchestrator(
        supervisor=Supervisor(DemoSequenceStrategy()),
        registry=registry,
    )

    result = orchestrator.run(
        OrchestrationRequest(
            payload={"value": 2},
            metadata={"case": "successful-flow"},
        )
    )
    return _capture_outcome(orchestrator, result, first, second)


def run_failure_case() -> DemoOutcome:
    orchestrator = Orchestrator(
        supervisor=Supervisor(DemoMissingComponentStrategy()),
        registry=ComponentRegistry(),
    )
    result = orchestrator.run(
        OrchestrationRequest(metadata={"case": "controlled-failure"})
    )
    return _capture_outcome(orchestrator, result)


def run_max_steps_case(max_steps: int = 3) -> DemoOutcome:
    component = DemoMultiplyComponent(
        ComponentId("repeating-demo-component"),
        factor=1,
    )
    registry = ComponentRegistry()
    registry.register(component)
    orchestrator = Orchestrator(
        supervisor=Supervisor(DemoRepeatingStrategy()),
        registry=registry,
        max_steps=max_steps,
    )
    result = orchestrator.run(
        OrchestrationRequest(metadata={"case": "max-steps"})
    )
    return _capture_outcome(orchestrator, result, component)


def main() -> None:
    print("=" * 48)
    print("PROVISIONAL ORCHESTRATION DEMO")
    print("=" * 48)
    print("Coordination strategy: Demo only")
    print("Architecture selected: NO")
    print("Demo strategy is not the final architecture.")

    success = run_success_case()
    print("\nCASE 1 - Successful flow")
    print(f"Execution ID: {success.result.execution_id}")
    print(f"Initial status: {ExecutionStatus.PENDING.name}")
    print("Components: demo-component-a, demo-component-b")
    print(f"Final value: {success.result.output['final_value']}")
    print(f"Final status: {success.result.status.name}")
    print(f"Steps: {success.steps}")
    _print_trace(success.trace_entries)

    failure = run_failure_case()
    print("\nCASE 2 - Controlled failure")
    print("Cause: missing-demo-component is not registered")
    print(f"Final status: {failure.result.status.name}")
    print(f"Reason: {failure.result.error}")
    _print_trace(failure.trace_entries)

    limited = run_max_steps_case(max_steps=3)
    print("\nCASE 3 - Max steps protection")
    print("Configured max steps: 3")
    print(f"Executed steps: {limited.steps}")
    print(f"Final status: {limited.result.status.name}")
    print(f"Reason: {limited.result.error}")
    _print_trace(limited.trace_entries)


def _latest_value(context: ExecutionContext) -> int:
    outputs = context.shared_data.get("component_outputs", [])
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("the demo requires a previous component output")
    latest = outputs[-1]
    return int(latest["output"]["value"])


def _capture_outcome(
    orchestrator: Orchestrator,
    result: OrchestrationResult,
    *components: DemoMultiplyComponent,
) -> DemoOutcome:
    context = orchestrator.context
    if context is None:
        raise RuntimeError("the demonstration did not create a context")
    executed = tuple(
        component.component_id
        for component in components
        for _ in component.calls
    )
    return DemoOutcome(
        result=result,
        trace_entries=context.trace.entries,
        executed_components=executed,
        steps=len(executed),
    )


def _print_trace(entries: tuple[TraceEntry, ...]) -> None:
    print("Trace:")
    for entry in entries:
        component = f" [{entry.component_id}]" if entry.component_id else ""
        print(f"{entry.sequence}. {entry.event_type.name}{component}")


if __name__ == "__main__":
    main()
