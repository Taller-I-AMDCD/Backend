from src.main import run_scenario


def test_consistent_relation():
    result = run_scenario(
        "consistent_relation",
        "consistent_relation.csv"
    )

    assert result["final_decision"] == "ACCEPT"
    assert result["iterations"] == 2


def test_confounded_relation():
    result = run_scenario(
        "confounded_relation",
        "confounded_relation.csv"
    )

    assert result["final_decision"] == "REJECT_SPURIOUS"
    assert result["iterations"] == 2


def test_outlier_relation():
    result = run_scenario(
        "outlier_relation",
        "outlier_relation.csv"
    )

    assert result["final_decision"] == "REJECT_SPURIOUS"
    assert result["iterations"] == 2