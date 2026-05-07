"""Tests for LangGraphSession adapter."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import langgraph_session
from langgraph_session import LangGraphSession, _load_system_prompt


# ---------------------------------------------------------------------------
# _load_system_prompt
# ---------------------------------------------------------------------------

class TestLoadSystemPrompt:
    def test_missing_config_returns_default(self, tmp_path):
        result = _load_system_prompt(str(tmp_path))
        assert "helpful assistant" in result.lower()

    def test_loads_prompt_from_file(self, tmp_path):
        (tmp_path / "langgraph_agent.json").write_text(
            '{"system_prompt_file": "skills/expert.md"}', encoding="utf-8"
        )
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "expert.md").write_text("You are a sports expert.", encoding="utf-8")
        result = _load_system_prompt(str(tmp_path))
        assert result == "You are a sports expert."

    def test_missing_prompt_file_returns_default(self, tmp_path):
        (tmp_path / "langgraph_agent.json").write_text(
            '{"system_prompt_file": "missing.md"}', encoding="utf-8"
        )
        result = _load_system_prompt(str(tmp_path))
        assert "helpful assistant" in result.lower()


# ---------------------------------------------------------------------------
# LangGraphSession construction
# ---------------------------------------------------------------------------

class TestLangGraphSessionInit:
    def test_init_does_not_build_graph(self, tmp_path):
        """Graph build is deferred until first prompt to avoid requiring API key
        for attach/delete."""
        with patch.object(langgraph_session, "build_sports_agent") as builder:
            sess = LangGraphSession(
                name="test",
                working_dir=str(tmp_path),
                LLM="openai/gpt-4o-mini",
            )
        assert sess.agent_harness == "langgraph"
        assert sess.name == "test"
        assert sess.LLM == "openai/gpt-4o-mini"
        assert sess._graph is None
        builder.assert_not_called()

    def test_graph_built_lazily_on_first_prompt(self, tmp_path):
        from ag_ui.core import TextMessageChunkEvent

        async def fake_stream(graph, messages, **kwargs):
            yield TextMessageChunkEvent(message_id="m1", role="assistant", delta="hi")

        with patch.object(langgraph_session, "build_sports_agent") as builder:
            builder.return_value = MagicMock()
            sess = LangGraphSession(name="t", working_dir=str(tmp_path), LLM="openai/gpt-4o-mini")
            assert sess._graph is None
            with patch.object(langgraph_session, "stream_langgraph_events", side_effect=fake_stream):
                import asyncio
                async def consume():
                    async for _ in sess.stream_prompt("hi"):
                        pass
                asyncio.run(consume())
        builder.assert_called_once()

    def test_default_llm_used_when_none(self, tmp_path):
        with patch.object(langgraph_session, "build_sports_agent") as builder:
            builder.return_value = MagicMock()
            sess = LangGraphSession(name="t", working_dir=str(tmp_path), LLM=None)
        assert sess.LLM == "openai/gpt-4o-mini"

    def test_close_clears_messages(self, tmp_path):
        with patch.object(langgraph_session, "build_sports_agent") as builder:
            builder.return_value = MagicMock()
            sess = LangGraphSession(name="t", working_dir=str(tmp_path), LLM="openai/gpt-4o-mini")
        sess._messages.append(MagicMock())
        sess.close_session()
        assert sess._messages == []

    def test_ensure_connected_is_noop(self, tmp_path):
        with patch.object(langgraph_session, "build_sports_agent") as builder:
            builder.return_value = MagicMock()
            sess = LangGraphSession(name="t", working_dir=str(tmp_path), LLM="openai/gpt-4o-mini")
        # Should not raise
        sess._ensure_connected()


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

class TestHistory:
    def test_restore_history_rehydrates_messages(self, tmp_path):
        with patch.object(langgraph_session, "build_sports_agent") as builder:
            builder.return_value = MagicMock()
            sess = LangGraphSession(name="t", working_dir=str(tmp_path), LLM="openai/gpt-4o-mini")
        sess.restore_history([
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ])
        assert len(sess._messages) == 2

    def test_read_history_round_trip(self, tmp_path):
        with patch.object(langgraph_session, "build_sports_agent") as builder:
            builder.return_value = MagicMock()
            sess = LangGraphSession(name="t", working_dir=str(tmp_path), LLM="openai/gpt-4o-mini")
        sess.restore_history([
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ])
        history = sess.read_history()
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "hi"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "hello"

    def test_read_history_with_tail(self, tmp_path):
        with patch.object(langgraph_session, "build_sports_agent") as builder:
            builder.return_value = MagicMock()
            sess = LangGraphSession(name="t", working_dir=str(tmp_path), LLM="openai/gpt-4o-mini")
        for i in range(5):
            sess.restore_history([{"role": "user", "content": f"msg{i}"}])
        history = sess.read_history(tail=2)
        assert len(history) == 2


# ---------------------------------------------------------------------------
# stream_prompt
# ---------------------------------------------------------------------------

class TestStreamPrompt:
    @pytest.mark.asyncio
    async def test_yields_agui_events_and_appends_history(self, tmp_path):
        from ag_ui.core import TextMessageChunkEvent
        from langchain_core.messages import AIMessage

        async def fake_stream(graph, messages, *, message_collector=None, **kwargs):
            yield TextMessageChunkEvent(message_id="m1", role="assistant", delta="hi")
            if message_collector is not None:
                message_collector.append(AIMessage(content="hi"))

        with patch.object(langgraph_session, "build_sports_agent") as builder:
            builder.return_value = MagicMock()
            sess = LangGraphSession(name="t", working_dir=str(tmp_path), LLM="openai/gpt-4o-mini")

            with patch.object(langgraph_session, "stream_langgraph_events", side_effect=fake_stream):
                events = []
                async for ev in sess.stream_prompt("hello"):
                    events.append(ev)

        # Skill activation now lives in run_agent (centralized) — only the text chunk here
        assert len(events) == 1
        assert isinstance(events[0], TextMessageChunkEvent)
        assert events[0].delta == "hi"
        # User message + AI message appended to history
        assert len(sess._messages) == 2
        assert sess._messages[0].content == "hello"
        assert sess._messages[1].content == "hi"
