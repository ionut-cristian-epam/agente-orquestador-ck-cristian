# Generador: Reglas Globales y Restricciones del Sistema

> **Sección 9 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes la estructura general del proyecto. DEBES leer los validators,
servicios de dominio y migraciones reales para documentar reglas y restricciones
con evidencia concreta.

---

## Exploración Requerida

### Lecturas obligatorias
- Al menos 3 archivos de validators o schemas con validaciones
- Al menos 2 archivos de services con lógica de negocio compleja
- Archivos de migración o schema de BD con constraints

### Búsquedas dirigidas
- Glob: `**/validators/**`, `**/rules/**`, `**/policies/**`, `**/schemas/**`
- Grep: `raise.*Exception|ValidationError|Field\(|def validate` para encontrar validaciones
- Grep: `UNIQUE|CHECK|NOT NULL|ForeignKey.*cascade` para restricciones de integridad
- Grep: `rate_limit|throttle|max_.*|limit.*=` para políticas operacionales

### Lecturas condicionales
- Si existen domain objects o aggregates → leer para identificar invariantes
- Si existen tests de validación → leer 2 (revelan reglas esperadas)

### Profundidad mínima
- Leer al menos 5 archivos antes de generar
- Documentar al menos 5 reglas concretas con evidencia de código

---

## Responsabilidades

1. Documentar reglas de validación de datos
2. Identificar reglas de negocio complejas
3. Especificar restricciones de integridad
4. Describir políticas y límites operacionales

---

## Cobertura Obligatoria

### 1. Reglas de Validación de Datos (OBLIGATORIO)
**Descripción:** Validaciones aplicadas a los datos de entrada
**Ejemplos:**
- "Email debe ser único y válido (regex)"
- "Edad debe ser >= 18"
- "Precio debe ser > 0"
**Qué documentar:**
- Validaciones de formato, rango y unicidad
- Validaciones condicionales
**Dónde buscar en el código:**
- Validators (Pydantic, Marshmallow, custom validators)
- Constraints de BD (UNIQUE, CHECK, NOT NULL)
- Métodos validate_*

### 2. Reglas de Negocio Complejas (OBLIGATORIO)
**Descripción:** Lógica de negocio más allá de validaciones simples
**Ejemplos:**
- "Descuento solo aplicable si total > $100 AND cliente es premium"
- "No se puede cancelar orden si ya fue enviada"
**Qué documentar:**
- Reglas condicionales complejas
- Reglas que involucran múltiples entidades
- Políticas de negocio
**Dónde buscar en el código:**
- Services (business logic layer)
- Métodos can_*, is_*, should_*
- State machines (transiciones condicionales)

### 3. Restricciones de Integridad (OBLIGATORIO)
**Descripción:** Reglas que mantienen consistencia de datos
**Ejemplos:**
- "Al eliminar usuario, eliminar cascada sus pedidos"
- "Stock no puede ser negativo"
**Qué documentar:**
- Foreign key constraints y cascade
- Invariantes de agregados
- Checks de consistencia
**Dónde buscar en el código:**
- Foreign keys con cascade
- Constraints CHECK en BD
- Validaciones de integridad en servicios

### 4. Políticas y Límites Operacionales (OBLIGATORIO)
**Descripción:** Restricciones de uso y límites del sistema
**Ejemplos:**
- "Máximo 10 intentos de login fallidos antes de bloqueo"
- "Rate limit: 100 requests/minuto por API key"
- "Máximo 50 items por pedido"
**Qué documentar:**
- Rate limiting
- Quotas y límites
- Políticas de reintentos y timeouts
**Dónde buscar en el código:**
- Middleware de rate limiting
- Configuraciones de límites
- Validaciones de cantidad máxima

---

## Proceso de Generación

### 1. Exploración

```
Glob: **/validators/**, **/services/**, **/migrations/**, **/schemas/**
Grep: "def validate", "CHECK", "UNIQUE", "rate_limit", "validator", "Field\\("
Read: Validators, services con lógica de negocio, migraciones con constraints
```

### 2. Análisis

- Validaciones: de schemas (Pydantic, Joi, etc.), validators, field definitions
- Reglas de negocio: de lógica condicional en services con múltiples pasos
- Integridad: de UNIQUE, FK, CHECK constraints en modelos y migraciones
- Límites: de rate limiters, timeout configs, quota configs

### 3. Sustento

Integrar evidencia de código. Citar archivos de validators, services y migraciones al documentar cada regla.

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Reglas de validación identificadas (≥3)
- [ ] Reglas de negocio documentadas (≥2)
- [ ] Restricciones de integridad mencionadas
- [ ] Políticas/límites operacionales descritos
- [ ] Archivos citados (4 small, 6 medium, 9 large)

---

## Criterios de Completitud

- [ ] Reglas de validación (≥3)
- [ ] Reglas de negocio (≥2)
- [ ] Restricciones de integridad
- [ ] Políticas/límites operacionales
- [ ] Archivos citados (4 small, 6 medium, 9 large)


