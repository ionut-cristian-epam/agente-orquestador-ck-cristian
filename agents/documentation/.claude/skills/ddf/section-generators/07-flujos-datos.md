# Generador: Flujos de Datos

> **Sección 7 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes integraciones detectadas. DEBES leer los servicios reales para trazar
los flujos de datos con transformaciones y rutas concretas.

---

## Exploración Requerida

### Lecturas obligatorias
- Al menos 3 archivos de services que procesan o transforman datos
- Archivos de configuración de pipelines o workers si existen

### Búsquedas dirigidas
- Glob: `**/services/**`, `**/pipelines/**`, `**/processors/**`, `**/workers/**`
- Grep: `def.*process|def.*transform|def.*calculate|async.*process` para encontrar transformaciones
- Grep: `publish|consume|send|receive|queue|topic|event` para flujos de mensajería
- Grep: `read_csv|parse|deserialize|serialize|to_json|from_json` para transformaciones de datos

### Lecturas condicionales
- Si existe mensajería (`rabbitmq`, `kafka`, `redis`) → buscar archivos de consumers/producers
- Si existe ETL o procesamiento batch → leer el archivo principal del pipeline
- Si hay workers o jobs → leer al menos 2 para entender qué datos procesan

### Profundidad mínima
- Leer al menos 5 archivos antes de generar
- Trazar al menos 2 flujos de datos completos (origen → transformación → destino) con evidencia de código

---

## Responsabilidades

1. Documentar flujos de entrada
2. Describir transformaciones y procesamiento
3. Documentar flujos de salida
4. Especificar flujos transaccionales y de persistencia

---

## Cobertura Obligatoria

### 1. Flujos de Entrada (OBLIGATORIO)
**Descripción:** Cómo ingresan los datos al sistema
**Ejemplos:**
- "Usuario envía request HTTP → API REST recibe JSON → valida con schema"
- "Archivo CSV subido → procesado por worker → insertado en BD"
**Qué documentar:**
- Origen de los datos (usuario, sistema externo, archivo)
- Punto de entrada al sistema (endpoint, cola, batch job)
- Formato de entrada y validaciones iniciales
**Dónde buscar en el código:**
- Endpoints de escritura (POST, PUT, PATCH)
- File uploads handlers
- Message queue consumers, event listeners

### 2. Transformaciones y Procesamiento (OBLIGATORIO)
**Descripción:** Qué se hace con los datos una vez dentro
**Ejemplos:**
- "Datos validados → enriquecidos con info de BD → aplicadas reglas de negocio → calculados totales"
- "JSON parseado → mapeado a entidad de dominio → procesado por servicio → persistido"
**Qué documentar:**
- Pasos de transformación
- Enriquecimiento de datos (joins, lookups)
- Cálculos o agregaciones
- Aplicación de reglas de negocio
**Dónde buscar en el código:**
- Services/business logic layer
- Data mappers, transformers
- Funciones de cálculo (calculate_*, compute_*)

### 3. Flujos de Salida (OBLIGATORIO)
**Descripción:** Cómo salen los datos del sistema
**Ejemplos:**
- "Query a BD → mapeado a DTO → serializado a JSON → retornado en response"
- "Datos procesados → escritos en archivo CSV → enviados por FTP"
**Qué documentar:**
- Destino de los datos (usuario, sistema externo, archivo)
- Formato de salida y transformaciones finales
- Canales de salida (HTTP response, archivo, email, cola)
**Dónde buscar en el código:**
- Endpoints de lectura (GET)
- Serializers, formatters
- Notification services

### 4. Flujos Transaccionales y Persistencia (OBLIGATORIO)
**Descripción:** Cómo se persisten y mantienen consistentes los datos
**Ejemplos:**
- "Create order: BEGIN transaction → insert order → insert order_items → update stock → COMMIT"
- "Si falla algún paso → ROLLBACK completo"
**Qué documentar:**
- Transacciones identificadas
- Operaciones atómicas y rollback en caso de error
**Dónde buscar en el código:**
- Decoradores @transaction, with transaction
- Commits explícitos
- Try/except con rollback

---

## Proceso de Generación

### 1. Exploración

```
Glob: **/services/**, **/handlers/**, **/jobs/**
Grep: "transaction", "commit", "rollback", "\\.save\\(", "\\.create\\(", "\\.update\\("
Read: Services, repositories, background jobs
```

### 2. Análisis

- Flujos de entrada: rastrear desde endpoints/handlers hasta servicios
- Transformaciones: conversiones, enriquecimientos y aplicación de reglas en services
- Flujos de salida: respuestas a clientes, eventos emitidos, datos persistidos
- Transacciones: bloques `db.begin/commit/rollback`, decoradores de transacción

### 3. Sustento

Integrar evidencia de código. Citar archivos de services y repositories al describir cada flujo.

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Flujos de entrada documentados (≥2)
- [ ] Transformaciones descritas
- [ ] Flujos de salida documentados (≥2)
- [ ] Transacciones/persistencia mencionadas
- [ ] Archivos citados (4 small, 6 medium, 9 large)

---

## Criterios de Completitud

- [ ] Flujos de entrada (≥2)
- [ ] Transformaciones documentadas
- [ ] Flujos de salida (≥2)
- [ ] Transacciones mencionadas
- [ ] Archivos citados (4 small, 6 medium, 9 large)


