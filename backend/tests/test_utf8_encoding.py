"""Tests to verify UTF-8 encoding works correctly for session names with special characters."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import agui_server as server_mod
from agui_server import app, _normalize_name, _load_local_index, _save_local_index, _add_to_local_index
from fastapi.testclient import TestClient


class TestUTF8Encoding:
    """Test that special characters in session names are preserved through the full stack."""

    def test_normalize_name_preserves_special_chars(self):
        """Test that _normalize_name correctly normalizes Unicode characters."""
        special_names = [
            "España",
            "Berlín",
            "café",
            "Москва",  # Cyrillic
            "日本",  # Japanese
            "Ñoño",  # Multiple special chars
        ]
        for name in special_names:
            normalized = _normalize_name(name)
            assert normalized == name, f"Failed to normalize {name}"
            # Verify it's in NFC form
            import unicodedata
            assert normalized == unicodedata.normalize("NFC", name)

    def test_save_and_load_special_chars_from_index(self):
        """Test that special characters are preserved when saving/loading from JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            sessions_dir = Path(tmp) / "sessions"
            sessions_dir.mkdir()

            # Patch the SESSIONS_DIR
            with patch.object(server_mod, "SESSIONS_DIR", sessions_dir):
                # Save entry with special characters
                entry = {
                    "name": "España_sesión_café",
                    "agent_harness": "opencode",
                    "cwd": "/home/españa/projects",
                    "LLM": "modelo_español",
                    "closed": False,
                }
                _add_to_local_index(entry)

                # Load and verify
                loaded = _load_local_index()
                assert len(loaded["entries"]) == 1
                assert loaded["entries"][0]["name"] == "España_sesión_café"
                assert loaded["entries"][0]["cwd"] == "/home/españa/projects"
                assert loaded["entries"][0]["LLM"] == "modelo_español"

                # Verify file contents are UTF-8 encoded
                index_path = sessions_dir / "index.json"
                with open(index_path, "rb") as f:
                    raw_content = f.read()
                # Should not contain mojibake patterns
                # "Ã¡" would be mojibake (á incorrectly decoded)
                # We expect to find the correct UTF-8 sequences
                assert b"Espa" in raw_content  # Start of "España"
                assert b"caf" in raw_content  # Start of "café"
                
                # Verify we can decode it as UTF-8 without errors
                decoded = raw_content.decode("utf-8")
                assert "España" in decoded
                assert "café" in decoded

    def test_api_response_preserves_special_chars(self):
        """Test that the list_sessions endpoint returns correct special characters."""
        with tempfile.TemporaryDirectory() as tmp:
            sessions_dir = Path(tmp) / "sessions"
            sessions_dir.mkdir()
            acpx_dir = Path(tmp) / "acpx"
            acpx_dir.mkdir()

            # Patch directories and pre-populate with special characters
            with patch.object(server_mod, "SESSIONS_DIR", sessions_dir):
                with patch.object(server_mod, "ACPX_SESSIONS_DIR", acpx_dir):
                    # Manually create an entry with special characters
                    entry = {
                        "name": "Berlín_España",
                        "agent_harness": "opencode",
                        "cwd": "/tmp/test",
                        "LLM": None,
                        "closed": False,
                        "createdAt": "2025-01-01T00:00:00Z",
                        "lastUsedAt": "2025-01-01T00:00:00Z",
                    }
                    _add_to_local_index(entry)
                    
                    # Now test the API response
                    client = TestClient(app)
                    response = client.get("/sessions")
                    assert response.status_code == 200
                    data = response.json()
                    
                    # Check that the session name is correctly returned
                    assert len(data["acpx"]) > 0 or len(data["registered"]) > 0
                    # The name should be in the response
                    session_names = data.get("acpx", [])
                    if session_names:
                        assert any(s["name"] == "Berlín_España" for s in session_names)

    def test_response_content_type_has_charset(self):
        """Test that JSON responses include charset=utf-8 in Content-Type header."""
        with tempfile.TemporaryDirectory() as tmp:
            sessions_dir = Path(tmp) / "sessions"
            sessions_dir.mkdir()

            with patch.object(server_mod, "SESSIONS_DIR", sessions_dir):
                client = TestClient(app)
                response = client.get("/sessions")
                assert response.status_code == 200
                # Check Content-Type header includes charset
                content_type = response.headers.get("content-type", "").lower()
                assert "application/json" in content_type
                assert "charset=utf-8" in content_type or "utf-8" in content_type.replace("-", "")
