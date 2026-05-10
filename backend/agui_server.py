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

import asyncio
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
    ToolCallResultEvent,
)
from ag_ui.encoder import EventEncoder

from launch_sessions import Session
from acp_to_agui import map_acp_event
from available_models import (
    SUPPORTED_MODELS_OPENCODE,
    SUPPORTED_MODELS_COPILOT_CLI,
    SUPPORTED_MODELS_LANGGRAPH,
)
from remove_session import remove_session
from langgraph_session import LangGraphSession

PROJECT_ROOT = Path(
    os.environ.get("AGENT_ORCH_PROJECT_ROOT", Path(__file__).resolve().parent.parent)
).resolve()
AGENTS_DIR = PROJECT_ROOT / "agents"
SESSIONS_DIR = PROJECT_ROOT / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# Directory for our own message history (preserves formatting lost by acpx)
HISTORY_DIR = SESSIONS_DIR / "history"
HISTORY_DIR.mkdir(exist_ok=True)

# Legacy fallback: acpx still writes to ~/.acpx/sessions
ACPX_SESSIONS_DIR = Path.home() / ".acpx" / "sessions"

_sessions: dict[str, "Session | LangGraphSession"] = {}

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


# ---------------------------------------------------------------------------
# SSE subscription: push status+metrics changes to connected clients
# ---------------------------------------------------------------------------

_status_subscribers: list[asyncio.Queue] = []


def _build_status_snapshot() -> dict:
    metrics = {}
    for name in _sessions:
        _init_metrics(name)
        metrics[name] = _session_metrics[name]
    return {
        "status": {
            name: {
                "activity": _session_status.get(name, "idle"),
                "health": _session_health.get(name, "connected"),
            }
            for name in _sessions
        },
        "metrics": metrics,
    }


def _notify_status_change():
    """Push status snapshot to all SSE subscribers."""
    if not _status_subscribers:
        return
    snapshot = _build_status_snapshot()
    for q in list(_status_subscribers):
        try:
            q.put_nowait(snapshot)
        except asyncio.QueueFull:
            pass


async def _auto_reconnect(name: str):
    """Background task: auto-reconnect a disconnected CLI session."""
    sess = _sessions.get(name)
    if not sess or isinstance(sess, LangGraphSession):
        return
    for attempt in range(3):
        await asyncio.sleep(5 * (attempt + 1))
        if _session_health.get(name) != "disconnected":
            return
        _session_health[name] = "reconnecting"
        _notify_status_change()
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, sess._ensure_connected)
            _session_health[name] = "connected"
            _notify_status_change()
            print(f"[auto-reconnect] {name} reconnected (attempt {attempt + 1})", flush=True)
            return
        except Exception as e:
            print(f"[auto-reconnect] {name} attempt {attempt + 1} failed: {e}", flush=True)
    _session_health[name] = "disconnected"
    _notify_status_change()
    print(f"[auto-reconnect] {name} gave up after 3 attempts", flush=True)


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
    "langgraph",
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


def _attach_existing(name: str) -> "Session | LangGraphSession | None":
    entry = _find_session_entry(name)
    if not entry:
        return None
    cwd = entry.get("cwd")
    cmd = entry.get("agentCommand", "") or ""
    harness = entry.get("agent_harness") or next(
        (h for h in KNOWN_HARNESSES if h in cmd), "opencode"
    )

    if harness == "langgraph":
        # Re-instantiate the in-process LangGraph session and rehydrate history
        sess = LangGraphSession(
            name=name,
            working_dir=cwd,
            LLM=entry.get("LLM"),
        )
        history = _load_own_history(name)
        if history:
            sess.restore_history(history)
        return sess

    sess = Session.__new__(Session)
    sess.agent_harness = harness
    sess.name = name
    sess.working_dir = cwd
    sess.LLM = entry.get("LLM")
    return sess


def _get_or_attach(name: str) -> "Session | LangGraphSession":
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


import re as _re

