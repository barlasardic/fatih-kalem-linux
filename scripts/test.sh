#!/usr/bin/env bash
# Run the test suite. Needs nothing but PyQt6 - pytest is used when present.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
cd "${ROOT}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"

if command -v pytest >/dev/null 2>&1; then
  exec pytest -q "$@"
fi

echo "pytest not installed - falling back to unittest"
exec python3 -m unittest discover -s tests -t . -v "$@"