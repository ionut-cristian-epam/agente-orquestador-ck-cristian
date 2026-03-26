---
name: ddf
description: "Genera Documentación de Diseño Funcional (DDF) completa o por secciones desde código fuente. Presenta siempre un selector interactivo para que el usuario elija exactamente qué secciones generar. Úsala cuando el usuario pida documentar, analizar o generar el DDF, la arquitectura, casos de uso, módulos, interfaces, flujos, o cualquier sección funcional del sistema."
argument-hint: "[completo | nombre-de-sección]"
allowed-tools: Glob, Grep, Read, Write, Bash, Task, AskUserQuestion
model: sonnet
effort: high
---

# Generador DDF Unificado

> **Skill orquestadora** para generación de Documentación de Diseño Funcional
> **Versión:** 4.0

---

## Fase 1: Selector de Secciones

**REGLA FUNDAMENTAL:** Mostrar el selector siempre que se invoque `/ddf`, sin importar el texto del argumento.

**Excepción única:** Si el argumento es exactamente `completo`, saltar directamente a Fase 2 con las 12 secciones.

### Paso 1 — Modo

Usar `AskUserQuestion` con esta pregunta:

```
"¿Qué quieres generar?"
Opciones:
  - "DDF Completo (12 secciones)"
  - "Secciones específicas"
```

Si elige **DDF Completo** → ir a Fase 2 con secciones [1,2,3,4,5,6,7,8,9,10,11,12].

Si elige **Secciones específicas** → continuar al Paso 2.

### Paso 2 — Selector granular

Usar `AskUserQuestion` con 3 preguntas multiselect en una sola llamada:

```
Q1 [multiSelect: true]: "Secciones 1–4 (marca las que quieres)"
  - "1. Introducción y Contexto"
  - "2. Arquitectura del Sistema"
  - "3. Subsistemas y Módulos Funcionales"
  - "4. Casos de Uso Detallados"

Q2 [multiSelect: true]: "Secciones 5–8 (marca las que quieres)"
  - "5. Modelo Conceptual Exhaustivo"
  - "6. Interfaces Detalladas"
  - "7. Flujos de Datos"
  - "8. Requisitos No Funcionales"

Q3 [multiSelect: true]: "Secciones 9–12 (marca las que quieres)"
  - "9. Reglas Globales y Restricciones"
  - "10. Algoritmos y Procesos Críticos"
  - "11. Gestión de Errores"
  - "12. Consideraciones de Despliegue"
```

Recolectar todas las selecciones. Si no marcó nada en ningún grupo, volver al Paso 1.

---

## Fase 2: Análisis de Orientación

Construir un **contexto de orientación liviano** que los subagentes usarán como punto de partida. No leer contenido de archivos — solo mapear la estructura.

### Qué construir

Ejecutar estas lecturas para construir el contexto:

1. Detectar stack: buscar `package.json`, `pyproject.toml`, `pom.xml`, `go.mod`, `Gemfile`, `*.csproj`. Leer el primero que encuentres para identificar nombre del proyecto, lenguaje y dependencias principales.

2. Mapear directorios: usar Glob con patrones como `src/*/`, `app/*/`, `lib/*/` para listar los directorios de primer y segundo nivel del proyecto fuente.

3. Detectar archivos clave por categoría:
   - Entrada: `**/routes/**`, `**/controllers/**`, `**/handlers/**`, `**/routers/**`
   - Negocio: `**/services/**`, `**/domain/**`, `**/business/**`
   - Modelos: `**/models/**`, `**/entities/**`, `**/schemas/**`
   - Config: `docker-compose.yml`, `Dockerfile`, `.env.example`, `**/config/**`
   - Tests: `**/tests/**`, `**/__tests__/**`, `**/spec/**`
   - CI/CD: `.github/workflows/**`, `.gitlab-ci.yml`, `Jenkinsfile`

4. Detectar integraciones: Grep `DATABASE_URL|REDIS_URL|MONGODB_URI|STRIPE_|SENDGRID_|AWS_` en `.env.example` o archivos de config.

### Formato del contexto de orientación

```
proyecto:
  nombre: [detectado]
  lenguaje: [detectado]
  framework: [detectado]
  directorio_raiz: [ruta]

estructura:
  directorios_clave: [lista de rutas]
  archivos_entrada: [lista]
  archivos_negocio: [lista]
  archivos_modelos: [lista]
  archivos_config: [lista]

integraciones_detectadas: [lista de nombres]
tiene_tests: [true/false]
tiene_docker: [true/false]
tiene_cicd: [true/false]
```

---

## Fase 3: Generación de Secciones

### Preparación del directorio temporal (solo para múltiples secciones)

Antes de lanzar subagentes, determinar la ruta del directorio temporal donde cada subagente escribirá su sección:

- Si existe `docs/` en la raíz del proyecto → `docs/ddf-sections/AAAA-MM-DD/`
- Si no existe → `.claude/ddf-sections/AAAA-MM-DD/`

Esta ruta (`RUTA_TEMP_SECCIONES`) se pasa a cada subagente en su prompt.

### Una sola sección

1. Leer el archivo generador: `section-generators/NN-nombre.md`
2. Seguir sus instrucciones, incluyendo el bloque **Exploración Requerida**
3. Generar la sección directamente
4. Continuar a Fase 4

### Múltiples secciones (2 o más)

Lanzar TODOS los subagentes en un solo turno (paralelo real). Para cada sección seleccionada:

