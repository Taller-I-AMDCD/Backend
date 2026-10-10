from src.stop_rules import (
    MAX_ITERATIONS,
    STATES,
    TRANSITIONS,
    action_key,
    is_duplicate_action,
    should_stop,
    run_controlled_cycle,
)


def test_max_iterations_is_8():
    assert MAX_ITERATIONS == 8


def test_stop_when_max_iterations_is_reached():
    stop, reason = should_stop(8)

    assert stop is True
    assert reason == "MAX_ITERATIONS"


def test_continue_before_max_iterations():
    stop, reason = should_stop(3)

    assert stop is False
    assert reason == "CONTINUE"


def test_stop_with_small_iteration_limit():
    stop, reason = should_stop(
        iterations=3,
        max_iterations=3,
    )

    assert stop is True
    assert reason == "MAX_ITERATIONS"


def test_stop_when_evidence_is_sufficient():
    stop, reason = should_stop(
        iterations=2,
        evidence_sufficient=True,
    )

    assert stop is True
    assert reason == "SUFFICIENT_EVIDENCE"


def test_stop_when_no_relevant_actions_exist():
    stop, reason = should_stop(
        iterations=2,
        actions_available=False,
    )

    assert stop is True
    assert reason == "NO_RELEVANT_ACTIONS"


def test_detect_duplicate_action():
    history = {
        action_key(
            "pearson_correlation",
            {"x": "X", "y": "Y"},
        )
    }

    assert is_duplicate_action(
        "pearson_correlation",
        {"x": "X", "y": "Y"},
        history,
    ) is True


def test_allow_new_action():
    history = {
        action_key(
            "pearson_correlation",
            {"x": "X", "y": "Y"},
        )
    }

    assert is_duplicate_action(
        "spearman_correlation",
        {"x": "X", "y": "Y"},
        history,
    ) is False


def test_all_states_are_defined():
    expected_states = {
        "INICIO",
        "VALIDAR_DATOS",
        "SELECCIONAR_ACCION",
        "EJECUTAR_ACCION",
        "EVALUAR_RESULTADO",
        "FINALIZAR",
        "DETENER",
    }

    assert STATES == expected_states


def test_all_transitions_use_valid_states():
    for state, destinations in TRANSITIONS.items():
        assert state in STATES

        for destination in destinations:
            assert destination in STATES


def test_terminal_states_have_no_outgoing_transitions():
    assert "FINALIZAR" not in TRANSITIONS
    assert "DETENER" not in TRANSITIONS


def test_initial_state_starts_validation():
    assert TRANSITIONS["INICIO"] == ["VALIDAR_DATOS"]


def test_result_evaluation_has_valid_next_states():
    assert set(TRANSITIONS["EVALUAR_RESULTADO"]) == {
        "FINALIZAR",
        "SELECCIONAR_ACCION",
        "DETENER",
    }


def test_controlled_cycle_stops_at_max_iterations():
    actions = [
        (f"action_{i}", {"value": i})
        for i in range(9)
    ]

    result = run_controlled_cycle(actions)

    assert result["reason"] == "MAX_ITERATIONS"
    assert result["iterations"] == 8
    assert len(result["executed_actions"]) == 8


def test_controlled_cycle_stops_on_duplicate():
    actions = [
        (
            "pearson_correlation",
            {"x": "X", "y": "Y"},
        ),
        (
            "pearson_correlation",
            {"x": "X", "y": "Y"},
        ),
    ]

    result = run_controlled_cycle(actions)

    assert result["reason"] == "DUPLICATE_ACTION"
    assert result["iterations"] == 1
    assert result["duplicates_prevented"] == 1


def test_controlled_cycle_stops_when_actions_finish():
    actions = [
        (
            "pearson_correlation",
            {"x": "X", "y": "Y"},
        ),
    ]

    result = run_controlled_cycle(actions)

    assert result["reason"] == "NO_RELEVANT_ACTIONS"
    assert result["iterations"] == 1