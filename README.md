# AMDCD Backend

Backend productivo del proyecto Arquitectura Multiagente para la Detección de Patrones y Filtrado de Relaciones Potencialmente Espurias en Datos.

El desarrollo productivo se realizará mediante ramas feature creadas desde `main`.

Los Spikes experimentales se mantienen aislados de esta base productiva mientras se completan y aprueban las decisiones arquitectónicas correspondientes.

## DO-002 — Provisional Orchestration Scaffold

La infraestructura provisional de orquestación incluye contratos neutrales, estado y contexto de ejecución, registro de componentes, trazabilidad en memoria, estrategia de coordinación reemplazable, supervisor y orquestador. El límite defensivo `max_steps` evita ejecuciones indefinidas causadas por estrategias defectuosas.

Flujo provisional:

```text
Request → Supervisor → Strategy → Decision → Registry → Component → Result
```

The final coordination architecture remains pending DO-001 and the ADR.

### Validación

Desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests -v
python -m src.orchestration.demo
```

## Pending after DO-001 / ADR

- Concrete coordination strategy.
- Semantic routing.
- Agent selection.
- Consensus mechanism.
- Domain stopping policy.
- Retry policy.
- Integration with real agents.
