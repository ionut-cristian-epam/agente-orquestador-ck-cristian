# Plantillas de Salida DDF

> **Templates estrictos** para generación de documentación
> **Última actualización:** 2026-03-12

---

## Template 1: Documento Completo (12 Secciones)

Usar **exactamente** esta estructura para DDF completo:

```markdown
# Documento de Diseño Funcional (DDF)

> **Proyecto:** [Nombre del proyecto detectado]
> **Versión:** [Detectada de package.json, pyproject.toml, etc. o "1.0.0"]
> **Fecha:** [Fecha actual YYYY-MM-DD]
> **Generado desde:** Análisis de código fuente
> **Lenguaje/Stack:** [Detectado: Python/FastAPI, Node.js/Express, etc.]

---

## Tabla de Contenidos

1. [Introducción y Contexto](#1-introducción-y-contexto)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Subsistemas o Módulos Funcionales](#3-subsistemas-o-módulos-funcionales)
4. [Casos de Uso Detallados](#4-casos-de-uso-detallados)
5. [Modelo Conceptual Exhaustivo](#5-modelo-conceptual-exhaustivo)
6. [Interfaces Detalladas](#6-interfaces-detalladas)
7. [Flujos de Datos](#7-flujos-de-datos)
8. [Requisitos No Funcionales Detallados](#8-requisitos-no-funcionales-detallados)
9. [Reglas Globales y Restricciones del Sistema](#9-reglas-globales-y-restricciones-del-sistema)
10. [Algoritmos y Procesos Críticos](#10-algoritmos-y-procesos-críticos)
11. [Gestión de Errores](#11-gestión-de-errores)
12. [Consideraciones de Despliegue](#12-consideraciones-de-despliegue)
13. [Apéndices](#apéndices)

---

## Resumen Ejecutivo

### Visión General

[2-3 párrafos describiendo:
- Qué es el sistema (propósito funcional)
- Stack tecnológico principal
- Valor de negocio que aporta
- Alcance funcional]

### Tecnologías Clave

- **Lenguaje principal:** [Detectado]
- **Framework:** [Detectado]
- **Base de datos:** [Detectada]
- **Integraciones:** [Listado de sistemas externos]
- **Infraestructura:** [Docker, cloud, on-premise, etc.]

### Hallazgos Críticos

[TOP 5 hallazgos más importantes extraídos de todas las secciones, rankeados por impacto funcional]

1. **[Hallazgo 1]**: [Descripción breve + sección origen]
2. **[Hallazgo 2]**: [Descripción breve + sección origen]
3. **[Hallazgo 3]**: [Descripción breve + sección origen]
4. **[Hallazgo 4]**: [Descripción breve + sección origen]
5. **[Hallazgo 5]**: [Descripción breve + sección origen]

### Riesgos Identificados

[TOP 3 riesgos funcionales detectados en el código]

⚠️ **[Riesgo 1]**: [Descripción + impacto + sección]
⚠️ **[Riesgo 2]**: [Descripción + impacto + sección]
⚠️ **[Riesgo 3]**: [Descripción + impacto + sección]

### Métricas del Sistema

- **Módulos funcionales:** [N] (de Sección 3)
- **Casos de uso identificados:** [N] (de Sección 4)
- **APIs/Endpoints:** [N] (de Sección 6)
- **Reglas de negocio:** [N] (de Sección 9)
- **Entidades de dominio:** [N] (de Sección 5)

### Recomendaciones Inmediatas

[3-5 recomendaciones accionables basadas en el análisis]

---

## 1. Introducción y Contexto

[Contenido generado por micro-skill]

---

## 2. Arquitectura del Sistema

[Contenido generado por micro-skill]

---

## 3. Subsistemas o Módulos Funcionales

[Contenido generado por micro-skill]

---

## 4. Casos de Uso Detallados

[Contenido generado por micro-skill]

---

## 5. Modelo Conceptual Exhaustivo

[Contenido generado por micro-skill]

---

## 6. Interfaces Detalladas

[Contenido generado por micro-skill]

---

## 7. Flujos de Datos

[Contenido generado por micro-skill]

---

## 8. Requisitos No Funcionales Detallados

[Contenido generado por micro-skill]

---

## 9. Reglas Globales y Restricciones del Sistema

[Contenido generado por micro-skill]

---

## 10. Algoritmos y Procesos Críticos

[Contenido generado por micro-skill]

---

## 11. Gestión de Errores

[Contenido generado por micro-skill]

---

## 12. Consideraciones de Despliegue

[Contenido generado por micro-skill]

---

## Apéndices

### A. Archivos Analizados

[Listado consolidado de TODOS los archivos citados en las 12 secciones, sin duplicados, ordenados alfabéticamente]

```
path/to/file1.ext - [Propósito]
path/to/file2.ext - [Propósito]
...
```

**Total:** [N] archivos

### B. Tecnologías Detectadas

[Lista exhaustiva de tecnologías, frameworks, bibliotecas identificadas]

**Categorías:**
- **Lenguajes:** [Lista]
- **Frameworks:** [Lista]
- **Bases de datos:** [Lista]
- **Colas/Mensajería:** [Lista]
- **Cache:** [Lista]
- **Autenticación:** [Lista]
- **Testing:** [Lista]
- **Deployment:** [Lista]

### C. Vacíos Identificados

[Unión de todos los vacíos reportados en las 12 secciones]

⚠️ **Información no encontrada en el código:**

1. [Vacío 1 - Sección origen]
2. [Vacío 2 - Sección origen]
...

💡 **Para completar, considerar analizar:**
- [Artefacto sugerido 1]
- [Artefacto sugerido 2]
...

### D. Matriz de Trazabilidad

[Tabla que relaciona componentes arquitectónicos con módulos, interfaces y casos de uso]

| Componente (S2) | Módulo (S3) | Interface (S6) | Caso de Uso (S4) |
|----------------|-------------|----------------|------------------|
| [Componente A] | [Módulo X]  | [API Y]        | [CU-01]          |
| [Componente B] | [Módulo Z]  | [API W]        | [CU-02]          |
| ...            | ...         | ...            | ...              |

### E. Próximos Pasos Sugeridos

[Recomendaciones basadas en:
- Vacíos detectados
- Riesgos identificados
- Mejores prácticas no implementadas
- Deuda técnica observable]

**Prioridad Alta:**
1. [Acción 1]
2. [Acción 2]

**Prioridad Media:**
3. [Acción 3]
4. [Acción 4]

**Prioridad Baja:**
5. [Acción 5]

---

📄 **Fin del Documento de Diseño Funcional**

---

**Notas de Generación:**
- Documento generado automáticamente desde código fuente
- Score de calidad: [NN]/100
- Archivos analizados: [N]
- Tiempo de generación: [N] minutos
- Hallazgos totales: [N]
```

