"""Launch the backend server from project root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("agui_server:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=["backend"])
