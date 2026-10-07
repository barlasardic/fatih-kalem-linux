"""Shared helpers for the test suite.

Tests are plain :mod:`unittest` so they run on a bare Pardus board with nothing
installed beyond PyQt6 (``python3 -m unittest discover -s tests``), and pytest
picks them up unchanged when it is available.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
