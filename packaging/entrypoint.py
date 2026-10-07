"""PyInstaller entry point.

``python -m fatih_kalem`` uses the package-relative import in
``fatih_kalem/__main__.py``. PyInstaller instead runs the entry script as
``__main__`` with no parent package, so relative imports fail there - this shim
uses an absolute import and works in both cases.
"""

from __future__ import annotations

import sys

from fatih_kalem.app import main

if __name__ == "__main__":
    sys.exit(main())
