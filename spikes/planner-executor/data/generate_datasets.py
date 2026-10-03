"""Generate reproducible datasets for the Planner–Executor evaluation spike."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
OBSERVATION_COUNT = 500
OUTLIER_FRACTION = 0.05
DATA_DIRECTORY = Path(__file__).resolve().parent
MANIFEST_FILENAME = "scenario_manifest.json"

DATASET_FILENAMES = {
    "consistent_relation": "consistent_relation.csv",
    "confounded_relation": "confounded_relation.csv",
    "outlier_relation": "outlier_relation.csv",
}


def generate_consistent_relation() -> pd.DataFrame:
    """Create a stable positive association with moderate random noise."""
    rng = np.random.default_rng(SEED)
    x = rng.normal(loc=0.0, scale=1.5, size=OBSERVATION_COUNT)
    noise = rng.normal(loc=0.0, scale=1.2, size=OBSERVATION_COUNT)
    y = 1.8 * x + noise
    return pd.DataFrame({"X": x, "Y": y})


def generate_confounded_relation() -> pd.DataFrame:
    """Create an association between X and Y explained primarily by Z."""
    rng = np.random.default_rng(SEED + 1)
    z = rng.normal(loc=0.0, scale=1.0, size=OBSERVATION_COUNT)
    x = 1.8 * z + rng.normal(loc=0.0, scale=0.8, size=OBSERVATION_COUNT)
    y = 2.0 * z + rng.normal(loc=0.0, scale=0.9, size=OBSERVATION_COUNT)
    return pd.DataFrame({"X": x, "Y": y, "Z": z})


def generate_outlier_relation() -> pd.DataFrame:
    """Create a weak baseline association altered by a small extreme subset."""
    rng = np.random.default_rng(SEED + 2)
    outlier_count = round(OBSERVATION_COUNT * OUTLIER_FRACTION)
    baseline_count = OBSERVATION_COUNT - outlier_count

    baseline_x = rng.normal(loc=0.0, scale=1.0, size=baseline_count)
    baseline_y = (
        0.25 * baseline_x
        + rng.normal(loc=0.0, scale=1.1, size=baseline_count)
    )

    extreme_x = rng.uniform(low=7.0, high=10.0, size=outlier_count)
    extreme_y = 4.0 * extreme_x + rng.normal(
        loc=0.0,
        scale=1.5,
        size=outlier_count,
    )

    frame = pd.DataFrame(
        {
            "X": np.concatenate((baseline_x, extreme_x)),
            "Y": np.concatenate((baseline_y, extreme_y)),
        }
    )
    return frame.iloc[rng.permutation(OBSERVATION_COUNT)].reset_index(drop=True)


def residual_correlation(frame: pd.DataFrame) -> float:
    """Calculate X–Y correlation after linear residualization against Z."""
    design = np.column_stack((np.ones(len(frame)), frame["Z"].to_numpy()))
    x = frame["X"].to_numpy()
    y = frame["Y"].to_numpy()

    x_coefficients, *_ = np.linalg.lstsq(design, x, rcond=None)
    y_coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    x_residuals = x - design @ x_coefficients
    y_residuals = y - design @ y_coefficients
    return float(np.corrcoef(x_residuals, y_residuals)[0, 1])


def non_extreme_mask(frame: pd.DataFrame) -> pd.Series:
    """Identify observations within 1.5 interquartile ranges for X and Y."""
    variables = frame[["X", "Y"]]
    first_quartile = variables.quantile(0.25)
    third_quartile = variables.quantile(0.75)
    interquartile_range = third_quartile - first_quartile
    lower_bounds = first_quartile - 1.5 * interquartile_range
    upper_bounds = third_quartile + 1.5 * interquartile_range
    return ((variables >= lower_bounds) & (variables <= upper_bounds)).all(axis=1)


def build_manifest() -> dict[str, object]:
    """Describe the purpose and expected qualitative behavior of each scenario."""
    return {
        "seed": SEED,
        "scenarios": [
            {
                "id": "consistent_relation",
                "name": "Consistent relation",
                "file": DATASET_FILENAMES["consistent_relation"],
                "records": OBSERVATION_COUNT,
                "variables": ["X", "Y"],
                "purpose": "Evaluate the stability of a direct association.",
                "expected_behavior": (
                    "X and Y exhibit a clear positive association that remains "
                    "stable across the sample."
                ),
            },
            {
                "id": "confounded_relation",
                "name": "Confounded relation",
                "file": DATASET_FILENAMES["confounded_relation"],
                "records": OBSERVATION_COUNT,
                "variables": ["X", "Y", "Z"],
                "purpose": "Evaluate an association explained primarily by a confounder.",
                "expected_behavior": (
                    "The apparent X–Y association decreases substantially after "
                    "controlling for Z."
                ),
            },
            {
                "id": "outlier_relation",
                "name": "Outlier-sensitive relation",
                "file": DATASET_FILENAMES["outlier_relation"],
                "records": OBSERVATION_COUNT,
                "variables": ["X", "Y"],
                "purpose": "Evaluate sensitivity of an association to extreme values.",
                "expected_behavior": (
                    "A small extreme subset materially changes the global X–Y "
                    "association."
                ),
            },
        ],
    }


def generate_all_datasets(
    output_directory: Path = DATA_DIRECTORY,
) -> dict[str, pd.DataFrame]:
    """Generate every scenario and persist it with a descriptive manifest."""
    output_directory.mkdir(parents=True, exist_ok=True)
    datasets = {
        "consistent_relation": generate_consistent_relation(),
        "confounded_relation": generate_confounded_relation(),
        "outlier_relation": generate_outlier_relation(),
    }

    for scenario_id, frame in datasets.items():
        output_path = output_directory / DATASET_FILENAMES[scenario_id]
        frame.to_csv(output_path, index=False, float_format="%.10f")

    manifest_path = output_directory / MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(build_manifest(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return datasets


def print_summary(datasets: dict[str, pd.DataFrame]) -> None:
    """Print calculated statistics for a generated dataset collection."""
    consistent = datasets["consistent_relation"]
    confounded = datasets["confounded_relation"]
    outlier = datasets["outlier_relation"]
    retained = outlier.loc[non_extreme_mask(outlier)]

    print("Synthetic evaluation datasets generated successfully.")
    print()
    _print_scenario_header("consistent_relation", consistent)
    print(f"Pearson X-Y: {consistent['X'].corr(consistent['Y']):.4f}")
    print()
    _print_scenario_header("confounded_relation", confounded)
    print(f"Pearson X-Y: {confounded['X'].corr(confounded['Y']):.4f}")
    print(f"Correlation after controlling Z: {residual_correlation(confounded):.4f}")
    print()
    _print_scenario_header("outlier_relation", outlier)
    print(f"Pearson with all observations: {outlier['X'].corr(outlier['Y']):.4f}")
    print(f"Pearson without detected extremes: {retained['X'].corr(retained['Y']):.4f}")
    print(f"Detected extremes: {len(outlier) - len(retained)}")


def _print_scenario_header(scenario_id: str, frame: pd.DataFrame) -> None:
    print(f"Scenario: {scenario_id}")
    print(f"Rows: {len(frame)}")
    print(f"Columns: {', '.join(frame.columns)}")


if __name__ == "__main__":
    generated_datasets = generate_all_datasets()
    print_summary(generated_datasets)
