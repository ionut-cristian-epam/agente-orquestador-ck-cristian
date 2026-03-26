# Generador: Requisitos No Funcionales Detallados

> **Sección 8 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes las integraciones detectadas. DEBES leer las configuraciones de infraestructura
y rendimiento reales para documentar NFRs con valores concretos.

---

## Exploración Requerida

### Lecturas obligatorias
- `docker-compose.yml` si existe (revela límites de recursos, replicas, healthchecks)
- Archivos de configuración principales (`config/settings.py`, `config/app.ts`, `application.yml`, etc.)
- `.env.example` (revela configuraciones de performance: pool size, timeouts, limits)

### Búsquedas dirigidas
- Grep: `timeout|max_connections|pool_size|workers|replicas|memory_limit|cpu` para configuraciones de rendimiento
- Grep: `cache|redis|ttl|expire|rate_limit|throttle` para políticas de caché y rate limiting
- Grep: `ssl|tls|https|cors|csp|hsts|encryption` para requisitos de seguridad
- Glob: `**/config/**`, `nginx.conf`, `**/settings*`

### Lecturas condicionales
- Si existe `nginx.conf` o `haproxy.cfg` → leerlo (define límites de conexiones, timeouts)
- Si existe `docker-compose.yml` con `deploy.resources` → documentar límites definidos
- Si existe configuración de autoscaling (k8s HPA, AWS ASG) → leerla

### Profundidad mínima
- Leer al menos 4 archivos antes de generar
- Para cada NFR documentado: incluir el valor numérico o configuración real del código, no estimaciones genéricas

---

## Responsabilidades

1. Documentar performance y tiempos de respuesta
2. Evaluar escalabilidad y concurrencia
3. Identificar mecanismos de disponibilidad
4. Documentar medidas de seguridad

---

## Cobertura Obligatoria

### 1. Performance y Tiempos de Respuesta (OBLIGATORIO)
**Descripción:** Métricas de rendimiento implementadas o esperadas
**Ejemplos:**
- "Endpoints con timeout de 30s configurado"
- "Cache Redis para optimizar lectura de productos (TTL 1h)"
**Qué documentar:**
- Timeouts configurados
- Estrategias de caching
- Optimizaciones implementadas (índices, paginación)
**Dónde buscar en el código:**
- Configuraciones de timeout
- Implementaciones de cache (Redis, Memcached)
- Índices de BD (migrations)
- Paginación en queries

### 2. Escalabilidad y Concurrencia (OBLIGATORIO)
**Descripción:** Capacidad del sistema para crecer y manejar carga
**Ejemplos:**
- "Stateless API permite horizontal scaling"
- "Worker jobs con Celery para procesamiento asíncrono"
**Qué documentar:**
- Diseño stateless vs stateful
- Capacidad de escalar horizontalmente
- Manejo de concurrencia (locks, queues)
- Procesamiento asíncrono
**Dónde buscar en el código:**
- Sesiones (si usa sesiones, es stateful)
- Background jobs (Celery, RQ, Bull)
- Locks para concurrencia (Redis locks, DB locks)
- Pool de conexiones

### 3. Disponibilidad y Confiabilidad (OBLIGATORIO)
**Descripción:** Mecanismos para mantener el sistema operativo
**Ejemplos:**
- "Health check endpoint en /health"
- "Retry automático con exponential backoff en llamadas externas"
**Qué documentar:**
- Health checks
- Reintentos automáticos y circuit breakers
- Graceful shutdown y fallbacks
**Dónde buscar en el código:**
- Endpoint /health, /status, /ping
- Retry logic (decoradores @retry)
- Circuit breaker implementations

### 4. Seguridad (OBLIGATORIO)
**Descripción:** Medidas de seguridad implementadas
**Ejemplos:**
- "Contraseñas hasheadas con bcrypt"
- "HTTPS enforced (redirect HTTP → HTTPS)"
- "CORS configurado para dominios específicos"
**Qué documentar:**
- Cifrado de datos (passwords, datos sensibles)
- Validación de inputs (sanitización, validación)
- Configuraciones de seguridad (CORS, HTTPS, CSP)
**Dónde buscar en el código:**
- Password hashing (bcrypt, argon2)
- HTTPS/SSL configurations
- CORS middleware
- Environment variables para secrets

---

## Proceso de Generación

### 1. Exploración

```
Glob: **/config/**, **/middleware/**, .env*, **/settings.py
Grep: "bcrypt", "cache", "CORS", "@retry", "health", "timeout", "rate_limit"
Read: Settings, config, middlewares principales
```

### 2. Análisis

- Performance: buscar caching (Redis, in-memory), timeouts configurados, paginación
- Escalabilidad: detectar operaciones async, workers, stateless design
- Disponibilidad: health check endpoints, retry decorators, circuit breakers
- Seguridad: hashing, CORS config, HTTPS, validación con schemas/DTOs

### 3. Sustento

Integrar evidencia de código. Citar archivos de configuración y middleware al documentar cada requisito.

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Performance documentada con evidencia
- [ ] Escalabilidad y concurrencia abordadas
- [ ] Disponibilidad y confiabilidad mencionadas
- [ ] Seguridad documentada
- [ ] Archivos citados (4 small, 6 medium, 9 large)

---

## Criterios de Completitud

- [ ] Performance documentada
- [ ] Escalabilidad abordada
- [ ] Disponibilidad mencionada
- [ ] Seguridad documentada
- [ ] Archivos citados (4 small, 6 medium, 9 large)


