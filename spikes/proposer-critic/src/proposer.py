import pandas as pd


def propose_initial_analysis(df):
    """
    Genera una primera propuesta de análisis a partir
    de las variables numéricas disponibles.
    """
    numeric_columns = list(
        df.select_dtypes(include="number").columns
    )

    if len(numeric_columns) < 2:
        raise ValueError("INSUFFICIENT_DATA")

    x = numeric_columns[0]
    y = numeric_columns[1]

    return {
        "agent": "Proposer",
        "stage": "initial",
        "hypothesis": f"Existe una relación entre {x} y {y}.",
        "action": "pearson_correlation",
        "parameters": {
            "x": x,
            "y": y
        },
        "reason": "Evaluar la asociación inicial entre las variables.",
    }


def propose_follow_up(critic_request):
    """
    Convierte una solicitud del Critic en una nueva propuesta.
    """
    if not critic_request:
        raise ValueError("INVALID_REQUEST")

    action = critic_request.get("action")
    parameters = critic_request.get("parameters", {})
    reason = critic_request.get("reason", "")

    return {
        "agent": "Proposer",
        "stage": "follow_up",
        "hypothesis": "La relación requiere evidencia adicional.",
        "action": action,
        "parameters": parameters,
        "reason": reason,
    }


def validate_proposal(proposal):
    """
    Comprueba que una propuesta tenga la estructura mínima esperada.
    """
    required_fields = [
        "agent",
        "stage",
        "hypothesis",
        "action",
        "parameters",
        "reason",
    ]

    missing = [
        field for field in required_fields
        if field not in proposal
    ]

    if missing:
        raise ValueError(
            f"INVALID_PROPOSAL: missing {missing}"
        )

    return True