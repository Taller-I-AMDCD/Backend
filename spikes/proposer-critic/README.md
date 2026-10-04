# Arquitectura Proposer–Critic

## Objetivo

Evaluar la arquitectura Proposer–Critic para analizar relaciones estadísticas y detectar posibles relaciones espurias mediante un proceso iterativo de propuesta, ejecución y crítica.

## Flujo de la arquitectura

Dataset → Proposer → Herramienta estadística → Resultado → Critic → nueva propuesta → decisión final

## Escenarios evaluados

- **Consistent relation:** relación estable entre X e Y.
- **Confounded relation:** relación afectada por una variable de confusión Z.
- **Outlier relation:** relación afectada por valores atípicos.

## Estructura

- `data/`: datasets utilizados en la evaluación.
- `src/`: componentes de la arquitectura y herramientas estadísticas.
- `tests/`: pruebas unitarias y de integración.
- `evaluation/`: evaluación formal de la arquitectura.
- `results/`: resultados generados durante las ejecuciones.

## Ejecución

Ejecutar la arquitectura:

```bash
python -m src.main