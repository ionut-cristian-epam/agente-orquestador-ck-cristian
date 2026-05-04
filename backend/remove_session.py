import json
import os
from pathlib import Path

PROJECT_ROOT = Path(
    os.environ.get("AGENT_ORCH_PROJECT_ROOT", Path(__file__).resolve().parent.parent)
).resolve()
LOCAL_SESSIONS_DIR = PROJECT_ROOT / "sessions"
ACPX_SESSIONS_DIR = Path.home() / ".acpx" / "sessions"


def _load_index(path: Path) -> dict:
    if not path.exists():
        return {"entries": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_index(path: Path, index: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def remove_all_sessions():
    """Remove all sessions from both local and acpx stores."""
    removed = 0

    # --- Local sessions ---
    local_index_path = LOCAL_SESSIONS_DIR / "index.json"
    local_index = _load_index(local_index_path)
    local_entries = local_index.get("entries", [])
    if local_entries:
        print(f"\n📋 Local sessions to remove: {len(local_entries)}")
        for entry in local_entries:
            print(f"  - {entry.get('name', '(unnamed)')} ({entry.get('agent_harness', '?')})")
        local_index["entries"] = []
        _save_index(local_index_path, local_index)
        removed += len(local_entries)
        print("  ✓ Local index cleared")

    # --- acpx sessions ---
    acpx_index_path = ACPX_SESSIONS_DIR / "index.json"
    acpx_index = _load_index(acpx_index_path)
    acpx_entries = acpx_index.get("entries", [])
    if acpx_entries:
        session_ids = [e["acpxRecordId"] for e in acpx_entries]
        files_to_delete = []
        total_size = 0

        print(f"\n📋 acpx sessions to remove: {len(acpx_entries)}")
        for entry in acpx_entries:
            name = entry.get("name", "(unnamed)")
            sid = entry["acpxRecordId"]
            status = "closed" if entry.get("closed") else "open"
            print(f"  - {name} [{sid}] ({status})")

            for suffix in (".json", ".stream.ndjson", ".stream.lock"):
                fp = ACPX_SESSIONS_DIR / f"{sid}{suffix}"
                if fp.exists():
                    size = fp.stat().st_size
                    total_size += size
                    files_to_delete.append(fp)

        print(f"\n  Total files: {len(files_to_delete)} ({total_size / 1024:.2f} KB)")
        for fp in files_to_delete:
            try:
                fp.unlink()
            except Exception as e:
                print(f"  ✗ Failed to delete {fp.name}: {e}")
                return False

        acpx_index["entries"] = []
        acpx_index["files"] = [
            f for f in acpx_index.get("files", [])
            if not any(f.startswith(sid) for sid in session_ids)
        ]
        _save_index(acpx_index_path, acpx_index)
        removed += len(acpx_entries)
        print("  ✓ acpx index cleared")

    # Clean stale tmp files
    for tmp in ACPX_SESSIONS_DIR.glob("*.tmp"):
        tmp.unlink(missing_ok=True)

    if removed == 0:
        print("ℹ️ No sessions found")
    else:
        print(f"\n✅ Removed {removed} sessions total")
    return True


def remove_session(session_name):
    """Remove a session by name from local index and/or acpx."""

    # --- Try local index first ---
    local_index_path = LOCAL_SESSIONS_DIR / "index.json"
    local_index = _load_index(local_index_path)
    local_match = [e for e in local_index["entries"] if e.get("name") == session_name]

    if local_match:
        local_index["entries"] = [e for e in local_index["entries"] if e.get("name") != session_name]
        _save_index(local_index_path, local_index)
        print(f"  ✓ Removed '{session_name}' from local index")

    # --- Try acpx index ---
    acpx_index_path = ACPX_SESSIONS_DIR / "index.json"
    acpx_index = _load_index(acpx_index_path)
    acpx_match = None
    for entry in acpx_index["entries"]:
        if entry.get("name") == session_name:
            acpx_match = entry
            break

    if acpx_match:
        sid = acpx_match["acpxRecordId"]
        for suffix in (".json", ".stream.ndjson", ".stream.lock"):
            fp = ACPX_SESSIONS_DIR / f"{sid}{suffix}"
            if fp.exists():
                fp.unlink()
        acpx_index["entries"] = [e for e in acpx_index["entries"] if e["acpxRecordId"] != sid]
        acpx_index["files"] = [f for f in acpx_index.get("files", []) if not f.startswith(sid)]
        _save_index(acpx_index_path, acpx_index)
        print(f"  ✓ Removed '{session_name}' from acpx index")

    if not local_match and not acpx_match:
        print(f"❌ Session '{session_name}' not found")
        return False

    print(f"\n✅ Successfully removed session '{session_name}'")
    return True


if __name__ == "__main__":
    remove_all_sessions()
