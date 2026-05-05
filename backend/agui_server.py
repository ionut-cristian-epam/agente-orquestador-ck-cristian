"""FastAPI bridge: AG-UI protocol <-> agent-harness-orchestrator Sessions.

Endpoints:
  POST /agent/{name}      AG-UI run endpoint (CopilotKit `runtimeUrl` target)
  GET  /sessions          List bridge-registered + acpx-known sessions
  POST /sessions          Create a new persistent session
  DELETE /sessions/{name} Close a session
"""
import sys
# Force UTF-8 encoding for all I/O
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

import json
import os
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# Custom JSON response to ensure UTF-8 encoding with proper headers
class UnicodeJSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"
    
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

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
from available_models import SUPPORTED_MODELS_OPENCODE, SUPPORTED_MODELS_COPILOT_CLI
from remove_session import remove_session

PROJECT_ROOT = Path(
    os.environ.get("AGENT_ORCH_PROJECT_ROOT", Path(__file__).resolve().parent.parent)
).resolve()
SESSIONS_DIR = PROJECT_ROOT / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# Directory for our own message history (preserves formatting lost by acpx)
HISTORY_DIR = SESSIONS_DIR / "history"
HISTORY_DIR.mkdir(exist_ok=True)

# Legacy fallback: acpx still writes to ~/.acpx/sessions
ACPX_SESSIONS_DIR = Path.home() / ".acpx" / "sessions"

_sessions: dict[str, Session] = {}

# Per-session activity status: "idle" | "thinking" | "tool_use" | "responding"
_session_status: dict[str, str] = {}

# Per-session connection health: "connected" | "disconnected" | "reconnecting"
_session_health: dict[str, str] = {}

# Per-session metrics
_session_metrics: dict[str, dict] = {}


def _init_metrics(name: str) -> None:
    """Initialise metrics dict for a session if it doesn't exist."""
    if name not in _session_metrics:
        _session_metrics[name] = {
            "turns": 0,
            "total_text_chars": 0,
            "total_thinking_chars": 0,
            "total_tool_calls": 0,
            "total_response_time_ms": 0,
            "last_response_time_ms": 0,
            "avg_response_time_ms": 0,
            "last_tool_calls": 0,
            "last_text_chars": 0,
            "last_thinking_chars": 0,
        }


def _update_metrics_after_turn(
    name: str,
    *,
    response_time_ms: int,
    text_chars: int,
    thinking_chars: int,
    tool_calls: int,
) -> None:
    _init_metrics(name)
    m = _session_metrics[name]
    m["turns"] += 1
    m["total_text_chars"] += text_chars
    m["total_thinking_chars"] += thinking_chars
    m["total_tool_calls"] += tool_calls
    m["total_response_time_ms"] += response_time_ms
    m["last_response_time_ms"] = response_time_ms
    m["avg_response_time_ms"] = round(m["total_response_time_ms"] / m["turns"])
    m["last_tool_calls"] = tool_calls
    m["last_text_chars"] = text_chars
    m["last_thinking_chars"] = thinking_chars


def _history_path(name: str) -> Path:
    """Return path to our own history file for a session."""
    safe = name.replace("/", "_").replace("\\", "_")
    return HISTORY_DIR / f"{safe}.json"


def _load_own_history(name: str) -> list[dict] | None:
    """Load our own saved history for a session, or None if not available."""
    p = _history_path(name)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("messages", [])
    except (json.JSONDecodeError, OSError):
        return None


