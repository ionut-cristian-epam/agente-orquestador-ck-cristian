# Agent Harness Orchestrator

Orquestador de sesiones de agentes IA de codificación en paralelo, construido sobre el [Agent Client Protocol (ACP)](https://agentcommunicationprotocol.dev) y el protocolo [AG-UI](https://docs.ag-ui.com) de CopilotKit.

En lugar de capturar terminales y parsear salida ANSI, este proyecto se comunica con agentes de codificación a través de [`acpx`](https://www.npmjs.com/package/acpx) — un cliente CLI headless que convierte mensajes del protocolo ACP en interacciones estructuradas y tipadas.

---

## Tecnologías Clave

### ACP (Agent Client Protocol)

Protocolo abierto de comunicación entre clientes y agentes IA. Define un formato estándar JSON-RPC para enviar prompts, recibir respuestas, notificar sobre pensamiento del agente, invocaciones de herramientas y sus resultados. Es agnóstico al agente: cualquier agente que implemente ACP puede ser controlado por cualquier cliente ACP. [Especificación](https://agentcommunicationprotocol.dev)

### acpx

Cliente CLI headless para el protocolo ACP. Actúa como intermediario entre nuestro orquestador y los agentes de codificación (OpenCode, Claude Code, Codex, etc.). En lugar de interactuar con la interfaz de terminal del agente, `acpx` expone los mensajes ACP como JSON-RPC sobre stdout/stdin. Permite crear sesiones, enviar prompts y recibir eventos estructurados (texto, pensamiento, tool calls) sin interfaz gráfica. [npm](https://www.npmjs.com/package/acpx)

### AG-UI (Agent-User Interaction Protocol)

Protocolo de CopilotKit que define cómo un frontend se comunica con agentes backend via streaming (SSE). Define tipos de eventos como `RunStartedEvent`, `TextMessageChunkEvent`, `ReasoningMessageChunkEvent`, `ToolCallStartEvent`, etc. El frontend envía un `POST` con los mensajes del chat, y el backend responde con un stream de eventos que el frontend renderiza en tiempo real. [Documentación](https://docs.ag-ui.com)

### CopilotKit

Framework React de código abierto para construir interfaces de chat con agentes IA. Proporciona componentes como `CopilotChat` (UI de chat completa), providers como `CopilotKitProvider` (registro de agentes) y hooks como `useAgent` (acceso programático al agente). En este proyecto, CopilotKit v2 consume los eventos AG-UI que genera nuestro backend FastAPI. [Web](https://copilotkit.ai)

### OpenCode

Agente de codificación open-source y multi-provider. Es el harness por defecto del orquestador. Soporta múltiples proveedores de LLM (NagaAI, OpenCode Zen, Amazon Bedrock) configurables via `opencode.json`. Se ejecuta a través de `acpx opencode`. [npm](https://www.npmjs.com/package/opencode-ai)

### FastAPI

Framework web Python de alto rendimiento para construir APIs. En este proyecto, sirve como puente entre el protocolo AG-UI (que espera el frontend CopilotKit) y el protocolo ACP (que hablan los agentes via acpx). Gestiona sesiones, traduce eventos y emite SSE. [Web](https://fastapi.tiangolo.com)

### Next.js

Framework React para aplicaciones web. Usado aquí como base del frontend (v16). Sirve la interfaz multi-panel de chat y se comunica con el backend via fetch/SSE. [Web](https://nextjs.org)

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                       │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ ChatPanel │  │ ChatPanel │  │ ChatPanel │  ← Paneles lado a  │
│  │ (sesión A)│  │ (sesión B)│  │ (sesión C)│    lado             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│       │              │              │                            │
│  CopilotKitProvider + HttpAgent (AG-UI)                         │
│       │              │              │                            │
└───────┼──────────────┼──────────────┼───────────────────────────┘
        │ SSE          │ SSE          │ SSE
        ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Python)                    │
│                                                                 │
│  POST /agent/{name}       ← Endpoint AG-UI (streaming SSE)     │
│  GET  /sessions           ← Listar sesiones (local + acpx)     │
│  POST /sessions           ← Crear nueva sesión                 │
│  DELETE /sessions/{n}     ← Cerrar sesión                      │
│  GET /sessions/status     ← Estado de actividad por sesión     │
│  GET /sessions/metrics    ← Métricas por sesión                │
│  GET /sessions/{n}/history← Historial de conversación          │
│  POST /sessions/{n}/reconnect ← Reconectar sesión caída       │
│  GET /workspaces          ← Workspaces de agentes con skills   │
│  GET /models/{harness}    ← Modelos disponibles por harness    │
│                                                                 │
│  agui_server.py ──→ launch_sessions.py ──→ acpx CLI            │
│       │                                       │                 │
│  acp_to_agui.py                               │                 │
│  (traduce ACP → AG-UI)                        ▼                 │
│                                          Agente (opencode,     │
│                                          claude, codex, etc.)  │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de una conversación

1. **Usuario** escribe un mensaje en un `ChatPanel` del frontend
2. **CopilotKit** envía un `POST /agent/{nombre}` al backend via `HttpAgent` (protocolo AG-UI)
3. **`agui_server.py`** extrae el texto del usuario y llama a `session.stream_prompt()`
4. **`launch_sessions.py`** ejecuta `acpx --format json {harness} -s {nombre} -f -` pasando el prompt por stdin
5. **`acpx`** envía el prompt al agente (opencode, claude, etc.) y retransmite eventos ACP como NDJSON por stdout
6. **`acp_to_agui.py`** traduce cada evento ACP (`agent_message_chunk`, `agent_thought_chunk`, `tool_call`, `tool_call_update`) a eventos AG-UI (`TextMessageChunkEvent`, `ReasoningMessageChunkEvent`, `ToolCallChunkEvent`, etc.)
7. **`agui_server.py`** gestiona el ciclo de vida de los eventos (start/content/end para reasoning y tool calls) y los envía como SSE al frontend
8. **CopilotKit** renderiza los mensajes, el pensamiento del agente y las tool calls en el chat

---

## Flujo de Mensajes y Persistencia

### Diagrama de flujo

```
 NAVEGADOR                          BACKEND (FastAPI)                    DISCO
 ─────────                          ─────────────────                    ─────

 ┌─────────────┐    POST /agent/{n}    ┌──────────────┐    stdin        ┌───────────┐
 │  CopilotChat │ ──────────────────▶  │ agui_server  │ ────────────▶  │   acpx    │
 │  (panel)     │    (AG-UI request)   │              │   prompt        │   CLI     │
 └──────┬───────┘                      └──────┬───────┘                 └─────┬─────┘
        │                                     │                               │
        │                                     │    stdout (NDJSON)            │
        │                                     │ ◀──────────────────────────── │
        │                                     │    eventos ACP JSON-RPC       │
        │                                     │                               │
        │                              ┌──────┴───────┐                       │
        │                              │ acp_to_agui  │                       │
        │                              │ (traductor)  │                ┌──────┴──────┐
        │                              └──────┬───────┘                │  ~/.acpx/   │
        │                                     │                        │  sessions/  │
        │         SSE stream (AG-UI)          │                        │  {id}.stream│
        │ ◀─────────────────────────────────  │                        │  .ndjson    │
        │   TextMessageChunkEvent             │                        │  (auto)     │
        │   ReasoningMessageChunkEvent        │                        └─────────────┘
        │   ToolCallChunkEvent                │
        │   ToolCallResultEvent               │
        │                                     │
 ┌──────┴───────┐                             │
 │  agent       │                             │
 │  .messages[] │                             │
 │  (JS memory) │                             │
 └──────┬───────┘                             │
        │                                     │
 ┌──────┴───────┐                      ┌──────┴───────┐
 │ localStorage │                      │  sessions/   │
 │ openPanels,  │                      │  index.json  │
 │ threadIds    │                      │  (metadata)  │
 └──────────────┘                      │              │
                                       │  sessions/   │
                                       │  history/    │
                                       │  {nombre}    │
                                       │  .json       │
                                       │  (mensajes   │
                                       │  con formato)│
                                       └──────────────┘
```

### Paso a paso

1. **Usuario escribe mensaje** — CopilotChat llama `agent.addMessage({ role: "user", content: texto })`, guarda en `agent.messages[]` (memoria JS), luego ejecuta `POST /agent/{nombre}` al backend
2. **Backend recibe prompt** — `agui_server.py` extrae el último texto del usuario y llama `session.stream_prompt(prompt)`
3. **Backend envía a acpx** — `launch_sessions.py` ejecuta `acpx --format json {harness} -s {nombre} -f -` y envía el prompt por stdin
4. **acpx comunica con el agente** — Reenvía el prompt al agente de codificación (OpenCode, Claude, etc.) via protocolo ACP. **acpx automáticamente escribe cada evento en `~/.acpx/sessions/{id}.stream.ndjson`**
5. **Backend traduce ACP → AG-UI** — `acp_to_agui.py` convierte cada evento: `agent_message_chunk` → `TextMessageChunkEvent`, `agent_thought_chunk` → `ReasoningMessageChunkEvent`, `tool_call` → `ToolCallChunkEvent`, `tool_call_update` → `ToolCallResultEvent`
6. **Backend envía SSE** — `agui_server.py` gestiona ciclo de vida de eventos (start/content/end) y envía como `StreamingResponse` SSE
7. **CopilotKit renderiza** — Recibe eventos SSE, actualiza `agent.messages[]` y renderiza texto (via ReactMarkdown con remarkGfm), pensamiento y tool calls en el panel de chat
8. **Backend guarda historial** — Al finalizar el stream, `agui_server.py` acumula todo el texto y thinking recibido durante el streaming y lo guarda en `sessions/history/{nombre}.json` con el formato markdown preservado (saltos de línea, listas, etc.)

### Dónde se almacena cada dato

| Dato | Ubicación | Tipo | Persiste tras cerrar navegador | Persiste tras reiniciar backend |
|------|-----------|------|-------------------------------|--------------------------------|
| Mensajes del chat (visual) | `agent.messages[]` | Memoria JS | No | No |
| Paneles abiertos y thread IDs | `localStorage` | Navegador | Sí | Sí |
| **Historial con formato** | **`sessions/history/{nombre}.json`** | **Archivo** | **Sí** | **Sí** |
| Stream ACP completo | `~/.acpx/sessions/{id}.stream.ndjson` | Archivo | Sí | Sí |
| Metadata de sesión (acpx) | `~/.acpx/sessions/{id}.json` | Archivo | Sí | Sí |
| Índice de sesiones (local) | `sessions/index.json` | Archivo | Sí | Sí |
| Índice de sesiones (acpx) | `~/.acpx/sessions/index.json` | Archivo | Sí | Sí |

> **Nota sobre historial y formato:** acpx guarda el contenido de los mensajes en `~/.acpx/sessions/`, pero **pierde los saltos de línea** al almacenar el texto final (ej. listas numeradas se concatenan sin `\n`). Por eso, el backend mantiene su propio historial en `sessions/history/` acumulando los chunks de texto durante el streaming, preservando así el formato markdown original (listas, párrafos, etc.). Al recargar la página, el endpoint `GET /sessions/{nombre}/history` consulta primero nuestro historial propio; solo si no existe, recurre al de acpx como fallback.

> **Nota sobre codificación UTF-8:** En Windows, `subprocess.Popen` con `text=True` usa cp1252 por defecto, lo que causaba corrupción de caracteres especiales (ñ, á, é, í → mojibake). Se forzó `encoding="utf-8"` en todas las llamadas a subprocesos, I/O de archivos y respuestas HTTP (`UnicodeJSONResponse` con `ensure_ascii=False`).

---

## Integración CopilotKit + AG-UI

Este proyecto usa [CopilotKit](https://copilotkit.ai) v2 con el protocolo [AG-UI](https://docs.ag-ui.com) para conectar el frontend con agentes backend personalizados.

### Paquetes utilizados

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `@copilotkit/react-core` | ^1.56.4 | Componentes React y hooks para chat con agentes |
| `@copilotkit/react-ui` | ^1.56.4 | Estilos CSS del chat |
| `@ag-ui/client` | ^0.0.52 | `HttpAgent` — cliente que conecta con endpoints AG-UI |
| `@ag-ui/core` | ^0.0.52 | Tipos de eventos AG-UI (backend Python) |
| `ag-ui-protocol` | ^0.1.10 | Tipos y `EventEncoder` para el backend Python |

### Componentes y hooks de CopilotKit usados

| Componente / Hook | Qué hace | Dónde se usa |
|-------------------|----------|--------------|
| **`CopilotKitProvider`** | Proveedor raíz que registra los agentes. Cada `ChatPanel` tiene su propio provider para que las sesiones streamen independientemente. | `ChatPanel` — envuelve cada panel de chat |
| **`CopilotChat`** | Componente de interfaz de chat completo (input, mensajes, thinking, tool calls). Renderiza la conversación con el agente. | `ChatPanel` — dentro de cada panel |
| **`CopilotChatConfigurationProvider`** | Configura qué agente (`agentId`) y qué hilo (`threadId`) usa un chat. | `ChatPanel` — envuelve `CopilotChat` y `BroadcastReceiver` |
| **`useCopilotChatConfiguration`** | Hook que lee la configuración del chat actual (agentId, threadId). | `BroadcastReceiver`, `ClearChatButton` — para obtener el agente activo |
| **`useAgent`** | Hook que devuelve la instancia del agente para un agentId/threadId dado. Permite acceder a `agent.addMessage()`, `agent.setMessages()`. | `BroadcastReceiver`, `ClearChatButton` — para enviar mensajes programáticamente o limpiar el chat |
| **`useCopilotKit`** | Hook que da acceso al runtime de CopilotKit. Permite ejecutar `copilotkit.runAgent()` manualmente. | `BroadcastReceiver` — para disparar el agente tras inyectar un mensaje de broadcast |

### Componente AG-UI

| Clase | Qué hace | Dónde se usa |
|-------|----------|--------------|
| **`HttpAgent`** | Cliente HTTP que implementa el protocolo AG-UI. Se conecta a un endpoint backend (`/agent/{nombre}`) y gestiona el streaming SSE. | `Home` — se crea un `HttpAgent` por cada sesión conocida, apuntando a `http://localhost:8000/agent/{nombre}` |

### Cómo se conectan

```
CopilotKitProvider
  ├── agents__unsafe_dev_only = { "mi_sesion": HttpAgent }
  │
  └── CopilotChatConfigurationProvider (agentId="mi_sesion")
       │
       ├── CopilotChat → renderiza la UI del chat
       │     └── al enviar mensaje → HttpAgent.run() → POST /agent/mi_sesion
       │
       └── BroadcastReceiver (opcional)
             └── inyecta mensajes programáticamente via useAgent + useCopilotKit
```

**Nota:** `agents__unsafe_dev_only` es una API de desarrollo de CopilotKit v2 que permite registrar agentes directamente sin pasar por CopilotKit Cloud. Los `HttpAgent` de AG-UI apuntan directamente a nuestro backend FastAPI.

---

## Estructura del Proyecto

```
agent-harness-orchestrator/
├── backend/
│   ├── agui_server.py          # Servidor FastAPI: endpoints AG-UI, gestión de sesiones
│   ├── launch_sessions.py      # Clase Session: crear/prompt/stream/cerrar via acpx
│   ├── acp_to_agui.py          # Traductor ACP JSON-RPC → eventos AG-UI
│   ├── available_models.py     # Listas de modelos soportados (OpenCode + Copilot CLI)
│   ├── remove_session.py       # Utilidad de limpieza de sesiones
│   ├── requirements.txt        # Dependencias Python
│   ├── Dockerfile              # Imagen Docker del backend
│   ├── pytest.ini              # Configuración pytest
│   └── tests/                  # Tests unitarios (8 archivos, 70+ tests)
│       ├── test_acp_to_agui.py
│       ├── test_agui_server.py
│       ├── test_session.py
│       ├── test_remove_session.py
│       ├── test_utf8_encoding.py
│       ├── test_history_persistence.py
│       ├── test_reconnect_timeout.py
│       └── test_tool_call_lifecycle.py
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Home: layout multi-panel, polling de estado, broadcast
│   │   ├── layout.tsx          # Layout raíz Next.js
│   │   ├── providers.tsx       # Providers de la app
│   │   ├── types.ts            # Tipos TypeScript (sesiones, estado, métricas, config)
│   │   ├── hooks.ts            # Hooks custom (useAccentColor)
│   │   ├── globals.css         # Estilos globales (Tailwind v4)
│   │   └── components/
│   │       ├── ChatPanel.tsx       # Panel de chat con CopilotKit + historial + broadcast
│   │       ├── Sidebar.tsx         # Sidebar colapsable: sesiones, tema, controles
│   │       ├── SessionForm.tsx     # Modal de creación de sesión con workspace/skills
│   │       ├── SessionListItem.tsx # Fila de sesión con indicadores de estado y salud
│   │       ├── BroadcastForm.tsx   # Formulario de broadcast a todos los paneles
│   │       └── ThemePanel.tsx      # Selector de tema y color de acento
│   ├── Dockerfile              # Imagen Docker del frontend
│   └── package.json
├── agents/                     # Workspaces de agentes con skills especializados
│   ├── debugging/
│   │   ├── opencode.json           # Config: modelo, provider, instrucciones
│   │   └── .opencode/skills/
│   │       └── systematic-debugging/
│   │           └── SKILL.md        # Skill de debugging sistemático
│   └── documentation/
│       ├── opencode.json           # Config: modelo, provider, instrucciones
│       └── .opencode/skills/
│           └── ddf/
│               ├── SKILL.md            # Skill de documentación funcional (DDF)
│               ├── references/         # Templates y checklists de calidad
│               └── section-generators/ # Generadores por sección (12 secciones)
├── sessions/                   # Índice local de sesiones
│   ├── index.json              # Metadata de sesiones (nombre, harness, modelo, fechas)
│   └── history/                # Historial propio de conversaciones (preserva formato markdown)
├── opencode.json               # Configuración de modelos y providers para OpenCode (raíz)
├── docker-compose.yml          # Docker Compose: backend (8000) + frontend (3000)
├── run.py                      # Launcher del backend desde la raíz del proyecto
├── dev.ps1                     # Script para lanzar backend + frontend + abrir navegador
└── docs/                       # Documentación adicional
```

---

## Funcionalidades

### Sesiones Multi-Agente
Ejecutar múltiples agentes en paralelo, cada uno con su modelo, directorio de trabajo y configuración independiente.

### 100+ Modelos Soportados
AWS Bedrock (Claude, Llama, Mistral, Qwen, DeepSeek, Nova, ...), NagaAI (7 modelos gratuitos) y OpenCode Zen (6 modelos gratuitos).

### 16 Harnesses de Agente
OpenCode, Claude Code, Codex, Gemini, Cursor, Copilot, Kiro, Qwen, Kimi, Kilocode, iFlow, Droid, OpenClaw, Pi, Qoder, Trae.

### Workspaces de Agentes con Skills
Directorios especializados en `agents/` con su propio `opencode.json`, modelos y skills. El backend auto-descubre workspaces via `GET /workspaces` y expone los skills disponibles (parseados desde YAML frontmatter en archivos `.md`). Actualmente existen:
- **debugging** — Skill de debugging sistemático (root-cause tracing, defense in depth, test isolation)
- **documentation** — Skill de Documentación de Diseño Funcional (DDF) con 12 secciones, templates y checklists de calidad

### Tool Calling Completo
Ciclo de vida completo de tool calls: `ToolCallStartEvent` → `ToolCallChunkEvent` (nombre + args) → `ToolCallResultEvent`. Deduplicación por ID, tracking de tool calls abiertos/cerrados, soporte para estados intermedios via `CustomEvent`.

### Interfaz Multi-Panel
Abrir múltiples chats lado a lado en el navegador. Componentes modulares: `ChatPanel`, `Sidebar`, `SessionForm`, `SessionListItem`, `BroadcastForm`, `ThemePanel`.

### Broadcast
Enviar el mismo prompt a todas las sesiones abiertas simultáneamente. Formulario muestra conteo de paneles activos y estado de envío.

### Estado en Tiempo Real
Indicadores visuales por sesión: `idle`, `thinking`, `tool_use`, `responding`. Polling cada 1.5 segundos.

### Health Check y Reconexión
Cada sesión reporta su salud: `connected`, `disconnected`, `reconnecting`. Endpoint `POST /sessions/{name}/reconnect` para reconectar sesiones caídas con cooldown de 10 segundos. Indicadores visuales en la UI.

### Métricas por Sesión
Endpoint `GET /sessions/metrics` con estadísticas por sesión: turnos, caracteres de texto/thinking, tool calls totales, tiempos de respuesta (total, promedio, último), métricas del último turno.

### Persistencia de Mensajes
Historial de chat guardado en `sessions/history/` con formato markdown preservado (saltos de línea, listas, código). Se restaura al recargar la página. Fallback a historial de acpx si no existe historial propio.

### Temas y Personalización
Modo claro/oscuro con toggle. 6 colores de acento seleccionables (Blue, Violet, Rose, Amber, Emerald, Cyan). Sidebar colapsable para maximizar espacio de paneles.

### Almacenamiento Local de Sesiones
Índice propio en `sessions/index.json`, con fallback a `~/.acpx/sessions/`. Historial de conversaciones con formato preservado en `sessions/history/`.

---

## Prerrequisitos

| Requisito | Versión | Instalación |
|-----------|---------|-------------|
| Python | 3.12+ | [python.org](https://python.org/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| acpx | latest | `npm install -g acpx@latest` |
| OpenCode | latest | `npm install -g opencode-ai@latest` |

Para modelos de AWS Bedrock, configurar credenciales AWS (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`).

Para modelos NagaAI (gratis), configurar `NAGA_API_KEY`.

---

## Instalación

```bash
git clone https://github.com/DDC-NEORIS/agent-harness-orchestrator.git
cd agent-harness-orchestrator

# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

---

## Inicio Rápido

### Opción 1: Docker Compose

```bash
docker compose up --build
```

Backend en `http://localhost:8000`, frontend en `http://localhost:3000`.

### Opción 2: Script de desarrollo

```powershell
.\dev.ps1
```

Lanza backend + frontend en terminales separadas y abre el navegador en `http://localhost:3000`.

### Opción 3: Manual

```bash
# Terminal 1 — Backend
python run.py

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Abrir `http://localhost:3000` en el navegador.

### Opción 4: Uso programático (sin frontend)

```python
from backend.launch_sessions import Session

session = Session(
    agent_harness="opencode",
    name="mi_agente",
    working_dir="./agents/debugging",
    LLM="opencode/big-pickle",
)

respuesta = session.prompt_session("Arregla el test que falla", capture_output=True)
print(respuesta)

session.close_session()
```

---

## API del Backend

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/sessions` | Listar sesiones (locales + acpx) |
| `POST` | `/sessions` | Crear nueva sesión |
| `DELETE` | `/sessions/{nombre}` | Cerrar y eliminar sesión |
| `GET` | `/sessions/{nombre}/history` | Historial de conversación (con formato preservado) |
| `GET` | `/sessions/status` | Estado de actividad y salud de cada sesión |
| `GET` | `/sessions/metrics` | Métricas de rendimiento por sesión |
| `POST` | `/sessions/{nombre}/reconnect` | Reconectar sesión desconectada |
| `GET` | `/workspaces` | Auto-descubrir workspaces de agentes con skills |
| `GET` | `/models/{harness}` | Modelos disponibles para un harness |
| `POST` | `/agent/{nombre}` | Endpoint AG-UI — streaming SSE de conversación |

### Crear sesión (POST /sessions)

```json
{
  "name": "mi_sesion",
  "agent_harness": "opencode",
  "working_dir": "C:/ruta/al/proyecto",
  "LLM": "opencode/big-pickle"
}
```

### Respuesta de métricas (GET /sessions/metrics)

```json
{
  "mi_sesion": {
    "turns": 5,
    "total_text_chars": 12340,
    "total_thinking_chars": 4500,
    "total_tool_calls": 8,
    "total_response_time_ms": 45000,
    "avg_response_time_ms": 9000,
    "last_response_time_ms": 7200,
    "last_tool_calls": 2,
    "last_text_chars": 1800,
    "last_thinking_chars": 600
  }
}
```

---

## Componentes Frontend

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| **Home** | `page.tsx` | Layout principal: multi-panel + sidebar, polling de estado, gestión de agentes HttpAgent |
| **ChatPanel** | `components/ChatPanel.tsx` | Panel de chat individual con CopilotKit, carga de historial, recepción de broadcast |
| **Sidebar** | `components/Sidebar.tsx` | Sidebar colapsable: lista de sesiones, creación/eliminación, tema, broadcast |
| **SessionForm** | `components/SessionForm.tsx` | Modal para crear sesión: harness, modelo, workspace con skills |
| **SessionListItem** | `components/SessionListItem.tsx` | Fila de sesión: indicadores de estado (pulsing dot), salud, directorio de trabajo |
| **BroadcastForm** | `components/BroadcastForm.tsx` | Formulario para enviar prompt a todos los paneles abiertos |
| **ThemePanel** | `components/ThemePanel.tsx` | Selector de tema claro/oscuro y color de acento |

### Tipos TypeScript (`types.ts`)

| Tipo | Descripción |
|------|-------------|
| `SessionStatus` | `"idle" \| "thinking" \| "tool_use" \| "responding"` |
| `SessionHealth` | `"connected" \| "disconnected" \| "reconnecting"` |
| `SessionMetrics` | Turnos, caracteres, tool calls, tiempos de respuesta |
| `AcpxSession` | Sesión de acpx: nombre, cwd, closed, lastUsedAt |
| `ModelData` | Grupos de modelos con default |
| `HistoryEntry` | Mensaje de historial: role, content, thinking |

---

## Eventos ACP → AG-UI

El traductor `acp_to_agui.py` mapea notificaciones ACP a eventos AG-UI:

| Evento ACP (`sessionUpdate`) | Evento AG-UI | Descripción |
|------------------------------|--------------|-------------|
| `agent_message_chunk` | `TextMessageChunkEvent` | Texto de respuesta del agente |
| `agent_thought_chunk` | `ReasoningMessageChunkEvent` | Pensamiento/razonamiento del agente |
| `tool_call` | `ToolCallChunkEvent` | Invocación de herramienta (nombre + args) |
| `tool_call_update` (completed/failed) | `ToolCallResultEvent` | Resultado de la herramienta |
| `tool_call_update` (otros) | `CustomEvent` | Estados intermedios |
| Cualquier otro | `CustomEvent` | Eventos desconocidos preservados |

---

## Workspaces de Agentes

Los workspaces son directorios en `agents/` que contienen un `opencode.json` y skills especializados. El backend los auto-descubre y los expone en el formulario de creación de sesiones.

### Estructura de un workspace

```
agents/{nombre}/
├── opencode.json                    # Modelo, provider, instrucciones
└── .opencode/skills/{skill-name}/
    ├── SKILL.md                     # Instrucciones del skill (YAML frontmatter + markdown)
    └── references/                  # Archivos de referencia opcionales
```

### Workspaces disponibles

| Workspace | Modelo por defecto | Skill | Descripción |
|-----------|-------------------|-------|-------------|
| **root** | (configurable) | — | Workspace genérico sin skills |
| **debugging** | `opencode/minimax-m2.5-free` | systematic-debugging | Root-cause tracing, defense in depth, test isolation |
| **documentation** | `opencode/minimax-m2.5-free` | ddf | Documentación de Diseño Funcional: 12 secciones, templates, checklists |

---

## Harnesses Soportados

| Agente | Comando acpx | Notas |
|--------|-------------|-------|
| OpenCode | `acpx opencode` | Por defecto — open-source, multi-provider |
| Claude Code | `acpx claude` | Anthropic Claude Code |
| Codex | `acpx codex` | OpenAI Codex CLI |
| Gemini | `acpx gemini` | Google Gemini CLI |
| Cursor | `acpx cursor` | Cursor CLI agent |
| Copilot | `acpx copilot` | GitHub Copilot CLI |
| Kiro | `acpx kiro` | Kiro CLI |
| Qwen | `acpx qwen` | Qwen Code |
| Kimi | `acpx kimi` | Kimi CLI |
| Kilocode | `acpx kilocode` | Kilocode agent |
| iFlow | `acpx iflow` | iFlow agent |
| Droid | `acpx droid` | Droid agent |
| OpenClaw | `acpx openclaw` | OpenClaw agent |
| Pi | `acpx pi` | Pi Coding Agent |
| Qoder | `acpx qoder` | Qoder agent |
| Trae | `acpx trae` | Trae agent |

---

## Docker

### Docker Compose (recomendado)

```bash
docker compose up --build
```

| Servicio | Puerto | Imagen base |
|----------|--------|-------------|
| backend | 8000 | Python 3.12-slim + Node.js 18 + acpx + opencode-ai |
| frontend | 3000 | Node 20 Alpine |

Variables de entorno via archivo `.env`. Volumen `./sessions` montado en `/project/sessions` para persistencia.

### Dockerfiles individuales

```bash
# Backend
docker build -t aho-backend ./backend
docker run -p 8000:8000 --env-file .env aho-backend

# Frontend
docker build -t aho-frontend ./frontend
docker run -p 3000:3000 aho-frontend
```

---

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

70+ tests en 8 archivos cubriendo:

| Archivo | Cobertura |
|---------|-----------|
| `test_acp_to_agui.py` | Traducción ACP → AG-UI para todos los tipos de evento |
| `test_agui_server.py` | Endpoints del servidor: sesiones, modelos, workspaces, agentes |
| `test_session.py` | Ciclo de vida de sesión: crear, stream, cerrar |
| `test_remove_session.py` | Limpieza de sesiones |
| `test_utf8_encoding.py` | Codificación UTF-8 con caracteres especiales |
| `test_history_persistence.py` | Persistencia de historial con formato markdown |
| `test_reconnect_timeout.py` | Reconexión con cooldown y timeouts |
| `test_tool_call_lifecycle.py` | Ciclo de vida completo de tool calls: start → chunks → result |

---

## Roadmap

| Fase | Foco | Estado |
|------|------|--------|
| **1** | Sesiones async + concurrentes (`asyncio`) | Completado |
| **2** | Frontend web con CopilotKit + AG-UI | Completado |
| **3** | Almacenamiento local de sesiones (pre-DB) | Completado |
| **4** | Docker Compose (backend + frontend) | Completado |
| **5** | Workspaces de agentes con skills especializados | Completado |
| **6** | Health checks, reconexión y métricas | Completado |
| **7** | Tool calling completo (ciclo de vida ACP → AG-UI) | Completado |
| **8** | Componentes frontend modulares (ChatPanel, Sidebar, SessionForm, etc.) | Completado |
| **9** | Base de datos para sesiones (reemplazar JSON) | Planificado |
| **10** | Bucle de reacción GitHub (`githubkit`) | Planificado |
| **11** | Coordinación multi-agente (descomposición de tareas) | Planificado |

---

## Licencia

[MIT](LICENSE) — Copyright (c) 2026 NEORIS