def _parse_skill_frontmatter(skill_path: Path) -> dict:
    """Parse YAML frontmatter from a skill markdown file."""
    text = skill_path.read_text(encoding="utf-8")
    match = _re.match(r"^---\s*\n(.+?)\n---", text, _re.DOTALL)
    if not match:
        return {"name": skill_path.stem, "description": ""}
    frontmatter = match.group(1)
    result = {"name": skill_path.stem, "description": ""}
    for line in frontmatter.splitlines():
        if line.startswith("name:"):
            result["name"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("description:"):
            result["description"] = line.split(":", 1)[1].strip().strip('"')
    return result


def _scan_skills(workspace_path: Path) -> list[dict]:
    """Scan the skills/ directory of a workspace and return skill metadata.

    Supports two layouts (matching the OpenCode convention):
      - Flat: skills/{name}.md
      - Subdir: skills/{name}/SKILL.md
    """
    skills_dir = workspace_path / "skills"
    if not skills_dir.is_dir():
        return []
    skills = []
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_file() and entry.suffix == ".md":
            skills.append(_parse_skill_frontmatter(entry))
        elif entry.is_dir():
            skill_md = entry / "SKILL.md"
            if skill_md.is_file():
                meta = _parse_skill_frontmatter(skill_md)
                # Prefer the directory name over the file stem for subdir layout
                if not meta.get("name") or meta["name"] == "SKILL":
                    meta["name"] = entry.name
                skills.append(meta)
    return skills


@app.get("/workspaces")
def list_workspaces():
    """Auto-discover available agent workspaces.

    Supports two workspace types:
      - opencode.json -> CLI harness (opencode and 15 others via acpx)
      - langgraph_agent.json -> in-process LangGraph harness
    """
    workspaces = [{
        "name": "root",
        "path": str(PROJECT_ROOT),
        "skills": [],
        "description": "Generic (no specialized skills)",
        "harness": None,
    }]
    if AGENTS_DIR.is_dir():
        for child in sorted(AGENTS_DIR.iterdir()):
            if not child.is_dir():
                continue
            if (child / "langgraph_agent.json").exists():
                try:
                    config = json.loads((child / "langgraph_agent.json").read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    config = {}
                workspaces.append({
                    "name": child.name,
                    "path": str(child),
                    "skills": _scan_skills(child),
                    "description": config.get("description", f"LangGraph: {child.name}"),
                    "harness": "langgraph",
                })
            elif (child / "opencode.json").exists():
                workspaces.append({
                    "name": child.name,
                    "path": str(child),
                    "skills": _scan_skills(child),
                    "description": f"Agent: {child.name}",
                    "harness": "opencode",
                })
    return workspaces


@app.post("/sessions")
def create_session(req: CreateSessionRequest):
    normalized_name = _normalize_name(req.name)
    print(f"[create_session] received name: {req.name!r} (len={len(req.name)})", flush=True)
    print(f"[create_session] normalized name: {normalized_name!r} (len={len(normalized_name)})", flush=True)
    if normalized_name in _sessions:
        return {"status": "exists", "name": normalized_name}

    if req.agent_harness == "langgraph":
        # In-process LangGraph agent — no acpx subprocess
        sess = LangGraphSession(
            name=normalized_name,
            working_dir=req.working_dir,
            LLM=req.LLM,
        )
    else:
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


@app.get("/sessions/subscribe")
async def subscribe_sessions():
    """SSE endpoint: streams session status+metrics in real time.

    Replaces polling of /sessions/status + /sessions/metrics.
    Sends an initial snapshot on connect, then pushes deltas on change.
    Sends a full snapshot every 15s as keepalive.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _status_subscribers.append(queue)

    async def event_stream():
        try:
            yield f"event: status\ndata: {json.dumps(_build_status_snapshot(), ensure_ascii=False)}\n\n"
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: status\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: status\ndata: {json.dumps(_build_status_snapshot(), ensure_ascii=False)}\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            if queue in _status_subscribers:
                _status_subscribers.remove(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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

    # Try to attach if not in memory, but tolerate failure (e.g. missing API key
    # for langgraph sessions). Deletion should always succeed if the session
    # exists in either local or acpx index.
    if sess is None:
        try:
            sess = _attach_existing(name)
        except Exception as e:
            print(f"[delete_session] _attach_existing failed: {e!r}", flush=True)
            sess = None

    entry = _find_session_entry(name)
    if sess is None and entry is None:
        raise HTTPException(404, f"Session '{name}' not found")

    remove_session(name)
    if sess is not None:
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
    """Attempt to reconnect a disconnected session's acpx process.

    No-op for langgraph sessions (always connected, in-process).
    """
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


@app.get("/sessions/{name}/tools")
def get_session_tools(name: str):
    """Return list of tools available to a session (LangGraph only, CLI agents don't expose tools)."""
    name = _normalize_name(name)
    sess = _get_or_attach(name)
    tools = getattr(sess, "available_tools", [])
    return {"session": name, "tools": tools}


_MODELS_BY_HARNESS: dict[str, dict[str, list[str]]] = {
    "opencode": {},
    "copilot": {"Copilot CLI": SUPPORTED_MODELS_COPILOT_CLI},
    "langgraph": {},
}

for _m in SUPPORTED_MODELS_OPENCODE:
    _provider = _m.split("/")[0]
    _label = {
        "nagaai": "NagaAI (Free)",
        "opencode": "OpenCode Zen (Free)",
        "amazon-bedrock": "Amazon Bedrock",
    }.get(_provider, _provider)
    _MODELS_BY_HARNESS["opencode"].setdefault(_label, []).append(_m)

for _m in SUPPORTED_MODELS_LANGGRAPH:
    _provider = _m.split("/")[0]
    _label = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "google": "Google",
        "groq": "Groq (Free)",
        "cerebras": "Cerebras (Free, fastest)",
        "nagaai": "NagaAI (Free)",
        "openrouter": "OpenRouter (Free tier)",
    }.get(_provider, _provider)
    _MODELS_BY_HARNESS["langgraph"].setdefault(_label, []).append(_m)


@app.get("/models/{harness}")
def get_models(harness: str):
    groups = _MODELS_BY_HARNESS.get(harness)
    if groups is None:
        return {"groups": {}, "default": ""}
    flat = [m for models in groups.values() for m in models]
    default = flat[0] if flat else ""
    return {"groups": groups, "default": default}


def _get_workspace_skill_info(working_dir: Optional[str], harness: str) -> Optional[dict]:
    """Return skill metadata for any workspace type, or None.

    Detects:
      - LangGraph workspaces: langgraph_agent.json -> system_prompt_file
      - OpenCode (and CLI agent) workspaces: opencode.json -> instructions[0]

    Returns dict with: skill_name, skill_path, prompt_chars (or None).
    """
    if not working_dir:
        return None
    wd = Path(working_dir)
    if not wd.is_dir():
        return None

    skill_path_rel: Optional[str] = None

    lg_config = wd / "langgraph_agent.json"
    oc_config = wd / "opencode.json"

    if lg_config.exists():
        try:
            cfg = json.loads(lg_config.read_text(encoding="utf-8"))
            skill_path_rel = cfg.get("system_prompt_file")
        except (json.JSONDecodeError, OSError):
            return None
    elif oc_config.exists():
        try:
            cfg = json.loads(oc_config.read_text(encoding="utf-8"))
            instructions = cfg.get("instructions") or []
            if instructions:
                skill_path_rel = instructions[0]
        except (json.JSONDecodeError, OSError):
            return None

    if not skill_path_rel:
        return None

    skill_path = wd / skill_path_rel
    if not skill_path.exists():
        return {"skill_name": Path(skill_path_rel).parent.name or "unknown", "skill_path": skill_path_rel, "prompt_chars": None}

    text = skill_path.read_text(encoding="utf-8")
    skill_name = Path(skill_path_rel).parent.name or skill_path.stem
    # Prefer YAML frontmatter "name:" if present
    fm = _re.match(r"^---\s*\n(.+?)\n---", text, _re.DOTALL)
    if fm:
        for line in fm.group(1).splitlines():
            if line.startswith("name:"):
                skill_name = line.split(":", 1)[1].strip().strip('"')
                break

    return {
        "skill_name": skill_name,
        "skill_path": skill_path_rel,
        "prompt_chars": len(text),
    }


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


async def _agui_event_source(sess, prompt: str):
    """Yield AG-UI BaseEvent objects from either an acpx Session or LangGraphSession.

    For acpx Session: stream_prompt yields ACP dicts -> map_acp_event translates.
    For LangGraphSession: stream_prompt yields BaseEvent directly.
    """
    if isinstance(sess, LangGraphSession):
        async for ev in sess.stream_prompt(prompt):
            yield ev
    else:
        async for rpc in sess.stream_prompt(prompt):
            print(f"[acp] {json.dumps(rpc, default=str)[:200]}", flush=True)
            for ev in map_acp_event(rpc):
                yield ev


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
        # Track all tool call IDs ever used (to avoid re-emitting START for same ID)
        seen_tool_call_ids: set[str] = set()

        # Accumulate streamed content to save history with proper formatting
        accumulated_text = []
        accumulated_thinking = []

        # Metrics tracking for this turn
        _turn_start = _time.monotonic()
        _turn_tool_calls = 0

        _prev_activity = None
        _session_status[name] = "thinking"
        _notify_status_change()
        yield encoder.encode(RunStartedEvent(
            thread_id=input_data.thread_id,
            run_id=input_data.run_id,
        ))

        # --- Skill activation: synthetic reasoning event (works for all harnesses) ---
        skill_info = _get_workspace_skill_info(
            getattr(sess, "working_dir", None),
            getattr(sess, "agent_harness", "unknown"),
        )
        is_first_turn = not (_load_own_history(_normalize_name(name)) or [])
        if skill_info or sess.LLM:
            lines = [
                f"🎯 **Workspace:** `{Path(sess.working_dir).name if sess.working_dir else 'root'}`",
                f"🤖 **Harness:** `{sess.agent_harness}` · **Modelo:** `{sess.LLM or '(default)'}`",
            ]
            if skill_info:
                lines.append(f"📋 **Skill activo:** `{skill_info['skill_name']}`")
                if is_first_turn and skill_info.get("prompt_chars"):
                    lines.append(
                        f"📂 **Cargado desde:** `{skill_info['skill_path']}` "
                        f"({skill_info['prompt_chars']} caracteres)"
                    )
            # Show available tools for LangGraph sessions
            tools_list = getattr(sess, "available_tools", None)
            if tools_list:
                tool_names = ", ".join(f"`{t['name']}`" for t in tools_list)
                lines.append(f"🔧 **Tools disponibles:** {tool_names}")
            yield encoder.encode(ReasoningMessageStartEvent(
                messageId=reasoning_id,
                role="reasoning",
            ))
            yield encoder.encode(ReasoningMessageContentEvent(
                messageId=reasoning_id,
                delta="\n".join(lines) + "\n\n---\n\n",
            ))
            reasoning_started = True
            # Skill activation is metadata — not persisted to history

        try:
            async for ev in _agui_event_source(sess, prompt):
                # --- Reasoning (thinking) lifecycle ---
                # Use explicit lifecycle (no chunk transformer for reasoning)
                if isinstance(ev, ReasoningMessageChunkEvent):
                    _session_status[name] = "thinking"
                    if _prev_activity != "thinking":
                        _prev_activity = "thinking"
                        _notify_status_change()
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
                # CopilotKit's chunk transformer auto-wraps TOOL_CALL_CHUNK
                # with TOOL_CALL_START/ARGS/END — do NOT send explicit lifecycle events
                if isinstance(ev, ToolCallChunkEvent):
                    _session_status[name] = "tool_use"
                    if _prev_activity != "tool_use":
                        _prev_activity = "tool_use"
                        _notify_status_change()
                    tc_id = ev.tool_call_id or str(uuid.uuid4())
                    tc_name = ev.tool_call_name or "tool"
                    # If this ID was already used (completed and closed), assign a new unique ID
                    if tc_id in seen_tool_call_ids and tc_id not in open_tool_calls:
                        tc_id = f"{tc_id}_{uuid.uuid4().hex[:8]}"
                    if tc_id not in open_tool_calls:
                        _turn_tool_calls += 1
                        open_tool_calls[tc_id] = tc_name
                        seen_tool_call_ids.add(tc_id)
                    # Ensure the chunk has toolCallId, toolCallName, and parentMessageId
                    ev.tool_call_id = tc_id
                    ev.tool_call_name = tc_name
                    ev.parent_message_id = msg_id
                    yield encoder.encode(ev)
                    continue

                if isinstance(ev, ToolCallResultEvent):
                    yield encoder.encode(ev)
                    tc_id = ev.tool_call_id
                    if tc_id and tc_id in open_tool_calls:
                        del open_tool_calls[tc_id]
                    continue

                # --- Text message chunks ---
                # The AG-UI client chunk transformer auto-wraps these
                # with TEXT_MESSAGE_START/CONTENT/END — do NOT send manual lifecycle events
                if isinstance(ev, TextMessageChunkEvent):
                    _session_status[name] = "responding"
                    if _prev_activity != "responding":
                        _prev_activity = "responding"
                        _notify_status_change()
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

            _session_status[name] = "idle"
            _session_health[name] = "connected"
            _notify_status_change()

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
            _notify_status_change()

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
            _session_status[name] = "idle"
            _session_health[name] = "disconnected"
            _notify_status_change()
            if not isinstance(sess, LangGraphSession):
                asyncio.create_task(_auto_reconnect(name))
            yield encoder.encode(RunErrorEvent(message=f"{type(e).__name__}: {e}"))

    return StreamingResponse(event_gen(), media_type=encoder.get_content_type())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agui_server:app", host="0.0.0.0", port=8000, reload=False)
