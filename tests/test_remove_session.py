"""Tests for remove_session / remove_all_sessions logic.

These tests use a temporary directory and mock Path.home() to point to it,
validating index manipulation, file deletion, and error handling without
touching real acpx data.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from remove_session import remove_session, remove_all_sessions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_index(sessions_dir: Path, entries: list[dict], files: list[str] | None = None):
    """Create a sessions directory with an index.json based on the given entries."""
    if files is None:
        files = [f"{e['acpxRecordId']}.json" for e in entries]
    index = {"entries": entries, "files": files}
    index_path = sessions_dir / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index))
    return index_path


def _make_session_files(sessions_dir: Path, entry: dict):
    """Create .json and .stream.ndjson files for a session entry."""
    sid = entry["acpxRecordId"]
    (sessions_dir / f"{sid}.json").write_text(json.dumps({"data": "session"}))
    (sessions_dir / f"{sid}.stream.ndjson").write_text(
        '{"line":1}\n{"line":2}\n'
    )


def _sample_entry(name: str = "test-session", sid: str = "abc123", closed: bool = False):
    return {
        "name": name,
        "acpxRecordId": sid,
        "closed": closed,
        "cwd": "/tmp/test",
        "lastUsedAt": "2025-01-01T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# remove_session
# ---------------------------------------------------------------------------

class TestRemoveSession:
    def test_removes_session_and_its_files(self):
        """Happy path: session found, files deleted, index updated."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            entry = _sample_entry()
            _make_index(sessions_dir, [entry])
            _make_session_files(sessions_dir, entry)

            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_session(entry["name"])

            assert result is True
            assert not (sessions_dir / f"{entry['acpxRecordId']}.json").exists()
            assert not (sessions_dir / f"{entry['acpxRecordId']}.stream.ndjson").exists()
            updated = json.loads((sessions_dir / "index.json").read_text())
            assert updated["entries"] == []
            assert updated["files"] == []

    def test_returns_false_when_index_missing(self):
        """If index.json doesn't exist, return False."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_session("nonexistent")
            assert result is False

    def test_returns_false_when_session_not_found(self):
        """If the session name is not in the index, return False."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            _make_index(sessions_dir, [_sample_entry(name="other")])
            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_session("not-there")
            assert result is False

    def test_exact_name_match_only(self):
        """Ensure partial name matching does not remove a session."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            entry = _sample_entry(name="my-agent")
            _make_index(sessions_dir, [entry])

            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_session("my-agent-partial")

            assert result is False
            updated = json.loads((sessions_dir / "index.json").read_text())
            assert len(updated["entries"]) == 1

    def test_succeeds_when_files_already_missing(self):
        """If session files don't exist on disk, still update the index."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            entry = _sample_entry()
            _make_index(sessions_dir, [entry])

            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_session(entry["name"])

            assert result is True
            updated = json.loads((sessions_dir / "index.json").read_text())
            assert updated["entries"] == []

    def test_removes_only_target_session(self):
        """When multiple sessions exist, only the target is removed."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            e1 = _sample_entry(name="keep-me", sid="111")
            e2 = _sample_entry(name="remove-me", sid="222")
            _make_index(sessions_dir, [e1, e2], files=["111.json", "222.json"])
            _make_session_files(sessions_dir, e1)
            _make_session_files(sessions_dir, e2)

            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_session("remove-me")

            assert result is True
            updated = json.loads((sessions_dir / "index.json").read_text())
            assert len(updated["entries"]) == 1
            assert updated["entries"][0]["name"] == "keep-me"
            assert updated["files"] == ["111.json"]

    def test_file_deletion_failure_returns_false(self):
        """If a file can't be deleted, return False."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            entry = _sample_entry()
            _make_index(sessions_dir, [entry])
            _make_session_files(sessions_dir, entry)

            with patch.object(Path, "home", return_value=tmp_path):
                with patch("pathlib.Path.unlink", side_effect=PermissionError("denied")):
                    result = remove_session(entry["name"])

            assert result is False

    def test_index_write_failure_returns_false(self):
        """If index.json can't be written (e.g. disk full), return False."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            entry = _sample_entry()
            _make_index(sessions_dir, [entry])
            _make_session_files(sessions_dir, entry)

            orig_open = open

            def _restricted_open(file, mode="r", *a, **kw):
                path = Path(str(file)).resolve()
                index_path = (sessions_dir / "index.json").resolve()
                if path == index_path and ("w" in mode or "a" in mode):
                    raise OSError("disk full")
                return orig_open(file, mode, *a, **kw)

            with patch.object(Path, "home", return_value=tmp_path):
                with patch("builtins.open", side_effect=_restricted_open):
                    result = remove_session(entry["name"])

            assert result is False

    def test_closed_session_can_be_removed(self):
        """Closed (already terminated) sessions can still be cleaned up."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            entry = _sample_entry(closed=True)
            _make_index(sessions_dir, [entry])
            _make_session_files(sessions_dir, entry)

            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_session(entry["name"])

            assert result is True
            updated = json.loads((sessions_dir / "index.json").read_text())
            assert updated["entries"] == []


