# AMDCD Backend

Backend productivo del proyecto Arquitectura Multiagente para la Detección de Patrones y Filtrado de Relaciones Potencialmente Espurias en Datos.

El desarrollo productivo se realizará mediante ramas feature creadas desde `main`.

Los Spikes experimentales se mantienen aislados de esta base productiva mientras se completan y aprueban las decisiones arquitectónicas correspondientes.

## HU-005 — Query Execution

La infraestructura de ejecución de herramientas se encuentra en desarrollo.
`ToolRegistry` mantiene la lista explícita de herramientas permitidas y
`ToolDispatcher` resuelve solicitudes exclusivamente contra ese registro. La
ejecución completa en `QueryExecutor` permanece pendiente de la siguiente
sesión. La selección de herramientas permanece fuera de HU-005 y su integración
con la arquitectura definitiva se realizará después de aprobar el ADR.
