"""Controlled analytical tools available to the Executor."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

MINIMUM_CORRELATION_SAMPLE = 3
DEFAULT_IQR_MULTIPLIER = 1.5


class ToolError(ValueError):
    """Represent a predictable validation failure raised by an analytical tool."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def profile_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    """Return JSON-compatible structural and numeric metadata for a dataset."""
    _require_dataframe(frame)
    numeric_columns = [
        column for column in frame.columns if is_numeric_dtype(frame[column])
    ]
    numeric_summary: dict[str, dict[str, float | int | None]] = {}

    for column in numeric_columns:
        series = frame[column].dropna()
        numeric_summary[str(column)] = {
            "count": int(series.count()),
            "mean": _optional_float(series.mean()),
            "std": _optional_float(series.std()),
            "min": _optional_float(series.min()),
            "25%": _optional_float(series.quantile(0.25)),
            "50%": _optional_float(series.quantile(0.50)),
            "75%": _optional_float(series.quantile(0.75)),
            "max": _optional_float(series.max()),
        }

    return {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": [str(column) for column in frame.columns],
        "numeric_columns": [str(column) for column in numeric_columns],
        "missing_values": {
            str(column): int(count) for column, count in frame.isna().sum().items()
        },
        "duplicate_rows": int(frame.duplicated().sum()),
        "numeric_summary": numeric_summary,
    }


def pearson_correlation(frame: pd.DataFrame, x: str, y: str) -> dict[str, Any]:
    """Calculate Pearson correlation for two numeric columns."""
    pairs = _valid_numeric_rows(frame, [x, y])
    coefficient = _pearson_coefficient(pairs[x], pairs[y])
    return {
        "x": x,
        "y": y,
        "coefficient": coefficient,
        "sample_size": int(len(pairs)),
    }


def spearman_correlation(frame: pd.DataFrame, x: str, y: str) -> dict[str, Any]:
    """Calculate Spearman rank correlation for two numeric columns."""
    pairs = _valid_numeric_rows(frame, [x, y])
    ranked_x = pairs[x].rank(method="average")
    ranked_y = pairs[y].rank(method="average")
    coefficient = _pearson_coefficient(ranked_x, ranked_y)
    return {
        "x": x,
        "y": y,
        "coefficient": coefficient,
        "sample_size": int(len(pairs)),
    }


def partial_correlation(
    frame: pd.DataFrame,
    x: str,
    y: str,
    control: str,
) -> dict[str, Any]:
    """Calculate X-Y correlation after residualizing both variables against one control."""
    observations = _valid_numeric_rows(frame, [x, y, control])
    if observations[control].nunique() < 2:
        raise ToolError(
            "INSUFFICIENT_DATA",
            f"Control column '{control}' must contain at least two distinct values.",
        )

    design = np.column_stack(
        (np.ones(len(observations)), observations[control].to_numpy(dtype=float))
    )
    x_values = observations[x].to_numpy(dtype=float)
    y_values = observations[y].to_numpy(dtype=float)
    x_coefficients, *_ = np.linalg.lstsq(design, x_values, rcond=None)
    y_coefficients, *_ = np.linalg.lstsq(design, y_values, rcond=None)
    x_residuals = x_values - design @ x_coefficients
    y_residuals = y_values - design @ y_coefficients
    coefficient = _pearson_coefficient(x_residuals, y_residuals)

    return {
        "x": x,
        "y": y,
        "control": control,
        "coefficient": coefficient,
        "sample_size": int(len(observations)),
    }


def detect_outliers(
    frame: pd.DataFrame,
    column: str,
    multiplier: float = DEFAULT_IQR_MULTIPLIER,
) -> dict[str, Any]:
    """Detect univariate outliers using the interquartile-range rule."""
    _require_dataframe(frame)
    _require_columns(frame, [column])
    _require_numeric_columns(frame, [column])
    if isinstance(multiplier, bool) or not isinstance(multiplier, (int, float)):
        raise ToolError("INVALID_PARAMETERS", "Multiplier must be a positive number.")
    if not np.isfinite(multiplier) or multiplier <= 0:
        raise ToolError("INVALID_PARAMETERS", "Multiplier must be a positive number.")

    values = frame[column].dropna()
    if len(values) < MINIMUM_CORRELATION_SAMPLE:
        raise ToolError(
            "INSUFFICIENT_DATA",
            f"Column '{column}' requires at least {MINIMUM_CORRELATION_SAMPLE} values.",
        )

    lower_bound, upper_bound = _iqr_bounds(values, float(multiplier))
    mask = (values < lower_bound) | (values > upper_bound)
    indices = [_json_scalar(index) for index in values.index[mask].tolist()]
    return {
        "column": column,
        "method": "IQR",
        "multiplier": float(multiplier),
        "count": len(indices),
        "indices": indices,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
    }


def correlation_without_outliers(
    frame: pd.DataFrame,
    x: str,
    y: str,
    multiplier: float = DEFAULT_IQR_MULTIPLIER,
) -> dict[str, Any]:
    """Compare Pearson correlation before and after bivariate IQR filtering."""
    pairs = _valid_numeric_rows(frame, [x, y])
    x_outliers = detect_outliers(pairs, x, multiplier)
    y_outliers = detect_outliers(pairs, y, multiplier)
    removed_indices = set(x_outliers["indices"]) | set(y_outliers["indices"])
    filtered = pairs.loc[~pairs.index.isin(removed_indices)]

    original_correlation = _pearson_coefficient(pairs[x], pairs[y])
    filtered_correlation = _pearson_coefficient(filtered[x], filtered[y])
    return {
        "x": x,
        "y": y,
        "method": "IQR",
        "multiplier": float(multiplier),
        "original_correlation": original_correlation,
        "filtered_correlation": filtered_correlation,
        "removed_count": int(len(pairs) - len(filtered)),
        "original_sample_size": int(len(pairs)),
        "filtered_sample_size": int(len(filtered)),
    }


def analyze_subgroups(
    frame: pd.DataFrame,
    x: str,
    y: str,
    group_by: str,
) -> dict[str, Any]:
    """Calculate X-Y correlation independently within each non-null group."""
    _require_dataframe(frame)
    _require_columns(frame, [x, y, group_by])
    _require_numeric_columns(frame, [x, y])
    observations = frame[[x, y, group_by]].dropna()
    if len(observations) < MINIMUM_CORRELATION_SAMPLE:
        raise ToolError("INSUFFICIENT_DATA", "Not enough complete subgroup observations.")

    groups: list[dict[str, Any]] = []
    for value, group in observations.groupby(group_by, sort=True):
        coefficient: float | None = None
        if len(group) >= MINIMUM_CORRELATION_SAMPLE:
            try:
                coefficient = _pearson_coefficient(group[x], group[y])
            except ToolError as error:
                if error.code != "INSUFFICIENT_DATA":
                    raise
        groups.append(
            {
                "value": _json_scalar(value),
                "sample_size": int(len(group)),
                "correlation": coefficient,
            }
        )

    return {"x": x, "y": y, "group_by": group_by, "groups": groups}


def _require_dataframe(frame: pd.DataFrame) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise ToolError("INVALID_PARAMETERS", "A pandas DataFrame is required.")


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    invalid_names = [column for column in columns if not isinstance(column, str)]
    if invalid_names:
        raise ToolError("INVALID_PARAMETERS", "Column names must be strings.")
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ToolError(
            "COLUMN_NOT_FOUND",
            f"Column not found: {', '.join(missing)}.",
        )


def _require_numeric_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    non_numeric = [column for column in columns if not is_numeric_dtype(frame[column])]
    if non_numeric:
        raise ToolError(
            "NON_NUMERIC_COLUMN",
            f"Numeric column required: {', '.join(non_numeric)}.",
        )


def _valid_numeric_rows(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    _require_dataframe(frame)
    _require_columns(frame, columns)
    _require_numeric_columns(frame, columns)
    observations = frame[columns].dropna()
    if len(observations) < MINIMUM_CORRELATION_SAMPLE:
        raise ToolError(
            "INSUFFICIENT_DATA",
            f"At least {MINIMUM_CORRELATION_SAMPLE} complete observations are required.",
        )
    return observations


def _pearson_coefficient(x: Any, y: Any) -> float:
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    if len(x_values) < MINIMUM_CORRELATION_SAMPLE:
        raise ToolError(
            "INSUFFICIENT_DATA",
            f"At least {MINIMUM_CORRELATION_SAMPLE} observations are required.",
        )
    if np.isclose(np.std(x_values), 0.0) or np.isclose(np.std(y_values), 0.0):
        raise ToolError(
            "INSUFFICIENT_DATA",
            "Correlation requires variation in both variables.",
        )
    return float(np.corrcoef(x_values, y_values)[0, 1])


def _iqr_bounds(values: pd.Series, multiplier: float) -> tuple[float, float]:
    first_quartile = float(values.quantile(0.25))
    third_quartile = float(values.quantile(0.75))
    interquartile_range = third_quartile - first_quartile
    return (
        first_quartile - multiplier * interquartile_range,
        third_quartile + multiplier * interquartile_range,
    )


def _optional_float(value: Any) -> float | None:
    return None if pd.isna(value) else float(value)


def _json_scalar(value: Any) -> Any:
    return value.item() if isinstance(value, np.generic) else value


ToolFunction = Callable[..., dict[str, Any]]

TOOL_REGISTRY: dict[str, ToolFunction] = {
    "profile_dataset": profile_dataset,
    "pearson_correlation": pearson_correlation,
    "spearman_correlation": spearman_correlation,
    "partial_correlation": partial_correlation,
    "detect_outliers": detect_outliers,
    "correlation_without_outliers": correlation_without_outliers,
    "analyze_subgroups": analyze_subgroups,
}
