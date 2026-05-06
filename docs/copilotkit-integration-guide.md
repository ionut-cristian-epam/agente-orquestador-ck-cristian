# Guía de Integración CopilotKit + AG-UI

Guía para migrar la integración CopilotKit + AG-UI a otros proyectos. Cubre todos los archivos necesarios, dependencias, y patrones clave.

---

## Resumen de la Arquitectura

```
Frontend (Next.js + CopilotKit)     Backend (FastAPI + ag-ui-protocol)
─────────────────────────────────   ──────────────────────────────────
CopilotKitProvider                  POST /agent/{name}
  └─ CopilotChat                      └─ SSE StreamingResponse
       └─ HttpAgent ──── SSE ────►        └─ EventEncoder
                                             └─ TextMessageChunkEvent
                                             └─ ReasoningMessageChunkEvent
                                             └─ ToolCallChunkEvent
                                             └─ ToolCallResultEvent
```

CopilotKit v2 consume eventos AG-UI. El frontend usa `HttpAgent` para conectarse a un endpoint backend que emite Server-Sent Events. No se necesita CopilotKit Cloud.

---

## 1. Dependencias

### Frontend (`package.json`)

```json
{
  "dependencies": {
    "@copilotkit/react-core": "^1.56.4",
    "@copilotkit/react-ui": "^1.56.4",
    "@ag-ui/client": "^0.0.52",
    "@ag-ui/core": "^0.0.52"
  }
}
```

```bash
npm install @copilotkit/react-core @copilotkit/react-ui @ag-ui/client @ag-ui/core
```

### Backend (`requirements.txt`)

```
fastapi>=0.115
uvicorn[standard]>=0.32
ag-ui-protocol>=0.1.10
pydantic>=2.0
```

```bash
pip install fastapi uvicorn ag-ui-protocol pydantic
```

---

## 2. Archivos Necesarios (Frontend)

### 2.1 `layout.tsx` — Importar estilos de CopilotKit

```tsx
// Línea clave: importar CSS de CopilotKit v2
import "@copilotkit/react-ui/v2/styles.css";
```

Sin esto, el chat no tiene estilos. Debe ir en el layout raíz.

### 2.2 `globals.css` — Fixes para CopilotKit + Tailwind

Tailwind preflight resetea listas. CopilotKit renderiza markdown internamente. Hay que restaurar estilos de listas y asegurar que el chat ocupe su contenedor:

```css
/* Restaurar listas dentro del markdown de CopilotKit */
.copilotKitMarkdown ol {
  list-style-type: decimal;
  padding-left: 20px;
}

.copilotKitMarkdown ul {
  list-style-type: disc;
  padding-left: 20px;
}

/* CopilotChat debe llenar su contenedor y hacer scroll interno */
[data-copilotkit-chat],
.copilotKitChat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
```

### 2.3 `page.tsx` (o componente principal) — Crear HttpAgent

```tsx
import { HttpAgent } from "@ag-ui/client";

// Crear un HttpAgent por cada agente/sesión
const agent = new HttpAgent({
  url: "http://localhost:8000/agent/mi_sesion",
});

// Mapa de agentes (si tienes varios)
const agents = { "mi_sesion": agent };
```

**Patrón multi-sesión** (crear agentes dinámicamente):

```tsx
import { useRef, useMemo } from "react";
import { HttpAgent } from "@ag-ui/client";

const agentMapRef = useRef<Record<string, HttpAgent>>({});

const agentMap = useMemo(() => {
  const prev = agentMapRef.current;
  const next: Record<string, HttpAgent> = {};
  for (const name of sessionNames) {
    // Reutilizar instancia existente o crear nueva
    next[name] = prev[name] ?? new HttpAgent({
      url: `${BACKEND}/agent/${encodeURIComponent(name)}`,
    });
  }
  agentMapRef.current = next;
  return next;
}, [sessionNames]);
```

