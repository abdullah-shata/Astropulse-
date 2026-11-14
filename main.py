"""Root FastAPI entrypoint discovered by Vercel's zero-configuration runtime."""

import importlib.util
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "3_backend_core"
spec = importlib.util.spec_from_file_location(
    "astropulse_backend",
    BACKEND_DIR / "main.py",
    submodule_search_locations=[str(BACKEND_DIR)],
)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load backend application from {BACKEND_DIR}")

backend = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = backend
spec.loader.exec_module(backend)

app = backend.app