---

## Template 2: Sección Individual

Usar **exactamente** esta estructura para secciones individuales:

```markdown
## [N]. [Título de Sección Canónica]

> **Sección [N] de 12** del Documento de Diseño Funcional
> **Proyecto:** [Nombre detectado]
> **Fecha:** [YYYY-MM-DD]
> **Generado desde:** Análisis de código fuente

---

### Objetivo funcional

[1-2 párrafos explicando el propósito de esta sección y qué información aporta]

---

### Hallazgos clave desde el código

[Mínimo adaptativo según tamaño del proyecto:
- Small: ≥1 hallazgos
- Medium: ≥2 hallazgos
- Large: ≥3 hallazgos]

- **[Hallazgo 1]**: [Descripción con evidencia integrada - mencionar archivos/componentes específicos]
- **[Hallazgo 2]**: [Descripción con evidencia integrada]
- **[Hallazgo 3]**: [Descripción con evidencia integrada] (si aplica)
- **[Hallazgo N]**: [Continuar si hay más hallazgos significativos]

---

### Desarrollo

[Apartados obligatorios según definición de sección - ver `sections/[NN]-[nombre].md`]

#### [Apartado Obligatorio 1]

[Contenido funcional detallado con evidencia de código integrada.
Mencionar rutas, componentes, clases, módulos específicos.
NO crear bloque separado de "Evidencia analizada".]

[Ejemplo de integración:
"El sistema implementa autenticación JWT en `src/auth/jwt.py`, manejada por la clase `JWTAuthenticator` que valida tokens en cada request a través del middleware `AuthMiddleware` definido en `src/middleware/auth.py`."]

#### [Apartado Obligatorio 2]

[Contenido funcional con evidencia integrada]

[... resto de apartados obligatorios según definición de sección ...]

---

### Supuestos o vacíos

[SI APLICA: listar información que no se pudo encontrar en el código]

- ⚠️ [Vacío 1]: No se encontró [qué] en el código analizado. Considerar revisar [artefacto sugerido].
- ⚠️ [Vacío 2]: [Descripción del vacío + sugerencia]
- ...

[SI NO HAY VACÍOS: "✅ No se identificaron vacíos significativos en esta sección."]

---

### Archivos analizados en esta sección

[Listado de archivos citados en esta sección específica, con su propósito]

```
path/to/file1.ext - [Propósito/Razón de análisis]
path/to/file2.ext - [Propósito]
path/to/file3.ext - [Propósito]
...
```

**Total:** [N] archivos analizados para esta sección

[Verificar mínimos según tamaño del proyecto:
- Small: ≥3 archivos
- Medium: ≥5 archivos
- Large: ≥8 archivos]

---

📄 **Fin de Sección [N]**

---

**Notas de Generación:**
- Sección generada automáticamente desde código fuente
- Score de calidad: [NN]/100
- Tiempo de generación: ~[N] minuto(s)
```

