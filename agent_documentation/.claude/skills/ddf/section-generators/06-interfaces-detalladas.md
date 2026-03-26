# Generador: Interfaces Detalladas

> **Sección 6 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes rutas de archivos de entrada y schemas detectados. DEBES leerlos para
documentar interfaces reales con parámetros, formatos y autenticación específicos.

---

## Exploración Requerida

### Lecturas obligatorias
- Al menos 4 archivos de rutas/endpoints (para inventariar la API)
- Al menos 3 archivos de schemas/DTOs (para documentar formatos de datos)
- Middleware de autenticación (para documentar auth/authz)

### Búsquedas dirigidas
- Glob: `**/routes/**`, `**/schemas/**`, `**/dto/**`, `**/types/**`
- Glob: `**/swagger*`, `**/openapi*` — si existe, leerlo (fuente más completa)
- Grep: `@app\.(get|post|put|delete|patch)|router\.` para listar endpoints
- Grep: `Bearer|Authorization|api_key|JWT|OAuth|require_auth|@auth` para identificar auth
- Grep: `class.*Schema|class.*DTO|interface.*Request|interface.*Response` para encontrar contratos

### Lecturas condicionales
- Si existe `openapi.json` o `swagger.yaml` → leerlo como fuente primaria de endpoints
- Si existe GraphQL → leer el schema principal (`schema.graphql` o equivalente)
- Si existen schemas Pydantic/Marshmallow/Zod → leer todos los que encuentres (definen contratos)

### Profundidad mínima
- Leer al menos 7 archivos antes de generar
- Documentar al menos 5 endpoints (small), 8 (medium), 12 (large) con método, ruta y payload
- Cada endpoint debe incluir ejemplo de request/response con campos reales del código

---

## Responsabilidades

1. Inventariar interfaces expuestas y consumidas
2. Detallar endpoints/operaciones principales
3. Especificar formatos de request/response
4. Documentar autenticación y autorización

---

## Cobertura Obligatoria

### 1. Inventario de Interfaces (OBLIGATORIO)
**Descripción:** Listado de todas las interfaces expuestas o consumidas
**Ejemplos:**
- "API REST con 15 endpoints en /api/v1/"
- "GraphQL API en /graphql"
- "Interfaz de mensajería con RabbitMQ (3 colas)"
**Qué documentar:**
- Tipo de interfaz (REST, GraphQL, gRPC, WebSocket, Message Queue)
- Cantidad de operaciones/endpoints
- Base URL o punto de entrada
**Dónde buscar en el código:**
- Routers, routes files
- API documentation (Swagger, OpenAPI)
- GraphQL schemas
- Message handlers, event listeners

### 2. Detalle de Endpoints/Operaciones Principales (OBLIGATORIO)
**Descripción:** Especificación de los endpoints más importantes
**Ejemplos:**
- "POST /api/users - Crear usuario (body: name, email, password) → 201 Created + user object"
- "GET /api/orders/{id} - Obtener orden (path param: id) → 200 OK + order object"
**Qué documentar:**
- Método HTTP, ruta, parámetros y respuestas
- Mínimo: 5 (small), 8 (medium), 12 (large)
**Dónde buscar en el código:**
- Decoradores de rutas (@app.get, @app.post)
- Schemas de request/response

### 3. Formatos de Datos (OBLIGATORIO)
**Descripción:** Estructura de datos de entrada y salida
**Ejemplos:**
- "Request: JSON con {name: string, email: string, password: string}"
- "Response: JSON con {id: int, name: string, created_at: datetime}"
**Qué documentar:**
- Formato (JSON, XML, Protocol Buffers, etc.)
- Schemas/DTOs utilizados
- Campos obligatorios vs opcionales
**Dónde buscar en el código:**
- Schemas (Pydantic, Marshmallow, JSON Schema)
- DTOs, request/response models
- Documentación OpenAPI/Swagger

### 4. Autenticación y Autorización (OBLIGATORIO)
**Descripción:** Mecanismos de seguridad en interfaces
**Ejemplos:**
- "Autenticación: JWT Bearer token en header Authorization"
- "Autorización: Permisos basados en roles (RBAC)"
**Qué documentar:**
- Tipo de autenticación (JWT, OAuth, API Key, Basic Auth)
- Dónde se valida (middleware, decorators)
- Permisos requeridos por endpoint
**Dónde buscar en el código:**
- Middlewares de auth
- Decoradores de permisos (@require_auth, @require_role)
- Configuración de security schemes

---

## Proceso de Generación

### 1. Exploración

```
Glob: **/routes.py, **/schemas/**, **/middleware/**
Grep: "@app\\.(get|post|put|delete|patch)", "Bearer", "Authorization", "require_auth"
Read: Routers, schemas, middleware de autenticación
```

### 2. Análisis

- Interfaces: identificar tipo y protocolo desde framework y componentes
- Endpoints: enumerar rutas, verbos HTTP, parámetros y respuestas esperadas
- Formatos: de schemas/DTOs para request y response
- Auth/authz: de middleware y decoradores de autenticación/permiso

### 3. Sustento

Integrar evidencia de código. Citar archivos de rutas y schemas al documentar cada endpoint.

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Interfaces identificadas con tipo y protocolo
- [ ] Endpoints documentados (5 small, 8 medium, 12 large)
- [ ] Formatos especificados con campos clave
- [ ] Auth/authz identificado y documentado
- [ ] Archivos citados (4 small, 6 medium, 9 large)

---

## Criterios de Completitud

- [ ] Interfaces identificadas
- [ ] Endpoints documentados (5 small, 8 medium, 12 large)
- [ ] Formatos especificados
- [ ] Auth/authz identificado
- [ ] Archivos citados (4 small, 6 medium, 9 large)


