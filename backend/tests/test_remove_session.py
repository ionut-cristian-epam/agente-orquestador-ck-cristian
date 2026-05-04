"""Tests for remove_session / remove_all_sessions logic.

Patches LOCAL_SESSIONS_DIR and ACPX_SESSIONS_DIR to temp directories
so no real data is touched.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import remove_session as mod
from remove_session import remove_session, remove_all_sessions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_acpx_index(sessions_dir: Path, entries: list[dict], files=None):
    if files is None:
        files = [f"{e['acpxRecordId']}.json" for e in entries]
    index = {"entries": entries, "files": files}
    index_path = sessions_dir / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def _make_local_index(sessions_dir: Path, entries: list[dict]):
    index = {"schema": "orchestrator.session-index.v1", "entries": entries}
    index_path = sessions_dir / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def _make_session_files(sessions_dir: Path, entry: dict):
    sid = entry["acpxRecordId"]
    (sessions_dir / f"{sid}.json").write_text(json.dumps({"data": "session"}, ensure_ascii=False), encoding="utf-8")
    (sessions_dir / f"{sid}.stream.ndjson").write_text('{"line":1}\n{"line":2}\n', encoding="utf-8")


def _sample_entry(name: str = "test-session", sid: str = "abc123", closed: bool = False):
    return {
        "name": name,
        "acpxRecordId": sid,
        "closed": closed,
        "cwd": "/tmp/test",
        "lastUsedAt": "2025-01-01T00:00:00Z",
    }


def _patched(local_dir, acpx_dir):
    return (
        patch.object(mod, "LOCAL_SESSIONS_DIR", local_dir),
        patch.object(mod, "ACPX_SESSIONS_DIR", acpx_dir),
    )


# ---------------------------------------------------------------------------
# remove_session
# ---------------------------------------------------------------------------

class TestRemoveSession:
    def test_removes_session_from_acpx(self):
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            entry = _sample_entry()
            _make_acpx_index(acpx, [entry])
            _make_session_files(acpx, entry)
            _make_local_index(local, [])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                result = remove_session(entry["name"])

            assert result is True
            assert not (acpx / f"{entry['acpxRecordId']}.json").exists()
            updated = json.loads((acpx / "index.json").read_text(encoding="utf-8"))
            assert updated["entries"] == []

    def test_removes_session_from_local_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            _make_acpx_index(acpx, [])
            _make_local_index(local, [{"name": "my-sess", "agent_harness": "opencode"}])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                result = remove_session("my-sess")

            assert result is True
            updated = json.loads((local / "index.json").read_text(encoding="utf-8"))
            assert updated["entries"] == []

    def test_returns_false_when_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            _make_acpx_index(acpx, [_sample_entry(name="other")])
            _make_local_index(local, [])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                result = remove_session("not-there")
            assert result is False

    def test_removes_only_target_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            e1 = _sample_entry(name="keep-me", sid="111")
            e2 = _sample_entry(name="remove-me", sid="222")
            _make_acpx_index(acpx, [e1, e2], files=["111.json", "222.json"])
            _make_session_files(acpx, e1)
            _make_session_files(acpx, e2)
            _make_local_index(local, [])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                result = remove_session("remove-me")

            assert result is True
            updated = json.loads((acpx / "index.json").read_text(encoding="utf-8"))
            assert len(updated["entries"]) == 1
            assert updated["entries"][0]["name"] == "keep-me"

    def test_closed_session_can_be_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            entry = _sample_entry(closed=True)
            _make_acpx_index(acpx, [entry])
            _make_session_files(acpx, entry)
            _make_local_index(local, [])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                result = remove_session(entry["name"])
            assert result is True

    def test_handles_special_characters_in_session_names(self):
        """Test that session names with special Unicode characters are preserved."""
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            # Test with Spanish characters (ñ, á, é, etc.)
            special_name = "España_sesión_café"
            entry = _sample_entry(name=special_name, sid="special123")
            _make_acpx_index(acpx, [entry])
            _make_session_files(acpx, entry)
            _make_local_index(local, [])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                result = remove_session(special_name)

            assert result is True
            assert not (acpx / f"{entry['acpxRecordId']}.json").exists()
            updated = json.loads((acpx / "index.json").read_text(encoding="utf-8"))
            assert updated["entries"] == []
            # Verify the special characters are preserved correctly
            assert all(e["name"] != special_name for e in updated["entries"])


# ---------------------------------------------------------------------------
# remove_all_sessions
# ---------------------------------------------------------------------------

class TestRemoveAllSessions:
    def test_removes_all_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            e1 = _sample_entry(name="a", sid="111")
            e2 = _sample_entry(name="b", sid="222")
            _make_acpx_index(acpx, [e1, e2])
            _make_session_files(acpx, e1)
            _make_session_files(acpx, e2)
            _make_local_index(local, [{"name": "c", "agent_harness": "opencode"}])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                result = remove_all_sessions()

            assert result is True
            assert json.loads((acpx / "index.json").read_text(encoding="utf-8"))["entries"] == []
            assert json.loads((local / "index.json").read_text(encoding="utf-8"))["entries"] == []

    def test_returns_true_when_no_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            _make_acpx_index(acpx, [])
            _make_local_index(local, [])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                result = remove_all_sessions()
            assert result is True

    def test_unrelated_files_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            entry = _sample_entry(sid="111")
            _make_acpx_index(acpx, [entry], files=["111.json", "other-log.txt", "111.stream.ndjson"])
            _make_session_files(acpx, entry)
            _make_local_index(local, [])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                result = remove_all_sessions()

            assert result is True
            updated = json.loads((acpx / "index.json").read_text(encoding="utf-8"))
            assert updated["files"] == ["other-log.txt"]

    def test_file_deletion_failure_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            acpx = Path(tmp) / "acpx"
            local = Path(tmp) / "local"
            entry = _sample_entry()
            _make_acpx_index(acpx, [entry])
            _make_session_files(acpx, entry)
            _make_local_index(local, [])

            p1, p2 = _patched(local, acpx)
            with p1, p2:
                with patch("pathlib.Path.unlink", side_effect=PermissionError("denied")):
                    result = remove_all_sessions()
            assert result is False
