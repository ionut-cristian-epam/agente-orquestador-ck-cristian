"""Tests for acp_to_agui.map_acp_event — ACP JSON-RPC → AG-UI event mapping."""
import json
import pytest

from ag_ui.core import (
    CustomEvent,
    ReasoningMessageChunkEvent,
    TextMessageChunkEvent,
    ToolCallChunkEvent,
    ToolCallResultEvent,
)

from acp_to_agui import map_acp_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _notification(session_update_kind: str, **update_fields) -> dict:
    """Build a minimal ACP session/update notification."""
    return {
        "jsonrpc": "2.0",
        "method": "session/update",
        "params": {
            "sessionId": "ses_test",
            "update": {"sessionUpdate": session_update_kind, **update_fields},
        },
    }


def _request(method: str, id: int = 0) -> dict:
    """Build a JSON-RPC request (has an id — should be filtered out)."""
    return {"jsonrpc": "2.0", "id": id, "method": method, "params": {}}


# ---------------------------------------------------------------------------
# Filtering — requests and unknown notifications are discarded
# ---------------------------------------------------------------------------

class TestFiltering:
    def test_request_with_id_is_ignored(self):
        rpc = _request("session/prompt", id=1)
        assert list(map_acp_event(rpc)) == []

    def test_non_session_update_notification_is_ignored(self):
        rpc = {"jsonrpc": "2.0", "method": "session/load", "params": {}}
        assert list(map_acp_event(rpc)) == []

    def test_empty_dict_is_ignored(self):
        assert list(map_acp_event({})) == []


# ---------------------------------------------------------------------------
# agent_message_chunk → TextMessageChunkEvent
# ---------------------------------------------------------------------------

class TestAgentMessageChunk:
    def test_string_content(self):
        rpc = _notification("agent_message_chunk", messageId="msg_1", content="Hello!")
        events = list(map_acp_event(rpc))
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, TextMessageChunkEvent)
        assert ev.delta == "Hello!"
        assert ev.message_id == "msg_1:text"

    def test_text_dict_content(self):
        rpc = _notification(
            "agent_message_chunk",
            messageId="msg_2",
            content={"type": "text", "text": "World"},
        )
        events = list(map_acp_event(rpc))
        assert len(events) == 1
        assert events[0].delta == "World"

    def test_list_content_concatenated(self):
        rpc = _notification(
            "agent_message_chunk",
            messageId="msg_3",
            content=[{"type": "text", "text": "foo"}, {"type": "text", "text": "bar"}],
        )
        events = list(map_acp_event(rpc))
        assert len(events) == 1
        assert events[0].delta == "foobar"

    def test_empty_content_yields_nothing(self):
        rpc = _notification("agent_message_chunk", messageId="msg_4", content="")
        assert list(map_acp_event(rpc)) == []

    def test_message_id_suffix_added(self):
        rpc = _notification("agent_message_chunk", messageId="abc", content="hi")
        ev = list(map_acp_event(rpc))[0]
        assert ev.message_id == "abc:text"

    def test_no_message_id_is_none(self):
        rpc = _notification("agent_message_chunk", content="hi")
        ev = list(map_acp_event(rpc))[0]
        assert ev.message_id is None


# ---------------------------------------------------------------------------
# agent_thought_chunk → ReasoningMessageChunkEvent
# ---------------------------------------------------------------------------

class TestAgentThoughtChunk:
    def test_produces_reasoning_chunk(self):
        rpc = _notification("agent_thought_chunk", messageId="msg_5", content="thinking...")
        events = list(map_acp_event(rpc))
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, ReasoningMessageChunkEvent)
        assert ev.delta == "thinking..."
        assert ev.message_id == "msg_5:think"

    def test_empty_thought_yields_nothing(self):
        rpc = _notification("agent_thought_chunk", messageId="msg_6", content="")
        assert list(map_acp_event(rpc)) == []


# ---------------------------------------------------------------------------
# tool_call → ToolCallChunkEvent
# ---------------------------------------------------------------------------

class TestToolCall:
    def test_basic_tool_call(self):
        rpc = _notification(
            "tool_call",
            toolCallId="tc_1",
            title="read_file",
            rawInput={"path": "/foo.py"},
        )
        events = list(map_acp_event(rpc))
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, ToolCallChunkEvent)
        assert ev.tool_call_id == "tc_1"
        assert ev.tool_call_name == "read_file"
        assert json.loads(ev.delta) == {"path": "/foo.py"}

    def test_tool_name_fallback_to_kind(self):
        # pass 'kind' inside the update dict directly to avoid keyword collision
        rpc = {
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": {
                "sessionId": "ses_test",
                "update": {"sessionUpdate": "tool_call", "id": "tc_2", "kind": "bash"},
            },
        }
        ev = list(map_acp_event(rpc))[0]
        assert ev.tool_call_name == "bash"

    def test_tool_name_fallback_to_default(self):
        rpc = _notification("tool_call", toolCallId="tc_3")
        ev = list(map_acp_event(rpc))[0]
        assert ev.tool_call_name == "tool"

    def test_no_input_gives_empty_delta(self):
        rpc = _notification("tool_call", toolCallId="tc_4", title="list_dir")
        ev = list(map_acp_event(rpc))[0]
        assert ev.delta is None


# ---------------------------------------------------------------------------
# tool_call_update → ToolCallResultEvent or CustomEvent
# ---------------------------------------------------------------------------

class TestToolCallUpdate:
    def test_completed_status_yields_result_event(self):
        rpc = _notification(
            "tool_call_update",
            toolCallId="tc_5",
            status="completed",
            content="file content here",
        )
        events = list(map_acp_event(rpc))
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, ToolCallResultEvent)
        assert ev.tool_call_id == "tc_5"
        assert ev.content == "file content here"

    def test_failed_status_yields_result_event(self):
        rpc = _notification(
            "tool_call_update",
            toolCallId="tc_6",
            status="failed",
            rawOutput="error message",
        )
        ev = list(map_acp_event(rpc))[0]
        assert isinstance(ev, ToolCallResultEvent)
        assert ev.content == "error message"

    def test_in_progress_status_yields_custom_event(self):
        rpc = _notification(
            "tool_call_update",
            toolCallId="tc_7",
            status="running",
        )
        ev = list(map_acp_event(rpc))[0]
        assert isinstance(ev, CustomEvent)
        assert ev.name == "acp.tool_call_update"

    def test_no_tool_call_id_yields_custom_event(self):
        rpc = _notification("tool_call_update", status="completed")
        ev = list(map_acp_event(rpc))[0]
        assert isinstance(ev, CustomEvent)


# ---------------------------------------------------------------------------
# Unknown sessionUpdate → CustomEvent
# ---------------------------------------------------------------------------

class TestUnknownUpdate:
    def test_unknown_kind_becomes_custom_event(self):
        rpc = _notification("usage_update", used=100, size=200000)
        events = list(map_acp_event(rpc))
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, CustomEvent)
        assert ev.name == "acp.usage_update"
        assert ev.value["used"] == 100

    def test_custom_event_preserves_all_fields(self):
        rpc = _notification("some_new_event", foo="bar", count=42)
        ev = list(map_acp_event(rpc))[0]
        assert ev.value["foo"] == "bar"
        assert ev.value["count"] == 42
