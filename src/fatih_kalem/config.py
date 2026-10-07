"""Persistent user settings backed by QSettings (human-editable INI).

The INI file lives at ``~/.config/fatih-kalem-linux/fatih-kalem-linux.ini`` so a
technician on a school board can inspect or pre-seed it over SSH.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QSettings

ORG_NAME = "fatih-kalem-linux"
ORG_DOMAIN = "fatih-kalem-linux.org"
APP_NAME = "fatih-kalem-linux"

#: Flat ``key -> default`` map. Every value is written to the INI on first run so
#: the file documents itself.
DEFAULTS: dict[str, Any] = {
    # -- general ---------------------------------------------------------
    "general/language": "system",  # system | tr_TR | en_US
    "general/showTrayIcon": True,
    "general/startInDrawMode": True,
    "general/singleInstance": True,
    "general/confirmOnQuit": True,
    # -- input / pointer -------------------------------------------------
    "input/passHotkey": "Ctrl+Alt+P",
    "input/toggleToolbarHotkey": "Ctrl+Alt+H",
    "input/passModeOnStart": "draw",  # draw | interact
    "input/minStrokeDistance": 1.5,
    "input/smoothing": 0.35,
    "input/pressureEnabled": True,
    "input/pressureGamma": 1.4,
    "input/pressureMinFactor": 0.35,
    "input/velocityWidth": False,
    # -- stylus ----------------------------------------------------------
    "stylus/palmRejection": True,
    "stylus/eraserEnd": True,
    "stylus/tiltNib": True,
    # -- pen -------------------------------------------------------------
    "pen/color": "#e11d2e",
    "pen/width": 4.0,
    "pen/penType": "solid",  # solid | dashed | broken
    "pen/markerOpacity": 0.35,
    "pen/tool": "pen",  # pen | marker | eraser
    "pen/favoriteColors": "#000000,#e11d2e,#1f6feb,#2da44e,#d29922,#8957e5,#e779c1",
    # -- eraser ----------------------------------------------------------
    "eraser/size": 48.0,
    "eraser/partial": True,
    # -- overlay ---------------------------------------------------------
    "overlay/screen": "",  # empty = primary screen
    "overlay/toolbarSide": "left",
    "overlay/toolbarAnchor": 0.5,  # 0.0 top .. 1.0 bottom
    "overlay/toolbarOpacity": 0.94,
    "overlay/buttonSize": 64,
    "overlay/keepAbove": True,
    "overlay/hint": "",  # optional first-run hint drawn under the ink
    "overlay/boardColor": "",  # "" = show the desktop through the overlay
    # -- gesture ---------------------------------------------------------
    "gesture/swipeColorEnabled": True,
    "gesture/swipeColorStep": 1,
    "gesture/swipeWidthEnabled": True,
    "gesture/twoFingerTapEraser": True,
    "gesture/edgeThreshold": 40,
    # -- capture / export ------------------------------------------------
    "capture/directory": "~/Pictures/FatihKalem",
    "capture/format": "png",
    "capture/includeCursor": False,
    "capture/namedSnippets": True,
}


def _settings(path: str | None = None) -> QSettings:
    """INI-backed settings: a technician can read them over SSH.

    ``path`` is only used by the test suite (and by a future portable mode) so a
    run never touches the teacher's real preferences.
    """
    if path:
        return QSettings(path, QSettings.Format.IniFormat)
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORG_NAME, APP_NAME)


def config_path() -> Path:
    """Absolute path of the INI file."""
    return Path(_settings().fileName())


def _coerce(default: Any, raw: Any) -> Any:
    if raw is None:
        return default
    if isinstance(default, bool):
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return bool(raw)
    if isinstance(default, int) and not isinstance(default, bool):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default
    if isinstance(default, float):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default
    return raw


class Config:
    """Typed accessor around :class:`QSettings`."""

    def __init__(self, *, path: str | None = None, auto_seed: bool = True) -> None:
        self._s = _settings(path)
        self._path = path

    # -- typed access ---------------------------------------------------
    def get(self, key: str) -> Any:
        default = DEFAULTS.get(key)
        if default is None:
            raise KeyError(f"unknown setting: {key}")
        return _coerce(default, self._s.value(key, default))

    def get_bool(self, key: str) -> bool:
        return bool(self.get(key))

    def get_int(self, key: str) -> int:
        return int(self.get(key))

    def get_float(self, key: str) -> float:
        return float(self.get(key))

    def get_str(self, key: str) -> str:
        return str(self.get(key))

    def get_list(self, key: str) -> list[str]:
        raw = self.get(key)
        if isinstance(raw, list):
            return [str(x) for x in raw if str(x).strip()]
        return [p for p in str(raw).split(",") if p.strip()]

    def set(self, key: str, value: Any) -> None:
        if key not in DEFAULTS:
            raise KeyError(f"unknown setting: {key}")
        self._s.setValue(key, value)

    def sync(self) -> None:
        self._s.sync()

    def is_default(self, key: str) -> bool:
        return self.get(key) == DEFAULTS[key]

    # -- maintenance ----------------------------------------------------
    def seed_missing(self) -> int:
        """Write any default that is absent from the INI. Returns count written."""
        written = 0
        for key, default in DEFAULTS.items():
            if not self._s.contains(key):
                self._s.setValue(key, default)
                written += 1
        if written:
            self._s.sync()
        return written

    def reset(self) -> None:
        self._s.clear()
        self.seed_missing()

    def backup(self, dest: str | Path | None = None) -> Path | None:
        src = config_path()
        if not src.exists():
            return None
        target = Path(dest) if dest else src.with_suffix(f".{os.getpid()}.bak")
        shutil.copy2(src, target)
        return target
