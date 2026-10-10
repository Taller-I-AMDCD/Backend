# Pattern Analyzer

## HU-006 — Detectar patrones candidatos

### Objetivo

Implementar un analizador inicial que identifique relaciones candidatas que puedan requerir un contraste adicional.

### Alcance

El analizador recibe relaciones entre variables acompañadas de un coeficiente de asociación.

A partir de un umbral inicial, identifica las relaciones que presentan suficiente evidencia para ser consideradas candidatas a un análisis posterior.

La implementación es independiente de la arquitectura multiagente que finalmente seleccione el equipo.

### Criterio inicial

Se utiliza un umbral de correlación absoluta de 0.5.

Las relaciones cuyo valor absoluto del coeficiente sea igual o superior al umbral son consideradas candidatas.

Este criterio es inicial y podrá ajustarse posteriormente según las decisiones del equipo.

### Salida estructurada

Cada patrón candidato contiene:

- Identificador.
- Variables involucradas.
- Coeficiente.
- Tipo de patrón detectado.
- Motivo para realizar un análisis adicional.

### Tipos de patrones

El analizador diferencia inicialmente entre:

- Asociación positiva.
- Asociación negativa.

### Validación

Se implementaron pruebas unitarias para verificar:

- Detección de asociaciones positivas.
- Detección de asociaciones negativas.
- Exclusión de relaciones por debajo del umbral.
- Detección de múltiples candidatos.
- Uso de un umbral personalizado.
- Rechazo de entradas inválidas.
- Rechazo de umbrales inválidos.
- Validación de coeficientes faltantes.

Resultado:

8 pruebas aprobadas.

### Demostración

Se utilizó un conjunto de tres relaciones:

- X → Y: 0.82
- X → Z: 0.20
- Y → Z: -0.71

Con el umbral inicial de 0.5, se identificaron dos patrones candidatos:

- X → Y: asociación positiva.
- Y → Z: asociación negativa.

La relación X → Z fue descartada por encontrarse por debajo del umbral.

### Consideraciones

- El desarrollo se realiza de manera neutral y provisional.
- No depende de una arquitectura específica.
- La identificación de un patrón candidato no constituye una validación estadística definitiva.
- La integración con la arquitectura seleccionada se realizará posteriormente.