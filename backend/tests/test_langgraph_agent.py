"""Tests for langgraph_agent module: tools, model factory, graph builder, streaming."""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

import langgraph_agent
from langgraph_agent import (
    SPORTS_TOOLS,
    _create_chat_model,
    _do_search,
    _extract_text_from_chunk,
    _parse_failed_generation,
    build_sports_agent,
    get_sport_rules,
    web_search,
)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

class TestToolDefinitions:
    def test_sports_tools_count(self):
        assert len(SPORTS_TOOLS) == 2

    def test_web_search_is_tool(self):
        assert hasattr(web_search, "invoke")
        assert web_search.name == "web_search"

    def test_get_sport_rules_is_tool(self):
        assert hasattr(get_sport_rules, "invoke")
        assert get_sport_rules.name == "get_sport_rules"


# ---------------------------------------------------------------------------
# Search routing (Tavily / DDG fallback)
# ---------------------------------------------------------------------------

class TestSearchRouting:
    def test_no_tavily_key_uses_ddg(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TAVILY_API_KEY", None)
            with patch.object(langgraph_agent, "_ddg_search", return_value="ddg_result") as ddg:
                result = _do_search("query")
        assert result == "ddg_result"
        ddg.assert_called_once()

    def test_tavily_key_uses_tavily(self):
        with patch.dict(os.environ, {"TAVILY_API_KEY": "fake"}):
            with patch.object(langgraph_agent, "_tavily_search", return_value="tavily_result") as tav:
                result = _do_search("query")
        assert result == "tavily_result"
        tav.assert_called_once()

    def test_tavily_failure_falls_back_to_ddg(self):
        with patch.dict(os.environ, {"TAVILY_API_KEY": "fake"}):
            with patch.object(langgraph_agent, "_tavily_search", side_effect=RuntimeError("boom")):
                with patch.object(langgraph_agent, "_ddg_search", return_value="ddg_result") as ddg:
                    result = _do_search("query")
        assert result == "ddg_result"

    def test_get_sport_rules_includes_sport_name(self):
        with patch.object(langgraph_agent, "_do_search", return_value="rules_result") as do:
            result = get_sport_rules.invoke({"sport_name": "cricket"})
        assert result == "rules_result"
        called_query = do.call_args[0][0]
        assert "cricket" in called_query
        assert "rules" in called_query.lower()


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

class TestCreateChatModel:
    def test_invalid_model_format_raises(self):
        with pytest.raises(ValueError, match="provider/model_id"):
            _create_chat_model("just-a-name")

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            _create_chat_model("xyz/some-model")

    def test_openai_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                _create_chat_model("openai/gpt-4o")

    def test_anthropic_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                _create_chat_model("anthropic/claude-sonnet-4-5-20250929")

    def test_google_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GOOGLE_API_KEY", None)
            with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
                _create_chat_model("google/gemini-2.5-flash")

    def test_openai_with_key_constructs_model(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake"}):
            model = _create_chat_model("openai/gpt-4o")
        assert model is not None
        assert type(model).__name__ == "ChatOpenAI"

    def test_groq_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GROQ_API_KEY", None)
            with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
                _create_chat_model("groq/llama-3.3-70b-versatile")

    def test_groq_with_key_uses_groq_endpoint(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake"}):
            model = _create_chat_model("groq/llama-3.3-70b-versatile")
        assert type(model).__name__ == "ChatGroq"

    def test_nagaai_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NAGA_API_KEY", None)
            with pytest.raises(RuntimeError, match="NAGA_API_KEY"):
                _create_chat_model("nagaai/gemini-2.5-flash:free")

    def test_nagaai_with_key_uses_naga_endpoint(self):
        with patch.dict(os.environ, {"NAGA_API_KEY": "fake"}):
            model = _create_chat_model("nagaai/gemini-2.5-flash:free")
        assert type(model).__name__ == "ChatOpenAI"
        assert "naga.ac" in str(model.openai_api_base or model.root_async_client.base_url)

    def test_openrouter_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENROUTER_API_KEY", None)
            with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
                _create_chat_model("openrouter/deepseek/deepseek-chat-v3:free")

    def test_openrouter_preserves_full_model_id(self):
        # OpenRouter model IDs contain slashes (e.g. "deepseek/deepseek-chat-v3:free")
        # The provider prefix is "openrouter" — the rest must be passed verbatim
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake"}):
            model = _create_chat_model("openrouter/deepseek/deepseek-chat-v3:free")
        assert model.model_name == "deepseek/deepseek-chat-v3:free"

    def test_cerebras_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEREBRAS_API_KEY", None)
            with pytest.raises(RuntimeError, match="CEREBRAS_API_KEY"):
                _create_chat_model("cerebras/llama-3.3-70b")


# ---------------------------------------------------------------------------
# Chunk text extraction
# ---------------------------------------------------------------------------

class TestExtractTextFromChunk:
    def test_string_content(self):
        chunk = MagicMock()
        chunk.content = "hello"
        assert _extract_text_from_chunk(chunk) == "hello"

    def test_list_of_text_blocks(self):
        chunk = MagicMock()
        chunk.content = [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]
        assert _extract_text_from_chunk(chunk) == "ab"

    def test_list_with_thinking_block_skipped(self):
        chunk = MagicMock()
        chunk.content = [{"type": "thinking", "thinking": "..."}, {"type": "text", "text": "answer"}]
        assert _extract_text_from_chunk(chunk) == "answer"

    def test_empty_content(self):
        chunk = MagicMock()
        chunk.content = ""
        assert _extract_text_from_chunk(chunk) == ""


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

class TestThinkingExtraction:
    def test_anthropic_thinking_block_extracted(self):
        from langgraph_agent import _extract_thinking_from_chunk
        chunk = MagicMock()
        chunk.content = [
            {"type": "thinking", "thinking": "Let me think about this..."},
            {"type": "text", "text": "answer"},
        ]
        assert _extract_thinking_from_chunk(chunk) == "Let me think about this..."

    def test_no_thinking_returns_empty(self):
        from langgraph_agent import _extract_thinking_from_chunk
        chunk = MagicMock()
        chunk.content = "just text"
        assert _extract_thinking_from_chunk(chunk) == ""

    def test_redacted_thinking_marked(self):
        from langgraph_agent import _extract_thinking_from_chunk
        chunk = MagicMock()
        chunk.content = [{"type": "redacted_thinking", "data": "..."}]
        assert "redacted" in _extract_thinking_from_chunk(chunk)


class TestParseFailedGeneration:
    """Recover tool calls from Groq/Llama malformed function calling."""

    def test_parenthesized_format(self):
        err = Exception(
            'Error code: 400 - {"error": {"message": "tool call validation failed: '
            "attempted to call tool 'web_search(query=\"Balon de Oro 2022 ganador\")' "
            'which was not in request.tools", "type": "invalid_request_error", '
            '"code": "tool_use_failed", "failed_generation": '
            '\'<function=web_search(query="Balon de Oro 2022 ganador")></function>\'}}'
        )
        result = _parse_failed_generation(err)
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "web_search"
        assert result[0]["args"]["query"] == "Balon de Oro 2022 ganador"

    def test_json_array_format(self):
        err = Exception(
            'failed_generation": \'<function=web_search [{"query": "test query"}]</function>\''
        )
        result = _parse_failed_generation(err)
        assert result is not None
        assert result[0]["name"] == "web_search"
        assert result[0]["args"]["query"] == "test query"

    def test_json_object_format(self):
        err = Exception(
            'failed_generation": \'<function=web_search{"query": "test"}></function>\''
        )
        result = _parse_failed_generation(err)
        assert result is not None
        assert result[0]["args"]["query"] == "test"

    def test_get_sport_rules_recovery(self):
        err = Exception(
            '<function=get_sport_rules(sport_name="cricket")></function>'
        )
        result = _parse_failed_generation(err)
        assert result is not None
        assert result[0]["name"] == "get_sport_rules"
        assert result[0]["args"]["sport_name"] == "cricket"

    def test_unknown_tool_ignored(self):
        err = Exception('<function=unknown_tool(x="1")></function>')
        result = _parse_failed_generation(err)
        assert result is None

    def test_no_match_returns_none(self):
        err = Exception("Some unrelated error message")
        result = _parse_failed_generation(err)
        assert result is None

    def test_recovered_call_has_id(self):
        err = Exception('<function=web_search(query="test")></function>')
        result = _parse_failed_generation(err)
        assert result[0]["id"].startswith("recovered_")


class TestBuildSportsAgent:
    def test_builds_compiled_graph(self):
        with patch.object(langgraph_agent, "_create_chat_model") as mock_factory:
            mock_llm = MagicMock()
            mock_llm.bind_tools = MagicMock(return_value=mock_llm)
            mock_factory.return_value = mock_llm
            graph = build_sports_agent("openai/gpt-4o", "system prompt")
        assert graph is not None
        # Compiled graph has invoke / astream methods
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "astream_events")
