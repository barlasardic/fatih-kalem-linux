"""Floating vertical toolbar (M1 subset).

Lives as a *child* of the overlay window rather than a separate top-level
widget: that keeps the z-order trivial (it is painted above the ink) and lets the
click-through region be expressed as a single rectangle when the overlay hands
control back to the application underneath.

M1 ships pen/marker/eraser, colour and size cycling, undo/redo, clear, capture,
pass-through and hide. The full panel set (shapes, backgrounds, pages, library,
curtain, favourites) lands in M2/M3.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import Config
from ..core.models import Tool
from . import icons
from .theme import ERASER_SIZES, PALETTE, PEN_WIDTHS, stylesheet

ICON_SIZE_RATIO = 0.52

#: Button order of the exclusive tool group.
_TOOLS: tuple[Tool, ...] = (Tool.PEN, Tool.MARKER, Tool.ERASER)


#: Smallest touch target we accept, even when the board is short.
MIN_BUTTON_SIZE = 40
MIN_SPACING = 3
MAX_SPACING = 8


def _make_button(name: str, size: int, tip: str = "", *, checkable: bool = False) -> QPushButton:
    btn = QPushButton()
    btn.setCheckable(checkable)
    btn.setFixedSize(size, size)
    btn.setIconSize(QSize(int(size * ICON_SIZE_RATIO), int(size * ICON_SIZE_RATIO)))
    btn.setIcon(icons.make_icon(name, int(size * ICON_SIZE_RATIO)))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    if tip:
        btn.setToolTip(tip)
    return btn


class Toolbar(QFrame):
    """Draggable, side-snapping vertical tool strip."""

    toolChanged = pyqtSignal(object)
    colorChanged = pyqtSignal(object)
    widthChanged = pyqtSignal(float)
    undoRequested = pyqtSignal()
    redoRequested = pyqtSignal()
    clearRequested = pyqtSignal()
    captureRequested = pyqtSignal()
    passToggled = pyqtSignal(bool)
    hideRequested = pyqtSignal()
    settingsRequested = pyqtSignal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = config
        self.setObjectName("toolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(stylesheet())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._button_size = max(MIN_BUTTON_SIZE, config.get_int("overlay/buttonSize"))
        self._requested_size = self._button_size
        self._color_index = 0
        self._width_index = 2
        self._side = config.get_str("overlay/toolbarSide")
        self._active_tool = Tool.PEN

        self._build()
        self._drag_origin: QPoint | None = None
        self._drag_pos: QPoint | None = None
        self._layout = self.layout()

    # -- construction ----------------------------------------------------
    def _build(self) -> None:
        size = self._button_size
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(6)

        grip = QLabel("\u22ee", self)
        grip.setObjectName("toolbarGrip")
        grip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        outer.addWidget(grip)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        self._btn_pen = _make_button("pen", size, "Kalem", checkable=True)
        self._btn_marker = _make_button("marker", size, "Foslu kalem", checkable=True)
        self._btn_eraser = _make_button("eraser", size, "Silgi", checkable=True)
        for i, btn in enumerate((self._btn_pen, self._btn_marker, self._btn_eraser)):
            btn.setChecked(i == 0)
            self._tool_group.addButton(btn, i)
            outer.addWidget(btn)
        self._tool_group.idClicked.connect(self._on_tool_clicked)

        outer.addWidget(self._separator())

        self._btn_color = _make_button("palette", size, "Renk")
        self._btn_color.clicked.connect(self._cycle_color)
        outer.addWidget(self._btn_color)

        self._btn_size = _make_button("size", size, "Kalınlık")
        self._btn_size.clicked.connect(self._cycle_width)
        outer.addWidget(self._btn_size)

        outer.addWidget(self._separator())

        self._btn_undo = _make_button("undo", size, "Geri al")
        self._btn_undo.clicked.connect(self.undoRequested.emit)
        outer.addWidget(self._btn_undo)

        self._btn_redo = _make_button("redo", size, "Yinele")
        self._btn_redo.clicked.connect(self.redoRequested.emit)
        outer.addWidget(self._btn_redo)

        self._btn_clear = _make_button("clear", size, "Temizle")
        self._btn_clear.clicked.connect(self.clearRequested.emit)
        outer.addWidget(self._btn_clear)

        outer.addWidget(self._separator())

        self._btn_capture = _make_button("screenshot", size, "Ekran görüntüsü")
        self._btn_capture.clicked.connect(self.captureRequested.emit)
        outer.addWidget(self._btn_capture)

        self._btn_pass = _make_button("passthrough", size, "Uygulamaya geç")
        self._btn_pass.setCheckable(True)
        self._btn_pass.clicked.connect(self.passToggled.emit)
        outer.addWidget(self._btn_pass)

        self._btn_settings = _make_button("settings", size, "Ayarlar")
        self._btn_settings.clicked.connect(self.settingsRequested.emit)
        outer.addWidget(self._btn_settings)

        self._btn_hide = _make_button("hide", size, "Gizle")
        self._btn_hide.clicked.connect(self.hideRequested.emit)
        outer.addWidget(self._btn_hide)

        self.adjustSize()
        self.sync_history(False, False)

    def _separator(self) -> QWidget:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,38); border: none;")
        return line

    # -- fitting -----------------------------------------------------------
    def _buttons(self) -> list[QPushButton]:
        return [
            self._btn_pen,
            self._btn_marker,
            self._btn_eraser,
            self._btn_color,
            self._btn_size,
            self._btn_undo,
            self._btn_redo,
            self._btn_clear,
            self._btn_capture,
            self._btn_pass,
            self._btn_settings,
            self._btn_hide,
        ]

    def fit_to_height(self, available: int) -> int:
        """Shrink buttons until the strip fits - a 1080-logical board is tight.

        Touch targets stay as large as possible; below 40 px the strip would be
        unusable, so instead the separators and grip are dropped.
        """
        available = max(MIN_BUTTON_SIZE * 4, int(available))
        size = self._requested_size
        spacing = MAX_SPACING
        while size > MIN_BUTTON_SIZE:
            self._apply_metrics(size, spacing, compact=False)
            if self.sizeHint().height() <= available:
                return size
            size -= 2
            spacing = MIN_SPACING if size < 52 else MAX_SPACING
        self._apply_metrics(MIN_BUTTON_SIZE, MIN_SPACING, compact=True)
        return MIN_BUTTON_SIZE

    def _apply_metrics(self, size: int, spacing: int, *, compact: bool) -> None:
        if self._button_size != size:
            self._button_size = size
            for btn in self._buttons():
                btn.setFixedSize(size, size)
                btn.setIconSize(QSize(int(size * ICON_SIZE_RATIO), int(size * ICON_SIZE_RATIO)))
        if self._layout is not None:
            self._layout.setSpacing(spacing)
        self._refresh_color_button()

    # -- placement --------------------------------------------------------
    def place(self, area: QSize) -> None:
        """Initial placement inside the overlay, honouring side + anchor."""
        self.fit_to_height(area.height() - 8)
        self.adjustSize()
        x = 12 if self._side == "left" else max(12, area.width() - self.width() - 12)
        span = max(0, area.height() - self.height())
        y = int(span * self._cfg.get_float("overlay/toolbarAnchor"))
        self.move(int(x), int(y))

    def snap_to_side(self, area: QSize, side: str | None = None) -> None:
        self._side = side or self._side
        self.fit_to_height(area.height() - 8)
        self.adjustSize()
        x = 12 if self._side == "left" else max(12, area.width() - self.width() - 12)
        span = max(0, area.height() - self.height())
        y = max(0, min(span, self.y()))
        self.move(int(x), int(y))
        self._cfg.set("overlay/toolbarSide", self._side)

    # -- dragging ---------------------------------------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.position().toPoint()
            self._drag_pos = self.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_origin is None or self._drag_pos is None:
            super().mouseMoveEvent(event)
            return
        delta = event.position().toPoint() - self._drag_origin
        self.move(self._drag_pos + delta)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_origin is not None:
            self._drag_origin = None
            self._drag_pos = None
            parent = self.parentWidget()
            if parent is not None:
                area = parent.size()
                side = "left" if self.x() + self.width() / 2 < area.width() / 2 else "right"
                self.snap_to_side(area, side)
                self._cfg.set(
                    "overlay/toolbarAnchor",
                    round(self.y() / max(1, area.height() - self.height()), 3),
                )
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # -- state ------------------------------------------------------------
    @property
    def active_tool(self) -> Tool:
        return self._active_tool

    @property
    def current_color(self) -> str:
        return PALETTE[self._color_index % len(PALETTE)]

    @property
    def current_width(self) -> float:
        if self._active_tool is Tool.ERASER:
            return ERASER_SIZES[self._width_index % len(ERASER_SIZES)]
        return PEN_WIDTHS[self._width_index % len(PEN_WIDTHS)]

    def _on_tool_clicked(self, index: int) -> None:
        try:
            tool = _TOOLS[index]
        except IndexError:
            return
        self._active_tool = tool
        self._refresh_color_button()
        self.toolChanged.emit(tool)

    def _cycle_color(self) -> None:
        self._color_index = (self._color_index + 1) % len(PALETTE)
        self._refresh_color_button()
        self.colorChanged.emit(self.current_color)

    def _cycle_width(self) -> None:
        self._width_index = (self._width_index + 1) % len(PEN_WIDTHS)
        self._refresh_color_button()
        self.widthChanged.emit(self.current_width)

    def _refresh_color_button(self) -> None:
        if self._btn_color is None:
            return
        if self._active_tool is Tool.ERASER:
            self._btn_color.setIcon(
                icons.make_brush_icon(
                    "#c9ced8",
                    self.current_width,
                    int(self._button_size * ICON_SIZE_RATIO),
                    tool="eraser",
                )
            )
            self._btn_color.setToolTip("Silgi boyutu")
            return
        self._btn_color.setIcon(
            icons.make_brush_icon(
                self.current_color, self.current_width, int(self._button_size * ICON_SIZE_RATIO)
            )
        )
        self._btn_color.setToolTip(
            f"Renk: {self.current_color}  ·  Genişlik: {self.current_width:g}"
        )

    def sync_history(self, can_undo: bool, can_redo: bool) -> None:
        self._btn_undo.setEnabled(can_undo)
        self._btn_redo.setEnabled(can_redo)

    def set_active_tool(self, tool: Tool) -> None:
        """Reflect a tool chosen elsewhere (config, shortcut, canvas) in the strip."""
        if tool not in _TOOLS:
            return
        self._active_tool = tool
        self._tool_group.button(_TOOLS.index(tool)).setChecked(True)
        self._refresh_color_button()

    def set_pass_state(self, enabled: bool) -> None:
        self._btn_pass.setChecked(enabled)

    def set_button_size(self, size: int) -> None:
        self._requested_size = max(MIN_BUTTON_SIZE, size)
        self._apply_metrics(self._requested_size, MAX_SPACING, compact=False)
        self.adjustSize()

    def side(self) -> str:
        return self._side


__all__ = ["Toolbar"]
