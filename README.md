# AMDCD Backend

Backend productivo del proyecto Arquitectura Multiagente para la Detección de Patrones y Filtrado de Relaciones Potencialmente Espurias en Datos.

El desarrollo productivo se realizará mediante ramas feature creadas desde `main`.

Los Spikes experimentales se mantienen aislados de esta base productiva mientras se completan y aprueban las decisiones arquitectónicas correspondientes.

## HU-005 — Query Executor and Tool Dispatcher

HU-005 entrega infraestructura neutral para ejecutar herramientas controladas:
`ToolSpec` describe una herramienta; `Tool` define su contrato estructural;
`ToolRegistry` mantiene la lista explícita permitida; `ToolDispatcher` resuelve
la solicitud exacta; `QueryExecutor` realiza una única ejecución; y
`QueryExecutionTrace` registra el resultado.

El flujo es `ToolExecutionRequest` → `QueryExecutor` → `ToolDispatcher` →
`ToolRegistry` → `Tool.execute` → `ToolExecutionResult`.

El ejecutor normaliza los fallos mediante los códigos `UNKNOWN_TOOL`,
`INVALID_PARAMETERS`, `TOOL_EXECUTION_ERROR`, `INVALID_TOOL_RESULT` y
`DUPLICATE_EXECUTION`. También conserva una traza ordenada de eventos y mide la
duración mediante un reloj monotónico. La protección contra IDs duplicados es
exclusivamente en memoria, local al proceso y a cada instancia; no proporciona
idempotencia distribuida.

El Query Executor ejecuta la herramienta solicitada, pero no decide cuál debe
solicitarse. La selección de herramientas permanece fuera de HU-005 y la
integración con la arquitectura definitiva se realizará después de aprobar el
ADR.

Las salvaguardas incluyen un registro explícito, ausencia de ejecución
arbitraria y fallback, fallos estructurados, protección contra IDs duplicados,
trazabilidad, medición de duración y ausencia de reintentos automáticos.

La protección de duplicados es local al proceso y a la instancia, en memoria y
no distribuida. La traza también reside únicamente en memoria. No existen
garantías de concurrencia, persistencia, reintentos ni timeout.

Esta entrega no incluye herramientas estadísticas productivas, Planner,
integración con Orchestrator, persistencia, concurrencia ni distribución. La
selección de arquitectura permanece pendiente del ADR.

Ejecutar la suite y la demostración desde la raíz del Backend:

```text
python -m unittest discover -s tests -v
python -m src.query_execution.demo
```
