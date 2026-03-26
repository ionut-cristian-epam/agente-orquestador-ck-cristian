# Generador: Modelo Conceptual Exhaustivo

> **Sección 5 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes la estructura del proyecto. DEBES leer los modelos/entidades reales para
documentar el modelo conceptual con atributos y relaciones concretas.

---

## Exploración Requerida

### Lecturas obligatorias
- Todos los archivos de modelos/entidades encontrados en `models/`, `entities/`, `domain/`
- Archivos de migración de base de datos si existen (`migrations/`, `alembic/versions/`)

### Búsquedas dirigidas
- Glob: `**/models/**`, `**/entities/**`, `**/domain/model*`, `**/schemas/**`
- Grep: `class.*Model|class.*Entity|@Entity|interface.*Schema` para encontrar definiciones de entidad
- Grep: `ForeignKey|relationship|OneToMany|ManyToOne|BelongsTo|HasMany` para mapear relaciones
- Grep: `Column|field|attribute|property` para encontrar atributos relevantes

### Lecturas condicionales
- Si existe un ORM configurado (SQLAlchemy, TypeORM, Hibernate) → leer al menos 4 archivos de modelos
- Si existe un esquema de base de datos (`schema.sql`, `schema.prisma`) → leerlo completo
- Si existen migrations → leer las más recientes (revelan la estructura actual)

### Profundidad mínima
- Leer TODOS los archivos de modelos disponibles (hasta 10; si hay más, los 10 más importantes)
- Documentar atributos clave y tipo de dato de cada entidad
- Identificar al menos 3 relaciones entre entidades con evidencia de código

---

## Responsabilidades

1. Identificar entidades del dominio
2. Documentar relaciones entre entidades
3. Especificar reglas de dominio
4. Describir ciclo de vida de entidades clave

---

## Cobertura Obligatoria

### 1. Entidades del Dominio (OBLIGATORIO)
**Descripción:** Objetos de negocio principales del sistema
**Ejemplos:**
- "Usuario, Pedido, Producto, Pago, Factura"
- "Paciente, Médico, Cita, Historia Clínica"
**Qué documentar:**
- Lista de entidades principales
- Propósito funcional de cada entidad
- Atributos clave (no todos, solo los principales)
**Dónde buscar en el código:**
- Models, entities, schemas
- Clases de dominio
- Tablas de BD (migrations, schema.sql)

### 2. Relaciones entre Entidades (OBLIGATORIO)
**Descripción:** Cómo se conectan las entidades
**Ejemplos:**
- "Usuario tiene muchos Pedidos (1:N)"
- "Pedido tiene muchos Productos, Producto en muchos Pedidos (N:M)"
**Qué documentar:**
- Tipo de relación (1:1, 1:N, N:M)
- Cardinalidad y opcionalidad
- Significado funcional de la relación
**Dónde buscar en el código:**
- Foreign keys en modelos
- Relaciones ORM (relationship, ForeignKey, ManyToMany)
- Referencias en schemas/DTOs

### 3. Reglas de Dominio sobre Entidades (OBLIGATORIO)
**Descripción:** Invariantes, validaciones, restricciones de negocio
**Ejemplos:**
- "Usuario debe tener email único"
- "Pedido no puede tener total negativo"
- "Producto debe tener precio > 0"
**Qué documentar:**
- Validaciones en modelos/entidades
- Constraints de BD (UNIQUE, NOT NULL, CHECK)
- Reglas de negocio implementadas
**Dónde buscar en el código:**
- Validators en modelos
- Constraints en migrations/schema
- Métodos de validación (validate_*, is_valid)

### 4. Ciclo de Vida de Entidades Clave (OBLIGATORIO)
**Descripción:** Estados por los que pasa una entidad
**Ejemplos:**
- "Pedido: DRAFT → PENDING → CONFIRMED → SHIPPED → DELIVERED → CLOSED"
- "Usuario: REGISTERED → ACTIVE → SUSPENDED → DELETED"
**Qué documentar:**
- Estados posibles (enum, constantes)
- Transiciones permitidas
- Eventos que causan cambios de estado
**Dónde buscar en el código:**
- Enums de estado (StatusEnum, OrderStatus)
- Campos status en modelos
- Lógica de transición de estados (state machine)

---

## Proceso de Generación

### 1. Exploración

```
Glob: **/models/*.py, **/entities/*.py, **/schemas/*.py, **/migrations/*.sql
Grep: "ForeignKey", "relationship", "ManyToMany", "UNIQUE", "CHECK"
Read: Models, schemas, migrations principales
```

### 2. Análisis

- Entidades: de modelos/schemas detectados
- Relaciones: de ForeignKey, relationship, ManyToMany
- Reglas: de validators, constraints en modelos y migraciones
- Ciclo de vida: de enums de estado, state machines, campos de status

### 3. Sustento

Integrar evidencia de código. Citar archivos de modelos y schemas al describir entidades y relaciones.

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Entidades identificadas (3 small, 5 medium, 7 large)
- [ ] Relaciones documentadas con tipo y cardinalidad
- [ ] Reglas de dominio mencionadas
- [ ] Ciclo de vida de ≥1 entidad principal
- [ ] Archivos citados (4 small, 6 medium, 9 large)

---

## Criterios de Completitud

- [ ] Entidades identificadas (3 small, 5 medium, 7 large)
- [ ] Relaciones documentadas
- [ ] Reglas de dominio mencionadas
- [ ] Ciclo de vida de ≥1 entidad
- [ ] Archivos citados (4 small, 6 medium, 9 large)


