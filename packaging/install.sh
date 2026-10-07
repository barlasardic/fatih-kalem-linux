#!/usr/bin/env bash
# Install Fatih Kalem for the current user (no root required).
#
#   ./packaging/install.sh                 # install + autostart on login
#   ./packaging/install.sh --no-autostart  # install only
#   ./packaging/install.sh --uninstall     # remove everything
set -euo pipefail

APP="fatih-kalem"
PREFIX="${HOME}/.local"
BIN_DIR="${PREFIX}/bin"
APPS_DIR="${PREFIX}/share/applications"
AUTOSTART_DIR="${HOME}/.config/autostart"
ICON_DIR="${PREFIX}/share/icons/hicolor/scalable/apps"
DESKTOP_SRC="$(dirname "$(readlink -f "$0")")/fatih-kalem.desktop"

AUTOSTART=1
UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --no-autostart) AUTOSTART=0 ;;
    --uninstall)   UNINSTALL=1 ;;
    -h|--help)     sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

echo "==> Installing Python dependencies"
python3 -c "import PyQt6" 2>/dev/null || {
  echo "    PyQt6 not found. Install it with:"
  echo "      sudo apt install python3-pyqt6      # Pardus / Ubuntu"
  echo "      sudo apt install python3-pyqt6-dev  # to build from source"
  exit 1
}

echo "==> Installing $APP into ${BIN_DIR}"
mkdir -p "${BIN_DIR}" "${APPS_DIR}"

cat >"${BIN_DIR}/${APP}" <<EOF
#!/usr/bin/env bash
exec "${PWD}/tools/run.sh" "\$@"
EOF
chmod +x "${BIN_DIR}/${APP}"

sed "s|Exec=fatih-kalem %U|Exec=${BIN_DIR}/${APP} %U|" "${DESKTOP_SRC}" >"${APPS_DIR}/${APP}.desktop"
chmod +x "${APPS_DIR}/${APP}.desktop"

if [ "${UNINSTALL}" -eq 1 ]; then
  echo "==> Removing autostart entry"
  rm -f "${AUTOSTART_DIR}/${APP}.desktop"
  echo "Done."
  exit 0
fi

mkdir -p "${ICON_DIR}"
if [ -f "assets/icon.svg" ]; then
  cp assets/icon.svg "${ICON_DIR}/${APP}.svg"
fi

if [ "${AUTOSTART}" -eq 1 ]; then
  echo "==> Enabling autostart (tahta açılınca hazır olsun)"
  mkdir -p "${AUTOSTART_DIR}"
  sed "s|Exec=fatih-kalem %U|Exec=${BIN_DIR}/${APP} %U|" \
    "${DESKTOP_SRC}" >"${AUTOSTART_DIR}/${APP}.desktop"
  chmod +x "${AUTOSTART_DIR}/${APP}.desktop"
fi

# Cinnamon is the session Pardus ETAP ships; refresh its menu cache if present.
if command -v cinnamon >/dev/null 2>&1 || [ -d /usr/share/cinnamon ]; then
  command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database -q "${APPS_DIR}" || true
fi

cat <<EOF

Installed.

  Start it      : ${BIN_DIR}/${APP}
  Settings file : ${HOME}/.config/${APP}/${APP}.ini
  Captures      : ${HOME}/Pictures/FatihKalem

Sign out and back in (or run the launcher from the Pardus menu) to pick it up.
EOF