"""Integration tests: LangGraph harness end-to-end through agui_server endpoints."""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import agui_server
from agui_server import (
    app,
    _sessions,
    _session_status,
    _session_health,
    _session_metrics,
)
from langgraph_session import LangGraphSession


@pytest.fixture(autouse=True)
def clear_state():
    _sessions.clear()
    _session_status.clear()
    _session_health.clear()
    _session_metrics.clear()
    yield
    _sessions.clear()
    _session_status.clear()
    _session_health.clear()
    _session_metrics.clear()


def _mock_langgraph_session(name: str = "sports", working_dir: str = ".") -> LangGraphSession:
    sess = LangGraphSession.__new__(LangGraphSession)
    sess.name = name
    sess.working_dir = working_dir
    sess.LLM = "openai/gpt-4o-mini"
    sess._system_prompt = "be helpful"
    sess._graph = MagicMock()
    sess._messages = []
    import asyncio
    sess._lock = asyncio.Lock()
    return sess


# ---------------------------------------------------------------------------
# /models/langgraph
# ---------------------------------------------------------------------------

class TestModelsEndpoint:
    def test_langgraph_models_grouped_by_provider(self):
        with TestClient(app) as client:
            res = client.get("/models/langgraph")
        assert res.status_code == 200
        data = res.json()
        assert "groups" in data
        assert "OpenAI" in data["groups"]
        assert "Anthropic" in data["groups"]
        assert "Google" in data["groups"]
        # Default should be the first OpenAI model
        assert data["default"].startswith("openai/")


# ---------------------------------------------------------------------------
# /workspaces (sports workspace discovered)
# ---------------------------------------------------------------------------

class TestWorkspacesEndpoint:
    def test_sports_workspace_detected_with_langgraph_harness(self, tmp_path):
        agents_dir = tmp_path / "agents"
        sports_dir = agents_dir / "sports"
        sports_dir.mkdir(parents=True)
        (sports_dir / "langgraph_agent.json").write_text(
            json.dumps({"description": "sports test", "type": "langgraph"}),
            encoding="utf-8",
        )
        with patch.object(agui_server, "AGENTS_DIR", agents_dir):
            with TestClient(app) as client:
                res = client.get("/workspaces")
        assert res.status_code == 200
        data = res.json()
        sports = next((w for w in data if w["name"] == "sports"), None)
        assert sports is not None
        assert sports["harness"] == "langgraph"
        assert sports["description"] == "sports test"


# ---------------------------------------------------------------------------
# POST /sessions with langgraph harness
# ---------------------------------------------------------------------------

class TestCreateLangGraphSession:
    def test_creates_langgraph_session(self, tmp_path):
        with patch.object(agui_server, "LangGraphSession") as MockLG:
            MockLG.return_value = _mock_langgraph_session("sport_chat")
            with TestClient(app) as client:
                res = client.post("/sessions", json={
                    "name": "sport_chat",
                    "agent_harness": "langgraph",
                    "working_dir": str(tmp_path),
                    "LLM": "openai/gpt-4o-mini",
                })
        assert res.status_code == 200
        assert res.json()["status"] == "created"
        # Did NOT create acpx Session
        MockLG.assert_called_once()


# ---------------------------------------------------------------------------
# POST /agent/{name} streams AG-UI events from LangGraphSession
# ---------------------------------------------------------------------------

