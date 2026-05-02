"""Map ACP JSON-RPC notifications (from acpx --format json) to AG-UI events.

Only `session/update` notifications are mapped. Initialize / session/new /
session/load / prompt request and response messages are filtered out by
the caller (they have an `id` field; notifications do not).
"""
import json
from typing import Iterator

from ag_ui.core import (
    BaseEvent,
    CustomEvent,
    ReasoningMessageChunkEvent,
    TextMessageChunkEvent,
    ToolCallChunkEvent,
    ToolCallResultEvent,
)


def _is_notification(rpc: dict) -> bool:
    return rpc.get("method") is not None and "id" not in rpc


def _session_update(rpc: dict) -> dict | None:
    if rpc.get("method") != "session/update":
        return None
    return (rpc.get("params") or {}).get("update")


def _content_text(content) -> str:
    if isinstance(content, dict):
        if content.get("type") == "text":
            return content.get("text") or ""
        return content.get("text") or ""
    if isinstance(content, list):
        return "".join(_content_text(c) for c in content)
    if isinstance(content, str):
        return content
    return ""


def map_acp_event(rpc: dict) -> Iterator[BaseEvent]:
    """Translate one parsed ACP JSON-RPC line into zero or more AG-UI events."""
    if not _is_notification(rpc):
        return
    update = _session_update(rpc)
    if update is None:
        return

    kind = update.get("sessionUpdate")

    if kind == "agent_message_chunk":
        delta = _content_text(update.get("content"))
        if delta:
            base_id = update.get("messageId")
            yield TextMessageChunkEvent(
                messageId=f"{base_id}:text" if base_id else None,
                role="assistant",
                delta=delta,
            )
        return

    if kind == "agent_thought_chunk":
        delta = _content_text(update.get("content"))
        if delta:
            base_id = update.get("messageId")
            yield ReasoningMessageChunkEvent(
                messageId=f"{base_id}:think" if base_id else None,
                delta=delta,
            )
        return

    if kind == "tool_call":
        tool_call_id = update.get("toolCallId") or update.get("id")
        tool_name = update.get("title") or update.get("kind") or "tool"
        raw_input = update.get("rawInput") or update.get("input")
        delta = json.dumps(raw_input) if raw_input is not None else ""
        yield ToolCallChunkEvent(
            toolCallId=tool_call_id,
            toolCallName=tool_name,
            delta=delta or None,
        )
        return

    if kind == "tool_call_update":
        tool_call_id = update.get("toolCallId") or update.get("id")
        status = update.get("status")
        content = update.get("content") or update.get("rawOutput")
        if status in ("completed", "failed") and tool_call_id:
            yield ToolCallResultEvent(
                messageId=update.get("messageId") or tool_call_id,
                toolCallId=tool_call_id,
                content=_content_text(content) or json.dumps(content) if content else "",
                role="tool",
            )
        else:
            yield CustomEvent(name="acp.tool_call_update", value=update)
        return

    yield CustomEvent(name=f"acp.{kind}", value=update)
