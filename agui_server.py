"""FastAPI bridge: AG-UI protocol <-> agent-harness-orchestrator Sessions.

Endpoints:
  POST /agent/{name}      AG-UI run endpoint (CopilotKit `runtimeUrl` target)
  GET  /sessions          List bridge-registered + acpx-known sessions
  POST /sessions          Create a new persistent session
  DELETE /sessions/{name} Close a session
"""
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ag_ui.core import (
    RunAgentInput,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageChunkEvent,
    ReasoningMessageChunkEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageStartEvent,
    ReasoningMessageEndEvent,
    ToolCallChunkEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
)
from ag_ui.encoder import EventEncoder

from launch_sessions import Session
from acp_to_agui import map_acp_event

ACPX_SESSIONS_DIR = Path.home() / ".acpx" / "sessions"
PROJECT_ROOT = Path(
    os.environ.get("AGENT_ORCH_PROJECT_ROOT", Path(__file__).resolve().parent)
).resolve()

_sessions: dict[str, Session] = {}

# Per-session activity status: "idle" | "thinking" | "tool_use" | "responding"
_session_status: dict[str, str] = {}


def _is_inside_project(cwd: Optional[str]) -> bool:
    if not cwd:
        return False
    try:
        return Path(cwd).resolve().is_relative_to(PROJECT_ROOT)
    except (OSError, ValueError):
        return False

KNOWN_HARNESSES = (
    "opencode", "claude", "codex", "gemini", "cursor", "copilot",
    "kiro", "qwen", "kimi", "kilocode", "iflow", "droid", "openclaw",
    "pi", "qoder", "trae",
)


class CreateSessionRequest(BaseModel):
    name: str
    agent_harness: str = "opencode"
    working_dir: str
    LLM: Optional[str] = None


def _load_acpx_index() -> dict:
    index_path = ACPX_SESSIONS_DIR / "index.json"
    if not index_path.exists():
        return {"entries": []}
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_acpx_entry(name: str) -> Optional[dict]:
    for entry in _load_acpx_index().get("entries", []):
        if (
            entry.get("name") == name
            and not entry.get("closed")
            and _is_inside_project(entry.get("cwd"))
        ):
            return entry
    return None


def _attach_existing(name: str) -> Optional[Session]:
    entry = _find_acpx_entry(name)
    if not entry:
        return None
    cwd = entry.get("cwd")
    cmd = entry.get("agentCommand", "") or ""
    harness = next((h for h in KNOWN_HARNESSES if h in cmd), "opencode")

    sess = Session.__new__(Session)
    sess.agent_harness = harness
    sess.name = name
    sess.working_dir = cwd
    sess.LLM = None
    return sess


def _get_or_attach(name: str) -> Session:
    if name in _sessions:
        return _sessions[name]
    sess = _attach_existing(name)
    if sess is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Session '{name}' not found. "
                f"Create it first: POST /sessions"
            ),
        )
    _sessions[name] = sess
    return sess


app = FastAPI(title="agent-harness-orchestrator AG-UI bridge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/sessions")
def list_sessions():
    index = _load_acpx_index()
    return {
        "projectRoot": str(PROJECT_ROOT),
        "registered": list(_sessions.keys()),
        "acpx": [
            {
                "name": e.get("name"),
                "cwd": e.get("cwd"),
                "closed": e.get("closed", False),
                "lastUsedAt": e.get("lastUsedAt"),
            }
            for e in index.get("entries", [])
            if _is_inside_project(e.get("cwd"))
        ],
    }


@app.post("/sessions")
def create_session(req: CreateSessionRequest):
    if req.name in _sessions:
        return {"status": "exists", "name": req.name}
    kwargs = dict(
        agent_harness=req.agent_harness,
        name=req.name,
        working_dir=req.working_dir,
        capture_output=True,
    )
    if req.LLM:
        kwargs["LLM"] = req.LLM
    sess = Session(**kwargs)
    _sessions[req.name] = sess
    return {"status": "created", "name": req.name}


@app.get("/sessions/status")
def session_status():
    """Return the current activity status of every registered session."""
    return {name: _session_status.get(name, "idle") for name in _sessions}


@app.delete("/sessions/{name}")
def delete_session(name: str):
    sess = _sessions.pop(name, None)
    _session_status.pop(name, None)
    if sess is None:
        sess = _attach_existing(name)
    if sess is None:
        raise HTTPException(404, f"Session '{name}' not found")
    try:
        sess.close_session()
    except Exception as e:
        return {"status": "closed_with_errors", "error": str(e)}
    return {"status": "closed"}


