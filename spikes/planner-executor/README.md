# Spike técnico: arquitectura Planner–Executor

## Objetivo técnico

Evaluar la viabilidad del patrón Planner–Executor como base para coordinar tareas de detección de patrones y filtrado de relaciones potencialmente espurias, manteniendo una separación explícita entre la definición de un plan y su ejecución.

## Arquitectura evaluada

La arquitectura divide el procesamiento en dos responsabilidades principales:

- **Planner:** transforma un objetivo de análisis en una secuencia estructurada de pasos verificables.
- **Executor:** interpreta el plan y coordina la ejecución controlada de cada paso mediante herramientas disponibles.

Las herramientas constituyen una frontera independiente para encapsular operaciones concretas y evitar que el Planner dependa de detalles de ejecución.

## Responsabilidades

### Planner

- Analizar el objetivo recibido.
- Definir pasos ordenados y explícitos.
- Declarar los datos y resultados esperados por cada paso.
- Mantener el plan independiente de la implementación de las herramientas.

### Executor

- Validar la estructura del plan recibido.
- Resolver y ejecutar cada paso en el orden establecido.
- Gestionar resultados, errores y estados de ejecución.
- Exponer trazabilidad sobre las operaciones realizadas.

## Flujo general

```text
Objetivo → Planner → Plan estructurado → Executor → Herramientas → Resultado
```

El Planner produce una representación del trabajo requerido. El Executor consume esa representación, selecciona las herramientas correspondientes y recopila los resultados sin alterar la intención del plan.

## Criterios de evaluación

- Separación efectiva de responsabilidades.
- Claridad y trazabilidad del plan generado.
- Capacidad para validar pasos antes de ejecutarlos.
- Manejo predecible de errores y resultados parciales.
- Facilidad para probar Planner, Executor y herramientas de forma aislada.
- Extensibilidad para incorporar nuevas herramientas.
- Sobrecarga técnica introducida por el patrón.
- Adecuación para flujos de análisis causal reproducibles.

## Evaluation scenarios

El Spike incluye tres datasets sintéticos reproducibles que funcionan como banco experimental común para comparar posteriormente el comportamiento de la arquitectura Planner–Executor:

- **Relación consistente:** presenta una asociación positiva clara y estable entre `X` e `Y`, acompañada de ruido moderado.
- **Confusión:** presenta una asociación entre `X` e `Y` explicada principalmente por la influencia compartida de `Z`.
- **Sensibilidad a outliers:** presenta una asociación base débil o moderada cuya estimación global cambia ante un pequeño grupo de observaciones extremas.

Estos escenarios describen condiciones experimentales controladas y no contienen resultados finales sobre el desempeño de la arquitectura.

## Analytical Executor

El Executor recibe solicitudes estructuradas y ejecuta operaciones analíticas sin decidir qué análisis debe realizarse. Esta separación mantiene la decisión fuera de la capa de ejecución y limita cada solicitud a un catálogo explícito de herramientas autorizadas.

Una solicitud indica el nombre de la herramienta y sus parámetros:

```json
{
  "tool": "pearson_correlation",
  "parameters": {"x": "X", "y": "Y"}
}
```

La respuesta informa el estado, la herramienta, los parámetros, el resultado o un error estructurado. Ambos formatos son serializables a JSON.

El catálogo permite actualmente:

- perfilado de datasets;
- correlaciones de Pearson, Spearman y parcial con una variable de control;
- detección de outliers mediante IQR;
- comparación de correlaciones antes y después de retirar outliers;
- análisis de correlación por subgrupos.

Desde la carpeta `spikes/planner-executor`, la validación y la demostración se ejecutan con:

```text
python -m pytest tests -v
python -m src.demo_executor
```
