# Catalogo Canonico de Secciones DDF

Referencia autorizada para deteccion de intencion, orden de ensamblado y nombres de seccion.

---

## Secciones Canonicas

Mantener exactamente este orden y estos titulos:

1. Introduccion y Contexto
2. Arquitectura del Sistema
3. Subsistemas o Modulos Funcionales
4. Casos de Uso Detallados
5. Modelo Conceptual Exhaustivo
6. Interfaces Detalladas
7. Flujos de Datos
8. Requisitos No Funcionales Detallados
9. Reglas Globales y Restricciones del Sistema
10. Algoritmos y Procesos Criticos
11. Gestion de Errores
12. Consideraciones de Despliegue

---

## Regla de Oro de Intencion

No asumir alcance completo si la peticion del usuario no lo dice de forma explicita o no acumula evidencia suficiente.

---

## Senales de Alcance

### Alcance Completo

Detectar modo completo cuando ocurra al menos una de estas condiciones:

1. La peticion contiene una senal explicita de documento completo:
   - completo
   - entero
   - todo
   - full
   - todas las secciones
   - documento completo
   - ddf completo
2. La peticion menciona 4 o mas secciones diferentes y no contiene limitadores como `solo`, `unicamente`, `solo la parte de`.

### Alcance Parcial

Detectar modo parcial cuando ocurra al menos una de estas condiciones:

1. La peticion nombra una o mas secciones canonicas de forma exacta.
2. La peticion incluye limitadores como:
   - solo
   - unicamente
   - nada mas
   - centrate en
   - especificamente
3. Las keywords mapean con confianza alta a 1-3 secciones.

### Alcance Ambiguo

Pedir aclaracion cuando ocurra cualquiera de estos casos:

1. El score maximo de match es menor que 2.
2. Las dos secciones mejor puntuadas difieren por 1 punto o menos y la peticion no contiene un titulo canonico exacto.
3. La peticion mezcla senales de completo y parcial.
4. La peticion usa verbos genericos como `documenta`, `analiza`, `explica` sin indicar alcance.

---

## Prioridad de Matching

Aplicar este orden de precedencia:

1. Titulo canonico exacto.
2. Keyword fuerte de seccion con limitador explicito.
3. Grupo de keywords convergentes en la misma seccion.
4. Keyword aislada.

Si una regla de mayor prioridad contradice a una de menor prioridad, gana la de mayor prioridad.

---

## Mapeo de Palabras Clave

### Seccion 1: Introduccion y Contexto
**Generador:** `section-generators/01-introduccion-contexto.md`
**Keywords fuertes:** introduccion, contexto, proposito, alcance
**Keywords secundarias:** problema de negocio, objetivos, vision, actores principales, stakeholders, justificacion

### Seccion 2: Arquitectura del Sistema
**Generador:** `section-generators/02-arquitectura-sistema.md`
**Keywords fuertes:** arquitectura, capas, componentes, patron arquitectonico
**Keywords secundarias:** estructura, organizacion tecnica, topologia, hexagonal, microservicios, monolitico

### Seccion 3: Subsistemas o Modulos Funcionales
**Generador:** `section-generators/03-subsistemas-modulos.md`
**Keywords fuertes:** modulos, subsistemas, capacidades, funcionalidades
**Keywords secundarias:** dominios, paquetes, features, division funcional, areas funcionales

### Seccion 4: Casos de Uso Detallados
**Generador:** `section-generators/04-casos-uso.md`
**Keywords fuertes:** casos de uso, use cases, escenarios
**Keywords secundarias:** actores, roles, flujos de usuario, interacciones, historias, operaciones

### Seccion 5: Modelo Conceptual Exhaustivo
**Generador:** `section-generators/05-modelo-conceptual.md`
**Keywords fuertes:** modelo conceptual, entidades, dominio
**Keywords secundarias:** objetos de negocio, relaciones, asociaciones, esquema, estructura de informacion

### Seccion 6: Interfaces Detalladas
**Generador:** `section-generators/06-interfaces-detalladas.md`
**Keywords fuertes:** interfaces, apis, contratos, endpoints
**Keywords secundarias:** servicios, metodos, operaciones, integracion, rest, graphql, grpc, soap

### Seccion 7: Flujos de Datos
**Generador:** `section-generators/07-flujos-datos.md`
**Keywords fuertes:** flujos de datos, data flow, pipeline
**Keywords secundarias:** transformaciones, etl, movimiento de informacion, origen, destino, ruta de datos

### Seccion 8: Requisitos No Funcionales Detallados
**Generador:** `section-generators/08-requisitos-no-funcionales.md`
**Keywords fuertes:** requisitos no funcionales, nfr, calidad
**Keywords secundarias:** rendimiento, performance, escalabilidad, disponibilidad, fiabilidad, seguridad, mantenibilidad, latencia

### Seccion 9: Reglas Globales y Restricciones del Sistema
**Generador:** `section-generators/09-reglas-restricciones.md`
**Keywords fuertes:** reglas de negocio, restricciones, validaciones
**Keywords secundarias:** politicas, invariantes, condiciones, limites, compliance, regulaciones

### Seccion 10: Algoritmos y Procesos Criticos
**Generador:** `section-generators/10-algoritmos-procesos.md`
**Keywords fuertes:** algoritmos, procesos, logica compleja
**Keywords secundarias:** calculos, procedimientos, workflows, operaciones complejas, rutinas

### Seccion 11: Gestion de Errores
**Generador:** `section-generators/11-gestion-errores.md`
**Keywords fuertes:** errores, excepciones, fallos
**Keywords secundarias:** manejo de errores, logs, auditoria, recovery, rollback, resiliencia

### Seccion 12: Consideraciones de Despliegue
**Generador:** `section-generators/12-consideraciones-despliegue.md`
**Keywords fuertes:** despliegue, deployment, release, infraestructura
**Keywords secundarias:** ambientes, entornos, ci/cd, devops, produccion, staging, setup

---

## Salida Esperada de la Fase de Intencion

La deteccion debe producir una estructura como esta:

```json
{
  "mode": "complete|partial|clarify",
  "sections_to_generate": [2, 6],
  "confidence": "high|medium|low",
  "reason": "senales detectadas"
}
```

---

## Pregunta de Aclaracion Recomendada

Si la intencion es ambigua, preguntar con esta forma:

1. DDF completo de 12 secciones.
2. Secciones especificas.

Si el usuario elige secciones especificas, ofrecer la lista completa de 12 secciones canonicas en multiseleccion.

---

## Regla de Ensamblado

Cuando se generen varias secciones, siempre ensamblarlas en el orden canonico definido arriba, aunque se hayan solicitado en otro orden.