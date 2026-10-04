def evaluate_result(result, df):
    """
    Evalúa el resultado obtenido y determina si la evidencia
    es suficiente o si se requiere un nuevo análisis.
    """
    if not result:
        raise ValueError("INVALID_RESULT")

    tool = result.get("tool")

    if tool == "pearson_correlation":
        coefficient = abs(result.get("coefficient", 0))

        numeric_columns = result.get("numeric_columns")

        if numeric_columns is None:
            numeric_columns = list(
                df.select_dtypes(include="number").columns
            )

        # Si existen al menos tres variables numéricas,
        # se considera posible variable de confusión.
        if len(numeric_columns) >= 3:
            control = numeric_columns[2]

            return {
                "agent": "Critic",
                "decision": "REQUEST_MORE_EVIDENCE",
                "reason": (
                    f"Existe una posible variable de confusión: {control}."
                ),
                "next_action": "partial_correlation",
                "parameters": {
                    "x": result["x"],
                    "y": result["y"],
                    "control": control,
                },
            }

        # Si la correlación es fuerte, se solicita
        # una comprobación frente a valores atípicos.
        if coefficient >= 0.7:
            return {
                "agent": "Critic",
                "decision": "REQUEST_MORE_EVIDENCE",
                "reason": (
                    "La asociación es fuerte; se requiere comprobar "
                    "su robustez frente a valores atípicos."
                ),
                "next_action": "correlation_without_outliers",
                "parameters": {
                    "x": result["x"],
                    "y": result["y"],
                },
            }

        return {
            "agent": "Critic",
            "decision": "REJECT",
            "reason": (
                "La asociación inicial no presenta suficiente evidencia."
            ),
            "next_action": None,
            "parameters": {},
        }

    if tool == "partial_correlation":
        coefficient = abs(result.get("coefficient", 0))

        if coefficient >= 0.7:
            decision = "ACCEPT"
            reason = (
                "La asociación se mantiene después de controlar "
                "la variable de confusión."
            )
        else:
            decision = "REJECT_SPURIOUS"
            reason = (
                "La asociación disminuye al controlar la variable "
                "de confusión y puede considerarse espuria."
            )

        return {
            "agent": "Critic",
            "decision": decision,
            "reason": reason,
            "next_action": None,
            "parameters": {},
        }

    if tool == "correlation_without_outliers":
        original = abs(result.get("original_correlation", 0))
        filtered = abs(result.get("filtered_correlation", 0))

        difference = abs(original - filtered)

        if difference > 0.2:
            decision = "REJECT_SPURIOUS"
            reason = (
                "La asociación cambia significativamente después "
                "de eliminar los valores atípicos."
            )
        elif filtered >= 0.7:
            decision = "ACCEPT"
            reason = (
                "La asociación se mantiene después de controlar "
                "los valores atípicos."
            )
        else:
            decision = "REJECT"
            reason = (
                "La evidencia restante no es suficientemente fuerte."
            )

        return {
            "agent": "Critic",
            "decision": decision,
            "reason": reason,
            "next_action": None,
            "parameters": {},
        }

    raise ValueError("UNKNOWN_RESULT_TOOL")