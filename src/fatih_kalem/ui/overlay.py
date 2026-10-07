"""The transparent full-screen annotation layer.

This is the component the whole project exists for. On X11 the window is
override-redirect (nothing the window manager does can push it down) plus
``_NET_WM_STATE_ABOVE`` as a belt-and-braces measure, and click-through is a
single XShape input region: the full screen while drawing, just the toolbar
rectangle when control is handed back to the application underneath.
"""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QGuiApplication,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
    QRegion,
    QScreen,
    QShortcut,
)
from PyQt6.QtWidgets import QLabel, QWidget

from ..config import Config
from ..core.models import PenType, Tool
from ..export import png as png_export
from ..i18n import tr
from ..platform.base import DesktopBackend
from .canvas import Canvas
from .toolbar import Toolbar

#: How long the overlay stays hidden so the X server re-reads the root window.
CAPTURE_SETTLE_MS = 130
#: Re-assert the stacking order this often (KDE/KWin and Cinnamon full-screen
#: windows both try to raise themselves).
RAISE_INTERVAL_MS = 1500


class Overlay(QWidget):
    """Full-screen click-through drawing surface plus its toolbar.

    ``sandbox=True`` turns the very same widget into an ordinary sized window so
    the UI can be developed and reviewed on a desktop session (Wayland included)
    without touching any X11 window-manager behaviour.
    """

    passModeChanged = pyqtSignal(bool)
    statusMessage = pyqtSignal(str)
    captureFinished = pyqtSignal(str)
    exitRequested = pyqtSignal()

    def __init__(
        self,
        config: Config,
        backend: DesktopBackend,
        parent: QWidget | None = None,
        *,
        sandbox: bool = False,
        size: tuple[int, int] = (1280, 720),
    ) -> None:
        super().__init__(parent)
        self._cfg = config
        self._backend = backend
        self._sandbox = sandbox
        self._sandbox_size = size
        self._pass_mode = False
        self._capturing = False
        self._raise_timer = QTimer(self)
        self._raise_timer.setInterval(RAISE_INTERVAL_MS)
        self._raise_timer.timeout.connect(self._reassert_stacking)

        self.canvas = Canvas(config, self)
        self.toolbar = Toolbar(config, self)
        self._status = QLabel(self)
        self._status.setObjectName("statusPill")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._status.hide()
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._status.hide)
        self._wire_toolbar()

        self._build_shortcuts()
        self._apply_window_flags()
        self._apply_style()
        self.toolbar.place(self.size())
        self.statusMessage.connect(self.show_status)

    # -- construction ----------------------------------------------------
    def _apply_window_flags(self) -> None:
        if self._sandbox:
            self.setWindowFlags(Qt.WindowType.Window)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setWindowTitle("Fatih Kalem - sandbox")
            return
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        if self._backend.name == "x11":
            # Override-redirect: Muffin cannot lower or cover it.
            flags |= Qt.WindowType.BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setWindowTitle("Fatih Kalem")

    def _apply_style(self) -> None:
        hint = self._cfg.get_str("overlay/hint")
        if hint:
            self.canvas.set_hint(hint)

    def _wire_toolbar(self) -> None:
        bar = self.toolbar
        bar.toolChanged.connect(self._on_tool)
        bar.colorChanged.connect(self.canvas.set_color)
        bar.widthChanged.connect(self._on_width)
        bar.undoRequested.connect(self.canvas.undo)
        bar.redoRequested.connect(self.canvas.redo)
        bar.clearRequested.connect(self.canvas.clear_all)
        bar.captureRequested.connect(lambda: self.request_capture(composite=True))
        bar.passToggled.connect(self.set_pass_mode)
        bar.settingsRequested.connect(self.show_settings_placeholder)
        bar.hideRequested.connect(self.hide_overlay)
        self.canvas.historyChanged.connect(self._sync_history)

    def _build_shortcuts(self) -> None:
        # Effective where the window can take focus (Wayland, sandbox). On X11 the
        # override-redirect surface never holds focus, so M4 adds root-level
        # XGrabKey equivalents for the same actions.
        self._shortcuts = [
            self._shortcut("Ctrl+Z", self.canvas.undo),
            self._shortcut("Ctrl+Shift+Z", self.canvas.redo),
            self._shortcut("Ctrl+Y", self.canvas.redo),
            self._shortcut("Ctrl+PgDown", self.canvas.clear_all),
            self._shortcut("Ctrl+Alt+P", self.toggle_pass_mode),
            self._shortcut("Escape", self.hide_overlay),
            self._shortcut("Ctrl+Shift+S", lambda: self.request_capture(composite=True)),
        ]

    def _shortcut(self, sequence: str, slot) -> QShortcut:
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.activated.connect(slot)
        return shortcut

    # -- lifecycle --------------------------------------------------------
    def primary_screen(self) -> QScreen | None:
        name = self._cfg.get_str("overlay/screen")
        if name:
            for s in QGuiApplication.screens():
                if s.name() == name:
                    return s
        return QGuiApplication.primaryScreen()

    def show_overlay(self) -> None:
        if self._sandbox:
            self.canvas.set_board_color(self._board_color())
            self.resize(*self._sandbox_size)
            self.show()
            self.toolbar.place(self.size())
            self.canvas.set_pass_mode(self._pass_mode)
            return
        screen = self.primary_screen()
        if screen is not None:
            self.setGeometry(screen.geometry())
            self.toolbar.place(self.size())
        self.canvas.set_board_color(self._board_color())
        self._backend.prepare_overlay(self)
        self.show()
        self._reassert_stacking()
        self._raise_timer.start()
        self.canvas.set_pass_mode(self._pass_mode)

    def hide_overlay(self) -> None:
        self._raise_timer.stop()
        self.canvas.cancel_stroke()
        self.hide()

    def close_overlay(self) -> None:
        self._raise_timer.stop()
        self.canvas.cancel_stroke()
        self._cfg.sync()
        self.close()

    def _reassert_stacking(self) -> None:
        if self._sandbox or not self.isVisible():
            return
        if self._cfg.get_bool("overlay/keepAbove"):
            self._backend.raise_window(self)
            self._backend.apply_sticky(self)

    def _board_color(self):
        value = self._cfg.get_str("overlay/boardColor")
        return value if value and value.lower() not in {"transparent", "#00000000", ""} else None

    # -- modes -------------------------------------------------------------
    def set_pass_mode(self, enabled: bool) -> None:
        """True = overlay lets the application underneath receive touches."""
        enabled = bool(enabled)
        if enabled == self._pass_mode:
            return
        self._pass_mode = enabled
        self.canvas.set_pass_mode(enabled)
        self.toolbar.set_pass_state(enabled)
        self._apply_input_region()
        self.passModeChanged.emit(enabled)
        self.statusMessage.emit(
            tr("Passed through to the application - pen hidden") if enabled else tr("Pen visible")
        )

    def toggle_pass_mode(self) -> None:
        self.set_pass_mode(not self._pass_mode)

    def _apply_input_region(self) -> None:
        """Qt maps this mask onto the XShape input region - the click-through."""
        if self._sandbox:
            return
        if self._pass_mode:
            mask = QRegion(self.toolbar.geometry())
        else:
            mask = QRegion(self.rect())
        self.setMask(mask)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.canvas.setGeometry(self.rect())
        self._apply_input_region()

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        self._apply_input_region()

    # -- toolbar plumbing ---------------------------------------------------
    def _on_tool(self, tool: Tool) -> None:
        self.canvas.set_tool(tool)
        if self._pass_mode:
            # Teacher asked for the eraser/marker from pass-through: bring ink back.
            self.set_pass_mode(False)
        self.statusMessage.emit(f"{tr('Tool')}: {tr(tool.value)}")

    def _on_width(self, width: float) -> None:
        if self.canvas.tool is Tool.ERASER:
            self.canvas.set_eraser_size(width)
        else:
            self.canvas.set_width(width)

    def _sync_history(self) -> None:
        self.toolbar.sync_history(self.canvas.can_undo(), self.canvas.can_redo())

    def show_status(self, text: str) -> None:
        """Transient toast at the bottom of the board."""
        if not text:
            return
        self._status.setText(text)
        self._status.adjustSize()
        pill_w = self._status.width() + 28
        pill_h = self._status.height() + 14
        self._status.setGeometry(
            max(0, (self.width() - pill_w) // 2),
            max(0, self.height() - pill_h - 28),
            pill_w,
            pill_h,
        )
        self._status.show()
        self._status.raise_()
        self._status_timer.start(2600)

    def show_settings_placeholder(self) -> None:
        self.statusMessage.emit(tr("Settings (coming in M2)"))

    def apply_pen_settings(self) -> None:
        """Push persisted settings into the canvas (called at startup)."""
        self.canvas.set_color(self._cfg.get_str("pen/color"))
        self.canvas.set_width(self._cfg.get_float("pen/width"))
        try:
            tool = Tool(self._cfg.get_str("pen/tool"))
        except ValueError:
            tool = Tool.PEN
        self.canvas.set_tool(tool)
        self.toolbar.set_active_tool(tool)
        self.canvas.set_pen_type(PenType(self._cfg.get_str("pen/penType")))
        self.canvas.set_marker_opacity(self._cfg.get_float("pen/markerOpacity"))
        self.canvas.set_eraser_size(self._cfg.get_float("eraser/size"))

    # -- capture ------------------------------------------------------------
    def request_capture(
        self, composite: bool = True, callback: Callable[[QImage], None] | None = None
    ) -> None:
        """Save a capture; hiding first so the screenshot is the clean desktop."""
        if self._capturing:
            return
        self._capturing = True
        directory = png_export.default_directory(self._cfg)
        fmt = self._cfg.get_str("capture/format")
        target = png_export.timestamped_path(directory, fmt=fmt)
        ink = self.canvas.ink_image()
        if not composite or not self._backend.caps.root_capture:
            self._capturing = False
            image = ink if ink.width() else QImage()
            self._write(image, target, tr("Only the drawing was saved"))
            if callback is not None:
                callback(image)
            return

        self.hide()
        QTimer.singleShot(
            CAPTURE_SETTLE_MS,
            lambda: self._finish_composite_capture(target, callback, ink),
        )

    def _finish_composite_capture(
        self, target, callback: Callable[[QImage], None] | None, ink: QImage
    ) -> None:
        try:
            background = self._backend.grab_screen(self.primary_screen())
        except Exception:  # pragma: no cover - backend failure must not kill the app
            background = None
        image = png_export.composite(background, ink) if background is not None else ink
        self._write(image, target, tr("Screenshot saved"))
        self._capturing = False
        self.show()
        self._apply_input_region()
        self._reassert_stacking()
        self._raise_timer.start()
        if callback is not None:
            callback(image)

    def _write(self, image: QImage, target, message: str) -> None:
        if image.isNull():
            self.statusMessage.emit(tr("Capture failed"))
            return
        try:
            if target.suffix.lower() == ".pdf":
                written = png_export.save_pdf(image, target)
            else:
                written = png_export.save_image(image, target)
        except OSError as exc:
            self.statusMessage.emit(f"{tr('Could not save')}: {exc}")
            return
        self.statusMessage.emit(f"{message}: {written}")
        self.captureFinished.emit(str(written))

    # -- history helpers ----------------------------------------------------
    def undo(self) -> None:
        if not self.canvas.undo():
            self.statusMessage.emit(tr("Nothing to undo"))

    def redo(self) -> None:
        if not self.canvas.redo():
            self.statusMessage.emit(tr("Nothing to redo"))

    def clear_all(self) -> None:
        if self.canvas.clear_all():
            self.statusMessage.emit(tr("Screen cleared"))

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._sandbox:
            # The canvas child paints the ink; nothing to draw on the shell itself.
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(24, 27, 33))
        for y in range(0, self.height(), 48):
            painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        for x in range(0, self.width(), 48):
            painter.drawLine(x, 0, x, self.height())
        painter.end()


__all__ = ["Overlay", "CAPTURE_SETTLE_MS", "RAISE_INTERVAL_MS"]
