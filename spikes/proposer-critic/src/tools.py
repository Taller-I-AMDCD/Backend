import numpy as np
import pandas as pd


def profile_dataset(df):
    """Obtiene información básica del dataset."""
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "numeric_columns": list(df.select_dtypes(include="number").columns),
        "missing_values": int(df.isna().sum().sum()),
    }


def pearson_correlation(df, x, y):
    """Calcula la correlación de Pearson entre dos variables."""
    if x not in df.columns or y not in df.columns:
        raise ValueError("COLUMN_NOT_FOUND")

    if not pd.api.types.is_numeric_dtype(df[x]):
        raise ValueError("NON_NUMERIC_COLUMN")

    if not pd.api.types.is_numeric_dtype(df[y]):
        raise ValueError("NON_NUMERIC_COLUMN")

    correlation = df[x].corr(df[y], method="pearson")

    return {
        "tool": "pearson_correlation",
        "x": x,
        "y": y,
        "coefficient": round(float(correlation), 4),
        "observations": len(df),
    }


def spearman_correlation(df, x, y):
    """Calcula la correlación de Spearman."""
    if x not in df.columns or y not in df.columns:
        raise ValueError("COLUMN_NOT_FOUND")

    correlation = df[x].corr(df[y], method="spearman")

    return {
        "tool": "spearman_correlation",
        "x": x,
        "y": y,
        "coefficient": round(float(correlation), 4),
        "observations": len(df),
    }


def partial_correlation(df, x, y, control):
    """Calcula la correlación parcial controlando una tercera variable."""
    required = [x, y, control]

    if not all(column in df.columns for column in required):
        raise ValueError("COLUMN_NOT_FOUND")

    data = df[required].dropna()

    control_values = data[control].to_numpy()
    x_values = data[x].to_numpy()
    y_values = data[y].to_numpy()

    design = np.column_stack([
        np.ones(len(control_values)),
        control_values
    ])

    x_coefficients = np.linalg.lstsq(
        design, x_values, rcond=None
    )[0]

    y_coefficients = np.linalg.lstsq(
        design, y_values, rcond=None
    )[0]

    x_residuals = x_values - design @ x_coefficients
    y_residuals = y_values - design @ y_coefficients

    correlation = np.corrcoef(
        x_residuals,
        y_residuals
    )[0, 1]

    return {
        "tool": "partial_correlation",
        "x": x,
        "y": y,
        "control": control,
        "coefficient": round(float(correlation), 4),
        "observations": len(data),
    }


def correlation_without_outliers(df, x, y):
    """Calcula la correlación eliminando outliers mediante IQR."""
    if x not in df.columns or y not in df.columns:
        raise ValueError("COLUMN_NOT_FOUND")

    original_correlation = df[x].corr(df[y])

    def valid_iqr(series):
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        return (series >= lower) & (series <= upper)

    valid_x = valid_iqr(df[x])
    valid_y = valid_iqr(df[y])

    valid_rows = valid_x & valid_y

    filtered = df.loc[valid_rows]

    filtered_correlation = filtered[x].corr(filtered[y])

    removed = int((~valid_rows).sum())

    return {
        "tool": "correlation_without_outliers",
        "x": x,
        "y": y,
        "original_correlation": round(float(original_correlation), 4),
        "filtered_correlation": round(float(filtered_correlation), 4),
        "removed_observations": removed,
        "remaining_observations": len(filtered),
    }


TOOL_REGISTRY = {
    "profile_dataset": profile_dataset,
    "pearson_correlation": pearson_correlation,
    "spearman_correlation": spearman_correlation,
    "partial_correlation": partial_correlation,
    "correlation_without_outliers": correlation_without_outliers,
}


def execute_tool(tool_name, df, **parameters):
    """Ejecuta únicamente herramientas registradas."""
    if tool_name not in TOOL_REGISTRY:
        raise ValueError("UNKNOWN_TOOL")

    tool = TOOL_REGISTRY[tool_name]

    return tool(df, **parameters)