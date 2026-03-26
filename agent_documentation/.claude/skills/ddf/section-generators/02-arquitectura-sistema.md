# Generador: Arquitectura del Sistema

> **Sección 2 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes un contexto de orientación con la estructura general del proyecto. Úsalo como
punto de partida. DEBES explorar el código para documentar la arquitectura real.

---

## Exploración Requerida

### Lecturas obligatorias
- Archivo principal de la app (`main.py`, `index.ts`, `app.js`, etc.)
- `docker-compose.yml` si existe
- Estructura de directorios de primer nivel bajo `src/` o `app/`

### Búsquedas dirigidas
- Glob: `**/docker-compose*.yml`, `**/Dockerfile*`
- Glob: `src/*/` o `app/*/` para mapear capas
- Grep: `from.*import|require\(|import ` en archivos principales (identificar dependencias entre capas)
- Grep: `microservice|hexagonal|clean architecture|domain|repository|port|adapter` para detectar patrón

### Lecturas condicionales
- Si existe `docker-compose.yml` con múltiples servicios → leer completo (indica microservicios)
- Si existe `src/domain/` o `src/core/` → leer estructura (indica arquitectura hexagonal/clean)
- Leer al menos 2 archivos de cada capa detectada (entrada, negocio, persistencia)
- Si existe configuración de infraestructura (`kubernetes/`, `terraform/`) → leer al menos 1 archivo

### Profundidad mínima
- Leer al menos 6 archivos antes de generar
- Identificar al menos 3 componentes/capas con evidencia concreta de código

---

## Responsabilidades

1. Analizar contexto rico
2. Identificar estilo arquitectónico
3. Enumerar componentes principales
4. Documentar dependencias e integraciones
5. Identificar riesgos funcionales
6. Integrar evidencia de código
7. Auto-validar y producir sección

---

## Cobertura Obligatoria

### 1. Estilo Arquitectónico Identificado (OBLIGATORIO)
**Descripción:** Patrón arquitectónico principal del sistema
**Ejemplos:**
- "Arquitectura en capas (3-tier)"
- "Microservicios con API Gateway"
- "Arquitectura hexagonal (ports & adapters)"
**Qué documentar:**
- Estilo identificado (monolítico, capas, microservicios, event-driven, hexagonal, serverless)
- Razón del estilo (si es evidente)
- Implicaciones funcionales
**Dónde buscar en el código:**
- Estructura de directorios (clara separación = capas)
- docker-compose.yml (múltiples servicios = microservicios)
- Patrones de imports/dependencias
- Presencia de API Gateway, Event Bus, etc.

### 2. Componentes Principales y Responsabilidades (OBLIGATORIO)
**Descripción:** Bloques funcionales principales del sistema
**Ejemplos:**
- "API REST (entrada), Service Layer (lógica), Data Layer (persistencia)"
- "Frontend, Backend API, Worker Jobs, Database"
**Qué documentar:**
- Lista de componentes principales (mínimo: 3 small, 5 medium, 7 large)
- Responsabilidad funcional de cada uno
- Tecnología usada por componente
**Dónde buscar en el código:**
- Directorios de primer nivel (src/api, src/services, src/models)
- Archivos docker-compose (servicios definidos)
- package.json scripts, Makefile targets

### 3. Dependencias e Integraciones (OBLIGATORIO)
**Descripción:** Componentes internos conectados + sistemas externos
**Ejemplos:**
- "API llama a Service Layer, Service Layer usa Repository"
- "Integración con Stripe (pagos), SendGrid (emails), PostgreSQL (datos)"
**Qué documentar:**
- Dependencias internas (quién llama a quién)
- Integraciones externas (APIs, bases de datos, colas)
- Tipo de comunicación (síncrona, asíncrona, eventos)
**Dónde buscar en el código:**
- Imports entre módulos
- Configuraciones de conexiones (DATABASE_URL, API_KEYS)
- Clients/SDKs de terceros
- requirements.txt, package.json (dependencias)

### 4. Riesgos Funcionales por Acoplamiento (OBLIGATORIO)
**Descripción:** Puntos de fallo, cuellos de botella, dependencias críticas
**Qué documentar:**
- Single points of failure
- Acoplamientos altos
- Dependencias críticas sin fallback
**Dónde buscar en el código:**
- Servicios sin retry logic
- Dependencias sin circuit breaker
- Componentes con múltiples responsabilidades

---

## Proceso de Generación

### 1. Exploración

Herramientas recomendadas:
```
Glob: **/docker-compose.yml, src/**/
Grep: "import", "from.*import", "DATABASE_URL"
Read: main.py / index.ts / app.js, docker-compose.yml, config/
```

### 2. Análisis

- **Estilo:** Inferir de estructura de directorios y servicios en docker-compose
- **Componentes:** De `componentes_clave` en contexto rico + exploración de directorios
- **Integraciones:** De `integraciones` en contexto rico + grep de conexiones
- **Riesgos:** Analizar dependencias críticas, single points of failure

### 3. Sustento

Integrar evidencia de código:
- Citar archivos de configuración al describir el estilo arquitectónico
- Mencionar rutas de directorios al enumerar componentes
- Referenciar docker-compose o infra al documentar integraciones

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Estilo arquitectónico identificado y justificado
- [ ] Componentes ≥ mínimo adaptativo (3/5/7)
- [ ] Dependencias documentadas
- [ ] Al menos 1 riesgo identificado
- [ ] Evidencia integrada
- [ ] Archivos citados (5 small, 7 medium, 10 large)

---

## Criterios de Completitud

- [ ] Estilo arquitectónico identificado
- [ ] Componentes >= mínimo adaptativo
- [ ] Dependencias documentadas
- [ ] Al menos 1 riesgo identificado
- [ ] Evidencia integrada
- [ ] Archivos citados (5 small, 7 medium, 10 large)