### 2.4 `ChatPanel.tsx` — Componente de chat completo

Este es el componente central. Integra `CopilotKitProvider`, `CopilotChat`, y hooks:

```tsx
"use client";

import { useMemo } from "react";
import {
  CopilotKitProvider,
  CopilotChat,
  CopilotChatConfigurationProvider,
} from "@copilotkit/react-core/v2";
import { HttpAgent } from "@ag-ui/client";

export function ChatPanel({
  name,
  agent,
}: {
  name: string;
  agent: HttpAgent;
}) {
  // Mapa de agentes: CopilotKit necesita un Record<string, HttpAgent>
  const agents = useMemo(() => ({ [name]: agent }), [name, agent]);

  // threadId único por sesión (persistir en localStorage)
  const threadId = useMemo(() => {
    const key = `chat_thread:${name}`;
    const existing = localStorage.getItem(key);
    if (existing) return existing;
    const id = crypto.randomUUID();
    localStorage.setItem(key, id);
    return id;
  }, [name]);

  return (
    <CopilotKitProvider agents__unsafe_dev_only={agents}>
      <CopilotChatConfigurationProvider agentId={name} threadId={threadId}>
        <CopilotChat
          agentId={name}
          labels={{ chatInputPlaceholder: `Message ${name}...` }}
        />
      </CopilotChatConfigurationProvider>
    </CopilotKitProvider>
  );
}
```

**Puntos clave:**
- `agents__unsafe_dev_only` — API de dev de CopilotKit v2 para registrar agentes sin CopilotKit Cloud
- Cada `CopilotKitProvider` es independiente — permite múltiples chats simultáneos
- `CopilotChatConfigurationProvider` vincula un agentId y threadId al chat
- `CopilotChat` renderiza la UI completa (input, mensajes, thinking, tool calls)

### 2.5 Hooks disponibles de CopilotKit

Si necesitas interactuar programáticamente con el chat (ej. broadcast, limpiar mensajes):

```tsx
import {
  useCopilotChatConfiguration,
  useAgent,
  useCopilotKit,
} from "@copilotkit/react-core/v2";

// Dentro de un componente hijo de CopilotChatConfigurationProvider:

// Leer configuración actual
const chatCfg = useCopilotChatConfiguration();

// Acceder al agente (mensajes, addMessage, setMessages)
const { agent } = useAgent({
  agentId: chatCfg?.agentId,
  threadId: chatCfg?.threadId,
});

// Acceder al runtime (para ejecutar agente manualmente)
const { copilotkit } = useCopilotKit();

// Enviar mensaje programáticamente
agent.addMessage({
  id: crypto.randomUUID(),
  role: "user",
  content: "Hola agente",
});
await copilotkit.runAgent({ agent });

// Limpiar chat
agent.setMessages([]);

// Cargar historial
agent.setMessages([
  { id: "1", role: "user", content: "Pregunta" },
  { id: "2", role: "assistant", content: "Respuesta" },
  { id: "3", role: "reasoning", content: "Pensamiento del agente" },
]);
```

---

## 3. Archivos Necesarios (Backend)

### 3.1 Endpoint AG-UI (`agui_server.py`)

El endpoint debe:
1. Recibir `RunAgentInput` (formato AG-UI)
2. Emitir SSE con `EventEncoder`
3. Enviar eventos con tipos AG-UI

**Ejemplo mínimo:**

