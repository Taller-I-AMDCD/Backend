def generate_hypotheses(profile, max_hypotheses=5):
    """Genera hipótesis estructuradas a partir del perfil de un dataset."""

    if not isinstance(profile, dict):
        raise ValueError("INVALID_PROFILE")

    numeric_columns = profile.get("numeric_columns", [])

    if not isinstance(numeric_columns, list):
        raise ValueError("INVALID_NUMERIC_COLUMNS")

    if len(numeric_columns) < 2:
        return {
            "tool": "hypothesis_generator",
            "hypotheses": [],
            "count": 0,
        }

    hypotheses = []

    for i, x in enumerate(numeric_columns):
        for y in numeric_columns[i + 1:]:

            if len(hypotheses) >= max_hypotheses:
                break

            hypotheses.append({
                "id": f"H{len(hypotheses) + 1:03d}",
                "independent_variable": x,
                "dependent_variable": y,
                "relationship": "possible association",
                "statement": (
                    f"{x} may be associated with {y}."
                ),
                "justification": (
                    "Both variables are numeric and can be "
                    "investigated for a possible association."
                ),
            })

        if len(hypotheses) >= max_hypotheses:
            break

    return {
        "tool": "hypothesis_generator",
        "hypotheses": hypotheses,
        "count": len(hypotheses),
    }