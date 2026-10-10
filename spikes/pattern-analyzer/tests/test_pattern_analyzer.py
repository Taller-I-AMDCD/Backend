from src.pattern_analyzer import analyze_patterns


def test_detect_positive_pattern():
    relations = [
        {
            "x": "X",
            "y": "Y",
            "coefficient": 0.82,
        }
    ]

    result = analyze_patterns(relations)

    assert result["tool"] == "pattern_analyzer"
    assert result["count"] == 1
    assert result["candidates"][0]["pattern_type"] == "positive_association"


def test_detect_negative_pattern():
    relations = [
        {
            "x": "X",
            "y": "Y",
            "coefficient": -0.71,
        }
    ]

    result = analyze_patterns(relations)

    assert result["count"] == 1
    assert result["candidates"][0]["pattern_type"] == "negative_association"


def test_ignore_relation_below_threshold():
    relations = [
        {
            "x": "X",
            "y": "Y",
            "coefficient": 0.30,
        }
    ]

    result = analyze_patterns(relations)

    assert result["count"] == 0
    assert result["candidates"] == []


def test_detect_multiple_candidates():
    relations = [
        {
            "x": "X",
            "y": "Y",
            "coefficient": 0.82,
        },
        {
            "x": "X",
            "y": "Z",
            "coefficient": 0.20,
        },
        {
            "x": "Y",
            "y": "Z",
            "coefficient": -0.71,
        },
    ]

    result = analyze_patterns(relations)

    assert result["count"] == 2
    assert len(result["candidates"]) == 2


def test_custom_threshold():
    relations = [
        {
            "x": "X",
            "y": "Y",
            "coefficient": 0.60,
        }
    ]

    result = analyze_patterns(
        relations,
        min_abs_correlation=0.70,
    )

    assert result["count"] == 0


def test_invalid_relations_are_rejected():
    try:
        analyze_patterns(None)
        assert False
    except ValueError as error:
        assert str(error) == "INVALID_RELATIONS"


def test_invalid_threshold_is_rejected():
    relations = [
        {
            "x": "X",
            "y": "Y",
            "coefficient": 0.80,
        }
    ]

    try:
        analyze_patterns(
            relations,
            min_abs_correlation=1.5,
        )
        assert False
    except ValueError as error:
        assert str(error) == "INVALID_THRESHOLD"


def test_missing_coefficient_is_rejected():
    relations = [
        {
            "x": "X",
            "y": "Y",
        }
    ]

    try:
        analyze_patterns(relations)
        assert False
    except ValueError as error:
        assert str(error) == "MISSING_COEFFICIENT"