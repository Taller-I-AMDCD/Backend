"""Reproducible demonstration of the neutral query execution infrastructure."""

from __future__ import annotations

from .contracts import (
    ExecutionId,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolId,
    ToolSpec,
)
from .dispatcher import ToolDispatcher
from .exceptions import InvalidParametersError
from .executor import QueryExecutor
from .registry import ToolRegistry
from .tool import Tool


class DemoDoubleTool:
    """Demo-only tool that doubles one numeric value."""

    def __init__(self) -> None:
        self._tool_id = ToolId("demo-double")
        self._spec = ToolSpec(
            tool_id=self._tool_id,
            name="Demo double",
            description="Doubles a numeric value for the HU-005 demonstration",
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
        value = request.parameters.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise InvalidParametersError("Parameter 'value' must be numeric")
        if request.execution_id is None:
            raise RuntimeError("execution_id is required")
        return ToolExecutionResult(
            execution_id=request.execution_id,
            tool_id=self.tool_id,
            status=ToolExecutionStatus.SUCCESS,
            output={"value": value * 2},
        )


class DemoInvalidParametersTool:
    """Demo-only tool that reports invalid request parameters."""

    def __init__(self) -> None:
        self._tool_id = ToolId("demo-invalid-parameters")
        self._spec = ToolSpec(
            tool_id=self._tool_id,
            name="Demo invalid parameters",
            description="Produces a controlled parameter error",
        )

    @property
    def tool_id(self) -> ToolId:
        return self._tool_id

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        raise InvalidParametersError("Demo parameters are invalid")


class DemoExplodingTool:
    """Demo-only tool that raises an unexpected execution error."""

    def __init__(self) -> None:
        self._tool_id = ToolId("demo-exploding")
        self._spec = ToolSpec(
            tool_id=self._tool_id,
            name="Demo exploding tool",
            description="Produces a controlled demonstration of an unexpected error",
        )

    @property
    def tool_id(self) -> ToolId:
        return self._tool_id

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        raise RuntimeError("Demo tool failure")


def _build_executor(*tools: Tool) -> QueryExecutor:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return QueryExecutor(ToolDispatcher(registry))


def _duration_ms(executor: QueryExecutor, execution_id: ExecutionId) -> float:
    terminal = executor.trace.for_execution(execution_id)[-1]
    return float(terminal.metadata["duration_ms"])


def _print_case(
    title: str,
    executor: QueryExecutor,
    request: ToolExecutionRequest,
) -> ToolExecutionResult:
    result = executor.execute(request)
    entries = executor.trace.for_execution(result.execution_id)
    print(f"\n{title}")
    print(f"Execution ID: {result.execution_id}")
    print(f"Requested tool: {result.tool_id}")
    print(f"Status: {result.status.value.upper()}")
    if result.status is ToolExecutionStatus.SUCCESS:
        print(f"Output: {result.output}")
    else:
        print(f"Error code: {result.error.code if result.error else 'UNKNOWN'}")
    print("Trace events: " + " -> ".join(entry.event_type.value for entry in entries))
    print(f"Duration ms: {_duration_ms(executor, result.execution_id):.6f}")
    return result


def run_demo() -> None:
    """Run five deterministic scenarios through the production infrastructure."""

    print("=" * 56)
    print("HU-005 QUERY EXECUTION DEMO")
    print("=" * 56)
    print("Architecture selected: NO")
    print("Tool selection responsibility: external")
    print("Analytical production tools: 0")

    successful_results = 0
    controlled_failures = 0

    success_tool = DemoDoubleTool()
    success_executor = _build_executor(success_tool)
    success = _print_case(
        "CASE 1 - Successful execution",
        success_executor,
        ToolExecutionRequest(
            execution_id=ExecutionId("demo-success"),
            tool_id=success_tool.tool_id,
            parameters={"value": 4},
        ),
    )
    successful_results += success.status is ToolExecutionStatus.SUCCESS

    unknown_executor = _build_executor()
    unknown = _print_case(
        "CASE 2 - Unknown tool",
        unknown_executor,
        ToolExecutionRequest(
            execution_id=ExecutionId("demo-unknown"),
            tool_id=ToolId("missing-tool"),
        ),
    )
    controlled_failures += unknown.status is ToolExecutionStatus.FAILURE

    invalid_tool = DemoInvalidParametersTool()
    invalid_executor = _build_executor(invalid_tool)
    invalid = _print_case(
        "CASE 3 - Invalid parameters",
        invalid_executor,
        ToolExecutionRequest(
            execution_id=ExecutionId("demo-invalid-parameters"),
            tool_id=invalid_tool.tool_id,
        ),
    )
    controlled_failures += invalid.status is ToolExecutionStatus.FAILURE

    exploding_tool = DemoExplodingTool()
    exploding_executor = _build_executor(exploding_tool)
    exploding = _print_case(
        "CASE 4 - Tool execution failure",
        exploding_executor,
        ToolExecutionRequest(
            execution_id=ExecutionId("demo-tool-failure"),
            tool_id=exploding_tool.tool_id,
        ),
    )
    controlled_failures += exploding.status is ToolExecutionStatus.FAILURE

    duplicate_tool = DemoDoubleTool()
    duplicate_executor = _build_executor(duplicate_tool)
    duplicate_request = ToolExecutionRequest(
        execution_id=ExecutionId("demo-duplicate"),
        tool_id=duplicate_tool.tool_id,
        parameters={"value": 4},
    )
    first = duplicate_executor.execute(duplicate_request)
    duplicate = _print_case(
        "CASE 5 - Duplicate execution protection",
        duplicate_executor,
        duplicate_request,
    )
    print(f"First attempt: {first.status.value.upper()}")
    print(f"Second attempt: {duplicate.status.value.upper()}")
    print(f"Tool execution count: {duplicate_tool.execution_count}")
    successful_results += first.status is ToolExecutionStatus.SUCCESS
    controlled_failures += duplicate.status is ToolExecutionStatus.FAILURE

    print("\n" + "=" * 56)
    print("DEMO SUMMARY")
    print("=" * 56)
    print(f"Success cases: {successful_results}")
    print(f"Controlled failure cases: {controlled_failures}")
    print("Unexpected traceback: NO")
    print("Architecture selected: NO")


if __name__ == "__main__":
    run_demo()
