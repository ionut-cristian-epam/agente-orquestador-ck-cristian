import json
import os
from pathlib import Path


def remove_all_sessions():
    """Remove all acpx sessions.

    Returns:
        bool: True if successful, False otherwise
    """

    sessions_path = Path.home() / ".acpx" / "sessions"
    index_path = sessions_path / "index.json"

    if not index_path.exists():
        print(f"❌ Error: Session index not found at {index_path}")
        return False

    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    entries = index.get('entries', [])
    if not entries:
        print("ℹ️ No sessions found")
        return True

    session_ids = [entry['acpxRecordId'] for entry in entries]
    files_to_delete = []
    total_size = 0

    print(f"\n📋 Sessions to remove: {len(entries)}")
    for entry in entries:
        name = entry.get('name', '(unnamed)')
        session_id = entry['acpxRecordId']
        status = "closed" if entry.get('closed') else "open"
        print(f"  - {name} [{session_id}] ({status})")

        for suffix in (".json", ".stream.ndjson"):
            file_path = sessions_path / f"{session_id}{suffix}"
            if file_path.exists():
                size = file_path.stat().st_size
                total_size += size
                files_to_delete.append((file_path, size))

    print(f"\n  Total files: {len(files_to_delete)}")
    print(f"  Total size: {total_size / 1024:.2f} KB")

    print("\n🗑️  Deleting files...")
    for file_path, _ in files_to_delete:
        try:
            file_path.unlink()
            print(f"  ✓ Deleted: {file_path.name}")
        except Exception as e:
            print(f"  ✗ Failed to delete {file_path.name}: {e}")
            return False

    print("\n📝 Updating index...")
    index['entries'] = []
    index['files'] = [
        file_name for file_name in index.get('files', [])
        if not any(file_name.startswith(session_id) for session_id in session_ids)
    ]

    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)
        print("  ✓ Index updated")
    except Exception as e:
        print(f"  ✗ Failed to update index: {e}")
        return False

    print("\n✅ Successfully removed all sessions")
    return True

def remove_session(session_name):
    """Remove an acpx session by name
    
    Args:
        session_name: Name of the session to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Path to sessions directory
    sessions_path = Path.home() / ".acpx" / "sessions"
    index_path = sessions_path / "index.json"
    
    if not index_path.exists():
        print(f"❌ Error: Session index not found at {index_path}")
        return False
    
    # Read the index
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    # Find the session
    session_to_remove = None
    for entry in index['entries']:
        if entry.get('name') == session_name:
            session_to_remove = entry
            break
    
    if not session_to_remove:
        print(f"❌ Error: Session '{session_name}' not found")
        return False
    
    # Display session info
    name = session_to_remove.get('name', '(unnamed)')
    session_id = session_to_remove['acpxRecordId']
    status = "closed" if session_to_remove.get('closed') else "open"
    
    print(f"\n📋 Session to remove:")
    print(f"  Name: {name}")
    print(f"  ID: {session_id}")
    print(f"  Status: {status}")
    print(f"  Path: {session_to_remove.get('cwd', 'N/A')}")
    print(f"  Last used: {session_to_remove.get('lastUsedAt', 'N/A')}")
    
    # Find files to delete
    json_file = sessions_path / f"{session_id}.json"
    stream_file = sessions_path / f"{session_id}.stream.ndjson"
    
    files_to_delete = []
    total_size = 0
    
    if json_file.exists():
        size = json_file.stat().st_size
        total_size += size
        files_to_delete.append((json_file, size))
        print(f"\n  📄 {json_file.name} ({size / 1024:.2f} KB)")
    
    if stream_file.exists():
        size = stream_file.stat().st_size
        total_size += size
        files_to_delete.append((stream_file, size))
        print(f"  📄 {stream_file.name} ({size / 1024:.2f} KB)")
    
    print(f"\n  Total size: {total_size / 1024:.2f} KB")
    
    # Delete files
    print("\n🗑️  Deleting files...")
    for file_path, _ in files_to_delete:
        try:
            file_path.unlink()
            print(f"  ✓ Deleted: {file_path.name}")
        except Exception as e:
            print(f"  ✗ Failed to delete {file_path.name}: {e}")
            return False
    
    # Update index.json
    print("\n📝 Updating index...")
    
    # Remove from entries
    index['entries'] = [e for e in index['entries'] if e['acpxRecordId'] != session_id]
    
    # Remove from files list
    index['files'] = [f for f in index['files'] if not f.startswith(session_id)]
    
    # Save updated index
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)
        print("  ✓ Index updated")
    except Exception as e:
        print(f"  ✗ Failed to update index: {e}")
        return False
    
    print(f"\n✅ Successfully removed session '{name}'")
    return True

if __name__ == "__main__":

    # Uncommment the following lines to remove a specific session by name
    # session_name = input("Enter the name of the session to remove: ")
    # remove_session(session_name)

    # Uncommment the following line to remove all sessions
    remove_all_sessions()