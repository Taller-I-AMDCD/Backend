"""Tests for the controlled analytical tool catalog."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.tools import (
    ToolError,
    analyze_subgroups,
    correlation_without_outliers,
    detect_outliers,
    partial_correlation,
    pearson_correlation,
    profile_dataset,
    spearman_correlation,
)

DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def consistent_frame() -> pd.DataFrame:
    return pd.read_csv(DATA_DIRECTORY / "consistent_relation.csv")


@pytest.fixture(scope="module")
def confounded_frame() -> pd.DataFrame:
    return pd.read_csv(DATA_DIRECTORY / "confounded_relation.csv")


@pytest.fixture(scope="module")
def outlier_frame() -> pd.DataFrame:
    return pd.read_csv(DATA_DIRECTORY / "outlier_relation.csv")


def test_profile_dataset_returns_expected_metadata() -> None:
    frame = pd.DataFrame(
        {
            "value": [1.0, 2.0, 2.0, None],
            "category": ["a", "b", "b", "c"],
        }
    )

    result = profile_dataset(frame)

    assert result["row_count"] == 4
    assert result["column_count"] == 2
    assert result["columns"] == ["value", "category"]
    assert result["numeric_columns"] == ["value"]
    assert result["missing_values"] == {"value": 1, "category": 0}
    assert result["duplicate_rows"] == 1
    assert result["numeric_summary"]["value"]["count"] == 3


def test_pearson_correlation_matches_consistent_scenario(
    consistent_frame: pd.DataFrame,
) -> None:
    result = pearson_correlation(consistent_frame, "X", "Y")

    assert result["sample_size"] == 500
    assert result["coefficient"] == pytest.approx(0.9038, abs=0.01)


def test_spearman_correlation_returns_valid_result(
    consistent_frame: pd.DataFrame,
) -> None:
    result = spearman_correlation(consistent_frame, "X", "Y")

    assert result["sample_size"] == 500
    assert 0.80 < result["coefficient"] < 1.0


def test_partial_correlation_removes_confounder_effect(
    confounded_frame: pd.DataFrame,
) -> None:
    simple = pearson_correlation(confounded_frame, "X", "Y")
    partial = partial_correlation(confounded_frame, "X", "Y", "Z")

    assert simple["coefficient"] > 0.80
    assert abs(partial["coefficient"]) < 0.10
    assert abs(partial["coefficient"]) < abs(simple["coefficient"]) * 0.20


def test_detect_outliers_identifies_extremes(outlier_frame: pd.DataFrame) -> None:
    result = detect_outliers(outlier_frame, "X")

    assert result["method"] == "IQR"
    assert result["multiplier"] == 1.5
    assert 10 < result["count"] < 50
    assert len(result["indices"]) == result["count"]


def test_correlation_without_outliers_reduces_association(
    outlier_frame: pd.DataFrame,
) -> None:
    result = correlation_without_outliers(outlier_frame, "X", "Y")

    assert result["original_correlation"] == pytest.approx(0.8881, abs=0.01)
    assert result["filtered_correlation"] == pytest.approx(0.2801, abs=0.02)
    assert result["removed_count"] == 29
    assert result["filtered_sample_size"] == 471


def test_analyze_subgroups_calculates_each_group() -> None:
    frame = pd.DataFrame(
        {
            "X": [1, 2, 3, 4, 1, 2, 3, 4],
            "Y": [2, 4, 6, 8, 8, 6, 4, 2],
            "segment": ["A"] * 4 + ["B"] * 4,
        }
    )

    result = analyze_subgroups(frame, "X", "Y", "segment")

    assert result["group_by"] == "segment"
    assert result["groups"] == [
        {"value": "A", "sample_size": 4, "correlation": pytest.approx(1.0)},
        {"value": "B", "sample_size": 4, "correlation": pytest.approx(-1.0)},
    ]


def test_missing_column_is_rejected(consistent_frame: pd.DataFrame) -> None:
    with pytest.raises(ToolError) as error:
        pearson_correlation(consistent_frame, "X", "unknown")

    assert error.value.code == "COLUMN_NOT_FOUND"


def test_non_numeric_column_is_rejected() -> None:
    frame = pd.DataFrame({"X": [1, 2, 3], "label": ["a", "b", "c"]})

    with pytest.raises(ToolError) as error:
        pearson_correlation(frame, "X", "label")

    assert error.value.code == "NON_NUMERIC_COLUMN"


def test_insufficient_data_is_rejected() -> None:
    frame = pd.DataFrame({"X": [1.0, 2.0], "Y": [2.0, 4.0]})

    with pytest.raises(ToolError) as error:
        pearson_correlation(frame, "X", "Y")

    assert error.value.code == "INSUFFICIENT_DATA"


def test_invalid_outlier_multiplier_is_rejected(outlier_frame: pd.DataFrame) -> None:
    with pytest.raises(ToolError) as error:
        detect_outliers(outlier_frame, "X", multiplier=0)

    assert error.value.code == "INVALID_PARAMETERS"