class TestWorkspaceSkillInfo:
    def test_langgraph_workspace_detected(self, tmp_path):
        from agui_server import _get_workspace_skill_info
        (tmp_path / "langgraph_agent.json").write_text(
            '{"system_prompt_file": "skills/sports/SKILL.md"}', encoding="utf-8"
        )
        skills = tmp_path / "skills" / "sports"
        skills.mkdir(parents=True)
        (skills / "SKILL.md").write_text(
            "---\nname: sports-expert\n---\nbody content here", encoding="utf-8"
        )
        info = _get_workspace_skill_info(str(tmp_path), "langgraph")
        assert info is not None
        assert info["skill_name"] == "sports-expert"
        assert info["skill_path"] == "skills/sports/SKILL.md"
        assert info["prompt_chars"] > 0

    def test_opencode_workspace_detected(self, tmp_path):
        from agui_server import _get_workspace_skill_info
        (tmp_path / "opencode.json").write_text(
            '{"instructions": [".opencode/skills/debug/SKILL.md"]}', encoding="utf-8"
        )
        skills = tmp_path / ".opencode" / "skills" / "debug"
        skills.mkdir(parents=True)
        (skills / "SKILL.md").write_text(
            "---\nname: systematic-debugging\n---\nbody", encoding="utf-8"
        )
        info = _get_workspace_skill_info(str(tmp_path), "opencode")
        assert info is not None
        assert info["skill_name"] == "systematic-debugging"

    def test_no_config_returns_none(self, tmp_path):
        from agui_server import _get_workspace_skill_info
        info = _get_workspace_skill_info(str(tmp_path), "opencode")
        assert info is None

    def test_missing_working_dir_returns_none(self):
        from agui_server import _get_workspace_skill_info
        assert _get_workspace_skill_info(None, "langgraph") is None
        assert _get_workspace_skill_info("/nonexistent/path/xyz", "langgraph") is None


class TestRunAgentLangGraph:
    def test_streams_text_and_finishes(self):
        from ag_ui.core import TextMessageChunkEvent

        sess = _mock_langgraph_session("sport_chat")

        async def fake_stream(prompt: str):
            yield TextMessageChunkEvent(message_id="m1", role="assistant", delta="Hello ")
            yield TextMessageChunkEvent(message_id="m1", role="assistant", delta="world!")

        sess.stream_prompt = fake_stream
        _sessions["sport_chat"] = sess
        _session_health["sport_chat"] = "connected"

        with patch("agui_server._save_own_history"):
            with patch("agui_server._load_own_history", return_value=None):
                with TestClient(app) as client:
                    res = client.post(
                        "/agent/sport_chat",
                        json={
                            "thread_id": "t1",
                            "run_id": "r1",
                            "state": {},
                            "messages": [
                                {"id": "u1", "role": "user", "content": "hi"}
                            ],
                            "tools": [],
                            "context": [],
                            "forwarded_props": {},
                        },
                    )

        assert res.status_code == 200
        body = res.text
        assert "RUN_STARTED" in body
        assert "RUN_FINISHED" in body
        assert "Hello " in body
        assert "world!" in body

    def test_tool_call_lifecycle(self):
        from ag_ui.core import (
            TextMessageChunkEvent,
            ToolCallChunkEvent,
            ToolCallResultEvent,
        )

        sess = _mock_langgraph_session("sport_chat")

        async def fake_stream(prompt: str):
            yield ToolCallChunkEvent(
                tool_call_id="tc1",
                tool_call_name="web_search",
                delta='{"query":"cricket"}',
            )
            yield ToolCallResultEvent(
                message_id="tc1",
                tool_call_id="tc1",
                content="results...",
                role="tool",
            )
            yield TextMessageChunkEvent(message_id="m1", role="assistant", delta="Cricket is...")

        sess.stream_prompt = fake_stream
        _sessions["sport_chat"] = sess
        _session_health["sport_chat"] = "connected"

        with patch("agui_server._save_own_history"):
            with patch("agui_server._load_own_history", return_value=None):
                with TestClient(app) as client:
                    res = client.post(
                        "/agent/sport_chat",
                        json={
                            "thread_id": "t1",
                            "run_id": "r1",
                            "state": {},
                            "messages": [
                                {"id": "u1", "role": "user", "content": "rules of cricket"}
                            ],
                            "tools": [],
                            "context": [],
                            "forwarded_props": {},
                        },
                    )

        body = res.text
        assert "TOOL_CALL_CHUNK" in body
        assert "TOOL_CALL_RESULT" in body
        assert "web_search" in body
        # Metrics should track the tool call
        assert _session_metrics["sport_chat"]["total_tool_calls"] == 1
