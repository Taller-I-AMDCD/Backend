from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
OBSERVATIONS = 500

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR


def generate_consistent_relation(rng):
    """Genera una relación estable entre X e Y."""
    x = rng.normal(0, 1, OBSERVATIONS)
    y = 2.2 * x + rng.normal(0, 0.8, OBSERVATIONS)

    return pd.DataFrame({
        "X": x,
        "Y": y
    })


def generate_confounded_relation(rng):
    """Genera una asociación X-Y explicada principalmente por Z."""
    z = rng.normal(0, 1, OBSERVATIONS)
    x = z + rng.normal(0, 0.6, OBSERVATIONS)
    y = 2.0 * z + rng.normal(0, 1.0, OBSERVATIONS)

    return pd.DataFrame({
        "X": x,
        "Y": y,
        "Z": z
    })


def generate_outlier_relation(rng):
    """Genera una relación aparente causada por valores atípicos."""
    x = rng.normal(0, 1, OBSERVATIONS)
    y = rng.normal(0, 1, OBSERVATIONS)

    outlier_indices = rng.choice(
        OBSERVATIONS,
        size=29,
        replace=False
    )

    x[outlier_indices] = rng.normal(10, 1, size=29)
    y[outlier_indices] = (
        x[outlier_indices] + rng.normal(0, 0.5, size=29)
    )

    return pd.DataFrame({
        "X": x,
        "Y": y
    })


def main():
    rng = np.random.default_rng(SEED)

    datasets = {
        "consistent_relation": generate_consistent_relation(rng),
        "confounded_relation": generate_confounded_relation(rng),
        "outlier_relation": generate_outlier_relation(rng),
    }

    for name, dataset in datasets.items():
        output_path = DATA_DIR / f"{name}.csv"
        dataset.to_csv(output_path, index=False)

        print(f"Escenario: {name}")
        print(f"Filas: {len(dataset)}")
        print(f"Columnas: {', '.join(dataset.columns)}")
        print(f"Archivo: {output_path.name}")
        print("-" * 40)


if __name__ == "__main__":
    main()