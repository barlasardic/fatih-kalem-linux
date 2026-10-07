"""Wayland backend.

A plain Wayland client cannot create a click-through surface above every other
window - the compositor decides stacking. Rather than pretending, the overlay
degrades to a normal always-on-top window and the UI explains the limitation and
points at the X11 session that Pardus ETAP uses.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QScreen
from PyQt6.QtWidgets import QWidget

from .base import Capabilities, DesktopBackend

NOTES = [
    "Wayland oturumu tespit edildi.",
    "Wayland, uygulamaların diğer pencerelerin üstüne şeffaf katman açmasına izin vermez.",
    "Tahtada tam işlev için X11 (Cinnamon) oturumu kullanın.",
    "Ekran görüntüsü alma desteklenmeyebilir.",
]


class WaylandBackend(DesktopBackend):
    name = "wayland"
    caps = Capabilities(
        global_overlay=False,
        click_through=False,
        root_capture=False,
        global_hotkeys=False,
        always_on_top=True,
        notes=list(NOTES),
    )

    @property
    def available(self) -> bool:
        return bool(os.environ.get("WAYLAND_DISPLAY"))

    def prepare_overlay(self, widget: QWidget) -> None:
        # All a client may ask for: stay on top. Stacking above every window and
        # click-through are compositor decisions on Wayland.
        widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

    def grab_screen(self, screen: QScreen) -> QImage | None:
        # Qt's Wayland plugin can only capture its own toplevels.
        return None
