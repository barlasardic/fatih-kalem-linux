"""X11 backend: EWMH stacking, sticky desktops and click-through input regions.

Qt already turns ``QWidget.setMask(QRegion)`` into an XShape input region, so
click-through needs no Xlib code here. What Qt does *not* do is keep the overlay
above Cinnamon/Muffin full-screen windows, which is why ``keep_above`` and
``raise_window`` talk to the server directly.
"""

from __future__ import annotations

import ctypes
import os

from PyQt6.QtGui import QImage, QScreen
from PyQt6.QtWidgets import QWidget

from .base import Capabilities, DesktopBackend

XA_ATOM = 4
XA_CARDINAL = 6

#: EWMH atoms we need. Interned lazily and cached.
_NET_WM_STATE = "_NET_WM_STATE"
NET_WM_STATE_ABOVE = "_NET_WM_STATE_ABOVE"
NET_WM_STATE_STICKY = "_NET_WM_STATE_STICKY"
NET_WM_STATE_SKIP_TASKBAR = "_NET_WM_STATE_SKIP_TASKBAR"
NET_WM_STATE_SKIP_PAGER = "_NET_WM_STATE_SKIP_PAGER"
NET_WM_STATE_FULLSCREEN = "_NET_WM_STATE_FULLSCREEN"
NET_WM_DESKTOP = "_NET_WM_DESKTOP"
NET_WM_WINDOW_TYPE = "_NET_WM_WINDOW_TYPE"
NET_WM_WINDOW_TYPE_NORMAL = "_NET_WM_WINDOW_TYPE_NORMAL"
NET_WM_WINDOW_TYPE_SPLASH = "_NET_WM_WINDOW_TYPE_SPLASH"

ALL_DESKTOPS = 0xFFFFFFFF


class X11Backend(DesktopBackend):
    name = "x11"

    def __init__(self) -> None:
        self._lib: ctypes.CDLL | None = None
        self._display: int | None = None
        self._atoms: dict[str, int] = {}

        if not os.environ.get("DISPLAY"):
            return
        try:
            lib = ctypes.CDLL("libX11.so.6")
        except OSError:
            return

        lib.XOpenDisplay.restype = ctypes.c_void_p
        lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        lib.XInternAtom.restype = ctypes.c_ulong
        lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        lib.XChangeProperty.restype = ctypes.c_int
        lib.XChangeProperty.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        lib.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        lib.XFlush.argtypes = [ctypes.c_void_p]
        lib.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]

        display = lib.XOpenDisplay(None)
        if not display:
            return
        self._lib = lib
        self._display = display
        self.caps = Capabilities(
            global_overlay=True,
            click_through=True,
            root_capture=True,
            global_hotkeys=True,
            always_on_top=True,
            notes=["X11 oturumu: tüm özellikler etkin."],
        )

    # -- plumbing --------------------------------------------------------
    @property
    def available(self) -> bool:
        return self._display is not None and self._lib is not None

    def _atom(self, name: str) -> int:
        assert self._lib is not None and self._display is not None
        if name not in self._atoms:
            self._atoms[name] = int(self._lib.XInternAtom(self._display, name.encode(), False))
        return self._atoms[name]

    def _set_state(self, win_id: int, atom: str, enabled: bool) -> None:
        assert self._lib is not None and self._display is not None
        prop = self._atom(_NET_WM_STATE)
        value = self._atom(atom)
        data = (ctypes.c_ulong * 2)(value, 1 if enabled else 0)
        self._lib.XChangeProperty(
            self._display,
            ctypes.c_ulong(win_id),
            ctypes.c_ulong(prop),
            ctypes.c_ulong(XA_ATOM),
            32,
            0,  # PropModeReplace
            ctypes.cast(data, ctypes.c_void_p),
            2,
        )
        self._lib.XFlush(self._display)

    def _set_cardinal(self, win_id: int, atom: str, value: int) -> None:
        assert self._lib is not None and self._display is not None
        data = (ctypes.c_ulong * 1)(value)
        self._lib.XChangeProperty(
            self._display,
            ctypes.c_ulong(win_id),
            ctypes.c_ulong(self._atom(atom)),
            ctypes.c_ulong(XA_CARDINAL),
            32,
            0,
            ctypes.cast(data, ctypes.c_void_p),
            1,
        )
        self._lib.XFlush(self._display)

    # -- DesktopBackend --------------------------------------------------
    def prepare_overlay(self, widget: QWidget) -> None:
        """Qt flags already create an override-redirect surface; nudge EWMH too."""
        if not self.available:
            return
        win = int(widget.winId())
        self._set_state(win, NET_WM_STATE_SKIP_TASKBAR, True)
        self._set_state(win, NET_WM_STATE_SKIP_PAGER, True)
        self._set_state(win, NET_WM_STATE_STICKY, True)
        self.apply_sticky(widget)

    def apply_sticky(self, widget: QWidget) -> None:
        if not self.available:
            return
        self._set_cardinal(int(widget.winId()), NET_WM_DESKTOP, ALL_DESKTOPS)

    def raise_window(self, widget: QWidget) -> None:
        assert self._lib is not None
        if self.available:
            self._lib.XRaiseWindow(self._display, ctypes.c_ulong(int(widget.winId())))
            self._lib.XFlush(self._display)
        else:
            super().raise_window(widget)

    def grab_screen(self, screen: QScreen) -> QImage | None:
        """``grabWindow(0)`` on X11 reads the root window: every window below us."""
        return super().grab_screen(screen)
