# AMDCD Backend

Backend productivo del proyecto Arquitectura Multiagente para la Detección de Patrones y Filtrado de Relaciones Potencialmente Espurias en Datos.

El desarrollo productivo se realizará mediante ramas feature creadas desde `main`.

Los Spikes experimentales se mantienen aislados de esta base productiva mientras se completan y aprueban las decisiones arquitectónicas correspondientes.

## HU-005 — Query Execution

La infraestructura de ejecución de herramientas se encuentra en desarrollo.
`ToolRegistry` mantiene la lista explícita de herramientas permitidas y
`ToolDispatcher` resuelve solicitudes exclusivamente contra ese registro. El
flujo productivo mínimo es `ToolExecutionRequest` → `QueryExecutor` →
`ToolDispatcher` → `ToolRegistry` → `Tool.execute` → `ToolExecutionResult`.

El ejecutor normaliza los fallos mediante los códigos `UNKNOWN_TOOL`,
`INVALID_PARAMETERS`, `TOOL_EXECUTION_ERROR` e `INVALID_TOOL_RESULT`. Ejecuta la
herramienta solicitada, pero no decide cuál debe solicitarse. La selección de
herramientas permanece fuera de HU-005 y la integración con la arquitectura
definitiva se realizará después de aprobar el ADR.
