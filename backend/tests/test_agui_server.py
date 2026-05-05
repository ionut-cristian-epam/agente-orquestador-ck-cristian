"""Tests for agui_server FastAPI endpoints.

Mocks acpx (Session) so no external processes are needed.
"""
import json
from typing import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

import agui_server
from agui_server import app, _sessions, _session_status, _session_health
from launch_sessions import Session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_sessions():
    """Reset server-side session registry between tests."""
    _sessions.clear()
    _session_status.clear()
    _session_health.clear()
    yield
    _sessions.clear()
    _session_status.clear()
    _session_health.clear()


def _mock_session(name: str = "test", harness: str = "opencode") -> Session:
    sess = Session.__new__(Session)
    sess.agent_harness = harness
    sess.name = name
    sess.working_dir = "."
    sess.LLM = "opencode/big-pickle"
    return sess


# ---------------------------------------------------------------------------
# GET /sessions
# ---------------------------------------------------------------------------

class TestListSessions:
    def test_empty_returns_structure(self):
        with patch("agui_server._load_acpx_index", return_value={"entries": []}):
            with TestClient(app) as client:
                res = client.get("/sessions")
        assert res.status_code == 200
        data = res.json()
        assert "registered" in data
        assert "acpx" in data
        assert "projectRoot" in data

    def test_registered_sessions_appear(self):
        _sessions["my_agent"] = _mock_session("my_agent")
        with patch("agui_server._load_acpx_index", return_value={"entries": []}):
            with TestClient(app) as client:
                res = client.get("/sessions")
        assert "my_agent" in res.json()["registered"]


# ---------------------------------------------------------------------------
# POST /sessions
# ---------------------------------------------------------------------------

class TestCreateSession:
    def test_creates_new_session(self, tmp_path):
        with patch("agui_server.Session") as MockSession:
            MockSession.return_value = _mock_session("new_sess")
            with TestClient(app) as client:
                res = client.post("/sessions", json={
                    "name": "new_sess",
                    "agent_harness": "opencode",
                    "working_dir": str(tmp_path),
                    "LLM": "opencode/big-pickle",
                })
        assert res.status_code == 200
        assert res.json()["status"] == "created"
        assert res.json()["name"] == "new_sess"

    def test_duplicate_session_returns_exists(self, tmp_path):
        _sessions["existing"] = _mock_session("existing")
        with TestClient(app) as client:
            res = client.post("/sessions", json={
                "name": "existing",
                "agent_harness": "opencode",
                "working_dir": str(tmp_path),
            })
        assert res.status_code == 200
        assert res.json()["status"] == "exists"


# ---------------------------------------------------------------------------
# DELETE /sessions/{name}
# ---------------------------------------------------------------------------

class TestDeleteSession:
    def test_closes_registered_session(self):
        sess = _mock_session("to_delete")
        sess.close_session = MagicMock()
        _sessions["to_delete"] = sess

        with TestClient(app) as client:
            res = client.delete("/sessions/to_delete")

        assert res.status_code == 200
        assert res.json()["status"] == "deleted"
        sess.close_session.assert_called_once()
        assert "to_delete" not in _sessions

    def test_delete_unknown_session_returns_404(self):
        with patch("agui_server._attach_existing", return_value=None):
            with TestClient(app) as client:
                res = client.delete("/sessions/nonexistent")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# POST /agent/{name} — SSE streaming
# ---------------------------------------------------------------------------

ACP_THOUGHT = {
    "jsonrpc": "2.0",
    "method": "session/update",
    "params": {
        "sessionId": "ses_test",
        "update": {
            "sessionUpdate": "agent_thought_chunk",
            "messageId": "msg_1",
            "content": "Thinking...",
        },
    },
}

ACP_MESSAGE = {
    "jsonrpc": "2.0",
    "method": "session/update",
    "params": {
        "sessionId": "ses_test",
        "update": {
            "sessionUpdate": "agent_message_chunk",
            "messageId": "msg_1",
            "content": "Hello!",
        },
    },
}

ACP_REQUEST = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "session/prompt",
    "params": {},
}


async def _fake_stream(*events) -> AsyncIterator[dict]:
    for e in events:
        yield e


RUN_INPUT = {
    "threadId": "thread_1",
    "runId": "run_1",
    "state": {},
    "tools": [],
    "context": [],
    "forwardedProps": {},
    "messages": [
        {"id": "m1", "role": "user", "content": "Hola", "createdAt": 0}
    ],
}


class TestRunAgent:
    def test_unknown_session_returns_404(self):
        with patch("agui_server._attach_existing", return_value=None):
            with TestClient(app) as client:
                res = client.post("/agent/ghost", json=RUN_INPUT)
        assert res.status_code == 404

    def test_empty_prompt_returns_400(self):
        _sessions["sess"] = _mock_session("sess")
        no_user_msg = {
            "threadId": "t1",
            "runId": "r1",
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
            "messages": [{"id": "m1", "role": "assistant", "content": "hi", "createdAt": 0}],
        }
        with TestClient(app) as client:
            res = client.post("/agent/sess", json=no_user_msg)
        assert res.status_code == 400

    def test_stream_contains_run_started_and_finished(self):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield ACP_REQUEST  # should be filtered
            yield ACP_MESSAGE

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post(
                "/agent/sess",
                json=RUN_INPUT,
                headers={"accept": "text/event-stream"},
            )

        assert res.status_code == 200
        body = res.text
        assert "RUN_STARTED" in body
        assert "RUN_FINISHED" in body

    def test_stream_contains_text_message_chunk(self):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield ACP_MESSAGE

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post(
                "/agent/sess",
                json=RUN_INPUT,
                headers={"accept": "text/event-stream"},
            )

        assert "TEXT_MESSAGE_CHUNK" in res.text

    def test_stream_contains_reasoning_events(self):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield ACP_THOUGHT
            yield ACP_MESSAGE

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post(
                "/agent/sess",
                json=RUN_INPUT,
                headers={"accept": "text/event-stream"},
            )

        body = res.text
        assert "REASONING_MESSAGE_START" in body
        assert "REASONING_MESSAGE_CONTENT" in body
        assert "REASONING_MESSAGE_END" in body

    def test_stream_error_yields_run_error_event(self):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            raise RuntimeError("acpx crashed")
            yield  # make it a generator

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            res = client.post(
                "/agent/sess",
                json=RUN_INPUT,
                headers={"accept": "text/event-stream"},
            )

        assert "RUN_ERROR" in res.text


