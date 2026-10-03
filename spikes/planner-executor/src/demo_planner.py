"""Terminal demonstration of isolated rule-based Planner decisions."""

from __future__ import annotations

from typing import Any, Mapping

from .planner import Planner, PlannerDecision, ResearchState


def _history(tool: str, **parameters: Any) -> Mapping[str, Any]:
    return {"tool": tool, "parameters": parameters}


def _result(
    tool: str,
    result: Mapping[str, Any],
    **parameters: Any,
) -> Mapping[str, Any]:
    return {
        "status": "success",
        "tool": tool,
        "parameters": parameters,
        "result": result,
    }


def _print_decision(label: str, decision: PlannerDecision) -> None:
    if label:
        print(label)
    print("Decision:")
    if decision["status"] == "stop":
        print("STOP")
        print(f"Reason: {decision['reason']}")
        print()
        return

    print(f"Tool: {decision['tool']}")
    if decision["parameters"]:
        rendered = ", ".join(
            f"{key}={value}" for key, value in decision["parameters"].items()
        )
        print(f"Parameters: {rendered}")
    print(f"Reason: {decision['reason']}")
    print()


def main() -> None:
    planner = Planner()
    objective = "Evaluate the association between X and Y."
    pearson_parameters = {"x": "X", "y": "Y"}

    states = [
        (
            "State 1: No metadata",
            ResearchState(
                objective=objective,
                iteration=0,
                columns=[],
                numeric_columns=[],
                target_variables=("X", "Y"),
            ),
        ),
        (
            "State 2: Metadata available",
            ResearchState(
                objective=objective,
                iteration=0,
                columns=["X", "Y"],
                numeric_columns=["X", "Y"],
                target_variables=("X", "Y"),
            ),
        ),
        (
            "State 3: Strong Pearson + candidate confounder",
            ResearchState(
                objective=objective,
                iteration=1,
                columns=["X", "Y", "candidate_control"],
                numeric_columns=["X", "Y", "candidate_control"],
                history=[_history("pearson_correlation", **pearson_parameters)],
                results=[
                    _result(
                        "pearson_correlation",
                        {"coefficient": 0.83, "sample_size": 500},
                        **pearson_parameters,
                    )
                ],
                target_variables=("X", "Y"),
            ),
        ),
        (
            "State 4: Pearson analyzed, no confounder",
            ResearchState(
                objective=objective,
                iteration=1,
                columns=["X", "Y"],
                numeric_columns=["X", "Y"],
                history=[_history("pearson_correlation", **pearson_parameters)],
                results=[
                    _result(
                        "pearson_correlation",
                        {"coefficient": 0.90, "sample_size": 500},
                        **pearson_parameters,
                    )
                ],
                target_variables=("X", "Y"),
            ),
        ),
        (
            "State 5: All relevant analyses completed",
            ResearchState(
                objective=objective,
                iteration=3,
                columns=["X", "Y"],
                numeric_columns=["X", "Y"],
                history=[
                    _history("pearson_correlation", **pearson_parameters),
                    _history("correlation_without_outliers", **pearson_parameters),
                    _history("spearman_correlation", **pearson_parameters),
                ],
                results=[
                    _result(
                        "pearson_correlation",
                        {"coefficient": 0.90, "sample_size": 500},
                        **pearson_parameters,
                    )
                ],
                target_variables=("X", "Y"),
            ),
        ),
    ]

    print("=" * 40)
    print("PLANNER DEMO")
    print("=" * 40)
    for label, state in states:
        print(label)
        if label.startswith("State 3"):
            print("Previous result: 0.83")
        _print_decision("", planner.plan(state))


if __name__ == "__main__":
    main()
