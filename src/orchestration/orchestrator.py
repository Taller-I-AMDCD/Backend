"""Provisional entry point for strategy-neutral orchestration."""

from __future__ import annotations

from uuid import uuid4

from .contracts import (
    ComponentRequest,
    ComponentStatus,
    ExecutionId,
    ExecutionStatus,
    OrchestrationRequest,
    OrchestrationResult,
)
from .context import ExecutionContext
from .exceptions import ComponentNotFoundError, MaxStepsExceededError
from .registry import ComponentRegistry
from .state import ExecutionState
from .strategy import CoordinationAction, CoordinationDecision
from .supervisor import Supervisor
from .trace import ExecutionTrace, TraceEventType


class Orchestrator:
    """Run bounded executions while keeping coordination replaceable."""

    def __init__(
        self,
        supervisor: Supervisor | None = None,
        registry: ComponentRegistry | None = None,
        max_steps: int = 20,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be greater than zero")
        self._supervisor = supervisor or Supervisor()
        self._registry = registry or ComponentRegistry()
        self._max_steps = max_steps
        self._context: ExecutionContext | None = None

    @property
    def context(self) -> ExecutionContext | None:
        """Return the most recently initialized execution context."""

        return self._context

    @property
    def state(self) -> ExecutionState | None:
        """Return the most recently initialized execution state."""

        return self._context.state if self._context is not None else None

    def initialize(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Create a pending execution without routing or running components."""

        execution_id = request.execution_id or ExecutionId(str(uuid4()))
        trace = ExecutionTrace(execution_id)
        trace.record(
            TraceEventType.EXECUTION_STARTED,
            metadata=request.metadata,
        )
        state = ExecutionState(
            execution_id=execution_id,
            metadata=dict(request.metadata),
        )
        contextualized_state = self._supervisor.contextualize(state)
        self._context = ExecutionContext(
            request=request,
            state=contextualized_state,
            trace=trace,
        )

        return OrchestrationResult(
            execution_id=self._context.state.execution_id,
            status=self._context.state.status,
            metadata=self._context.state.metadata,
        )

    def run(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Run a bounded flow whose decisions come only from the strategy."""

        self.initialize(request)
        context = self._require_context()
        self._transition(context, ExecutionStatus.RUNNING)
        completed_steps = 0

        while True:
            decision = self._supervisor.decide(context)
            if decision.action is CoordinationAction.COMPLETE:
                return self._complete(context, decision)
            if decision.action is CoordinationAction.FAIL:
                return self._fail(
                    context,
                    decision.reason or "coordination strategy requested failure",
                )
            if completed_steps >= self._max_steps:
                error = MaxStepsExceededError(
                    f"maximum component steps exceeded: {self._max_steps}"
                )
                return self._fail(context, str(error))

            result = self._execute_component(context, decision)
            if result is not None:
                return result
            completed_steps += 1
            context.state.set_current_step(str(completed_steps))

    def _execute_component(
        self,
        context: ExecutionContext,
        decision: CoordinationDecision,
    ) -> OrchestrationResult | None:
        component_id = decision.component_id
        if component_id is None:
            return self._fail(context, "execute decision has no component_id")

        try:
            component = self._registry.get(component_id)
        except ComponentNotFoundError as error:
            return self._fail(context, str(error))

        context.trace.record(
            TraceEventType.COMPONENT_SELECTED,
            component_id=component_id,
            message=decision.reason,
            metadata=decision.metadata,
        )
        component_request = ComponentRequest(
            execution_id=context.state.execution_id,
            component_id=component_id,
            payload=decision.payload,
            metadata=decision.metadata,
        )
        context.trace.record(
            TraceEventType.COMPONENT_STARTED,
            component_id=component_id,
        )

        try:
            component_result = component.handle(component_request)
        except Exception as error:
            message = (
                f"component {component_id} raised "
                f"{type(error).__name__}: {error}"
            )
            context.trace.record(
                TraceEventType.COMPONENT_FAILED,
                component_id=component_id,
                message=message,
            )
            return self._fail(context, message)

        if component_result.status is ComponentStatus.FAILURE:
            message = component_result.error or (
                f"component {component_id} reported failure"
            )
            context.trace.record(
                TraceEventType.COMPONENT_FAILED,
                component_id=component_id,
                message=message,
                metadata=component_result.metadata,
            )
            return self._fail(context, message)

        outputs = context.shared_data.setdefault("component_outputs", [])
        if not isinstance(outputs, list):
            return self._fail(context, "component_outputs storage is invalid")
        outputs.append(
            {
                "component_id": component_id,
                "output": dict(component_result.output),
                "metadata": dict(component_result.metadata),
            }
        )
        context.trace.record(
            TraceEventType.COMPONENT_COMPLETED,
            component_id=component_id,
            metadata=component_result.metadata,
        )
        return None

    def _complete(
        self,
        context: ExecutionContext,
        decision: CoordinationDecision,
    ) -> OrchestrationResult:
        self._transition(context, ExecutionStatus.COMPLETED)
        context.trace.record(
            TraceEventType.EXECUTION_COMPLETED,
            message=decision.reason,
            metadata=decision.metadata,
        )
        output = dict(context.shared_data)
        output.update(decision.payload)
        return OrchestrationResult(
            execution_id=context.state.execution_id,
            status=context.state.status,
            output=output,
            metadata=context.state.metadata,
        )

    def _fail(
        self,
        context: ExecutionContext,
        message: str,
    ) -> OrchestrationResult:
        self._transition(context, ExecutionStatus.FAILED)
        context.trace.record(
            TraceEventType.EXECUTION_FAILED,
            message=message,
        )
        return OrchestrationResult(
            execution_id=context.state.execution_id,
            status=context.state.status,
            output=context.shared_data,
            metadata=context.state.metadata,
            error=message,
        )

    @staticmethod
    def _transition(
        context: ExecutionContext,
        status: ExecutionStatus,
    ) -> None:
        previous = context.state.status
        context.state.transition_to(status)
        context.trace.record(
            TraceEventType.STATE_CHANGED,
            metadata={"from": previous.value, "to": status.value},
        )

    def _require_context(self) -> ExecutionContext:
        if self._context is None:
            raise RuntimeError("execution context has not been initialized")
        return self._context
