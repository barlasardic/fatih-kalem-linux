#!/usr/bin/env bash
# Run Fatih Kalem straight from a checkout - no install step.
#
#   ./tools/run.sh                 # full-screen overlay
#   ./tools/run.sh --sandbox       # normal window, for developing the UI
#   ./tools/run.sh --print-session # what the session supports
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

# A board is a single-user kiosk; keep Qt from reading the developer's theme.
export QT_ENABLE_HIGHDPI_SCALING=1

exec python3 -m fatih_kalem "$@"