from src.hypothesis_generator import generate_hypotheses


def test_generate_hypotheses_with_numeric_variables():
    profile = {
        "rows": 500,
        "columns": ["X", "Y", "Z"],
        "numeric_columns": ["X", "Y", "Z"],
        "missing_values": 0,
    }

    result = generate_hypotheses(profile)

    assert result["tool"] == "hypothesis_generator"
    assert result["count"] > 0
    assert len(result["hypotheses"]) == result["count"]


def test_hypothesis_has_structured_output():
    profile = {
        "rows": 500,
        "columns": ["X", "Y"],
        "numeric_columns": ["X", "Y"],
        "missing_values": 0,
    }

    result = generate_hypotheses(profile)

    hypothesis = result["hypotheses"][0]

    assert "id" in hypothesis
    assert "independent_variable" in hypothesis
    assert "dependent_variable" in hypothesis
    assert "relationship" in hypothesis
    assert "statement" in hypothesis
    assert "justification" in hypothesis


def test_generate_hypotheses_respects_maximum():
    profile = {
        "rows": 500,
        "columns": ["X", "Y", "Z", "A"],
        "numeric_columns": ["X", "Y", "Z", "A"],
        "missing_values": 0,
    }

    result = generate_hypotheses(
        profile,
        max_hypotheses=2,
    )

    assert result["count"] == 2
    assert len(result["hypotheses"]) == 2


def test_no_hypotheses_with_insufficient_numeric_variables():
    profile = {
        "rows": 500,
        "columns": ["X"],
        "numeric_columns": ["X"],
        "missing_values": 0,
    }

    result = generate_hypotheses(profile)

    assert result["count"] == 0
    assert result["hypotheses"] == []


def test_invalid_profile_is_rejected():
    try:
        generate_hypotheses(None)
        assert False
    except ValueError as error:
        assert str(error) == "INVALID_PROFILE"


def test_invalid_numeric_columns_are_rejected():
    profile = {
        "rows": 500,
        "columns": ["X", "Y"],
        "numeric_columns": "X,Y",
        "missing_values": 0,
    }

    try:
        generate_hypotheses(profile)
        assert False
    except ValueError as error:
        assert str(error) == "INVALID_NUMERIC_COLUMNS"