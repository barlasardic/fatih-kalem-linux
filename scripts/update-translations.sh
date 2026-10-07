#!/usr/bin/env bash
# Regenerate the Qt .ts catalogs for external translators.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
cd "${ROOT}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
from pathlib import Path
from fatih_kalem import i18n

for locale_name in i18n.SUPPORTED_LOCALES:
    target = Path("i18n") / locale_name / "messages.ts"
    count = i18n.write_ts_skeleton(target, locale_name)
    print(f"{target}: {count} messages")
PY

echo
echo "Now translate the empty <translation></translation> entries and commit."
echo "The app itself uses i18n.py's catalog at runtime, so .ts files are for"
echo "translators and future lrelease-based plural handling."