def _last_user_text(input_data: RunAgentInput) -> Optional[str]:
    for m in reversed(input_data.messages):
        if m.role != "user":
            continue
        if isinstance(m.content, str) and m.content.strip():
            return m.content
        if isinstance(m.content, list):
            parts = [p.text for p in m.content if getattr(p, "type", None) == "text" and getattr(p, "text", None)]
            if parts:
                return "".join(parts)
    return None


@app.post("/agent/{name}")
async def run_agent(name: str, input_data: RunAgentInput, request: Request):
    sess = _get_or_attach(name)
    prompt = _last_user_text(input_data)
    if not prompt:
        raise HTTPException(400, "No user message with content found in messages")

    accept = request.headers.get("accept")
    encoder = EventEncoder(accept=accept)
    print(f"[run_agent] session={name!r} prompt={prompt!r} accept={accept!r}", flush=True)

    async def event_gen():
        import uuid
        msg_id = str(uuid.uuid4())
        reasoning_id = str(uuid.uuid4())
        reasoning_started = False
        # Track open tool calls: toolCallId -> toolCallName
        open_tool_calls: dict[str, str] = {}

        _session_status[name] = "thinking"
        yield encoder.encode(RunStartedEvent(
            thread_id=input_data.thread_id,
            run_id=input_data.run_id,
        ))
        try:
            async for rpc in sess.stream_prompt(prompt):
                print(f"[acp] {json.dumps(rpc, default=str)[:200]}", flush=True)
                for ev in map_acp_event(rpc):
                    # --- Reasoning (thinking) lifecycle ---
                    # Use explicit lifecycle (no chunk transformer for reasoning)
                    if isinstance(ev, ReasoningMessageChunkEvent):
                        _session_status[name] = "thinking"
                        if not reasoning_started:
                            yield encoder.encode(ReasoningMessageStartEvent(
                                messageId=reasoning_id,
                                role="reasoning",
                            ))
                            reasoning_started = True
                        yield encoder.encode(ReasoningMessageContentEvent(
                            messageId=reasoning_id,
                            delta=ev.delta,
                        ))
                        continue

                    # --- Tool call lifecycle ---
                    if isinstance(ev, ToolCallChunkEvent):
                        _session_status[name] = "tool_use"
                        tc_id = ev.toolCallId or str(uuid.uuid4())
                        tc_name = ev.toolCallName or "tool"
                        if tc_id not in open_tool_calls:
                            if reasoning_started:
                                yield encoder.encode(ReasoningMessageEndEvent(messageId=reasoning_id))
                                reasoning_started = False
                                reasoning_id = str(uuid.uuid4())
                            yield encoder.encode(ToolCallStartEvent(
                                toolCallId=tc_id,
                                toolCallName=tc_name,
                                parentMessageId=msg_id,
                            ))
                            open_tool_calls[tc_id] = tc_name
                        yield encoder.encode(ev)
                        continue

                    if isinstance(ev, ToolCallResultEvent):
                        yield encoder.encode(ev)
                        tc_id = ev.toolCallId
                        if tc_id and tc_id in open_tool_calls:
                            yield encoder.encode(ToolCallEndEvent(toolCallId=tc_id))
                            del open_tool_calls[tc_id]
                        continue

                    # --- Text message chunks ---
                    # The AG-UI client chunk transformer auto-wraps these
                    # with TEXT_MESSAGE_START/CONTENT/END — do NOT send manual lifecycle events
                    if isinstance(ev, TextMessageChunkEvent):
                        _session_status[name] = "responding"
                        if reasoning_started:
                            yield encoder.encode(ReasoningMessageEndEvent(messageId=reasoning_id))
                            reasoning_started = False
                            reasoning_id = str(uuid.uuid4())
                        ev.messageId = msg_id
                        yield encoder.encode(ev)
                        continue

                    # Other events (CustomEvent, etc.)
                    print(f"[run_agent] unhandled event: {ev}", flush=True)
                    yield encoder.encode(ev)

            # Close any open lifecycle events
            if reasoning_started:
                yield encoder.encode(ReasoningMessageEndEvent(messageId=reasoning_id))
            for tc_id in list(open_tool_calls):
                yield encoder.encode(ToolCallEndEvent(toolCallId=tc_id))

            _session_status[name] = "idle"
            yield encoder.encode(RunFinishedEvent(
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            ))
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[run_agent] {type(e).__name__}: {e!r}\n{tb}", flush=True)
            if reasoning_started:
                yield encoder.encode(ReasoningMessageEndEvent(messageId=reasoning_id))
            for tc_id in list(open_tool_calls):
                yield encoder.encode(ToolCallEndEvent(toolCallId=tc_id))
            _session_status[name] = "idle"
            yield encoder.encode(RunErrorEvent(message=f"{type(e).__name__}: {e}"))

    return StreamingResponse(event_gen(), media_type=encoder.get_content_type())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agui_server:app", host="0.0.0.0", port=8000, reload=False)
