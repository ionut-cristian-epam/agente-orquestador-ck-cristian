# Generador: Casos de Uso Detallados

> **Sección 4 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes rutas de archivos de entrada detectados. DEBES leerlos para documentar
los casos de uso reales del sistema, no inferirlos del resumen.

---

## Exploración Requerida

### PASO 1 — Mapear todos los archivos fuente del proyecto

Ejecutar estas búsquedas para obtener el inventario completo. **NUNCA limitar a routes/ o controllers/ — leer TODO:**

1. **Inventario de archivos de negocio** (excluir .venv, node_modules, __pycache__, dist, build):
   - Glob: `**/*.py` (o `**/*.java`, `**/*.ts`, etc. según el lenguaje)
   - Resultado esperado: lista de todos los archivos fuente a analizar

2. **Identificar entry points reales** (independientemente de la arquitectura):
   - REST/FastAPI/Flask → Grep: `@app\.(get|post|put|delete|patch)`, `@router\.`
   - DIAL SDK / ChatCompletion → Grep: `class.*ChatCompletion`, `async def.*complete`, `def chat_completion`
   - Event-driven / Handlers → Grep: `def handle_`, `async def handle`, `class.*Handler`, `class.*Processor`
   - CLI → Grep: `@click\.command`, `argparse`, `def main(`
   - Clases heredadas → Grep: `class \w+\(` para detectar herencia de frameworks
   - gRPC / WebSocket → Grep: `servicer`, `on_message`, `websocket`
   - Cualquier función pública async con parámetros de request/response

3. **Leer README.md o documentación principal** → revela casos de uso descritos por el equipo

### PASO 2 — Lectura exhaustiva de TODOS los archivos relevantes

**Leer TODOS los archivos identificados**, comenzando por los más importantes:

1. **Todos los archivos del directorio raíz** (app.py, main.py, server.py, index.py, etc.)
2. **Todos los archivos en services/** (cada servicio = múltiples casos de uso)
3. **Todos los archivos en utils/** o helpers/ (funciones de utilidad = casos de uso de soporte)
4. **Todos los archivos en handlers/, controllers/, routes/** si existen
5. **Archivos de tests** (test_*.py, *_test.py, *spec*) — revelan comportamiento esperado
6. **Archivos de configuración de prompts o templates** (prompts/, templates/) — cada prompt = un caso de uso funcional

**Regla estricta: leer mínimo 10 archivos. Para proyectos large, leer TODOS los archivos fuente sin excepción.**

### PASO 3 — Extracción exhaustiva de casos de uso

Por cada archivo leído, aplicar esta regla:

> **Cada función/método público = candidato a caso de uso**

Mapear:
- Cada función pública en services/ → caso de uso de negocio
- Cada función en utils/ con lógica significativa (>15 líneas) → caso de uso de soporte
- Cada bloque `try/except` identificado → flujo alterno de un caso de uso
- Cada comando o flag de configuración aceptado → caso de uso de gestión
- Cada integración con sistema externo (API, BD, caché, cola) → caso de uso de integración

### Lecturas condicionales adicionales
- Si existe `swagger.yml` / `openapi.json` / `openapi.yaml` → leerlo (inventario completo de operaciones)
- Si existen tests de integración → leer al menos 3 (describen flujos completos)
- Si existe archivo de roles/permisos → leerlo para identificar actores

### Profundidad mínima
- Leer al menos 10 archivos antes de generar (sin excepción)
- **Para proyectos large: leer todos los archivos fuente identificados**
- Documentar al menos: 5 (small), 10 (medium), 15+ (large) casos de uso
- Cada caso de uso debe citar el archivo y función específica que lo implementa

---

## Responsabilidades

1. Leer exhaustivamente TODOS los archivos fuente del proyecto
2. Identificar todos los casos de uso (mínimo 1 por función pública de negocio)
3. Definir actores y objetivos para cada caso de uso
4. Documentar flujo principal, flujos alternos y postcondiciones
5. Citar el archivo y función exacta que implementa cada caso de uso

---

## Formato de Salida

**IMPORTANTE: La sección NO incluye subsecciones de "Hallazgos clave" ni "Desarrollo". Solo genera la lista de casos de uso directamente.**

La estructura de salida es:

```
## 4. Casos de Uso Detallados

> metadatos

---

### Actores del Sistema
[tabla de actores]

---

### Inventario de Casos de Uso
[tabla resumen con ID, nombre, actor, archivo]

---

### [CU-01]: Nombre del caso de uso

| Campo | Detalle |
|---|---|
| **Actor** | ... |
| **Precondición** | ... |
| **Objetivo** | ... |

**Flujo principal:**
1. paso 1
2. paso 2
...

**Flujos alternos:**
- FA-01: ...

**Postcondición:** ...

---

### [CU-02]: ...

[repetir para cada caso de uso identificado]

---

### Vacíos identificados
[lista de funcionalidades en el código que no pudieron documentarse completamente]

---

### Archivos analizados
[tabla con ruta y propósito]
```

---

## Proceso de Generación

### 1. Exploración (OBLIGATORIO — no saltar pasos)

```
PASO 1: Inventario (Glob todos los archivos .py/.java/.ts según lenguaje)
PASO 2: README (leer para entender el dominio funcional)
PASO 3: Entry points (leer main.py, app.py, server.py, index.py o equivalentes)
PASO 4: Todos los services/ (leer UNO A UNO)
PASO 5: Todos los utils/ y helpers/ (leer UNO A UNO)
PASO 6: Tests si existen (leer al menos 3)
PASO 7: Archivos de prompts/templates si existen
```

### 2. Análisis

- Entry point principal → caso de uso orquestador
- Cada método/función pública en services/ → caso de uso de negocio
- Cada función en utils/ con lógica propia → caso de uso de soporte
- Cada integración externa detectada → caso de uso de integración
- Cada bloque try/except → flujo alterno de su caso de uso padre
- Cada variable de entorno o flag de configuración → caso de uso de configuración/gestión

### 3. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Leídos todos los archivos fuente (mínimo 10, todos para large)
- [ ] Casos de uso: ≥5 (small), ≥10 (medium), ≥15 (large)
- [ ] Actor y objetivo por caso de uso
- [ ] Flujo principal documentado con pasos numerados
- [ ] Flujos alternos mencionados
- [ ] Postcondiciones descritas
- [ ] Cada caso de uso cita archivo y función específica
- [ ] Archivos citados: ≥5 (small), ≥8 (medium), ≥12 (large)

---

## Criterios de Completitud

- [ ] Leídos todos los archivos fuente sin excepción
- [ ] Casos de uso: ≥5 (small), ≥10 (medium), ≥15 (large)
- [ ] Actor y objetivo por caso de uso
- [ ] Flujo principal documentado
- [ ] Flujos alternos mencionados
- [ ] Postcondiciones descritas
- [ ] Archivos citados: ≥5 (small), ≥8 (medium), ≥12 (large)