# ---------------------------------------------------------------------------
# GET /sessions/status
# ---------------------------------------------------------------------------

class TestSessionStatus:
    def test_empty_when_no_sessions(self):
        with TestClient(app) as client:
            res = client.get("/sessions/status")
        assert res.status_code == 200
        assert res.json() == {}

    def test_returns_idle_for_new_session(self):
        _sessions["s1"] = _mock_session("s1")
        with TestClient(app) as client:
            res = client.get("/sessions/status")
        assert res.json() == {"s1": {"activity": "idle", "health": "connected"}}

    def test_returns_explicit_status(self):
        _sessions["s1"] = _mock_session("s1")
        _session_status["s1"] = "thinking"
        with TestClient(app) as client:
            res = client.get("/sessions/status")
        assert res.json() == {"s1": {"activity": "thinking", "health": "connected"}}

    def test_stream_sets_idle_on_finish(self):
        sess = _mock_session("sess")

        async def fake_stream(_prompt):
            yield ACP_MESSAGE

        sess.stream_prompt = fake_stream
        _sessions["sess"] = sess

        with TestClient(app) as client:
            client.post(
                "/agent/sess",
                json=RUN_INPUT,
                headers={"accept": "text/event-stream"},
            )
            # After stream completes, status should be idle
            assert _session_status.get("sess") == "idle"

    def test_delete_clears_status(self):
        sess = _mock_session("s1")
        sess.close_session = MagicMock()
        _sessions["s1"] = sess
        _session_status["s1"] = "responding"

        with TestClient(app) as client:
            client.delete("/sessions/s1")
        assert "s1" not in _session_status
        assert "s1" not in _session_health


# ---------------------------------------------------------------------------
# POST /sessions/{name}/reconnect
# ---------------------------------------------------------------------------

class TestReconnectSession:
    def test_reconnect_success(self):
        sess = _mock_session("s1")
        sess._ensure_connected = MagicMock()
        _sessions["s1"] = sess
        _session_health["s1"] = "disconnected"

        with TestClient(app) as client:
            res = client.post("/sessions/s1/reconnect")

        assert res.status_code == 200
        assert res.json()["status"] == "reconnected"
        assert _session_health["s1"] == "connected"
        sess._ensure_connected.assert_called_once()

    def test_reconnect_failure_stays_disconnected(self):
        sess = _mock_session("s1")
        sess._ensure_connected = MagicMock(side_effect=RuntimeError("acpx dead"))
        _sessions["s1"] = sess
        _session_health["s1"] = "disconnected"

        with TestClient(app) as client:
            res = client.post("/sessions/s1/reconnect")

        assert res.status_code == 500
        assert _session_health["s1"] == "disconnected"

    def test_reconnect_unknown_session_404(self):
        from unittest.mock import patch
        with patch("agui_server._attach_existing", return_value=None):
            with TestClient(app) as client:
                res = client.post("/sessions/ghost/reconnect")
        assert res.status_code == 404

    def test_health_set_connected_after_successful_stream(self):
        sess = _mock_session("sess")
        _sessions["sess"] = sess
        _session_health["sess"] = "disconnected"

        async def fake_stream(_prompt):
            yield ACP_MESSAGE

        sess.stream_prompt = fake_stream

        with TestClient(app) as client:
            client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        assert _session_health["sess"] == "connected"

    def test_health_set_disconnected_after_stream_error(self):
        sess = _mock_session("sess")
        _sessions["sess"] = sess
        _session_health["sess"] = "connected"

        async def fake_stream(_prompt):
            raise RuntimeError("crash")
            yield

        sess.stream_prompt = fake_stream

        with TestClient(app) as client:
            client.post("/agent/sess", json=RUN_INPUT, headers={"accept": "text/event-stream"})

        assert _session_health["sess"] == "disconnected"


# ---------------------------------------------------------------------------
# GET /models/{harness}
# ---------------------------------------------------------------------------

class TestGetModels:
    def test_opencode_returns_grouped_models(self):
        with TestClient(app) as client:
            res = client.get("/models/opencode")
        assert res.status_code == 200
        data = res.json()
        assert "groups" in data
        assert "default" in data
        assert len(data["groups"]) > 0
        assert data["default"] != ""

    def test_copilot_returns_models(self):
        with TestClient(app) as client:
            res = client.get("/models/copilot")
        assert res.status_code == 200
        data = res.json()
        assert "Copilot CLI" in data["groups"]
        assert len(data["groups"]["Copilot CLI"]) > 0

    def test_unknown_harness_returns_empty(self):
        with TestClient(app) as client:
            res = client.get("/models/claude")
        assert res.status_code == 200
        data = res.json()
        assert data["groups"] == {}
        assert data["default"] == ""
