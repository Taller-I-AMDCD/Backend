# Hypothesis Generator

## HU-003 — Generar hipótesis

### Objetivo

Implementar un generador que transforme el perfil de un dataset en posibles relaciones investigables mediante una salida estructurada.

### Alcance

El generador recibe un perfil de dataset que contiene información básica y sus variables numéricas.

A partir de las variables numéricas disponibles, propone combinaciones que pueden ser investigadas posteriormente.

La implementación es independiente de la arquitectura multiagente que finalmente seleccione el equipo.

### Salida estructurada

Cada hipótesis generada contiene:

- Identificador.
- Variable independiente.
- Variable dependiente.
- Relación propuesta.
- Planteamiento de la hipótesis.
- Justificación.

La respuesta completa también indica la cantidad de hipótesis generadas.

### Control de generación

El generador permite establecer un número máximo de hipótesis para evitar una generación excesiva.

Cuando el perfil no contiene suficientes variables numéricas, no se generan hipótesis.

También se validan perfiles y estructuras de entrada inválidas.

### Validación

Se implementaron pruebas unitarias para verificar:

- Generación de hipótesis con variables numéricas.
- Estructura de cada hipótesis.
- Límite máximo de hipótesis.
- Ausencia de hipótesis con datos insuficientes.
- Rechazo de perfiles inválidos.
- Rechazo de variables numéricas con formato incorrecto.

Resultado de las pruebas:

6 pruebas aprobadas.

### Demostración

La ejecución de ejemplo utiliza un perfil con las variables X, Y y Z y genera tres posibles relaciones:

- X → Y
- X → Z
- Y → Z

La salida se presenta en formato JSON para facilitar su posterior procesamiento.

### Consideraciones

- El desarrollo se realiza de manera neutral y provisional.
- No depende de una arquitectura específica.
- La integración con la arquitectura definitiva se realizará después de la decisión del equipo.
- Las relaciones generadas representan posibilidades de investigación y no conclusiones estadísticas.