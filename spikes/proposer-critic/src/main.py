import json
from pathlib import Path

import pandas as pd

from src.proposer import (
    propose_initial_analysis,
    propose_follow_up,
)
from src.critic import evaluate_result
from src.tools import execute_tool


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"


def run_scenario(name, filename):
    print("\n" + "=" * 60)
    print(f"ESCENARIO: {name}")
    print("=" * 60)

    df = pd.read_csv(DATA_DIR / filename)

    history = []
    iteration = 1

    # 1. Proposer genera el análisis inicial
    proposal = propose_initial_analysis(df)

    while iteration <= 3:
        print(f"\n--- ITERACIÓN {iteration} ---")

        print("Proposer:")
        print(f"  Acción: {proposal['action']}")
        print(f"  Parámetros: {proposal['parameters']}")

        # 2. Ejecutar herramienta propuesta
        result = execute_tool(
            proposal["action"],
            df,
            **proposal["parameters"]
        )

        print("Resultado:")
        print(result)

        # 3. Critic evalúa el resultado
        critic = evaluate_result(result, df)

        print("Critic:")
        print(f"  Decisión: {critic['decision']}")
        print(f"  Razón: {critic['reason']}")

        history.append({
            "iteration": iteration,
            "proposal": proposal,
            "result": result,
            "critic": critic,
        })

        # 4. Si no solicita más evidencia, finaliza
        if critic["next_action"] is None:
            break

        # 5. Proposer genera una nueva propuesta
        proposal = propose_follow_up({
            "action": critic["next_action"],
            "parameters": critic["parameters"],
            "reason": critic["reason"],
        })

        iteration += 1

    return {
        "scenario": name,
        "iterations": iteration,
        "history": history,
        "final_decision": history[-1]["critic"]["decision"],
    }


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    scenarios = [
        ("consistent_relation", "consistent_relation.csv"),
        ("confounded_relation", "confounded_relation.csv"),
        ("outlier_relation", "outlier_relation.csv"),
    ]

    results = []

    for name, filename in scenarios:
        results.append(
            run_scenario(name, filename)
        )

    output_file = RESULTS_DIR / "proposer_critic_run.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("\n" + "=" * 60)
    print("EVALUACIÓN FINALIZADA")
    print("=" * 60)
    print(f"Resultados guardados en: {output_file}")


if __name__ == "__main__":
    main()