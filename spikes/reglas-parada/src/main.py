from src.stop_rules import (
    TRANSITIONS,
    action_key,
    is_duplicate_action,
    run_controlled_cycle,
    should_stop,
)


def show_graph():
    print("=" * 60)
    print("GRAFO DE ESTADOS Y TRANSICIONES")
    print("=" * 60)

    for state, destinations in TRANSITIONS.items():
        print(f"{state} -> {', '.join(destinations)}")


def demo_max_iterations():
    print("\n" + "=" * 60)
    print("DEMO: LÍMITE DE ITERACIONES")
    print("=" * 60)

    actions = [
        (f"action_{i}", {"value": i})
        for i in range(9)
    ]

    result = run_controlled_cycle(actions)

    print(f"Acciones ejecutadas: {result['iterations']}")
    print(f"Estado final: {result['status']}")
    print(f"Razón de parada: {result['reason']}")


def demo_duplicate_action():
    print("\n" + "=" * 60)
    print("DEMO: CONTROL DE ACCIONES DUPLICADAS")
    print("=" * 60)

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

    print(f"Acciones ejecutadas: {result['iterations']}")
    print(f"Estado final: {result['status']}")
    print(f"Razón de parada: {result['reason']}")
    print(f"Duplicados evitados: {result['duplicates_prevented']}")


def demo_evidence():
    print("\n" + "=" * 60)
    print("DEMO: EVIDENCIA SUFICIENTE")
    print("=" * 60)

    stop, reason = should_stop(
        iterations=2,
        evidence_sufficient=True,
    )

    print(f"Estado: {'DETENER' if stop else 'CONTINUAR'}")
    print(f"Razón: {reason}")


def main():
    show_graph()
    demo_max_iterations()
    demo_duplicate_action()
    demo_evidence()


if __name__ == "__main__":
    main()