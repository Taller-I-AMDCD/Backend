MAX_ITERATIONS = 8


STATES = {
    "INICIO",
    "VALIDAR_DATOS",
    "SELECCIONAR_ACCION",
    "EJECUTAR_ACCION",
    "EVALUAR_RESULTADO",
    "FINALIZAR",
    "DETENER",
}


TRANSITIONS = {
    "INICIO": ["VALIDAR_DATOS"],
    "VALIDAR_DATOS": ["SELECCIONAR_ACCION"],
    "SELECCIONAR_ACCION": [
        "EJECUTAR_ACCION",
        "DETENER",
    ],
    "EJECUTAR_ACCION": ["EVALUAR_RESULTADO"],
    "EVALUAR_RESULTADO": [
        "FINALIZAR",
        "SELECCIONAR_ACCION",
        "DETENER",
    ],
}


def action_key(action, parameters=None):
    """Genera una clave única para identificar una acción."""
    parameters = parameters or {}

    return (
        action,
        tuple(sorted(parameters.items()))
    )


def is_duplicate_action(action, parameters, history):
    """Comprueba si una acción ya fue ejecutada."""
    key = action_key(action, parameters)

    return key in history


def should_stop(
    iterations,
    evidence_sufficient=False,
    actions_available=True,
    max_iterations=MAX_ITERATIONS,
):
    """Determina si el proceso debe detenerse."""

    if evidence_sufficient:
        return True, "SUFFICIENT_EVIDENCE"

    if iterations >= max_iterations:
        return True, "MAX_ITERATIONS"

    if not actions_available:
        return True, "NO_RELEVANT_ACTIONS"

    return False, "CONTINUE"


def run_controlled_cycle(actions, max_iterations=MAX_ITERATIONS):
    """Ejecuta un ciclo controlado evitando duplicados y exceso de iteraciones."""

    history = set()
    executed_actions = []
    duplicates_prevented = 0
    iterations = 0

    for action, parameters in actions:

        stop, reason = should_stop(
            iterations,
            max_iterations=max_iterations,
        )

        if stop:
            return {
                "status": "DETENER",
                "reason": reason,
                "iterations": iterations,
                "executed_actions": executed_actions,
                "duplicates_prevented": duplicates_prevented,
            }

        if is_duplicate_action(action, parameters, history):
            duplicates_prevented += 1

            return {
                "status": "DETENER",
                "reason": "DUPLICATE_ACTION",
                "iterations": iterations,
                "executed_actions": executed_actions,
                "duplicates_prevented": duplicates_prevented,
            }

        history.add(action_key(action, parameters))

        executed_actions.append({
            "action": action,
            "parameters": parameters,
        })

        iterations += 1

    return {
        "status": "DETENER",
        "reason": "NO_RELEVANT_ACTIONS",
        "iterations": iterations,
        "executed_actions": executed_actions,
        "duplicates_prevented": duplicates_prevented,
    }