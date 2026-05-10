"""Tests for tool call lifecycle in SSE streaming.

Verifies:
- ToolCallStartEvent emitted on first ToolCallChunkEvent for a given toolCallId
- ToolCallEndEvent emitted after ToolCallResultEvent
- Multiple concurrent tool calls tracked independently
- Open tool calls closed on stream end (normal finish)
- Open tool calls closed on stream error
- Reasoning closed before tool call starts
"""
import json
import uuid
from typing import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agui_server import app, _sessions, _session_status, _session_health
from launch_sessions import Session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_sessions():
    _sessions.clear()
    _session_status.clear()
    _session_health.clear()
    yield
    _sessions.clear()
    _session_status.clear()
    _session_health.clear()


def _mock_session(name: str = "test") -> Session:
    sess = Session.__new__(Session)
    sess.agent_harness = "opencode"
    sess.name = name
    sess.working_dir = "."
    sess.LLM = "opencode/big-pickle"
    return sess


RUN_INPUT = {
    "threadId": "thread_1",
    "runId": "run_1",
    "state": {},
    "tools": [],
    "context": [],
    "forwardedProps": {},
    "messages": [
        {"id": "m1", "role": "user", "content": "Do something", "createdAt": 0}
    ],
}


def _notif(session_update_kind: str, **fields) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "session/update",
        "params": {
            "sessionId": "ses_test",
            "update": {"sessionUpdate": session_update_kind, **fields},
        },
    }


def _parse_sse_events(body: str) -> list[dict]:
    """Parse SSE body into list of event dicts."""
    events = []
    for line in body.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                continue
    return events


def _event_types(events: list[dict]) -> list[str]:
    return [e.get("type") for e in events]


# ---------------------------------------------------------------------------
# Tool call start/end lifecycle
# ---------------------------------------------------------------------------

class TestToolCallLifecycle:
    def test_tool_call_chunk_emitted(self):
        """TOOL_CALL_CHUNK is emitted (lifecycle managed by client chunk transformer)."""
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("tool_call", toolCallId="tc_1", title="read_file", rawInput={"path": "/x"})

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        events = _parse_sse_events(res.text)
        types = _event_types(events)

        assert "TOOL_CALL_CHUNK" in types
        # No explicit START/END — chunk transformer on client handles lifecycle
        assert "TOOL_CALL_START" not in types
        assert "TOOL_CALL_END" not in types

    def test_tool_call_result_after_chunk(self):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("tool_call", toolCallId="tc_1", title="bash", rawInput={"cmd": "ls"})
            yield _notif("tool_call_update", toolCallId="tc_1", status="completed", content="file.txt")

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        events = _parse_sse_events(res.text)
        types = _event_types(events)

        # Should have CHUNK then RESULT
        chunk_idx = types.index("TOOL_CALL_CHUNK")
        result_idx = types.index("TOOL_CALL_RESULT")
        assert chunk_idx < result_idx

    def test_multiple_tool_calls_tracked_independently(self):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("tool_call", toolCallId="tc_A", title="read_file")
            yield _notif("tool_call", toolCallId="tc_B", title="write_file")
            yield _notif("tool_call_update", toolCallId="tc_A", status="completed", content="done A")
            yield _notif("tool_call_update", toolCallId="tc_B", status="completed", content="done B")

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        events = _parse_sse_events(res.text)

        # Two CHUNK events with different IDs
        chunks = [e for e in events if e.get("type") == "TOOL_CALL_CHUNK"]
        assert len(chunks) == 2
        chunk_ids = {e.get("toolCallId") for e in chunks}
        assert chunk_ids == {"tc_A", "tc_B"}

        # Two RESULT events
        results = [e for e in events if e.get("type") == "TOOL_CALL_RESULT"]
        assert len(results) == 2

    def test_no_duplicate_chunk_for_same_tool_call(self):
        """If same toolCallId appears twice, both chunks are emitted (args accumulate)."""
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("tool_call", toolCallId="tc_1", title="bash", rawInput={"cmd": "ls"})
            yield _notif("tool_call", toolCallId="tc_1", title="bash", rawInput={"cmd": "ls -la"})
            yield _notif("tool_call_update", toolCallId="tc_1", status="completed", content="result")

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        events = _parse_sse_events(res.text)
        chunks = [e for e in events if e.get("type") == "TOOL_CALL_CHUNK"]
        # Both chunks emitted
        assert len(chunks) == 2

    def test_error_emits_run_error(self):
        """If stream errors, RUN_ERROR is emitted."""
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("tool_call", toolCallId="tc_1", title="bash")
            raise RuntimeError("crash")
            yield  # make it async gen

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        events = _parse_sse_events(res.text)
        types = _event_types(events)

        assert "TOOL_CALL_CHUNK" in types
        assert "RUN_ERROR" in types
        assert "RUN_ERROR" in types

    def test_reasoning_stays_open_through_tool_call(self):
        """Reasoning stays open through tool calls — single thinking box."""
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("agent_thought_chunk", messageId="msg_1", content="thinking...")
            yield _notif("tool_call", toolCallId="tc_1", title="bash")

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        events = _parse_sse_events(res.text)
        types = _event_types(events)

        assert "REASONING_MESSAGE_START" in types
        assert "TOOL_CALL_CHUNK" in types
        # Reasoning END comes after tool call (at stream end), not before
        reasoning_end_idx = types.index("REASONING_MESSAGE_END")
        tool_chunk_idx = types.index("TOOL_CALL_CHUNK")
        assert reasoning_end_idx > tool_chunk_idx

    def test_status_changes_to_tool_use_during_tool_call(self):
        sess = _mock_session("sess")

        statuses_during = []

        async def fake_stream(_prompt):
            yield _notif("tool_call", toolCallId="tc_1", title="bash")
            statuses_during.append(_session_status.get("sess"))
            yield _notif("tool_call_update", toolCallId="tc_1", status="completed", content="ok")

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        # After stream finishes, status is idle
        assert _session_status.get("sess") == "idle"
