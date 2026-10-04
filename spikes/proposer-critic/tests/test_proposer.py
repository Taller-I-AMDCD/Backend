import pandas as pd
import pytest

from src.proposer import (
    propose_initial_analysis,
    propose_follow_up,
    validate_proposal,
)


def sample_dataset():
    return pd.DataFrame({
        "X": [1, 2, 3, 4, 5],
        "Y": [2, 4, 6, 8, 10],
        "Z": [1, 1, 2, 2, 3],
    })


def test_initial_proposal():
    df = sample_dataset()

    proposal = propose_initial_analysis(df)

    assert proposal["agent"] == "Proposer"
    assert proposal["stage"] == "initial"
    assert proposal["action"] == "pearson_correlation"
    assert proposal["parameters"]["x"] == "X"
    assert proposal["parameters"]["y"] == "Y"


def test_follow_up_proposal():
    critic_request = {
        "action": "partial_correlation",
        "parameters": {
            "x": "X",
            "y": "Y",
            "control": "Z",
        },
        "reason": "Evaluar posible variable de confusión.",
    }

    proposal = propose_follow_up(critic_request)

    assert proposal["agent"] == "Proposer"
    assert proposal["stage"] == "follow_up"
    assert proposal["action"] == "partial_correlation"
    assert proposal["parameters"]["control"] == "Z"


def test_validate_valid_proposal():
    proposal = {
        "agent": "Proposer",
        "stage": "initial",
        "hypothesis": "Existe una relación entre X y Y.",
        "action": "pearson_correlation",
        "parameters": {
            "x": "X",
            "y": "Y",
        },
        "reason": "Evaluar asociación inicial.",
    }

    assert validate_proposal(proposal) is True


def test_reject_invalid_proposal():
    invalid_proposal = {
        "agent": "Proposer",
        "action": "pearson_correlation",
    }

    with pytest.raises(ValueError, match="INVALID_PROPOSAL"):
        validate_proposal(invalid_proposal)


def test_reject_insufficient_data():
    df = pd.DataFrame({
        "X": [1, 2, 3, 4, 5]
    })

    with pytest.raises(ValueError, match="INSUFFICIENT_DATA"):
        propose_initial_analysis(df)