def _save_own_history(name: str, messages: list[dict]) -> None:
    """Save messages to our own history file for a session."""
    p = _history_path(name)
    p.write_text(
        json.dumps({"messages": messages}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

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


def _normalize_name(name: str) -> str:
    """Normalize session names to NFC form for consistent handling of Unicode characters."""
    return unicodedata.normalize("NFC", name)


class CreateSessionRequest(BaseModel):
    name: str
    agent_harness: str = "opencode"
    working_dir: str
    LLM: Optional[str] = None


def _load_local_index() -> dict:
    index_path = SESSIONS_DIR / "index.json"
    if not index_path.exists():
        return {"schema": "orchestrator.session-index.v1", "entries": []}
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_local_index(index: dict) -> None:
    index_path = SESSIONS_DIR / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def _add_to_local_index(entry: dict) -> None:
    entry_name = _normalize_name(entry.get("name", ""))
    index = _load_local_index()
    index["entries"] = [e for e in index["entries"] if _normalize_name(e.get("name", "")) != entry_name]
    index["entries"].append(entry)
    _save_local_index(index)


def _remove_from_local_index(name: str) -> None:
    name = _normalize_name(name)
    index = _load_local_index()
    index["entries"] = [e for e in index["entries"] if _normalize_name(e.get("name", "")) != name]
    _save_local_index(index)


def _load_acpx_index() -> dict:
    index_path = ACPX_SESSIONS_DIR / "index.json"
    if not index_path.exists():
        return {"entries": []}
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_session_entry(name: str) -> Optional[dict]:
    name = _normalize_name(name)
    for entry in _load_local_index().get("entries", []):
        if _normalize_name(entry.get("name", "")) == name and not entry.get("closed"):
            return entry
    for entry in _load_acpx_index().get("entries", []):
        if (
            _normalize_name(entry.get("name", "")) == name
            and not entry.get("closed")
            and _is_inside_project(entry.get("cwd"))
        ):
            return entry
    return None


def _attach_existing(name: str) -> Optional[Session]:
    entry = _find_session_entry(name)
    if not entry:
        return None
    cwd = entry.get("cwd")
    cmd = entry.get("agentCommand", "") or ""
    harness = entry.get("agent_harness") or next(
        (h for h in KNOWN_HARNESSES if h in cmd), "opencode"
    )

    sess = Session.__new__(Session)
    sess.agent_harness = harness
    sess.name = name
    sess.working_dir = cwd
    sess.LLM = entry.get("LLM")
    return sess


def _get_or_attach(name: str) -> Session:
    name = _normalize_name(name)
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
    _session_health[name] = "connected"
    return sess


app = FastAPI(
    title="agent-harness-orchestrator AG-UI bridge",
    default_response_class=UnicodeJSONResponse
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/sessions")
def list_sessions():
    local = _load_local_index()
    acpx = _load_acpx_index()
    seen = set()
    merged = []
    for e in local.get("entries", []):
        seen.add(e.get("name"))
        merged.append({
            "name": e.get("name"),
            "cwd": e.get("cwd"),
            "closed": e.get("closed", False),
            "lastUsedAt": e.get("lastUsedAt"),
            "agent_harness": e.get("agent_harness", "opencode"),
            "LLM": e.get("LLM"),
        })
    for e in acpx.get("entries", []):
        if e.get("name") not in seen and _is_inside_project(e.get("cwd")):
            merged.append({
                "name": e.get("name"),
                "cwd": e.get("cwd"),
                "closed": e.get("closed", False),
                "lastUsedAt": e.get("lastUsedAt"),
            })
    return {
        "projectRoot": str(PROJECT_ROOT),
        "registered": list(_sessions.keys()),
        "acpx": merged,
    }


@app.post("/sessions")
def create_session(req: CreateSessionRequest):
    normalized_name = _normalize_name(req.name)
    print(f"[create_session] received name: {req.name!r} (len={len(req.name)})", flush=True)
    print(f"[create_session] normalized name: {normalized_name!r} (len={len(normalized_name)})", flush=True)
    if normalized_name in _sessions:
        return {"status": "exists", "name": normalized_name}
    kwargs = dict(
        agent_harness=req.agent_harness,
        name=normalized_name,
        working_dir=req.working_dir,
        capture_output=True,
    )
    if req.LLM:
        kwargs["LLM"] = req.LLM
    sess = Session(**kwargs)
    _sessions[normalized_name] = sess
    _session_health[normalized_name] = "connected"
    _add_to_local_index({
        "name": normalized_name,
        "agent_harness": req.agent_harness,
        "cwd": req.working_dir,
        "LLM": req.LLM,
        "closed": False,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "lastUsedAt": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "created", "name": normalized_name}


@app.get("/sessions/status")
def session_status():
    """Return activity status and connection health of every registered session."""
    return {
        name: {
            "activity": _session_status.get(name, "idle"),
            "health": _session_health.get(name, "connected"),
        }
        for name in _sessions
    }


@app.get("/sessions/metrics")
def all_session_metrics():
    """Return metrics for all registered sessions."""
    result = {}
    for name in _sessions:
        _init_metrics(name)
        result[name] = _session_metrics[name]
    return result


@app.get("/sessions/{name}/history")
def get_session_history(name: str, tail: Optional[int] = None):
    """Return conversation history, preferring our own saved copy (preserves formatting)."""
    sess = _get_or_attach(name)
    normalized = _normalize_name(name)

    # Try our own history first (preserves markdown newlines)
    own = _load_own_history(normalized)
    if own is not None:
        entries = own
    else:
        # Fallback to acpx (may have stripped newlines)
        entries = sess.read_history(tail=None)

    if tail is not None and tail > 0:
        entries = entries[-tail:]
    return {"session": name, "entries": entries}


@app.delete("/sessions/{name}")
def delete_session(name: str):
    name = _normalize_name(name)
    sess = _sessions.pop(name, None)
    _session_status.pop(name, None)
    _session_health.pop(name, None)
    _session_metrics.pop(name, None)
    if sess is None:
        sess = _attach_existing(name)
    if sess is None:
        raise HTTPException(404, f"Session '{name}' not found")
    remove_session(name)
    try:
        sess.close_session()
    except Exception:
        pass
    # Clean up our own history file
    hp = _history_path(name)
    if hp.exists():
        hp.unlink()
    _remove_from_local_index(name)
    return {"status": "deleted"}


@app.post("/sessions/{name}/reconnect")
def reconnect_session(name: str):
    """Attempt to reconnect a disconnected session's acpx process."""
    name = _normalize_name(name)
    sess = _get_or_attach(name)
    _session_health[name] = "reconnecting"
    try:
        sess._ensure_connected()
        _session_health[name] = "connected"
        return {"status": "reconnected"}
    except Exception as e:
        _session_health[name] = "disconnected"
        raise HTTPException(500, f"Reconnect failed: {e}")


_MODELS_BY_HARNESS: dict[str, dict[str, list[str]]] = {
    "opencode": {},
    "copilot": {"Copilot CLI": SUPPORTED_MODELS_COPILOT_CLI},
}

for _m in SUPPORTED_MODELS_OPENCODE:
    _provider = _m.split("/")[0]
    _label = {
        "nagaai": "NagaAI (Free)",
        "opencode": "OpenCode Zen (Free)",
        "amazon-bedrock": "Amazon Bedrock",
    }.get(_provider, _provider)
    _MODELS_BY_HARNESS["opencode"].setdefault(_label, []).append(_m)


@app.get("/models/{harness}")
def get_models(harness: str):
    groups = _MODELS_BY_HARNESS.get(harness)
    if groups is None:
        return {"groups": {}, "default": ""}
    flat = [m for models in groups.values() for m in models]
    default = flat[0] if flat else ""
    return {"groups": groups, "default": default}


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
        import time as _time
        msg_id = str(uuid.uuid4())
        reasoning_id = str(uuid.uuid4())
        reasoning_started = False
        # Track open tool calls: toolCallId -> toolCallName
        open_tool_calls: dict[str, str] = {}

        # Accumulate streamed content to save history with proper formatting
        accumulated_text = []
        accumulated_thinking = []

        # Metrics tracking for this turn
        _turn_start = _time.monotonic()
        _turn_tool_calls = 0

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
                        accumulated_thinking.append(ev.delta)
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
                        tc_id = ev.tool_call_id or str(uuid.uuid4())
                        tc_name = ev.tool_call_name or "tool"
                        if tc_id not in open_tool_calls:
                            _turn_tool_calls += 1
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
                        tc_id = ev.tool_call_id
                        if tc_id and tc_id in open_tool_calls:
                            yield encoder.encode(ToolCallEndEvent(toolCallId=tc_id))
                            del open_tool_calls[tc_id]
                        continue

                    # --- Text message chunks ---
                    # The AG-UI client chunk transformer auto-wraps these
                    # with TEXT_MESSAGE_START/CONTENT/END — do NOT send manual lifecycle events
                    if isinstance(ev, TextMessageChunkEvent):
                        _session_status[name] = "responding"
                        accumulated_text.append(ev.delta)
                        if reasoning_started:
                            yield encoder.encode(ReasoningMessageEndEvent(messageId=reasoning_id))
                            reasoning_started = False
                            reasoning_id = str(uuid.uuid4())
                        ev.message_id = msg_id
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
            _session_health[name] = "connected"

            # Update per-session metrics
            _turn_elapsed_ms = int((_time.monotonic() - _turn_start) * 1000)
            _text_chars = sum(len(c) for c in accumulated_text)
            _think_chars = sum(len(c) for c in accumulated_thinking)
            _update_metrics_after_turn(
                name,
                response_time_ms=_turn_elapsed_ms,
                text_chars=_text_chars,
                thinking_chars=_think_chars,
                tool_calls=_turn_tool_calls,
            )

            # Save accumulated content to our own history (preserves formatting)
            normalized = _normalize_name(name)
            existing = _load_own_history(normalized) or []
            existing.append({"role": "user", "content": prompt})
            assistant_entry = {"role": "assistant", "content": "".join(accumulated_text)}
            thinking_text = "".join(accumulated_thinking)
            if thinking_text:
                assistant_entry["thinking"] = thinking_text
            existing.append(assistant_entry)
            _save_own_history(normalized, existing)

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
            _session_health[name] = "disconnected"
            yield encoder.encode(RunErrorEvent(message=f"{type(e).__name__}: {e}"))

    return StreamingResponse(event_gen(), media_type=encoder.get_content_type())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agui_server:app", host="0.0.0.0", port=8000, reload=False)
