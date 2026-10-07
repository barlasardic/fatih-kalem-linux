"""Backend selection.

X11 is the target (Pardus ETAP runs Cinnamon on Xorg), Wayland is degraded, and
anything else falls back to the base implementation.
"""

from __future__ import annotations

import os
import sys

from .base import Capabilities, DesktopBackend
from .wayland import WaylandBackend
from .x11 import X11Backend

__all__ = ["DesktopBackend", "Capabilities", "detect_backend", "backend_report"]


def detect_backend() -> DesktopBackend:
    if os.environ.get("WAYLAND_DISPLAY"):
        return WaylandBackend()
    if os.environ.get("DISPLAY"):
        backend = X11Backend()
        if backend.available:
            return backend
    # Fall back to X11 when a Qt xcb connection is in use without an X client
    # library (e.g. a stripped AppImage).
    if "xcb" in sys.argv or os.environ.get("QT_QPA_PLATFORM") == "xcb":
        return X11Backend()
    return DesktopBackend()


def backend_report(backend: DesktopBackend) -> str:
    return f"backend: {backend.name}\n{backend.caps.describe()}"


def session_report() -> str:
    parts = [
        f"platform : {sys.platform}",
        f"Qt       : {os.environ.get('QT_QPA_PLATFORM', 'auto')}",
        f"DISPLAY  : {os.environ.get('DISPLAY', '-')}",
        f"WAYLAND  : {os.environ.get('WAYLAND_DISPLAY', '-')}",
        f"desktop  : {os.environ.get('XDG_CURRENT_DESKTOP', '-')}",
    ]
    return "\n".join(parts)
