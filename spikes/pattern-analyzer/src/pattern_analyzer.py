def analyze_patterns(relations, min_abs_correlation=0.5):
    """Identifica relaciones candidatas para un contraste posterior."""

    if not isinstance(relations, list):
        raise ValueError("INVALID_RELATIONS")

    if not 0 <= min_abs_correlation <= 1:
        raise ValueError("INVALID_THRESHOLD")

    candidates = []

    for relation in relations:
        if not isinstance(relation, dict):
            raise ValueError("INVALID_RELATION")

        if "x" not in relation or "y" not in relation:
            raise ValueError("INVALID_RELATION")

        if "coefficient" not in relation:
            raise ValueError("MISSING_COEFFICIENT")

        coefficient = relation["coefficient"]

        if not isinstance(coefficient, (int, float)):
            raise ValueError("INVALID_COEFFICIENT")

        if abs(coefficient) >= min_abs_correlation:
            if coefficient > 0:
                pattern_type = "positive_association"
            elif coefficient < 0:
                pattern_type = "negative_association"
            else:
                pattern_type = "no_association"

            candidates.append({
                "id": f"P{len(candidates) + 1:03d}",
                "x": relation["x"],
                "y": relation["y"],
                "coefficient": coefficient,
                "pattern_type": pattern_type,
                "reason": (
                    "The association meets the initial threshold "
                    "for additional analysis."
                ),
            })

    return {
        "tool": "pattern_analyzer",
        "candidates": candidates,
        "count": len(candidates),
    }