# Generador: Subsistemas o Módulos Funcionales

> **Sección 3 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes un contexto de orientación con directorios detectados. Úsalo como índice.
DEBES leer los módulos reales para documentar sus responsabilidades funcionales.

---

## Exploración Requerida

### Lecturas obligatorias
- Archivos `__init__.py`, `index.ts`, `mod.rs` o equivalente de cada módulo principal (revelan la API pública del módulo)
- Al menos 1 archivo de lógica de negocio por módulo identificado

### Búsquedas dirigidas
- Glob: `src/*/`, `app/*/`, `lib/*/` para mapear módulos de primer nivel
- Glob: `**/module.ts`, `**/index.py`, `**/mod.go` para encontrar puntos de entrada de módulos
- Grep: `class.*Service|class.*Manager|class.*Handler` para identificar responsabilidades por módulo
- Grep: `export default|module.exports|__all__` para ver qué expone cada módulo

### Lecturas condicionales
- Si hay más de 5 módulos detectados → leer al menos el archivo principal de cada uno
- Si existe `README.md` por módulo → leerlos (documentan la responsabilidad funcional)
- Si existe un archivo de routing o feature flags → leerlo (indica módulos activables)

### Profundidad mínima
- Leer al menos 1 archivo por módulo identificado (mínimo 3 módulos)
- Documentar la responsabilidad funcional de cada módulo con evidencia del código

---

## Responsabilidades

1. Identificar módulos funcionales
2. Describir capacidades de cada módulo
3. Documentar relaciones entre módulos
4. Evaluar estado de madurez
5. Integrar evidencia y auto-validar

---

## Cobertura Obligatoria

### 1. Listado de Módulos Funcionales (OBLIGATORIO)
**Descripción:** Áreas funcionales del sistema
**Ejemplos:**
- "Módulo de Autenticación, Módulo de Usuarios, Módulo de Reportes"
- "Gestión de Pedidos, Inventario, Facturación, Pagos"
**Qué documentar:**
- Nombre de cada módulo funcional
- Responsabilidad funcional de cada uno
- Alcance (qué incluye, qué NO)
**Dónde buscar en el código:**
- Directorios de dominio (src/orders, src/inventory)
- Nombres de servicios/módulos
- Blueprints/routers agrupados

### 2. Capacidades por Módulo (OBLIGATORIO)
**Descripción:** Funcionalidades que ofrece cada módulo
**Ejemplos:**
- "Módulo de Usuarios: registro, login, recuperación de contraseña, gestión de perfil"
- "Módulo de Reportes: generación PDF, envío email, programación automática"
**Qué documentar:**
- Funcionalidades principales de cada módulo
- Operaciones CRUD o acciones específicas
- Flujos funcionales incluidos
**Dónde buscar en el código:**
- Endpoints agrupados por módulo
- Métodos de servicios
- Casos de uso implementados

### 3. Relaciones entre Módulos (OBLIGATORIO)
**Descripción:** Cómo se comunican o dependen los módulos
**Ejemplos:**
- "Módulo de Pedidos depende de Módulo de Inventario (verificar stock)"
- "Módulo de Notificaciones es usado por todos (envío de emails)"
**Qué documentar:**
- Dependencias funcionales (quién usa a quién)
- Flujos cross-módulo
- Módulos core vs auxiliares
**Dónde buscar en el código:**
- Imports entre módulos
- Llamadas a servicios de otros módulos
- Event subscriptions (si es event-driven)

### 4. Estado de Madurez y Cobertura (OBLIGATORIO)
**Descripción:** Completitud de cada módulo
**Ejemplos:**
- "Módulo de Usuarios: completo y estable"
- "Módulo de Reportes: en desarrollo (solo PDF, falta Excel)"
**Qué documentar:**
- Módulos completos vs incompletos
- Funcionalidades pendientes o TODOs
- Deuda técnica visible
**Dónde buscar en el código:**
- Comentarios TODO, FIXME
- Funciones stub o NotImplementedError
- Tests (cobertura por módulo)

---

## Proceso de Generación

### 1. Exploración

```
Glob: src/**/,**/services/,**/routers/
Grep: "from src\\..*import", "TODO", "FIXME", "NotImplementedError"
Read: Services, routers, __init__ de módulos principales
```

### 2. Análisis

- Módulos: de `componentes_clave` + exploración de directorios
- Capacidades: de endpoints/servicios en cada módulo
- Relaciones: de imports entre módulos
- Estado de madurez: de TODOs/FIXMEs y funciones no implementadas

### 3. Sustento

Integrar evidencia de código en el desarrollo. Citar archivos de servicios, routers y módulos explorados.

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Módulos identificados y descritos
- [ ] Capacidades documentadas por módulo
- [ ] Relaciones documentadas
- [ ] Estado de madurez mencionado
- [ ] Archivos citados (4 small, 6 medium, 9 large)

---

## Criterios de Completitud

- [ ] Módulos identificados
- [ ] Capacidades descritas por módulo
- [ ] Relaciones documentadas
- [ ] Estado de madurez mencionado
- [ ] Archivos citados (4 small, 6 medium, 9 large)


