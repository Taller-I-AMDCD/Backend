import pandas as pd

from src.tools import (
    profile_dataset,
    pearson_correlation,
    spearman_correlation,
    partial_correlation,
    correlation_without_outliers,
    execute_tool,
)


def sample_dataset():
    return pd.DataFrame({
        "X": [1, 2, 3, 4, 5],
        "Y": [2, 4, 6, 8, 10],
        "Z": [1, 1, 2, 2, 3],
    })


def test_profile_dataset():
    df = sample_dataset()

    result = profile_dataset(df)

    assert result["rows"] == 5
    assert "X" in result["numeric_columns"]
    assert result["missing_values"] == 0


def test_pearson_correlation():
    df = sample_dataset()

    result = pearson_correlation(df, "X", "Y")

    assert result["coefficient"] == 1.0


def test_spearman_correlation():
    df = sample_dataset()

    result = spearman_correlation(df, "X", "Y")

    assert result["coefficient"] == 1.0


def test_partial_correlation():
    df = sample_dataset()

    result = partial_correlation(df, "X", "Y", "Z")

    assert "coefficient" in result


def test_correlation_without_outliers():
    df = sample_dataset()

    result = correlation_without_outliers(df, "X", "Y")

    assert "original_correlation" in result
    assert "filtered_correlation" in result


def test_execute_registered_tool():
    df = sample_dataset()

    result = execute_tool(
        "pearson_correlation",
        df,
        x="X",
        y="Y"
    )

    assert result["coefficient"] == 1.0


def test_reject_unknown_tool():
    df = sample_dataset()

    try:
        execute_tool("unsupported_tool", df, x="X", y="Y")
        assert False
    except ValueError as error:
        assert str(error) == "UNKNOWN_TOOL"