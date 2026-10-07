"""Backend interface.

The overlay is the risky part of the whole app: on X11 we can make a real
always-on-top, click-through transparent surface; on Wayland a normal client
cannot, so the backend degrades and the UI tells the teacher.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PyQt6.QtGui import QImage, QScreen
from PyQt6.QtWidgets import QWidget


@dataclass(frozen=True, slots=True)
class Capabilities:
    """What the current session lets us do."""

    global_overlay: bool = False
    click_through: bool = False
    root_capture: bool = False
    global_hotkeys: bool = False
    always_on_top: bool = False
    notes: list[str] = field(default_factory=list)

    def describe(self) -> str:
        lines = [
            f"global overlay      : {'yes' if self.global_overlay else 'no'}",
            f"click-through regions: {'yes' if self.click_through else 'no'}",
            f"screen capture      : {'yes' if self.root_capture else 'no'}",
            f"global hotkeys      : {'yes' if self.global_hotkeys else 'no'}",
            f"always on top        : {'yes' if self.always_on_top else 'no'}",
        ]
        if self.notes:
            lines.append("")
            lines.extend(self.notes)
        return "\n".join(lines)


class DesktopBackend:
    """Base class; also used as a null backend when nothing is available."""

    name = "none"
    caps = Capabilities()

    @staticmethod
    def detect() -> DesktopBackend:  # pragma: no cover - overridden
        from .factory import detect_backend

        return detect_backend()

    # -- window management ---------------------------------------------
    def prepare_overlay(self, widget: QWidget) -> None:
        """Apply the server-specific attributes the overlay needs."""

    def raise_window(self, widget: QWidget) -> None:
        widget.raise_()
        widget.requestActivate()

    def apply_sticky(self, widget: QWidget) -> None:
        """Keep the overlay on every workspace."""

    # -- capture ---------------------------------------------------------
    def grab_screen(self, screen: QScreen) -> QImage | None:
        """Whole-screen pixels including everything underneath the overlay."""
        if screen is None:
            return None
        pixmap = screen.grabWindow(0)
        if pixmap.isNull():
            return None
        return pixmap.toImage()

    def grab_window(self, screen: QScreen, win_id: int) -> QImage | None:
        if screen is None:
            return None
        pixmap = screen.grabWindow(win_id)
        if pixmap.isNull():
            return None
        return pixmap.toImage()
