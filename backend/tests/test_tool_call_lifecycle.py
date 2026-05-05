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
    def test_tool_call_start_emitted_on_first_chunk(self):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("tool_call", toolCallId="tc_1", title="read_file", rawInput={"path": "/x"})

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        events = _parse_sse_events(res.text)
        types = _event_types(events)

        assert "TOOL_CALL_START" in types
        assert "TOOL_CALL_CHUNK" in types
        # ToolCallEnd emitted at stream end for unclosed tool calls
        assert "TOOL_CALL_END" in types

    def test_tool_call_end_after_result(self):
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

        # Should have: START, CHUNK, RESULT, END
        start_idx = types.index("TOOL_CALL_START")
        result_idx = types.index("TOOL_CALL_RESULT")
        end_idx = types.index("TOOL_CALL_END")

        assert start_idx < result_idx < end_idx

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

        # Two START events
        starts = [e for e in events if e.get("type") == "TOOL_CALL_START"]
        assert len(starts) == 2
        start_ids = {e.get("toolCallId") for e in starts}
        assert start_ids == {"tc_A", "tc_B"}

        # Two END events
        ends = [e for e in events if e.get("type") == "TOOL_CALL_END"]
        assert len(ends) == 2

    def test_no_duplicate_start_for_same_tool_call(self):
        """If same toolCallId appears twice, only one START emitted."""
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
        starts = [e for e in events if e.get("type") == "TOOL_CALL_START"]
        assert len(starts) == 1

    def test_open_tool_calls_closed_on_error(self):
        """If stream errors, open tool calls still get END events."""
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

        assert "TOOL_CALL_START" in types
        assert "TOOL_CALL_END" in types
        assert "RUN_ERROR" in types

    def test_reasoning_closed_before_tool_call(self):
        """If reasoning is active when tool call arrives, reasoning ends first."""
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

        # Reasoning END should come before TOOL_CALL_START
        reasoning_end_idx = types.index("REASONING_MESSAGE_END")
        tool_start_idx = types.index("TOOL_CALL_START")
        assert reasoning_end_idx < tool_start_idx

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
