"""Session adapter for the in-process LangGraph harness.

Mirrors the public interface of `launch_sessions.Session` (constructor,
stream_prompt, read_history, close_session) but runs an in-process LangGraph
agent instead of a subprocess via acpx.

Key differences from acpx Session:
  - stream_prompt yields AG-UI BaseEvent objects directly, NOT ACP dicts
  - No subprocess; no acpx; no ACP protocol
  - Conversation history kept in memory (list of BaseMessage)
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import AsyncIterator, Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)

from ag_ui.core import BaseEvent

from langgraph_agent import build_sports_agent, stream_langgraph_events, SPORTS_TOOLS


def _load_skill_metadata(working_dir: str) -> dict:
    """Load skill metadata (name, description, system_prompt_file path, prompt text)
    from the workspace's langgraph_agent.json.
    """
    meta = {
        "skill_name": "default",
        "skill_path": None,
        "system_prompt": "You are a helpful assistant.",
    }
    config_path = Path(working_dir) / "langgraph_agent.json"
    if not config_path.exists():
        return meta
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return meta
    prompt_rel = config.get("system_prompt_file")
    if not prompt_rel:
        meta["system_prompt"] = config.get("default_system_prompt", meta["system_prompt"])
        return meta
    prompt_path = Path(working_dir) / prompt_rel
    meta["skill_path"] = prompt_rel
    if not prompt_path.exists():
        return meta
    text = prompt_path.read_text(encoding="utf-8")
    meta["system_prompt"] = text
    # Extract skill name from frontmatter or path
    import re
    m = re.match(r"^---\s*\n(.+?)\n---", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if line.startswith("name:"):
                meta["skill_name"] = line.split(":", 1)[1].strip().strip('"')
                break
    else:
        # Fallback: directory name (skills/{name}/SKILL.md) or file stem
        parent = prompt_path.parent
        meta["skill_name"] = parent.name if parent.name != "skills" else prompt_path.stem
    return meta


def _load_system_prompt(working_dir: str) -> str:
    """Backwards-compatible helper — returns just the system prompt string."""
    return _load_skill_metadata(working_dir)["system_prompt"]


class LangGraphSession:
    """In-process LangGraph agent session. Same interface as Session, no acpx.

    Graph construction is lazy — deferred until the first prompt — so that
    sessions can be re-attached (or deleted) without requiring an LLM API key.
    """

    agent_harness = "langgraph"
    available_tools: list[dict] = []

    def __init__(
        self,
        name: str,
        working_dir: str,
        LLM: Optional[str] = None,
        capture_output: bool = True,
    ):
        self.name = name
        self.working_dir = working_dir
        self.LLM = LLM or "openai/gpt-4o-mini"

        skill = _load_skill_metadata(working_dir)
        self._skill_name = skill["skill_name"]
        self._skill_path = skill["skill_path"]
        self._system_prompt = skill["system_prompt"]
        self._graph = None  # built lazily on first stream_prompt
        # Expose tool metadata for UI
        self.available_tools = [
            {"name": t.name, "description": t.description}
            for t in SPORTS_TOOLS
        ]
        # Persistent conversation history across turns
        self._messages: list[BaseMessage] = []
        # Serialize concurrent prompts to the same session
        self._lock = asyncio.Lock()

    def _ensure_graph(self) -> None:
        """Build the compiled graph on first use. Requires LLM API key."""
        if self._graph is None:
            self._graph = build_sports_agent(self.LLM, self._system_prompt)

    async def stream_prompt(self, prompt: str) -> AsyncIterator[BaseEvent]:
        """Run the graph for one user turn. Yields AG-UI events directly.

        Skill activation reasoning is centralized in agui_server.run_agent
        (works uniformly for both LangGraph and CLI harnesses).

        Captures the AIMessage/ToolMessage objects produced by the graph in a
        single invocation and appends them to self._messages in correct order
        (Human -> AI(tool_calls) -> ToolMessage -> AI(text)).
        """
        async with self._lock:
            self._ensure_graph()
            self._messages.append(HumanMessage(content=prompt))
            print(f"[langgraph][{self.name}] turn start — model={self.LLM!r} prompt={prompt!r}", flush=True)

            new_msgs: list = []
            try:
                async for ev in stream_langgraph_events(
                    self._graph,
                    list(self._messages),
                    message_collector=new_msgs,
                ):
                    yield ev
                self._messages.extend(new_msgs)
                print(f"[langgraph][{self.name}] turn complete — appended {len(new_msgs)} messages", flush=True)
            except Exception as e:
                print(f"[langgraph][{self.name}] ERROR: {type(e).__name__}: {e}", flush=True)
                raise

    def read_history(self, tail: Optional[int] = None) -> list[dict]:
        """Return conversation history in the {role, content, thinking?} dict format."""
        result = []
        for msg in self._messages:
            if isinstance(msg, HumanMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                result.append({"role": "user", "content": content})
            elif isinstance(msg, AIMessage):
                content = msg.content if isinstance(msg.content, str) else _flatten_blocks(msg.content)
                if content or msg.tool_calls:
                    result.append({"role": "assistant", "content": content})
        if tail is not None and tail > 0:
            result = result[-tail:]
        return result

    def restore_history(self, entries: list[dict]) -> None:
        """Rehydrate self._messages from saved history entries."""
        for entry in entries:
            role = entry.get("role")
            content = entry.get("content", "")
            if role == "user":
                self._messages.append(HumanMessage(content=content))
            elif role == "assistant":
                self._messages.append(AIMessage(content=content))

    def close_session(self) -> None:
        """Cleanup in-memory state. No subprocess to kill."""
        self._messages.clear()

    def _ensure_connected(self) -> None:
        """No-op for in-process agent. Always 'connected'."""
        return


def _safe_json_loads(s: str):
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return {}


def _flatten_blocks(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    parts.append(b.get("text", ""))
            elif isinstance(b, str):
                parts.append(b)
        return "".join(parts)
    return str(content)
