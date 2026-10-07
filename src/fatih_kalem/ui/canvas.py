"""The drawing surface.

Owns three things: an offscreen ``ink`` layer holding every committed stroke, a
patch-based undo stack, and the pointer/touch/stylus router. The live stroke is
painted straight onto the widget (never into the layer) so a teacher drawing a
long line cannot trigger an undo snapshot per event.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QEventPoint,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QTabletEvent,
    QTouchEvent,
)
from PyQt6.QtWidgets import QWidget

from ..config import Config
from ..core.models import ClearAction, Document, PenStyle, PenType, StrokeAction, Tool
from ..core.stroke_engine import StrokeBuilder, render_stroke, stroke_bounds
from ..core.undo import PatchStack

INK_FORMAT = QImage.Format.Format_ARGB32_Premultiplied

#: Extra pixels around a stroke so antialiasing is never clipped.
ANTIALIAS_PAD = 3


class Canvas(QWidget):
    """Transparent, full-screen drawing area."""

    inkChanged = pyqtSignal()
    historyChanged = pyqtSignal()
    strokeFinished = pyqtSignal()
    hintChanged = pyqtSignal(str)

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = config

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.document = Document()
        self._ink = QImage()
        self._undo = PatchStack()

        self._tool = Tool.PEN
        self._color = QColor(self._cfg.get_str("pen/color"))
        self._width = self._cfg.get_float("pen/width")
        self._pen_type = PenType(self._cfg.get_str("pen/penType"))
        self._marker_opacity = self._cfg.get_float("pen/markerOpacity")
        self._eraser_size = self._cfg.get_float("eraser/size")

        self._board_color: QColor | None = None
        self._hint = ""

        self._builder: StrokeBuilder | None = None
        self._source: str | None = None
        self._live_rect = QRect()
        self._press_pos: QPoint | None = None
        self._pass_mode = False

    # -- geometry / layer -------------------------------------------------
    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        size = self.size()
        if size.isEmpty() or self._ink.size() == size:
            return
        self._ink = QImage(size, INK_FORMAT)
        self._ink.fill(Qt.GlobalColor.transparent)
        self._undo.clear()
        self.document.clear()
        self._live_rect = QRect()

    def _ensure_layer(self) -> None:
        if self._ink.size() != self.size() and not self.size().isEmpty():
            self._ink = QImage(self.size(), INK_FORMAT)
            self._ink.fill(Qt.GlobalColor.transparent)
            self._undo.clear()
            self.document.clear()

    # -- public state -----------------------------------------------------
    @property
    def tool(self) -> Tool:
        return self._tool

    @property
    def color(self) -> QColor:
        return QColor(self._color)

    @property
    def width(self) -> float:
        return self._width

    @property
    def pen_type(self) -> PenType:
        return self._pen_type

    @property
    def eraser_size(self) -> float:
        return self._eraser_size

    @property
    def pass_mode(self) -> bool:
        return self._pass_mode

    def can_undo(self) -> bool:
        return self._undo.can_undo

    def can_redo(self) -> bool:
        return self._undo.can_redo

    def is_empty(self) -> bool:
        return self.document.strokes == [] or self._ink.isNull()

    def ink_image(self) -> QImage:
        self._ensure_layer()
        return self._ink.copy()

    def undo_bytes(self) -> int:
        return self._undo.bytes_used

    def set_tool(self, tool: Tool) -> None:
        if tool is not self._tool:
            self._tool = tool

    def set_color(self, color: QColor | str) -> None:
        self._color = theme_color(color)

    def set_width(self, width: float) -> None:
        self._width = max(0.5, float(width))

    def set_pen_type(self, pen_type: PenType) -> None:
        self._pen_type = pen_type

    def set_eraser_size(self, size: float) -> None:
        self._eraser_size = max(1.0, float(size))

    def set_marker_opacity(self, opacity: float) -> None:
        self._marker_opacity = max(0.05, min(1.0, float(opacity)))

    def set_board_color(self, color: QColor | str | None) -> None:
        if color is None:
            self._board_color = None
        else:
            c = theme_color(color)
            c.setAlpha(255)
            self._board_color = c
        self.update()

    def set_hint(self, text: str) -> None:
        if text != self._hint:
            self._hint = text
            self.hintChanged.emit(text)
            self.update()

    def set_pass_mode(self, enabled: bool) -> None:
        """When enabled the overlay lets clicks through and hides the ink."""
        self._pass_mode = bool(enabled)
        # The X11 input region already routes touches outside the toolbar to the
        # application below, so only mouse transparency is toggled here.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._pass_mode)
        self.update()

    def cancel_stroke(self) -> None:
        self._builder = None
        self._source = None
        self._live_rect = QRect()
        self.update()

    # -- style ------------------------------------------------------------
    def _style(self) -> PenStyle:
        if self._tool is Tool.ERASER:
            return PenStyle(tool=Tool.ERASER, color=QColor(0, 0, 0), width=self._eraser_size)
        if self._tool is Tool.MARKER:
            return PenStyle(
                tool=Tool.MARKER,
                color=QColor(self._color),
                width=max(self._width, 12.0),
                pen_type=PenType.SOLID,
                opacity=self._marker_opacity,
            )
        return PenStyle(
            tool=Tool.PEN, color=QColor(self._color), width=self._width, pen_type=self._pen_type
        )

    def _pressure_options(self) -> dict[str, float | bool]:
        return {
            "pressure_enabled": self._cfg.get_bool("input/pressureEnabled"),
            "gamma": self._cfg.get_float("input/pressureGamma"),
            "min_factor": self._cfg.get_float("input/pressureMinFactor"),
        }

    # -- history ----------------------------------------------------------
    def _clamped(self, rect: QRect) -> QRect:
        self._ensure_layer()
        r = rect.intersected(self._ink.rect())
        if r.width() <= 0 or r.height() <= 0:
            return QRect()
        return r

    def _apply_patch(self, rect: QRect, image: QImage) -> None:
        """Paste an undo/redo patch back into the ink layer.

        ``CompositionMode_Source`` replaces the region instead of blending over
        it: a patch is a *snapshot*, so the transparent parts must erase the ink
        that a stroke just added - plain SourceOver would leave it behind.
        """
        painter = QPainter(self._ink)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawImage(rect.topLeft(), image)
        painter.end()

    def undo(self) -> bool:
        step = self._undo.undo()
        if step is None:
            return False
        rect, image = step
        rect = self._clamped(rect)
        if rect.isEmpty():
            return True
        self._apply_patch(rect, image)
        # The cursor moved back, so the reverted step now sits in the redo slot.
        meta = self._undo.peek_redo_meta()
        if meta is not None:
            meta.undo(self.document)
        self.update(rect)
        self.historyChanged.emit()
        self.inkChanged.emit()
        return True

    def redo(self) -> bool:
        step = self._undo.redo()
        if step is None:
            return False
        rect, image = step
        rect = self._clamped(rect)
        if rect.isEmpty():
            return True
        self._apply_patch(rect, image)
        # The cursor moved forward, so the replayed step is the last applied one.
        meta = self._undo.peek_undo_meta()
        if meta is not None:
            meta.redo(self.document)
        self.update(rect)
        self.historyChanged.emit()
        self.inkChanged.emit()
        return True

    def clear_all(self) -> bool:
        self._ensure_layer()
        rect = self._clamped(self._ink.rect())
        if rect.isEmpty() or self.is_empty():
            return False
        before = self._ink.copy(rect)
        snapshot = list(self.document.strokes)
        self._ink.fill(Qt.GlobalColor.transparent)
        after = self._ink.copy(rect)
        self._undo.record_cropped(rect, before, after, ClearAction(snapshot))
        self.document.clear()
        self.update(rect)
        self.historyChanged.emit()
        self.inkChanged.emit()
        return True

    # -- painting ---------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        if self._board_color is not None:
            painter.fillRect(self.rect(), self._board_color)
        if not self._ink.isNull():
            painter.drawImage(self.rect().topLeft(), self._ink)

        if self._builder is not None and not self._builder.is_empty:
            style = self._builder.style
            if style.is_eraser:
                # Punch the live eraser through to the desktop underneath, so the
                # teacher sees the real result while rubbing, not a mock overlay.
                painter.save()
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                render_stroke(painter, self._builder.points, style, **self._pressure_options())
                painter.restore()
            else:
                render_stroke(painter, self._builder.points, style, **self._pressure_options())

        if self._hint and self.is_empty():
            self._paint_hint(painter)
        painter.end()

    def _paint_hint(self, painter: QPainter) -> None:
        rect = self.rect()
        pen = QPen(QColor(30, 34, 42, 90))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawText(
            rect.adjusted(0, 0, 0, -int(rect.height() * 0.18)),
            Qt.AlignmentFlag.AlignCenter,
            self._hint,
        )

    # -- pointer plumbing --------------------------------------------------
    def _begin(self, pos: QPointF, pressure: float, source: str, tilt: float = 0.0) -> None:
        if self._source is not None or self._pass_mode:
            return
        self._ensure_layer()
        self._source = source
        self._press_pos = QPoint(int(pos.x()), int(pos.y()))
        builder = StrokeBuilder(
            self._style(),
            min_distance=self._cfg.get_float("input/minStrokeDistance"),
            smoothing=self._cfg.get_float("input/smoothing"),
        )
        builder.add(pos.x(), pos.y(), pressure, tilt)
        self._builder = builder
        self._live_rect = stroke_bounds(builder.points, builder.style.width).toAlignedRect()
        self.update(self._live_rect)

    def _extend(self, pos: QPointF, pressure: float, tilt: float = 0.0) -> None:
        builder = self._builder
        if builder is None or self._pass_mode:
            return
        builder.add(pos.x(), pos.y(), pressure, tilt)
        rect = stroke_bounds(builder.points, builder.style.width).toAlignedRect()
        self._live_rect = self._live_rect.united(rect)
        self.update(rect)

    def _end(self) -> None:
        builder = self._builder
        self._builder = None
        self._source = None
        if builder is None:
            return
        self._ensure_layer()

        stroke = builder.build()
        live = self._live_rect
        self._live_rect = QRect()
        if stroke is None:
            self.update(live)
            return

        style = stroke.style
        rect = self._clamped(stroke_bounds(stroke.points, style.width).toAlignedRect())
        if rect.isEmpty():
            self.update(live)
            return

        before = self._ink.copy(rect)
        painter = QPainter(self._ink)
        render_stroke(painter, stroke.points, style, **self._pressure_options())
        painter.end()
        after = self._ink.copy(rect)

        # Eraser strokes mutate pixels only; the serialisable list keeps pen and
        # shape strokes.
        meta: object | None = None
        if not style.is_eraser:
            self.document.add(stroke)
            meta = StrokeAction(stroke)
        self._undo.record_cropped(rect, before, after, meta)

        self.update(rect.united(live))
        self.historyChanged.emit()
        self.inkChanged.emit()
        self.strokeFinished.emit()

    # -- Qt events ---------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._begin(event.position(), 1.0, "mouse")

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._source == "mouse" and event.buttons() & Qt.MouseButton.LeftButton:
            self._extend(event.position(), 1.0)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._source == "mouse" and event.button() == Qt.MouseButton.LeftButton:
            self._extend(event.position(), 1.0)
            self._end()
        else:
            super().mouseReleaseEvent(event)

    # -- touch -------------------------------------------------------------
    def touchEvent(self, event: QTouchEvent) -> None:  # noqa: N802
        points = event.touchPoints()
        active = [p for p in points if p.state() == QEventPoint.State.Pressed]
        released = [p for p in points if p.state() == QEventPoint.State.Released]

        if event.type() == QTouchEvent.Type.TouchBegin and active and self._source is None:
            # Multi-finger input is reserved for gestures (M4); drawing stays
            # single-finger so a stray palm cannot scribble over the board.
            if len(points) == 1:
                p = active[0]
                self._begin(p.position(), _touch_pressure(p), "touch")
            return

        if self._source != "touch":
            return

        if event.type() == QTouchEvent.Type.TouchUpdate and active:
            p = active[0]
            self._extend(p.position(), _touch_pressure(p), _touch_tilt(p))
        elif event.type() == QTouchEvent.Type.TouchEnd:
            if released:
                p = released[0]
                self._extend(p.position(), _touch_pressure(p), _touch_tilt(p))
            self._end()
        elif event.type() == QTouchEvent.Type.TouchCancel:
            self.cancel_stroke()

    def tabletEvent(self, event: QTabletEvent) -> None:  # noqa: N802
        kind = event.type()
        pressure = _tablet_pressure(event)
        tilt = float(event.tiltX())
        if kind == QTabletEvent.Type.TabletPress:
            self._begin(event.position(), pressure, "pen", tilt)
        elif kind == QTabletEvent.Type.TabletMove and self._source == "pen":
            self._extend(event.position(), pressure, tilt)
        elif kind == QTabletEvent.Type.TabletRelease and self._source == "pen":
            self._extend(event.position(), pressure, tilt)
            self._end()
        else:
            super().tabletEvent(event)


def theme_color(value: QColor | str) -> QColor:
    if isinstance(value, QColor):
        return QColor(value)
    c = QColor(value)
    return c if c.isValid() else QColor("#000000")


def _touch_pressure(point) -> float:
    """Touch panels often report 0 or 1; treat missing pressure as full."""
    try:
        p = float(point.pressure())
    except (TypeError, ValueError):
        return 1.0
    return p if p > 0.0 else 1.0


def _touch_tilt(point) -> float:
    """``QTouchEvent.TouchPoint.angle()`` is Qt5-era; QEventPoint has no tilt."""
    getter = getattr(point, "angle", None)
    if getter is None:
        return 0.0
    try:
        return float(getter())
    except (TypeError, ValueError):
        return 0.0


def _tablet_pressure(event: QTabletEvent) -> float:
    try:
        p = float(event.pressure())
    except (TypeError, ValueError):
        return 1.0
    return p if p > 0.0 else 1.0


__all__ = ["Canvas", "INK_FORMAT", "ANTIALIAS_PAD", "theme_color"]
