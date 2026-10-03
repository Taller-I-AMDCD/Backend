"""Validation tests for the reproducible synthetic evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from data.generate_datasets import (
    DATASET_FILENAMES,
    MANIFEST_FILENAME,
    OBSERVATION_COUNT,
    generate_all_datasets,
    non_extreme_mask,
    residual_correlation,
)

EXPECTED_COLUMNS = {
    "consistent_relation": ["X", "Y"],
    "confounded_relation": ["X", "Y", "Z"],
    "outlier_relation": ["X", "Y"],
}


@pytest.fixture
def generated_datasets(tmp_path: Path) -> dict[str, pd.DataFrame]:
    return generate_all_datasets(tmp_path)


def test_generator_creates_expected_files(tmp_path: Path) -> None:
    generate_all_datasets(tmp_path)

    expected_files = set(DATASET_FILENAMES.values()) | {MANIFEST_FILENAME}
    actual_files = {path.name for path in tmp_path.iterdir() if path.is_file()}
    assert actual_files == expected_files


@pytest.mark.parametrize("scenario_id", EXPECTED_COLUMNS)
def test_dataset_shape_columns_and_missing_values(
    generated_datasets: dict[str, pd.DataFrame],
    scenario_id: str,
) -> None:
    frame = generated_datasets[scenario_id]

    assert len(frame) == OBSERVATION_COUNT
    assert frame.columns.tolist() == EXPECTED_COLUMNS[scenario_id]
    assert not frame.isna().any().any()


def test_generation_is_reproducible(tmp_path: Path) -> None:
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    first_datasets = generate_all_datasets(first_output)
    second_datasets = generate_all_datasets(second_output)

    for scenario_id in EXPECTED_COLUMNS:
        assert_frame_equal(first_datasets[scenario_id], second_datasets[scenario_id])
        first_csv = first_output / DATASET_FILENAMES[scenario_id]
        second_csv = second_output / DATASET_FILENAMES[scenario_id]
        assert first_csv.read_bytes() == second_csv.read_bytes()

    assert (first_output / MANIFEST_FILENAME).read_bytes() == (
        second_output / MANIFEST_FILENAME
    ).read_bytes()


def test_manifest_describes_all_scenarios(tmp_path: Path) -> None:
    generate_all_datasets(tmp_path)
    manifest = json.loads((tmp_path / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    scenarios = manifest["scenarios"]

    assert {scenario["id"] for scenario in scenarios} == set(EXPECTED_COLUMNS)
    for scenario in scenarios:
        assert scenario["records"] == OBSERVATION_COUNT
        assert scenario["variables"] == EXPECTED_COLUMNS[scenario["id"]]
        assert scenario["purpose"]
        assert scenario["expected_behavior"]


def test_consistent_relation_has_clear_non_perfect_association(
    generated_datasets: dict[str, pd.DataFrame],
) -> None:
    frame = generated_datasets["consistent_relation"]
    correlation = frame["X"].corr(frame["Y"])

    assert 0.75 < correlation < 0.98


def test_confounding_explains_most_of_apparent_association(
    generated_datasets: dict[str, pd.DataFrame],
) -> None:
    frame = generated_datasets["confounded_relation"]
    simple_correlation = abs(frame["X"].corr(frame["Y"]))
    controlled_correlation = abs(residual_correlation(frame))

    assert simple_correlation > 0.70
    assert controlled_correlation < 0.20
    assert controlled_correlation < simple_correlation * 0.30


def test_outliers_materially_change_global_correlation(
    generated_datasets: dict[str, pd.DataFrame],
) -> None:
    frame = generated_datasets["outlier_relation"]
    retained = frame.loc[non_extreme_mask(frame)]
    global_correlation = frame["X"].corr(frame["Y"])
    retained_correlation = retained["X"].corr(retained["Y"])
    detected_fraction = 1 - len(retained) / len(frame)

    assert abs(global_correlation - retained_correlation) > 0.40
    assert len(retained) > OBSERVATION_COUNT * 0.85
    assert 0.02 < detected_fraction < 0.15
