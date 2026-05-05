# Generador: Introducción y Contexto

> **Sección 1 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes un contexto de orientación del orquestador con la estructura general del proyecto
(stack, directorios clave, archivos detectados). Úsalo como punto de partida, no como
fuente única. DEBES leer el código antes de generar.

---

## Exploración Requerida

### Lecturas obligatorias
- `README.md` — propósito, descripción del proyecto, instrucciones de uso
- Archivo principal de la app (`main.py`, `app.py`, `index.ts`, `app.js`, `main.go`, etc.)
- Archivo de metadatos (`package.json`, `pyproject.toml`, `pom.xml`, o equivalente)

### Búsquedas dirigidas
- Grep: `description|purpose|about|overview` en README.md y archivos de config
- Grep: `class.*User|class.*Admin|class.*Role|interface.*User` para identificar actores
- Glob: `.env.example` o `config/` para identificar contexto operativo

### Lecturas condicionales
- Si existe `.env.example` → leerlo completo (revela integraciones y ambiente)
- Si existe `docker-compose.yml` → leerlo (revela contexto de despliegue)
- Si existe documentación en `docs/` → leer al menos el archivo principal

### Profundidad mínima
- Leer al menos 4 archivos antes de generar
- Si no encuentras descripción del propósito: inferirla del nombre del proyecto y módulos principales, declarando el supuesto

---

## Responsabilidades

1. Analizar el contexto rico disponible
2. Realizar lecturas adicionales de archivos si es necesario (usando Read/Grep)
3. Generar contenido cumpliendo TODA la cobertura obligatoria
4. Integrar evidencia de código en hallazgos y desarrollo
5. Identificar y reportar vacíos
6. Auto-validar antes de entregar
7. Producir la sección formateada según template

---

## Cobertura Obligatoria

### 1. Propósito Funcional del Sistema (OBLIGATORIO)
**Descripción:** Qué hace el sistema y por qué existe
**Ejemplos:**
- "Sistema de gestión de inventarios para retail"
- "Plataforma de procesamiento de pagos en línea"
**Qué documentar:**
- Función principal del sistema
- Valor de negocio que aporta
- Problema que resuelve
**Dónde buscar en el código:**
- README.md, package.json (description)
- Comentarios en archivos main/app
- Nombres de módulos principales

### 2. Problema de Negocio que Resuelve (OBLIGATORIO)
**Descripción:** Contexto del negocio y necesidad que cubre
**Ejemplos:**
- "Automatiza proceso manual de facturación"
- "Reduce tiempo de respuesta en atención al cliente"
**Qué documentar:**
- Situación antes del sistema
- Pain points que aborda
- Mejora funcional esperada
**Dónde buscar en el código:**
- Documentación de requisitos
- Comentarios de alto nivel
- Nombres de módulos de negocio

### 3. Actores Principales y Alcance (OBLIGATORIO)
**Descripción:** Quiénes usan el sistema y qué roles tienen
**Ejemplos:**
- "Usuarios finales (clientes), Administradores, Operadores"
- "Sistemas externos (APIs), Procesos batch"
**Qué documentar:**
- Tipos de usuarios/roles
- Sistemas que interactúan
- Alcance funcional por actor
**Dónde buscar en el código:**
- Modelos de usuario (User, Role, Permission)
- Endpoints de autenticación/autorización
- Middlewares de permisos

### 4. Contexto Operativo y Límites (OBLIGATORIO)
**Descripción:** Dónde opera el sistema y sus fronteras
**Ejemplos:**
- "Opera en cloud AWS, disponible 24/7"
- "Sistema interno de uso corporativo"
**Qué documentar:**
- Ambiente de operación
- Fronteras del sistema (qué NO hace)
- Dependencias externas
**Dónde buscar en el código:**
- docker-compose.yml, Dockerfile
- README (sección de deployment/environment)
- Variables de entorno (.env.example)

---

## Proceso de Generación

### 1. Exploración

Desde el contexto rico, identificar:
- Información en `proyecto.nombre`, `proyecto.tipo`, `proyecto.framework`
- Componentes clave que indican actores (ej: "auth", "admin", "api")
- Integraciones que indican contexto operativo

**Lecturas adicionales recomendadas:**
```
Read: README.md (si existe)
Read: package.json o pyproject.toml (metadatos)
Read: main file (main.py, index.ts, app.js)
Grep: "class.*User|def.*user|interface.*User" (buscar actores)
```

### 2. Análisis

Extraer información funcional:
- **Propósito:** Inferir de nombre del proyecto, comentarios en main, README
- **Problema de negocio:** Buscar comentarios que expliquen el "por qué"
- **Actores:** Identificar roles en modelos de usuario o endpoints con auth
- **Contexto operativo:** Ver configuraciones de deployment, env vars

### 3. Estructuración

Organizar contenido según cobertura obligatoria:
1. Propósito funcional del sistema
2. Problema de negocio que resuelve
3. Actores principales y alcance
4. Contexto operativo y límites

### 4. Sustento

Integrar evidencia de código:
- Citar README.md al explicar propósito
- Mencionar modelos de usuario al listar actores (ej: `models/user.py` define roles Admin, Operator)
- Referenciar archivos de configuración al describir ambiente (ej: `docker-compose.yml` indica deployment containerizado)

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 5. Validación (Auto-validación)

Antes de entregar, verificar:
- [ ] Todos los apartados obligatorios cubiertos (4 apartados)
- [ ] Cantidad de hallazgos ≥ expectativa del contexto (min 1-3)
- [ ] Cantidad de archivos citados ≥ mínimo (3 small, 5 medium, 8 large)
- [ ] Tono funcional (no demasiado técnico)
- [ ] Sin contradicciones internas
- [ ] Formato según template

**Si falla algún criterio:** Intentar completar o marcar vacío explícitamente.

### 6. Formato de salida

Producir el contenido markdown de la sección siguiendo el template de `references/output-template.md`:

```markdown
## 1. Introducción y Contexto

> **Sección 1 de 12** del Documento de Diseño Funcional
> **Proyecto:** {nombre}
> **Fecha:** {YYYY-MM-DD}
> **Generado desde:** Análisis de código fuente

---

### Objetivo funcional

Establecer el propósito del sistema, el problema de negocio que resuelve, los actores involucrados y el alcance funcional.

---

### Hallazgos clave desde el código

- **[Hallazgo 1]**: [Descripción con evidencia integrada]
- **[Hallazgo 2]**: [Descripción con evidencia integrada]

---

### Desarrollo

#### Propósito Funcional del Sistema
[Contenido con evidencia integrada]

#### Problema de Negocio que Resuelve
[Contenido con evidencia integrada]

#### Actores Principales y Alcance
[Contenido con evidencia integrada]

#### Contexto Operativo y Límites
[Contenido con evidencia integrada]

---

### Supuestos o vacíos

[Si aplica: información faltante]
[Si no: "✅ No se identificaron vacíos significativos en esta sección."]

---
```

---

## Criterios de Completitud

- [ ] Propósito funcional documentado
- [ ] Problema de negocio descrito
- [ ] Actores y alcance especificados
- [ ] Contexto operativo y límites definidos
- [ ] Evidencia de código integrada
- [ ] Archivos citados (3 small, 5 medium, 8 large)
