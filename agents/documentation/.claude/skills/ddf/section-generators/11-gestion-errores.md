# Generador: Gestión de Errores

> **Sección 11 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes la estructura general del proyecto. DEBES leer los archivos de
excepciones, middleware global y configuración de logging para documentar
la estrategia de errores con evidencia real.

---

## Exploración Requerida

### Lecturas obligatorias
- Todos los archivos de exceptions/errors custom del proyecto
- Middleware global de manejo de errores (exception handlers)
- Configuración de logging (`logging.conf`, `settings.py`, `app.ts`)

### Búsquedas dirigidas
- Glob: `**/exceptions/**`, `**/errors/**`, `**/middleware/**`
- Grep: `class.*Exception|class.*Error` para inventariar excepciones custom
- Grep: `logger\.|logging\.|log\.` para identificar qué se loggea y dónde
- Grep: `rollback|@retry|circuit_breaker|exponential` para mecanismos de recuperación

### Lecturas condicionales
- Si existe Sentry, Datadog o servicio de monitoreo → leer su configuración
- Si existe error response schema → leerlo para documentar formato de errores

### Profundidad mínima
- Leer al menos 5 archivos antes de generar
- Identificar la jerarquía de excepciones custom y el handler global

---

## Responsabilidades

1. Documentar estrategia de manejo de excepciones
2. Describir logging y auditoría
3. Especificar respuestas de error para clientes
4. Documentar mecanismos de recuperación y rollback

---

## Cobertura Obligatoria

### 1. Estrategia de Manejo de Excepciones (OBLIGATORIO)
**Descripción:** Cómo se capturan y procesan errores
**Ejemplos:**
- "Try/except en handlers con logging de errores"
- "Exception handlers globales que capturan errores no controlados"
**Qué documentar:**
- Tipos de excepciones definidas (custom exceptions)
- Dónde se capturan (middleware, handlers, services)
- Qué se hace con ellas (log, retry, return error)
**Dónde buscar en el código:**
- Custom exception classes
- Exception handlers (@app.exception_handler)
- Try/except blocks en handlers

### 2. Logging y Auditoría (OBLIGATORIO)
**Descripción:** Qué se registra y cómo
**Ejemplos:**
- "Logs estructurados en JSON con level (INFO, WARNING, ERROR)"
- "Audit log de operaciones críticas (create, update, delete)"
**Qué documentar:**
- Niveles de log usados
- Qué se loggea (requests, errors, operaciones críticas)
- Formato y destino de logs
**Dónde buscar en el código:**
- Configuración de logging (logging.conf, config)
- Llamadas a logger (logger.info, logger.error)
- Middleware de logging, decoradores @audit_log

### 3. Respuestas de Error para Clientes (OBLIGATORIO)
**Descripción:** Cómo se comunican errores a usuarios/clientes
**Ejemplos:**
- "Status codes HTTP apropiados (400, 404, 500)"
- "Mensajes de error estructurados con código y descripción"
**Qué documentar:**
- Status codes utilizados
- Formato de respuesta de error (JSON schema)
- Códigos de error custom (si existen)
**Dónde buscar en el código:**
- Return statements con status codes
- Exception handlers que retornan responses
- Error response schemas

### 4. Recuperación y Rollback (OBLIGATORIO)
**Descripción:** Mecanismos para recuperarse de fallos
**Ejemplos:**
- "Rollback automático de transacciones en caso de error"
- "Reintentos con exponential backoff en llamadas externas"
**Qué documentar:**
- Transactional rollback
- Retry logic y circuit breakers
- Graceful degradation
**Dónde buscar en el código:**
- Rollback en try/except
- Decoradores @retry
- Circuit breaker implementations

---

## Proceso de Generación

### 1. Exploración

```
Glob: **/exceptions/**, **/errors/**, **/middleware/**
Grep: "class.*Exception", "class.*Error", "logger\\.", "rollback", "@retry", "exception_handler"
Read: Exceptions/errors definidos, exception handlers, logging config
```

### 2. Análisis

- Excepciones: clases de excepción custom y su jerarquía
- Captura: middleware global de error handling, try/except en handlers y services
- Logging: configuración de loggers, niveles, formato, handlers (file, stdout, service)
- Respuestas: mapeo de excepciones a status codes HTTP y estructura de response
- Rollback/retry: en services con transacciones, decoradores de retry

### 3. Sustento

Integrar evidencia de código. Citar archivos de exceptions, handlers y config de logging.

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Manejo de excepciones documentado con tipos identificados
- [ ] Logging descrito (niveles, destino, qué se loggea)
- [ ] Respuestas de error especificadas (status codes + formato)
- [ ] Recuperación/rollback documentados
- [ ] Archivos citados (4 small, 6 medium, 9 large)

---

## Criterios de Completitud

- [ ] Manejo de excepciones documentado
- [ ] Logging descrito
- [ ] Respuestas de error especificadas
- [ ] Recuperación/rollback documentados
- [ ] Archivos citados (4 small, 6 medium, 9 large)


