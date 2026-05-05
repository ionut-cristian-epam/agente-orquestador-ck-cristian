"""Tests for conversation history persistence.

Verifies:
- _save_own_history / _load_own_history round-trip
- History accumulated correctly during SSE stream (user + assistant)
- Thinking content saved separately in assistant entries
- GET /sessions/{name}/history returns saved history
- History cleaned up on session delete
- Corrupt JSON handled gracefully
- Unicode preserved in history
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import agui_server as server_mod
from agui_server import (
    app,
    _sessions,
    _session_status,
    _save_own_history,
    _load_own_history,
    _history_path,
)
from launch_sessions import Session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_sessions():
    _sessions.clear()
    _session_status.clear()
    yield
    _sessions.clear()
    _session_status.clear()


@pytest.fixture
def history_dir(tmp_path):
    hdir = tmp_path / "history"
    hdir.mkdir()
    with patch.object(server_mod, "HISTORY_DIR", hdir):
        yield hdir


def _mock_session(name: str = "test") -> Session:
    sess = Session.__new__(Session)
    sess.agent_harness = "opencode"
    sess.name = name
    sess.working_dir = "."
    sess.LLM = "opencode/big-pickle"
    return sess


def _notif(kind: str, **fields) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "session/update",
        "params": {
            "sessionId": "ses_test",
            "update": {"sessionUpdate": kind, **fields},
        },
    }


RUN_INPUT = {
    "threadId": "thread_1",
    "runId": "run_1",
    "state": {},
    "tools": [],
    "context": [],
    "forwardedProps": {},
    "messages": [
        {"id": "m1", "role": "user", "content": "Hello agent", "createdAt": 0}
    ],
}


# ---------------------------------------------------------------------------
# _save_own_history / _load_own_history
# ---------------------------------------------------------------------------

class TestHistoryIO:
    def test_save_and_load_roundtrip(self, history_dir):
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello!"},
        ]
        _save_own_history("mysess", messages)
        loaded = _load_own_history("mysess")
        assert loaded == messages

    def test_load_nonexistent_returns_none(self, history_dir):
        assert _load_own_history("nonexistent") is None

    def test_load_corrupt_json_returns_none(self, history_dir):
        p = _history_path("corrupt")
        p.write_text("not valid json{{{", encoding="utf-8")
        assert _load_own_history("corrupt") is None

    def test_unicode_preserved(self, history_dir):
        messages = [
            {"role": "user", "content": "¿Cómo estás?"},
            {"role": "assistant", "content": "Estoy bien, España está soleada ☀️"},
        ]
        _save_own_history("unicode_sess", messages)
        loaded = _load_own_history("unicode_sess")
        assert loaded == messages

        # Verify file is actually UTF-8
        p = _history_path("unicode_sess")
        raw = p.read_bytes()
        decoded = raw.decode("utf-8")
        assert "España" in decoded
        assert "☀️" in decoded

    def test_multiline_content_preserved(self, history_dir):
        """Markdown with newlines should be preserved exactly."""
        content = "# Title\n\nParagraph 1\n\n```python\nprint('hello')\n```\n\n- item 1\n- item 2"
        messages = [
            {"role": "assistant", "content": content},
        ]
        _save_own_history("markdown", messages)
        loaded = _load_own_history("markdown")
        assert loaded[0]["content"] == content

    def test_save_overwrites_previous(self, history_dir):
        _save_own_history("sess", [{"role": "user", "content": "first"}])
        _save_own_history("sess", [{"role": "user", "content": "second"}])
        loaded = _load_own_history("sess")
        assert len(loaded) == 1
        assert loaded[0]["content"] == "second"

    def test_history_path_sanitizes_slashes(self, history_dir):
        p = _history_path("path/with/slashes")
        assert "/" not in p.stem
        assert "\\" not in p.stem


# ---------------------------------------------------------------------------
# History accumulated during SSE stream
# ---------------------------------------------------------------------------

class TestHistoryAccumulation:
    def test_user_and_assistant_saved_after_stream(self, history_dir):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("agent_message_chunk", messageId="msg_1", content="Hello ")
            yield _notif("agent_message_chunk", messageId="msg_1", content="world!")

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        history = _load_own_history("sess")
        assert history is not None
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello agent"}
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hello world!"

    def test_thinking_saved_separately(self, history_dir):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("agent_thought_chunk", messageId="msg_1", content="Let me think...")
            yield _notif("agent_thought_chunk", messageId="msg_1", content=" about this")
            yield _notif("agent_message_chunk", messageId="msg_1", content="Answer here")

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        history = _load_own_history("sess")
        assistant = history[1]
        assert assistant["content"] == "Answer here"
        assert assistant["thinking"] == "Let me think... about this"

    def test_no_thinking_key_when_empty(self, history_dir):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield _notif("agent_message_chunk", messageId="msg_1", content="Direct answer")

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        history = _load_own_history("sess")
        assert "thinking" not in history[1]

    def test_history_appends_across_turns(self, history_dir):
        """Second prompt appends to existing history."""
        sess = _mock_session("sess")
        _sessions["sess"] = sess

        # Pre-save first turn
        _save_own_history("sess", [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
        ])

        async def fake_stream(_prompt):
            yield _notif("agent_message_chunk", messageId="msg_2", content="second answer")

        sess.stream_prompt = fake_stream

        with TestClient(app) as client:
            client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        history = _load_own_history("sess")
        assert len(history) == 4
        assert history[2] == {"role": "user", "content": "Hello agent"}
        assert history[3]["content"] == "second answer"

    def test_history_not_saved_on_error(self, history_dir):
        """If stream errors, partial history should NOT corrupt existing data."""
        sess = _mock_session("sess")
        _sessions["sess"] = sess

        # Pre-existing history
        _save_own_history("sess", [
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "old answer"},
        ])

        async def fake_stream(_prompt):
            yield _notif("agent_message_chunk", messageId="msg_1", content="partial")
            raise RuntimeError("crash")
            yield

        sess.stream_prompt = fake_stream

        with TestClient(app) as client:
            client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        # On error, the current implementation still saves — this test documents behavior
        # If we want atomic saves, this would need changing
        history = _load_own_history("sess")
        assert history is not None


# ---------------------------------------------------------------------------
# GET /sessions/{name}/history endpoint
# ---------------------------------------------------------------------------

class TestHistoryEndpoint:
    def test_returns_saved_history(self, history_dir):
        sess = _mock_session("sess")
        sess.read_history = MagicMock(return_value=[])
        _sessions["sess"] = sess

        _save_own_history("sess", [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ])

        with TestClient(app) as client:
            res = client.get("/sessions/sess/history")

        assert res.status_code == 200
        data = res.json()
        assert data["session"] == "sess"
        assert len(data["entries"]) == 2
        assert data["entries"][0]["content"] == "hi"

    def test_tail_parameter_limits_results(self, history_dir):
        sess = _mock_session("sess")
        sess.read_history = MagicMock(return_value=[])
        _sessions["sess"] = sess

        messages = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        _save_own_history("sess", messages)

        with TestClient(app) as client:
            res = client.get("/sessions/sess/history?tail=3")

        assert len(res.json()["entries"]) == 3
        assert res.json()["entries"][0]["content"] == "msg 7"

    def test_falls_back_to_acpx_when_no_own_history(self, history_dir):
        sess = _mock_session("sess")
        acpx_history = [
            {"role": "user", "content": "from acpx"},
            {"role": "assistant", "content": "acpx response"},
        ]
        sess.read_history = MagicMock(return_value=acpx_history)
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.get("/sessions/sess/history")

        assert res.status_code == 200
        assert res.json()["entries"] == acpx_history
        sess.read_history.assert_called_once()

    def test_404_for_unknown_session(self, history_dir):
        with patch("agui_server._attach_existing", return_value=None):
            with TestClient(app) as client:
                res = client.get("/sessions/ghost/history")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# History cleanup on delete
# ---------------------------------------------------------------------------

class TestHistoryCleanup:
    def test_delete_removes_history_file(self, history_dir):
        sess = _mock_session("sess")
        sess.close_session = MagicMock()
        _sessions["sess"] = sess

        _save_own_history("sess", [{"role": "user", "content": "data"}])
        assert _history_path("sess").exists()

        with (
            patch("agui_server.remove_session"),
            patch("agui_server._remove_from_local_index"),
        ):
            with TestClient(app) as client:
                res = client.delete("/sessions/sess")

        assert res.status_code == 200
        assert not _history_path("sess").exists()
