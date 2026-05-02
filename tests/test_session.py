"""Tests for Session model validation and config injection logic.

These tests do NOT call acpx — they mock _run and create_session to
test only the pure Python logic.
"""
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from launch_sessions import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(tmp_dir: str, harness: str = "opencode", LLM: str = "opencode/big-pickle") -> Session:
    """Create a Session without calling acpx by mocking _run and create_session."""
    with (
        patch.object(Session, "_run", return_value=None),
        patch.object(Session, "create_session", return_value=None),
        patch.object(Session, "_set_model_copilot", return_value=None),
    ):
        return Session(
            agent_harness=harness,
            name="test",
            working_dir=tmp_dir,
            LLM=LLM,
            capture_output=True,
        )


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------

class TestModelValidation:
    def test_valid_opencode_model_is_accepted(self, tmp_path):
        sess = _make_session(str(tmp_path), harness="opencode", LLM="opencode/big-pickle")
        assert sess.LLM == "opencode/big-pickle"

    def test_invalid_opencode_model_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unsupported model"):
            _make_session(str(tmp_path), harness="opencode", LLM="totally/fake-model")

    def test_invalid_model_message_contains_model_name(self, tmp_path):
        with pytest.raises(ValueError, match="fake-model-xyz"):
            _make_session(str(tmp_path), harness="opencode", LLM="fake-model-xyz")

    def test_claude_harness_skips_model_validation(self, tmp_path):
        # Non-opencode harnesses don't call _set_model_in_config
        sess = _make_session(str(tmp_path), harness="claude", LLM="anything/goes")
        assert sess.LLM == "anything/goes"


# ---------------------------------------------------------------------------
# opencode.json config injection
# ---------------------------------------------------------------------------

class TestConfigInjection:
    def test_creates_config_if_missing(self, tmp_path):
        _make_session(str(tmp_path), harness="opencode", LLM="opencode/big-pickle")
        config_path = tmp_path / "opencode.json"
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert config["model"] == "opencode/big-pickle"

    def test_updates_existing_config(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        config_path.write_text(json.dumps({"$schema": "...", "model": "old/model", "other": "kept"}))

        _make_session(str(tmp_path), harness="opencode", LLM="opencode/big-pickle")

        config = json.loads(config_path.read_text())
        assert config["model"] == "opencode/big-pickle"
        assert config["other"] == "kept"  # existing fields preserved

    def test_schema_key_preserved_on_creation(self, tmp_path):
        _make_session(str(tmp_path), harness="opencode", LLM="opencode/big-pickle")
        config = json.loads((tmp_path / "opencode.json").read_text())
        assert "$schema" in config

    def test_non_opencode_harness_does_not_write_config(self, tmp_path):
        _make_session(str(tmp_path), harness="claude", LLM="anything")
        assert not (tmp_path / "opencode.json").exists()


# ---------------------------------------------------------------------------
# _filter_output
# ---------------------------------------------------------------------------

class TestFilterOutput:
    def setup_method(self):
        with (
            patch.object(Session, "_run", return_value=None),
            patch.object(Session, "create_session", return_value=None),
        ):
            self.sess = Session.__new__(Session)
            self.sess.agent_harness = "opencode"
            self.sess.name = "test"
            self.sess.working_dir = "."
            self.sess.LLM = "opencode/big-pickle"

    def test_strips_acpx_metadata_lines(self):
        raw = "[INFO] starting\nActual response\n[DEBUG] done\n"
        result = self.sess._filter_output(raw)
        assert result == "actual response" or result == "Actual response"

    def test_keeps_non_bracket_lines(self):
        raw = "Hello world\nThis is the answer\n"
        result = self.sess._filter_output(raw)
        assert "Hello world" in result
        assert "This is the answer" in result

    def test_strips_leading_trailing_whitespace(self):
        raw = "\n\nActual content\n\n"
        result = self.sess._filter_output(raw)
        assert result == "Actual content"

    def test_empty_input_returns_empty_string(self):
        assert self.sess._filter_output("") == ""

    def test_all_metadata_returns_empty_string(self):
        raw = "[INFO] a\n[DEBUG] b\n[WARN] c\n"
        result = self.sess._filter_output(raw)
        assert result == ""


# ---------------------------------------------------------------------------
# stream_prompt — unit test with mocked subprocess
# ---------------------------------------------------------------------------

class TestStreamPrompt:
    @pytest.mark.asyncio
    async def test_yields_parsed_json_lines(self, tmp_path):
        lines = [
            b'{"jsonrpc":"2.0","method":"session/update","params":{"update":{"sessionUpdate":"agent_message_chunk","content":"Hi"}}}\n',
            b'{"jsonrpc":"2.0","method":"session/update","params":{"update":{"sessionUpdate":"agent_message_chunk","content":" there"}}}\n',
        ]

        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter(lines)
        mock_proc.wait = MagicMock(return_value=0)

        with (
            patch.object(Session, "_run", return_value=None),
            patch.object(Session, "create_session", return_value=None),
            patch("launch_sessions.subprocess.Popen", return_value=mock_proc),
        ):
            sess = Session(
                agent_harness="opencode",
                name="test",
                working_dir=str(tmp_path),
                LLM="opencode/big-pickle",
                capture_output=True,
            )
            results = []
            async for rpc in sess.stream_prompt("Hello"):
                results.append(rpc)

        assert len(results) == 2
        assert results[0]["method"] == "session/update"
        assert results[1]["params"]["update"]["content"] == " there"

    @pytest.mark.asyncio
    async def test_skips_invalid_json_lines(self, tmp_path):
        lines = [
            b"not json\n",
            b'{"jsonrpc":"2.0","method":"session/update","params":{"update":{"sessionUpdate":"agent_message_chunk","content":"ok"}}}\n',
        ]

        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter(lines)
        mock_proc.wait = MagicMock(return_value=0)

        with (
            patch.object(Session, "_run", return_value=None),
            patch.object(Session, "create_session", return_value=None),
            patch("launch_sessions.subprocess.Popen", return_value=mock_proc),
        ):
            sess = Session(
                agent_harness="opencode",
                name="test",
                working_dir=str(tmp_path),
                LLM="opencode/big-pickle",
                capture_output=True,
            )
            results = []
            async for rpc in sess.stream_prompt("Hello"):
                results.append(rpc)

        assert len(results) == 1
        assert results[0]["params"]["update"]["content"] == "ok"
