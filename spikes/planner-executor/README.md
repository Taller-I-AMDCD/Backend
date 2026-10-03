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

## Rule-based Planner

El Planner selecciona de forma determinista la siguiente operación analítica sin ejecutar cálculos. Recibe un estado de investigación con el objetivo, la iteración, las columnas disponibles, las variables numéricas, el par objetivo explícito, el historial y los resultados anteriores.

Su salida es una decisión serializable a JSON: una acción con herramienta, parámetros y razón explicable, o una decisión de parada. Las reglas se evalúan en este orden:

1. perfilado cuando no existe metadata suficiente;
2. correlación de Pearson para el par objetivo;
3. correlación parcial para la primera variable numérica candidata ordenada;
4. contraste de sensibilidad a outliers;
5. correlación de Spearman como métrica alternativa;
6. parada cuando no existen acciones nuevas o se alcanza el límite de iteraciones.

La correlación inicial se considera relevante cuando su valor absoluto es al menos `0.5`. La selección de la primera candidata ordenada es una simplificación determinista del Spike cuando existen múltiples variables de control posibles.

El Planner decide qué operación solicitar. El Executor valida y ejecuta únicamente la operación autorizada. En esta etapa ambos componentes permanecen aislados y no existe todavía un ciclo integrado.

La demostración independiente del Planner se ejecuta desde `spikes/planner-executor`:

```text
python -m src.demo_planner
```

## Integrated Planner–Executor loop

El orquestador conecta los componentes sin asumir sus responsabilidades: entrega el estado al Planner, convierte cada decisión en una solicitud para el Executor, incorpora la respuesta al estado y conserva la trazabilidad hasta recibir una decisión de parada.

El ciclo mantiene por separado la decisión, la ejecución y la actualización del estado:

```text
Dataset → State → Planner → Executor → State → Planner → Stop
```

Cada ejecución registra las decisiones, razones, parámetros, respuestas, errores, metadata del estado y métricas finales. La traza completa se guarda como JSON en `results/<dataset>_run.json`.

Desde `spikes/planner-executor`, un dataset puede procesarse con:

```text
python -m src.main --dataset data/confounded_relation.csv --x X --y Y
```

El límite puede ajustarse con `--max-iterations`; su valor predeterminado es `8`. Esta integración recopila evidencia analítica y no asigna clasificaciones finales a las relaciones estudiadas.

## Execution safeguards

El ciclo aplica el límite `max_iterations` tanto en el Planner como defensivamente en el orquestador. El orquestador también normaliza `tool + parameters` para bloquear solicitudes duplicadas antes de invocar nuevamente al Executor.

Los errores estructurados del Executor se conservan en la iteración correspondiente, incrementan las métricas de fallo y detienen el ciclo con `EXECUTION_ERROR`. Las trazas acumuladas, incluidas las ejecuciones fallidas, pueden persistirse como JSON para su auditoría.

El CLI rechaza de forma controlada archivos inexistentes o vacíos, targets ausentes o no numéricos, variables objetivo idénticas y límites de iteración inválidos. Estos errores esperables producen un mensaje breve y un código de salida distinto de cero, sin ocultar fallos inesperados de programación.

Las defensas pueden demostrarse de manera aislada con:

```text
python -m src.demo_robustness
```
