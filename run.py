"""Launch the backend server from project root."""
import sys
# Force UTF-8 encoding before importing anything else
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("agui_server:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=["backend"])