---

## Reglas de Formato

### Markdown
- Usar títulos con `##` para secciones principales
- Usar `###` para apartados dentro de secciones
- Usar `####` para sub-apartados
- Listas con `-` o `1.` según corresponda
- Énfasis con `**bold**` para conceptos clave
- Código inline con backticks: `` `code` ``
- Bloques de código con triple backticks

### Evidencia Integrada
✅ **CORRECTO - Evidencia integrada:**
"El módulo de pagos (`src/payments/processor.py`) implementa el patrón Strategy para soportar múltiples gateways: `StripeGateway`, `PayPalGateway` y `BraintreeGateway`."

❌ **INCORRECTO - Bloque separado:**
```
### Evidencia analizada
- src/payments/processor.py
- src/payments/gateways/stripe.py
```

### Tono y Estilo
- **Funcional, no técnico excesivo:** Orientado a audiencia de negocio
- **Específico:** Citar nombres reales del código, no generalizar
- **Accionable:** Información útil para toma de decisiones
- **Conciso pero completo:** Balance entre brevedad y exhaustividad

### Estructura de Hallazgos
Cada hallazgo debe:
1. Tener un título descriptivo en **bold**
2. Incluir evidencia específica (rutas, componentes)
3. Explicar el impacto o relevancia funcional
4. Ser verificable en el código

---

## Adaptación por Tamaño de Proyecto

### Proyectos Small (<1000 LOC)
- Resumen ejecutivo: 1-2 párrafos
- Hallazgos por sección: ≥1
- Archivos citados por sección: ≥3
- Extensión de sección: 100-300 palabras

### Proyectos Medium (1000-10000 LOC)
- Resumen ejecutivo: 3-4 párrafos
- Hallazgos por sección: ≥2
- Archivos citados por sección: ≥5
- Extensión de sección: 300-600 palabras

### Proyectos Large (>10000 LOC)
- Resumen ejecutivo: 1 página
- Hallazgos por sección: ≥3
- Archivos citados por sección: ≥8
- Extensión de sección: 600-1000 palabras

---

## Notas Finales

1. **Consistencia:** Usar el mismo formato en todas las secciones
2. **Referencias cruzadas:** Permitidas con formato: "(ver Sección [N]: [Título])"
3. **Actualizaciones:** Incluir fecha en metadatos
4. **Versionado:** Sincronizar con versión del código analizado