# ---------------------------------------------------------------------------
# remove_all_sessions
# ---------------------------------------------------------------------------

class TestRemoveAllSessions:
    def test_removes_all_sessions(self):
        """All entries and their files are deleted."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            e1 = _sample_entry(name="a", sid="111")
            e2 = _sample_entry(name="b", sid="222")
            _make_index(sessions_dir, [e1, e2])
            _make_session_files(sessions_dir, e1)
            _make_session_files(sessions_dir, e2)

            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_all_sessions()

            assert result is True
            updated = json.loads((sessions_dir / "index.json").read_text())
            assert updated["entries"] == []
            assert updated["files"] == []

    def test_returns_false_when_index_missing(self):
        """If no index exists, return False."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_all_sessions()
            assert result is False

    def test_returns_true_when_no_entries(self):
        """Empty index is a successful no-op."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            _make_index(sessions_dir, [])
            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_all_sessions()
            assert result is True

    def test_file_deletion_failure_returns_false(self):
        """If any file can't be deleted, return False immediately."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            entry = _sample_entry()
            _make_index(sessions_dir, [entry])
            _make_session_files(sessions_dir, entry)

            with patch.object(Path, "home", return_value=tmp_path):
                with patch("pathlib.Path.unlink", side_effect=PermissionError("denied")):
                    result = remove_all_sessions()

            assert result is False

    def test_index_write_failure_returns_false(self):
        """If the index.json write fails, return False."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            entry = _sample_entry()
            _make_index(sessions_dir, [entry])
            _make_session_files(sessions_dir, entry)

            orig_open = open

            def _restricted_open(file, mode="r", *a, **kw):
                path = Path(str(file)).resolve()
                index_path = (sessions_dir / "index.json").resolve()
                if path == index_path and ("w" in mode or "a" in mode):
                    raise OSError("disk full")
                return orig_open(file, mode, *a, **kw)

            with patch.object(Path, "home", return_value=tmp_path):
                with patch("builtins.open", side_effect=_restricted_open):
                    result = remove_all_sessions()

            assert result is False

    def test_unrelated_files_preserved(self):
        """Files in .files list that don't match any acpxRecordId are kept."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_dir = tmp_path / ".acpx" / "sessions"
            entry = _sample_entry(sid="111")
            _make_index(
                sessions_dir,
                [entry],
                files=["111.json", "other-log.txt", "111.stream.ndjson"],
            )
            _make_session_files(sessions_dir, entry)

            with patch.object(Path, "home", return_value=tmp_path):
                result = remove_all_sessions()

            assert result is True
            updated = json.loads((sessions_dir / "index.json").read_text())
            assert updated["files"] == ["other-log.txt"]