```python
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ag_ui.core import (
    RunAgentInput,
    RunStartedEvent,
    RunFinishedEvent,
    TextMessageChunkEvent,
    ReasoningMessageChunkEvent,
    ToolCallChunkEvent,
    ToolCallResultEvent,
)
from ag_ui.encoder import EventEncoder

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/agent/{name}")
async def run_agent(name: str, input_data: RunAgentInput, request: Request):
    accept = request.headers.get("accept")
    encoder = EventEncoder(accept=accept)

    async def event_gen():
        msg_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        # 1. Señal de inicio
        yield encoder.encode(RunStartedEvent(runId=run_id, threadId=input_data.threadId))

        # 2. Emitir texto (chunked)
        for chunk in ["Hola", ", ", "mundo!"]:
            yield encoder.encode(TextMessageChunkEvent(
                messageId=msg_id,
                role="assistant",
                delta=chunk,
            ))

        # 3. Emitir pensamiento/reasoning (opcional)
        yield encoder.encode(ReasoningMessageChunkEvent(
            messageId=f"{msg_id}:think",
            delta="Estoy pensando en la respuesta...",
        ))

        # 4. Emitir tool call (opcional)
        tool_id = str(uuid.uuid4())
        yield encoder.encode(ToolCallChunkEvent(
            toolCallId=tool_id,
            toolCallName="read_file",
            delta='{"path": "main.py"}',
        ))
        yield encoder.encode(ToolCallResultEvent(
            messageId=tool_id,
            toolCallId=tool_id,
            content="print('hello world')",
            role="tool",
        ))

        # 5. Señal de fin
        yield encoder.encode(RunFinishedEvent(runId=run_id, threadId=input_data.threadId))

    return StreamingResponse(event_gen(), media_type=encoder.content_type)
```

### 3.2 Traductor ACP → AG-UI (`acp_to_agui.py`)

Si usas `acpx` (protocolo ACP), necesitas traducir eventos. Este archivo mapea:

| Evento ACP | Evento AG-UI | Cuándo |
|------------|-------------|--------|
| `agent_message_chunk` | `TextMessageChunkEvent` | Texto del agente |
| `agent_thought_chunk` | `ReasoningMessageChunkEvent` | Pensamiento/reasoning |
| `tool_call` | `ToolCallChunkEvent` | Inicio de herramienta |
| `tool_call_update` (completed/failed) | `ToolCallResultEvent` | Resultado de herramienta |
| Cualquier otro | `CustomEvent` | Eventos desconocidos |

**Si NO usas acpx**, no necesitas este archivo. Solo emite eventos AG-UI directamente desde tu lógica de backend.

### 3.3 Ciclo de vida de eventos en streaming

El flujo SSE completo debe seguir este orden:

```
RunStartedEvent
  ├─ ReasoningMessageChunkEvent (N chunks, opcional)
  ├─ TextMessageChunkEvent (N chunks)
  ├─ ToolCallChunkEvent → ToolCallResultEvent (por cada tool call)
  └─ (repetir según interacción)
RunFinishedEvent
```

**Tracking de tool calls abiertos** (importante para evitar duplicados):

```python
open_tool_calls: dict[str, str] = {}    # toolCallId -> toolCallName
seen_tool_call_ids: set[str] = set()     # evitar re-emitir START para mismo ID

# Al recibir ToolCallChunkEvent:
if tool_call_id not in seen_tool_call_ids:
    seen_tool_call_ids.add(tool_call_id)
    open_tool_calls[tool_call_id] = tool_name
    # Emitir ToolCallStartEvent

# Al recibir ToolCallResultEvent:
if tool_call_id in open_tool_calls:
    del open_tool_calls[tool_call_id]
    # Emitir ToolCallEndEvent
```

---

## 4. Resumen de Archivos para Copiar

### Mínimo viable (un solo chat)

| Archivo | Capa | Qué copiar |
|---------|------|-----------|
| `package.json` | Frontend | 4 dependencias: `@copilotkit/*` + `@ag-ui/*` |
| `layout.tsx` | Frontend | Línea `import "@copilotkit/react-ui/v2/styles.css"` |
| `globals.css` | Frontend | Bloque CSS de fixes (listas + contenedor) |
| `ChatPanel.tsx` | Frontend | Componente completo (o simplificado) |
| `requirements.txt` | Backend | `ag-ui-protocol>=0.1.10` |
| Endpoint `/agent/{name}` | Backend | Función `run_agent` con `EventEncoder` + SSE |

