#!/usr/bin/env bash
# Board diagnostic: what does this session support, and what hardware is there?
# Safe to run in front of a teacher and paste straight into an issue report.
set -uo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"

section() { printf '\n== %s ==\n' "$1"; }

section "system"
cat /etc/os-release 2>/dev/null | grep -E '^(PRETTY_NAME|VERSION)=' || uname -a

section "session"
printf 'DISPLAY=%s\nWAYLAND_DISPLAY=%s\nDESKTOP=%s\n' \
  "${DISPLAY:--}" "${WAYLAND_DISPLAY:--}" "${XDG_CURRENT_DESKTOP:--}"
echo
"${ROOT}/tools/run.sh" --print-session 2>&1

section "desktop tooling"
for tool in cinnamon muffin xinput xrandr libinput wmctrl; do
  printf '%-10s %s\n' "$tool" "$(command -v "$tool" || echo '-')"
done

section "touch / pen input"
if command -v libinput >/dev/null 2>&1; then
  libinput list-devices 2>/dev/null | grep -E '^(Device:|Kernel:|  .*(Touch|Pen|Tablet))' | head -40
elif [ -d /dev/input ]; then
  echo "libinput not installed; raw devices:"
  ls -l /dev/input/ 2>/dev/null
fi

section "touchscreen module"
lsmod 2>/dev/null | grep -iE 'hid|wacom|usbtouch|elo' | head -10

section "screens"
if command -v xrandr >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
  xrandr --current 2>/dev/null | grep -E ' connected' || echo "(X11 only)"
fi

section "resources"
free -m 2>/dev/null | head -2
df -h / 2>/dev/null | tail -1

section "pyqt6"
python3 -c "from PyQt6.QtCore import QT_VERSION_STR; print('Qt', QT_VERSION_STR)" 2>&1

section "config"
cfg="${HOME}/.config/fatih-kalem-linux/fatih-kalem-linux.ini"
if [ -f "$cfg" ]; then
  echo "$cfg"
  grep -Ev '^\s*($|;|\[)' "$cfg" | head -40
else
  echo "not created yet (run the app once)"
fi