```
Task tool:
  subagent_type: "general-purpose"
  model: "sonnet"
  prompt: |
    Eres un generador especializado de documentación DDF para la sección {N} - "{nombre}".

    CONTEXTO DE ORIENTACIÓN (punto de partida, no fuente única):
    {contexto_orientacion}

    PRIMER PASO OBLIGATORIO: Lee el archivo de instrucciones:
      .claude/skills/ddf/section-generators/{NN}-{nombre}.md

    SEGUNDO PASO OBLIGATORIO: Ejecuta TODAS las lecturas de código
    indicadas en la sección "Exploración Requerida" de ese archivo.
    No generes contenido sin haber leído el código real del proyecto.

    TERCER PASO: Genera el contenido markdown completo de la sección
    siguiendo el template en .claude/skills/ddf/references/output-template.md
    con evidencia integrada de los archivos que leíste.

    CUARTO PASO OBLIGATORIO: Usa la herramienta Write para guardar
    el contenido markdown generado en:
      {RUTA_TEMP_SECCIONES}/section-{NN}.md

    Devuelve ÚNICAMENTE esta línea de confirmación (nada más):
      SECTION_WRITTEN: {RUTA_TEMP_SECCIONES}/section-{NN}.md
```

**Mapa sección → archivo generador:**

| N | Archivo |
|---|---|
| 1 | `section-generators/01-introduccion-contexto.md` |
| 2 | `section-generators/02-arquitectura-sistema.md` |
| 3 | `section-generators/03-subsistemas-modulos.md` |
| 4 | `section-generators/04-casos-uso.md` |
| 5 | `section-generators/05-modelo-conceptual.md` |
| 6 | `section-generators/06-interfaces-detalladas.md` |
| 7 | `section-generators/07-flujos-datos.md` |
| 8 | `section-generators/08-requisitos-no-funcionales.md` |
| 9 | `section-generators/09-reglas-restricciones.md` |
| 10 | `section-generators/10-algoritmos-procesos.md` |
| 11 | `section-generators/11-gestion-errores.md` |
| 12 | `section-generators/12-consideraciones-despliegue.md` |

---

## Fase 4: Validación y Ensamblado

### Preparación del archivo de salida

Determinar la ruta de salida antes de ensamblar:
- Si existe el directorio `docs/` → `docs/ddf-AAAA-MM-DD.md`
- Si no existe → `ddf-AAAA-MM-DD.md` en la raíz del proyecto

### Verificación de archivos temporales (solo para múltiples secciones)

Antes de validar, confirmar que cada subagente escribió su archivo:

1. Para cada sección esperada, verificar que existe `{RUTA_TEMP_SECCIONES}/section-{NN}.md`
2. Si falta algún archivo: relanzar el subagente correspondiente con el mismo prompt (incluyendo CUARTO PASO). Si vuelve a fallar: aceptar con advertencia marcada.

### Validación por sección

Para cada sección, leer su archivo temporal con la herramienta `Read` y verificar:

- ¿Tiene los apartados obligatorios definidos en su generador?
- ¿Cita archivos reales del proyecto con rutas concretas?
- ¿Los hallazgos tienen evidencia integrada (no en bloque separado)?
- ¿El formato sigue el template de `references/output-template.md`?

Si una sección falla la validación: relanzar ese subagente una vez con feedback explícito de qué falta. Si vuelve a fallar: aceptar con advertencia marcada.

Para criterios de scoring detallados → ver `references/quality-checklist.md`.

### Ensamblado → siempre escribir a archivo

**REGLA CRÍTICA:** No outputear el contenido del documento en el chat. Usar la herramienta `Write` para escribir el documento completo en disco. Esta llamada a `Write` es OBLIGATORIA — no se puede omitir ni reemplazar por un mensaje de progreso.

1. Leer cada archivo temporal de sección con `Read` en orden canónico (1–12)
2. Construir el contenido completo del documento:
   - Cabecera con metadatos del template (proyecto, versión, fecha, stack)
   - Tabla de contenidos fija del template
   - Resumen ejecutivo sintetizado en máximo 300 palabras a partir de los hallazgos clave de cada sección (visión general, tecnologías clave, top 5 hallazgos, top 3 riesgos, métricas, 3-5 recomendaciones)
   - Secciones en orden canónico (1–12) — contenido leído de los archivos temporales
   - Apéndice A: listado consolidado de archivos citados (sin duplicados)
   - Apéndice C: vacíos unificados de todas las secciones
   - Apéndice E: próximos pasos priorizados
3. **Llamar a `Write` con el contenido completo** hacia la ruta de salida determinada
4. Eliminar el directorio temporal `{RUTA_TEMP_SECCIONES}` con Bash `rm -rf`

---

## Fase 5: Entrega

Confirmar la escritura y mostrar al usuario únicamente este resumen compacto:

```
✅ DDF generado y guardado en: `<ruta-del-archivo>`

📊 Resumen de generación:
- Secciones generadas: [N]/[N]
- Archivos analizados: [N] en total
- Score de calidad promedio: [NN]/100
```

Si hubo secciones con advertencias, añadir:

```
⚠️ Secciones con información limitada: [lista]
💡 Para mejorar: revisar [artefactos sugeridos]
```

**No outputear el contenido del documento en el chat.** El usuario lo abre desde la ruta indicada.

---

## Referencias

- Secciones canónicas y keywords → `references/sections-catalog.md`
- Templates de salida → `references/output-template.md`
- Criterios de calidad → `references/quality-checklist.md`
- Generadores de sección → `section-generators/NN-nombre.md`