### Completo (multi-sesión + broadcast + historial)

| Archivo | Qué aporta |
|---------|-----------|
| `page.tsx` | Multi-panel, creación dinámica de `HttpAgent`, polling de estado |
| `ChatPanel.tsx` | Chat con historial, broadcast, métricas, health check |
| `types.ts` | Tipos TypeScript: sesiones, estado, métricas, broadcast |
| `hooks.ts` | Hook de color de acento (opcional) |
| `Sidebar.tsx` | Gestión visual de sesiones (opcional) |
| `BroadcastForm.tsx` | UI de broadcast (opcional) |
| `agui_server.py` | Servidor FastAPI completo con gestión de sesiones |
| `acp_to_agui.py` | Traductor ACP → AG-UI (solo si usas acpx) |

---

## 5. Pasos de Migración

### Paso 1 — Instalar dependencias

```bash
# Frontend
npm install @copilotkit/react-core @copilotkit/react-ui @ag-ui/client @ag-ui/core

# Backend
pip install ag-ui-protocol fastapi uvicorn
```

### Paso 2 — Importar CSS en layout

```tsx
// En tu layout.tsx raíz
import "@copilotkit/react-ui/v2/styles.css";
```

### Paso 3 — Añadir fixes CSS

Copiar el bloque de `.copilotKitMarkdown` y `[data-copilotkit-chat]` a tu `globals.css`.

### Paso 4 — Crear endpoint backend

Crear un `POST /agent/{name}` que reciba `RunAgentInput` y devuelva `StreamingResponse` con eventos codificados por `EventEncoder`.

### Paso 5 — Crear componente ChatPanel

Copiar el patrón `CopilotKitProvider > CopilotChatConfigurationProvider > CopilotChat` con `HttpAgent`.

### Paso 6 — Configurar CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL de tu frontend
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Paso 7 — Verificar

1. Levantar backend: `uvicorn tu_servidor:app --port 8000`
2. Levantar frontend: `npm run dev`
3. Abrir `http://localhost:3000`
4. Enviar mensaje → debe aparecer respuesta via SSE

---

## 6. Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| Chat sin estilos | Falta CSS import | Añadir `import "@copilotkit/react-ui/v2/styles.css"` en layout |
| Listas sin bullets/números | Tailwind preflight | Añadir fixes CSS para `.copilotKitMarkdown` |
| Chat no hace scroll | Contenedor sin height | Añadir CSS `height: 100%; overflow: hidden` |
| CORS error en browser | Backend sin CORS | Añadir `CORSMiddleware` a FastAPI |
| "No agent found" | `agents__unsafe_dev_only` mal configurado | Verificar que el nombre del agente coincide con `agentId` |
| SSE no llega al frontend | `EventEncoder` con `accept` incorrecto | Pasar `request.headers.get("accept")` al `EventEncoder` |
| UTF-8 corrupto (Windows) | `subprocess.Popen` usa cp1252 | Forzar `encoding="utf-8"` en Popen y respuestas |

---

## 7. Referencia de Imports

### Frontend

```tsx
// CopilotKit — componentes y hooks
import {
  CopilotKitProvider,
  CopilotChat,
  CopilotChatConfigurationProvider,
  useCopilotChatConfiguration,
  useAgent,
  useCopilotKit,
} from "@copilotkit/react-core/v2";

// AG-UI — cliente HTTP
import { HttpAgent } from "@ag-ui/client";

// CSS (en layout.tsx)
import "@copilotkit/react-ui/v2/styles.css";
```

### Backend

```python
# AG-UI — tipos de eventos
from ag_ui.core import (
    RunAgentInput,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageChunkEvent,
    ReasoningMessageChunkEvent,
    ToolCallChunkEvent,
    ToolCallResultEvent,
    CustomEvent,
)

# AG-UI — encoder SSE
from ag_ui.encoder import EventEncoder
```
