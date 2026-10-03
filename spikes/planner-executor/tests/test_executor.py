"""Tests for controlled request execution and error handling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.executor import Executor
from src.tools import TOOL_REGISTRY

DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def consistent_frame() -> pd.DataFrame:
    return pd.read_csv(DATA_DIRECTORY / "consistent_relation.csv")


@pytest.fixture(scope="module")
def confounded_frame() -> pd.DataFrame:
    return pd.read_csv(DATA_DIRECTORY / "confounded_relation.csv")


@pytest.fixture
def executor() -> Executor:
    return Executor()


def _request(tool: str, **parameters: Any) -> dict[str, Any]:
    return {"tool": tool, "parameters": parameters}


def test_executor_profiles_dataset(
    executor: Executor,
    consistent_frame: pd.DataFrame,
) -> None:
    response = executor.execute(consistent_frame, _request("profile_dataset"))

    assert response["status"] == "success"
    assert response["result"]["row_count"] == 500
    assert response["error"] is None


def test_executor_calculates_pearson(
    executor: Executor,
    consistent_frame: pd.DataFrame,
) -> None:
    response = executor.execute(
        consistent_frame,
        _request("pearson_correlation", x="X", y="Y"),
    )

    assert response["status"] == "success"
    assert response["result"]["coefficient"] == pytest.approx(0.9038, abs=0.01)


def test_executor_calculates_partial_correlation(
    executor: Executor,
    confounded_frame: pd.DataFrame,
) -> None:
    response = executor.execute(
        confounded_frame,
        _request("partial_correlation", x="X", y="Y", control="Z"),
    )

    assert response["status"] == "success"
    assert abs(response["result"]["coefficient"]) < 0.10


def test_executor_rejects_unknown_tool(
    executor: Executor,
    consistent_frame: pd.DataFrame,
) -> None:
    response = executor.execute(consistent_frame, _request("unsupported_tool"))

    assert response["status"] == "error"
    assert response["error"]["code"] == "UNKNOWN_TOOL"


def test_executor_rejects_missing_parameters(
    executor: Executor,
    consistent_frame: pd.DataFrame,
) -> None:
    response = executor.execute(
        consistent_frame,
        _request("pearson_correlation", x="X"),
    )

    assert response["status"] == "error"
    assert response["error"]["code"] == "INVALID_PARAMETERS"


def test_executor_reports_missing_column(
    executor: Executor,
    consistent_frame: pd.DataFrame,
) -> None:
    response = executor.execute(
        consistent_frame,
        _request("pearson_correlation", x="X", y="unknown"),
    )

    assert response["status"] == "error"
    assert response["error"]["code"] == "COLUMN_NOT_FOUND"


def test_executor_reports_non_numeric_column(executor: Executor) -> None:
    frame = pd.DataFrame({"X": [1, 2, 3], "label": ["a", "b", "c"]})
    response = executor.execute(
        frame,
        _request("pearson_correlation", x="X", y="label"),
    )

    assert response["status"] == "error"
    assert response["error"]["code"] == "NON_NUMERIC_COLUMN"


def test_executor_contains_internal_error(
    executor: Executor,
    consistent_frame: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_tool(frame: pd.DataFrame) -> dict[str, Any]:
        raise RuntimeError("internal diagnostic must not escape")

    monkeypatch.setitem(TOOL_REGISTRY, "profile_dataset", failing_tool)
    response = executor.execute(consistent_frame, _request("profile_dataset"))

    assert response["status"] == "error"
    assert response["error"] == {
        "code": "EXECUTION_ERROR",
        "message": "Tool 'profile_dataset' could not be executed.",
    }


def test_executor_blocks_arbitrary_execution_attempt(
    executor: Executor,
    consistent_frame: pd.DataFrame,
) -> None:
    malicious_name = "__import__('os').system('echo unsafe')"
    response = executor.execute(consistent_frame, _request(malicious_name))

    assert response["status"] == "error"
    assert response["error"]["code"] == "UNKNOWN_TOOL"


def test_executor_response_is_json_serializable(
    executor: Executor,
    consistent_frame: pd.DataFrame,
) -> None:
    response = executor.execute(
        consistent_frame,
        _request("pearson_correlation", x="X", y="Y"),
    )

    serialized = json.dumps(response)
    assert json.loads(serialized) == response
