# Generador: Algoritmos y Procesos Críticos

> **Sección 10 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes la estructura general del proyecto. DEBES leer los servicios y jobs
reales para identificar algoritmos y procesos críticos con sus pasos concretos.

---

## Exploración Requerida

### Lecturas obligatorias
- Al menos 3 archivos de services con lógica computacional o multi-paso
- Archivos de background jobs, tasks o workers si existen

### Búsquedas dirigidas
- Glob: `**/algorithms/**`, `**/engine/**`, `**/calculators/**`, `**/tasks/**`
- Grep: `def.*calculate|def.*compute|def.*process|def.*generate` para algoritmos
- Grep: `@task|@job|@periodic|celery|rq\.job|schedule` para jobs asíncronos
- Grep: `cache\.|bulk_|batch_|async def` para optimizaciones

### Lecturas condicionales
- Si existe ML o IA → buscar archivos de modelos/predicciones y leerlos
- Si existe lógica financiera → leer servicios de cálculo de precios/impuestos

### Profundidad mínima
- Leer al menos 4 archivos antes de generar
- Documentar al menos 1 algoritmo complejo con sus pasos detallados

---

## Responsabilidades

1. Identificar algoritmos de cálculo críticos
2. Documentar workflows de negocio
3. Describir procesos asíncronos y background jobs
4. Mencionar algoritmos de optimización

---

## Cobertura Obligatoria

### 1. Algoritmos de Cálculo (OBLIGATORIO)
**Descripción:** Lógica matemática o computacional compleja
**Ejemplos:**
- "Cálculo de precio con impuestos, descuentos y envío"
- "Algoritmo de matching entre usuarios y productos"
**Qué documentar:**
- Propósito del algoritmo
- Inputs y outputs
- Pasos principales
**Dónde buscar en el código:**
- Funciones calculate_*, compute_*
- Servicios con lógica matemática
- Algoritmos de scoring, ranking, matching

### 2. Workflows de Negocio (OBLIGATORIO)
**Descripción:** Procesos multi-paso que implementan lógica de negocio
**Ejemplos:**
- "Workflow de aprobación: validar → revisar → aprobar → procesar"
- "Onboarding: registrar → verificar email → completar perfil → activar"
**Qué documentar:**
- Nombre del workflow
- Pasos secuenciales y condiciones
- Estados intermedios
**Dónde buscar en el código:**
- Services con múltiples pasos
- State machines, saga patterns
- Orchestration logic

### 3. Procesos Asíncronos y Background Jobs (OBLIGATORIO)
**Descripción:** Tareas que se ejecutan fuera del flujo principal
**Ejemplos:**
- "Job nocturno de generación de reportes"
- "Worker asíncrono para procesamiento de imágenes"
**Qué documentar:**
- Tipo de job (cron, event-triggered, manual)
- Frecuencia o trigger y qué procesa
**Dónde buscar en el código:**
- Celery tasks, RQ jobs, Bull queues
- Cron configurations, background workers

### 4. Algoritmos de Optimización (OBLIGATORIO)
**Descripción:** Lógica para mejorar eficiencia o resultados
**Ejemplos:**
- "Cache de resultados de queries frecuentes"
- "Batch processing para reducir llamadas a BD"
**Qué documentar:**
- Qué se optimiza (tiempo, memoria, costos)
- Técnica usada (cache, batch, lazy loading)
**Dónde buscar en el código:**
- Implementaciones de cache
- Batch inserts/updates
- Lazy loading, eager loading, índices de BD

---

## Proceso de Generación

### 1. Exploración

```
Glob: **/services/**, **/tasks/**, **/jobs/**, **/workers/**
Grep: "def calculate", "def compute", "@task", "@job", "@periodic", "async def"
Read: Services con lógica compleja, tasks, workers, jobs
```

### 2. Análisis

- Algoritmos: funciones con cálculos multi-paso (`calculate_*`, `compute_*`, `process_*`)
- Workflows: servicios que coordinan múltiples operaciones secuenciales
- Jobs asíncronos: tasks de Celery, cron jobs, workers de colas
- Optimizaciones: uso de índices, caching de cálculos costosos, bulk operations

### 3. Sustento

Integrar evidencia de código. Citar archivos de services y tasks al describir cada proceso.

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Al menos 1 algoritmo de cálculo documentado
- [ ] Al menos 1 workflow de negocio descrito
- [ ] Procesos asíncronos documentados (si existen)
- [ ] Optimizaciones mencionadas (si existen)
- [ ] Archivos citados (3 small, 5 medium, 8 large)

---

## Criterios de Completitud

- [ ] Algoritmos de cálculo (≥1)
- [ ] Workflows (≥1)
- [ ] Procesos asíncronos (si existen)
- [ ] Optimizaciones (si existen)
- [ ] Archivos citados (3 small, 5 medium, 8 large)


