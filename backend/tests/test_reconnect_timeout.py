"""Tests for reconnection and timeout logic in Session.stream_prompt.

Verifies:
- TimeoutError raised when subprocess produces no output for STREAM_IDLE_TIMEOUT seconds
- Reconnect attempt triggered when stderr contains 'needs reconnect' and no events received
- No reconnect if events were successfully received
- MAX_RECONNECT_ATTEMPTS respected (no infinite loop)
"""
import asyncio
import json
import queue
import threading
import time
from unittest.mock import MagicMock, patch, call

import pytest

from launch_sessions import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(tmp_path, harness="opencode") -> Session:
    with (
        patch.object(Session, "_run", return_value=None),
        patch.object(Session, "create_session", return_value=None),
        patch.object(Session, "_set_model_copilot", return_value=None),
    ):
        sess = Session.__new__(Session)
        sess.agent_harness = harness
        sess.name = "test-reconnect"
        sess.working_dir = str(tmp_path)
        sess.LLM = "opencode/big-pickle"
        return sess


def _mock_proc(stdout_lines: list[bytes], stderr_lines: list[bytes] = None, delay_per_line: float = 0):
    """Create a mock Popen process with controlled stdout/stderr."""
    proc = MagicMock()
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.flush = MagicMock()
    proc.stdin.close = MagicMock()

    class FakeStdout:
        def __init__(self, lines, delay):
            self._lines = iter(lines)
            self._delay = delay

        def __iter__(self):
            return self

        def __next__(self):
            if self._delay:
                time.sleep(self._delay)
            try:
                return next(self._lines)
            except StopIteration:
                raise StopIteration

    class FakeStderr:
        def __init__(self, lines):
            self._lines = iter(lines or [])

        def __iter__(self):
            return self

        def __next__(self):
            try:
                return next(self._lines)
            except StopIteration:
                raise StopIteration

        def read(self):
            return b""

    proc.stdout = FakeStdout(stdout_lines, delay_per_line)
    proc.stderr = FakeStderr(stderr_lines)
    proc.wait = MagicMock(return_value=0)
    return proc


def _acp_line(content: str) -> bytes:
    obj = {
        "jsonrpc": "2.0",
        "method": "session/update",
        "params": {
            "sessionId": "ses_test",
            "update": {
                "sessionUpdate": "agent_message_chunk",
                "messageId": "msg_1",
                "content": content,
            },
        },
    }
    return (json.dumps(obj) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# Timeout tests
# ---------------------------------------------------------------------------

class TestStreamTimeout:
    @pytest.mark.asyncio
    async def test_timeout_raises_after_idle(self, tmp_path):
        """No output for longer than STREAM_IDLE_TIMEOUT → TimeoutError."""
        sess = _make_session(tmp_path)
        sess.STREAM_IDLE_TIMEOUT = 1  # 1 second for fast test

        # Process that produces nothing on stdout, hangs
        proc = MagicMock()
        proc.stdin = MagicMock()
        proc.stdin.write = MagicMock()
        proc.stdin.flush = MagicMock()
        proc.stdin.close = MagicMock()

        class HangingStdout:
            def __iter__(self):
                time.sleep(3)  # hang longer than timeout
                return iter([])

        class EmptyStderr:
            def __iter__(self):
                return iter([])
            def read(self):
                return b""

        proc.stdout = HangingStdout()
        proc.stderr = EmptyStderr()
        proc.wait = MagicMock(return_value=0)

        with patch("launch_sessions.subprocess.Popen", return_value=proc):
            with pytest.raises(TimeoutError, match="no output"):
                results = []
                async for item in sess.stream_prompt("hello"):
                    results.append(item)

    @pytest.mark.asyncio
    async def test_no_timeout_when_output_arrives(self, tmp_path):
        """Output arriving within timeout → no error."""
        sess = _make_session(tmp_path)
        sess.STREAM_IDLE_TIMEOUT = 5

        lines = [_acp_line("Hello"), _acp_line(" world")]
        proc = _mock_proc(lines)

        with patch("launch_sessions.subprocess.Popen", return_value=proc):
            results = []
            async for item in sess.stream_prompt("hello"):
                results.append(item)

        assert len(results) == 2


# ---------------------------------------------------------------------------
# Reconnect tests
# ---------------------------------------------------------------------------

class TestStreamReconnect:
    @pytest.mark.asyncio
    async def test_reconnect_triggered_on_stderr_signal(self, tmp_path):
        """When stderr has 'needs reconnect' and no events → retry."""
        sess = _make_session(tmp_path)
        sess.STREAM_IDLE_TIMEOUT = 10
        sess.MAX_RECONNECT_ATTEMPTS = 1

        call_count = [0]

        def make_proc(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: no stdout events, stderr says reconnect
                return _mock_proc(
                    stdout_lines=[],
                    stderr_lines=[b"error: needs reconnect\n"],
                )
            else:
                # Second call after reconnect: produces events
                return _mock_proc(
                    stdout_lines=[_acp_line("reconnected!")],
                    stderr_lines=[],
                )

        with (
            patch("launch_sessions.subprocess.Popen", side_effect=make_proc),
            patch.object(sess, "_ensure_connected") as mock_ensure,
        ):
            results = []
            async for item in sess.stream_prompt("hello"):
                results.append(item)

        mock_ensure.assert_called_once()
        assert len(results) == 1
        assert results[0]["params"]["update"]["content"] == "reconnected!"

    @pytest.mark.asyncio
    async def test_no_reconnect_when_events_received(self, tmp_path):
        """If events were received, don't reconnect even if stderr has signal."""
        sess = _make_session(tmp_path)
        sess.MAX_RECONNECT_ATTEMPTS = 1

        proc = _mock_proc(
            stdout_lines=[_acp_line("got data")],
            stderr_lines=[b"warning: needs reconnect\n"],
        )

        with (
            patch("launch_sessions.subprocess.Popen", return_value=proc),
            patch.object(sess, "_ensure_connected") as mock_ensure,
        ):
            results = []
            async for item in sess.stream_prompt("hello"):
                results.append(item)

        mock_ensure.assert_not_called()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_max_reconnect_attempts_respected(self, tmp_path):
        """Don't retry more than MAX_RECONNECT_ATTEMPTS times."""
        sess = _make_session(tmp_path)
        sess.STREAM_IDLE_TIMEOUT = 10
        sess.MAX_RECONNECT_ATTEMPTS = 1

        # Always fails with reconnect signal
        def make_proc(*args, **kwargs):
            return _mock_proc(
                stdout_lines=[],
                stderr_lines=[b"error: needs reconnect\n"],
            )

        with (
            patch("launch_sessions.subprocess.Popen", side_effect=make_proc),
            patch.object(sess, "_ensure_connected") as mock_ensure,
        ):
            results = []
            async for item in sess.stream_prompt("hello"):
                results.append(item)

        # Should only reconnect once (MAX_RECONNECT_ATTEMPTS=1)
        assert mock_ensure.call_count == 1
        assert results == []

    @pytest.mark.asyncio
    async def test_ensure_connected_calls_acpx(self, tmp_path):
        """_ensure_connected runs 'sessions ensure' command."""
        sess = _make_session(tmp_path)

        with patch.object(sess, "_run") as mock_run:
            sess._ensure_connected()

        mock_run.assert_called_once_with(
            ["acpx", "opencode", "sessions", "ensure", "--name", "test-reconnect"],
            capture_output=True,
        )
