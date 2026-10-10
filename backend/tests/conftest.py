"""Pytest bootstrap: make `app` and `tests` importable without installing the package."""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Never hit real treg / Gemini from tests
os.environ["TREG_TOKEN"] = "test-token"
os.environ["GEMINI_API_KEY"] = ""

