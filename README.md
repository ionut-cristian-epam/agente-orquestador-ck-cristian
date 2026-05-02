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
│  POST /agent/{name}  ← Endpoint AG-UI (streaming SSE)           │
│  GET  /sessions      ← Listar sesiones (local + acpx)           │
│  POST /sessions      ← Crear nueva sesión                       │
│  DELETE /sessions/{n} ← Cerrar sesión                           │
│  GET /sessions/status ← Estado de actividad por sesión          │
│  GET /models/{harness}← Modelos disponibles por harness         │
│                                                                 │
│  agui_server.py ──→ launch_sessions.py ──→ acpx CLI             │
│       │                                       │                 │
│  acp_to_agui.py                               │                 │
│  (traduce ACP → AG-UI)                        ▼                 │
│                                          Agente (opencode,      │
│                                          claude, codex, etc.)   │
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
│   ├── pytest.ini              # Configuración pytest
│   └── tests/                  # Tests unitarios
│       ├── test_acp_to_agui.py
│       ├── test_agui_server.py
│       ├── test_session.py
│       └── test_remove_session.py
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # UI principal: sidebar + paneles de chat multi-sesión
│   │   ├── layout.tsx          # Layout raíz Next.js
│   │   └── globals.css         # Estilos globales (Tailwind)
│   └── package.json
├── sessions/                   # Índice local de sesiones (gitignored)
├── opencode.json               # Configuración de modelos y providers para OpenCode
├── run.py                      # Launcher del backend desde la raíz del proyecto
├── dev.ps1                     # Script para lanzar backend + frontend + abrir navegador
├── agent_debugging/            # Directorio de trabajo para agentes de debugging
├── agent_documentation/        # Directorio de trabajo para agentes de documentación
└── docs/                       # Documentación adicional
```

---

## Funcionalidades

- **Sesiones multi-agente** — Ejecutar múltiples agentes en paralelo, cada uno con su modelo, directorio de trabajo y configuración
- **100+ modelos soportados** — AWS Bedrock (Claude, Llama, Mistral, Qwen, DeepSeek, ...), NagaAI (gratis) y OpenCode Zen (gratis)
- **16 harnesses de agente** — OpenCode, Claude Code, Codex, Gemini, Cursor, Copilot, Kiro, Qwen, Kimi, Kilocode, iFlow, Droid, OpenClaw, Pi, Qoder, Trae
- **Interfaz multi-panel** — Abrir múltiples chats lado a lado en el navegador
- **Broadcast** — Enviar el mismo prompt a todas las sesiones abiertas simultáneamente
- **Estado en tiempo real** — Indicadores visuales por sesión: idle, thinking, tool_use, responding
- **Persistencia de mensajes** — Historial de chat guardado en localStorage por sesión
- **Sidebar colapsable** — Más espacio para los paneles cuando se necesita
- **Almacenamiento local de sesiones** — Índice propio en `sessions/index.json`, con fallback a `~/.acpx/sessions/`

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

### Opción 1: Script de desarrollo (recomendado)

```powershell
.\dev.ps1
```

Lanza backend + frontend en terminales separadas y abre el navegador en `http://localhost:3000`.

### Opción 2: Manual

```bash
# Terminal 1 — Backend
python run.py

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Abrir `http://localhost:3000` en el navegador.

### Opción 3: Uso programático (sin frontend)

```python
from backend.launch_sessions import Session

session = Session(
    agent_harness="opencode",
    name="mi_agente",
    working_dir="./agent_debugging",
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
| `GET` | `/sessions/status` | Estado de actividad de cada sesión |
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

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

65 tests cubriendo: traducción ACP→AG-UI, endpoints del servidor, validación de modelos, gestión de sesiones y limpieza.

---

## Roadmap

| Fase | Foco | Estado |
|------|------|--------|
| **1** | Sesiones async + concurrentes (`asyncio`) | Completado |
| **2** | Frontend web con CopilotKit + AG-UI | Completado |
| **3** | Almacenamiento local de sesiones (pre-DB) | Completado |
| **4** | Docker Compose (backend + frontend) | Planificado |
| **5** | Base de datos para sesiones (reemplazar JSON) | Planificado |
| **6** | Bucle de reacción GitHub (`githubkit`) | Planificado |
| **7** | Coordinación multi-agente (descomposición de tareas) | Planificado |

---

## Licencia

[MIT](LICENSE) — Copyright (c) 2026 NEORIS
