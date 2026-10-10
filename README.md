# AMDCD Backend

Backend productivo del proyecto Arquitectura Multiagente para la Detección de Patrones y Filtrado de Relaciones Potencialmente Espurias en Datos.

El desarrollo productivo se realizará mediante ramas feature creadas desde `main`.

Los Spikes experimentales se mantienen aislados de esta base productiva mientras se completan y aprueban las decisiones arquitectónicas correspondientes.

## HU-005 — Query Execution

La infraestructura de ejecución de herramientas se encuentra en desarrollo. El
Query Executor preparará y ejecutará solicitudes controladas, mientras que la
decisión sobre qué herramienta utilizar permanecerá en una capa superior. Su
integración con la arquitectura definitiva se realizará después de aprobar el
ADR correspondiente.
