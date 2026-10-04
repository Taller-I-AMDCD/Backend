import pandas as pd
import pytest

from src.critic import evaluate_result


def sample_dataset():
    return pd.DataFrame({
        "X": [1, 2, 3, 4, 5],
        "Y": [2, 4, 6, 8, 10],
        "Z": [1, 1, 2, 2, 3],
    })


def test_detect_possible_confounder():
    df = sample_dataset()

    result = {
        "tool": "pearson_correlation",
        "x": "X",
        "y": "Y",
        "coefficient": 0.83,
    }

    decision = evaluate_result(result, df)

    assert decision["agent"] == "Critic"
    assert decision["decision"] == "REQUEST_MORE_EVIDENCE"
    assert decision["next_action"] == "partial_correlation"
    assert decision["parameters"]["control"] == "Z"


def test_request_outlier_analysis():
    df = pd.DataFrame({
        "X": [1, 2, 3, 4, 5],
        "Y": [2, 4, 6, 8, 10],
    })

    result = {
        "tool": "pearson_correlation",
        "x": "X",
        "y": "Y",
        "coefficient": 0.90,
    }

    decision = evaluate_result(result, df)

    assert decision["decision"] == "REQUEST_MORE_EVIDENCE"
    assert decision["next_action"] == "correlation_without_outliers"


def test_accept_partial_correlation():
    df = sample_dataset()

    result = {
        "tool": "partial_correlation",
        "coefficient": 0.85,
    }

    decision = evaluate_result(result, df)

    assert decision["decision"] == "ACCEPT"


def test_reject_spurious_partial_correlation():
    df = sample_dataset()

    result = {
        "tool": "partial_correlation",
        "coefficient": 0.08,
    }

    decision = evaluate_result(result, df)

    assert decision["decision"] == "REJECT_SPURIOUS"


def test_reject_spurious_outliers():
    df = sample_dataset()

    result = {
        "tool": "correlation_without_outliers",
        "original_correlation": 0.90,
        "filtered_correlation": 0.20,
    }

    decision = evaluate_result(result, df)

    assert decision["decision"] == "REJECT_SPURIOUS"


def test_accept_after_outlier_filter():
    df = sample_dataset()

    result = {
        "tool": "correlation_without_outliers",
        "original_correlation": 0.90,
        "filtered_correlation": 0.85,
    }

    decision = evaluate_result(result, df)

    assert decision["decision"] == "ACCEPT"


def test_reject_invalid_result():
    df = sample_dataset()

    with pytest.raises(ValueError, match="INVALID_RESULT"):
        evaluate_result({}, df)


def test_reject_unknown_tool():
    df = sample_dataset()

    result = {
        "tool": "unsupported_tool",
    }

    with pytest.raises(ValueError, match="UNKNOWN_RESULT_TOOL"):
        evaluate_result(result, df)