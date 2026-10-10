# Reglas de parada y control de ciclos

## Objetivo

Definir un mecanismo de control para detener la ejecución del sistema cuando se cumplan determinadas condiciones, evitando ciclos innecesarios, operaciones repetidas y un número excesivo de iteraciones.

## Estados del sistema

- INICIO
- VALIDAR DATOS
- SELECCIONAR ACCIÓN
- EJECUTAR ACCIÓN
- EVALUAR RESULTADO
- FINALIZAR
- DETENER

## Transiciones

1. INICIO → VALIDAR DATOS
2. VALIDAR DATOS → SELECCIONAR ACCIÓN
3. SELECCIONAR ACCIÓN → EJECUTAR ACCIÓN
4. EJECUTAR ACCIÓN → EVALUAR RESULTADO
5. EVALUAR RESULTADO → FINALIZAR si existe evidencia suficiente.
6. EVALUAR RESULTADO → SELECCIONAR ACCIÓN si se requiere continuar.
7. SELECCIONAR ACCIÓN → DETENER si la acción ya fue ejecutada.
8. SELECCIONAR ACCIÓN → DETENER si se alcanza el límite de iteraciones.

## Reglas de parada

- El sistema debe detenerse cuando se alcance `max_iterations = 8`.
- El sistema no debe ejecutar nuevamente una operación que ya haya sido realizada.
- El sistema debe finalizar cuando ya no existan acciones relevantes.
- Ante una condición que impida continuar de forma válida, la ejecución debe detenerse de manera controlada.

### ¿Por qué empezamos así?

Porque aquí estamos definiendo **el comportamiento que debe cumplir el sistema**, no quién lo ejecuta. Eso nos permite mantener RN-003 válido independientemente de que posteriormente el equipo seleccione Planner–Executor, Supervisor jerárquica, Blackboard, Proposer–Critic o Híbrida.

Además, el límite de **8 iteraciones** y la prevención de operaciones duplicadas deben mantenerse como reglas comunes. :chatgpt-content-reference{index="0"}

**Haz esto y no programes todavía.** Cuando hayas guardado el README, dime **“listo”** y pasamos al siguiente paso: convertir este diseño en una implementación sencilla y testeable.
## Grafo de estados

```text
INICIO
   ↓
VALIDAR DATOS
   ↓
SELECCIONAR ACCIÓN
   ↓
¿ACCIÓN REPETIDA?
   ├── SÍ → DETENER
   └── NO
        ↓
   EJECUTAR ACCIÓN
        ↓
   EVALUAR RESULTADO
        ↓
¿EVIDENCIA SUFICIENTE?
   ├── SÍ → FINALIZAR
   └── NO
        ↓
¿ITERACIONES < 8?
   ├── NO → DETENER
   └── SÍ
        ↓
SELECCIONAR ACCIÓN
        ↺