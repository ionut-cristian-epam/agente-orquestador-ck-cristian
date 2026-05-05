# Checklist de Calidad DDF

Framework de validacion para secciones individuales y documentos completos.

---

## 1. Gates Obligatorios

Si una seccion falla cualquiera de estos gates, no debe aprobarse aunque el score numerico sea alto.

### Gate 1. Titulo Canonico

- La seccion usa el titulo canonico correcto.
- El numero de seccion coincide con el titulo.

### Gate 2. Cobertura Obligatoria

- Todos los apartados obligatorios del generador correspondiente aparecen cubiertos.
- Si falta informacion, debe declararse como vacio o supuesto, no omitirse silenciosamente.

### Gate 3. Evidencia Integrada

- La seccion cita archivos o elementos concretos del codigo.
- La evidencia esta integrada en hallazgos y desarrollo.
- No existe un bloque separado de evidencia.

### Gate 4. Formato Valido

- La salida sigue `references/output-template.md`.
- El markdown esta bien formado.
- Incluye metadatos requeridos.

### Gate 5. Minimos Adaptativos

- Cumple el minimo de hallazgos por tamano de proyecto.
- Cumple el minimo de archivos citados por tamano de proyecto.

---

## 2. Scoring Operable

Aplicar score solo despues de pasar los gates obligatorios.

### 2.1. Completitud de Contenido

**30 puntos**

- 30: cubre todos los apartados obligatorios con desarrollo suficiente.
- 20: cubre todos los apartados, pero uno o mas estan superficiales.
- 10: faltan matices importantes aunque la estructura este presente.
- 0: falta al menos un apartado obligatorio.

### 2.2. Sustento desde Codigo

**25 puntos**

- 25: evidencia clara, especifica e integrada de forma consistente.
- 15: evidencia suficiente, pero parcial o poco distribuida.
- 5: evidencia minima o poco precisa.
- 0: afirmaciones sin respaldo visible.

### 2.3. Formato y Estructura

**15 puntos**

- 15: respeta completamente la plantilla y el orden esperado.
- 10: pequenas desviaciones sin afectar el uso.
- 5: formato irregular pero recuperable.
- 0: formato incompatible con la plantilla.

### 2.4. Vacios y Supuestos

**10 puntos**

- 10: diferencia bien hallazgos, vacios y supuestos.
- 5: existen vacios, pero no siempre estan bien clasificados.
- 0: oculta incertidumbre o afirma sin base.

### 2.5. Relevancia Funcional

**10 puntos**

- 10: enfocado en valor funcional y decisiones de negocio.
- 5: mezcla adecuada, pero con exceso tecnico.
- 0: contenido predominantemente tecnico sin foco funcional.

### 2.6. Coherencia Interna

**10 puntos**

- 10: sin contradicciones internas y con narrativa consistente.
- 5: pequenas tensiones o terminologia inestable.
- 0: contradicciones claras.

**Score total:** 100 puntos.

---

## 3. Minimos Adaptativos por Tamano

### Small

- LOC: <1000
- Hallazgos minimos por seccion: 1
- Archivos citados minimos: 3
- Extension objetivo: 100-300 palabras
- Score minimo: 60

### Medium

- LOC: 1000-10000
- Hallazgos minimos por seccion: 2
- Archivos citados minimos: 5
- Extension objetivo: 300-600 palabras
- Score minimo: 70

### Large

- LOC: >10000
- Hallazgos minimos por seccion: 3
- Archivos citados minimos: 8
- Extension objetivo: 600-1000 palabras
- Score minimo: 75

---

## 4. Politica de Reintento

Permitir solo un reintento por seccion y solo si el fallo es reparable con mas lectura o mejor estructuracion.

### Reintentar Si

- Falta cubrir un apartado obligatorio.
- Hay evidencia insuficiente, pero hay rutas claras para seguir leyendo.
- El formato no sigue exactamente la plantilla.

### No Reintentar Si

- La informacion no existe en el repositorio analizado.
- El problema es ambiguedad no resuelta en la peticion del usuario.
- La seccion ya declaro correctamente los vacios y aun asi no alcanza profundidad ideal.

### Resultado Tras Reintento Fallido

- Entregar la seccion con vacios declarados.
- Indicar brevemente que no se encontro mas evidencia concluyente.
- No seguir iterando.

---

## 5. Validaciones Inter-Seccionales

Aplican cuando se generan dos o mas secciones, y son obligatorias para documentos completos.

### 5.1. Coherencia de Entidades

Verificar:

- Componentes de arquitectura en secciones de modulos.
- Actores de contexto en casos de uso.
- Entidades de dominio en interfaces.
- Flujos de datos alineados con casos de uso.
- Reglas conectadas con algoritmos.
- Errores relacionados con flujos o procesos donde corresponda.

### 5.2. Trazabilidad Cruzada

Construir matriz de trazabilidad para documento completo:

| De | A | Verificacion |
|---|---|---|
| S2 | S3 | Componentes a modulos |
| S1 | S4 | Actores a roles o escenarios |
| S5 | S6 | Entidades a DTOs, contratos o payloads |
| S4 | S7 | Operaciones a flujos de datos |
| S9 | S10 | Reglas a implementaciones |
| S4 | S11 | Flujos alternos a manejo de errores |

### 5.3. Contradicciones

Si hay contradicciones graves entre secciones, el documento completo no aprueba aunque las secciones individuales hayan aprobado.

Ejemplos de contradiccion grave:

- una seccion afirma monolito y otra microservicios sin evidencia de ambas;
- una seccion afirma actor humano principal y otra solo integraciones automaticas para el mismo flujo;
- una seccion afirma base de datos relacional y otra documenta persistencia exclusiva en cache.

---

## 6. Causas de Rechazo Rapido

Rechazar sin score si ocurre cualquiera de estas condiciones:

- titulo no canonico;
- ausencia de evidencia concreta;
- apartados obligatorios omitidos;
- afirmaciones claramente inventadas;
- mezcla no declarada de hallazgos y supuestos;
- documento completo con contradicciones graves.