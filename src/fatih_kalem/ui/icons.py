"""Icons drawn with QPainter.

No SVG runtime and no binary assets: the toolbar stays crisp at 4K (it is simply
re-rendered at the requested device size) and the repository stays text-only.
Every glyph is drawn inside a 24x24 viewbox.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

VIEWBOX = 24.0

PainterFn = Callable[[QPainter, QColor], None]


def _stroke(painter: QPainter, color: QColor, width: float = 2.1) -> None:
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _fill(painter: QPainter, color: QColor, alpha: float = 1.0) -> None:
    c = QColor(color)
    c.setAlphaF(alpha)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(c))


# --------------------------------------------------------------------------
# glyphs
# --------------------------------------------------------------------------
def _pen(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.2)
    p.drawLine(QPointF(6.2, 17.8), QPointF(17.6, 6.4))
    p.drawLine(QPointF(13.4, 10.6), QPointF(17.6, 6.4))
    _fill(p, c)
    p.drawPolygon(QPolygonF([QPointF(3.3, 20.7), QPointF(6.2, 17.8), QPointF(7.5, 19.1)]))


def _marker(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 5.0)
    p.drawLine(QPointF(7.4, 16.6), QPointF(15.6, 8.4))
    _stroke(p, c, 2.0)
    p.drawLine(QPointF(11.4, 12.6), QPointF(14.0, 10.0))
    _fill(p, c)
    p.drawPolygon(QPolygonF([QPointF(3.4, 20.6), QPointF(7.0, 17.0), QPointF(9.4, 19.4)]))


def _eraser(p: QPainter, c: QColor) -> None:
    body = QPolygonF(
        [
            QPointF(4.2, 15.6),
            QPointF(15.4, 4.4),
            QPointF(20.2, 9.2),
            QPointF(9.0, 20.4),
        ]
    )
    _fill(p, c, 0.45)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(body)
    _stroke(p, c, 2.1)
    p.drawPolygon(body)
    p.drawLine(QPointF(9.4, 20.2), QPointF(14.6, 15.0))


def _undo(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.2)
    p.drawArc(QRectF(4.0, 4.0, 16.0, 16.0), int(270 * 16), int(270 * 16))
    p.drawLine(QPointF(4.6, 12.0), QPointF(9.6, 12.0))
    p.drawLine(QPointF(4.6, 12.0), QPointF(4.6, 7.0))


def _redo(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.2)
    p.drawArc(QRectF(4.0, 4.0, 16.0, 16.0), int(90 * 16), int(270 * 16))
    p.drawLine(QPointF(19.4, 12.0), QPointF(14.4, 12.0))
    p.drawLine(QPointF(19.4, 12.0), QPointF(19.4, 7.0))


def _clear(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.1)
    p.drawLine(QPointF(3.6, 6.4), QPointF(20.4, 6.4))
    p.drawLine(QPointF(9.0, 3.8), QPointF(15.0, 3.8))
    p.drawPolygon(
        QPolygonF([QPointF(6.4, 8.6), QPointF(17.6, 8.6), QPointF(16.4, 20.4), QPointF(7.6, 20.4)])
    )
    p.drawLine(QPointF(10.2, 11.4), QPointF(10.6, 17.8))
    p.drawLine(QPointF(13.8, 11.4), QPointF(13.4, 17.8))


def _screenshot(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.1)
    p.drawPolygon(
        QPolygonF(
            [
                QPointF(3.2, 8.4),
                QPointF(7.8, 8.4),
                QPointF(9.4, 5.4),
                QPointF(14.6, 5.4),
                QPointF(16.2, 8.4),
                QPointF(20.8, 8.4),
            ]
        )
    )
    p.drawRoundedRect(QRectF(3.2, 8.4, 17.6, 11.8), 2.6, 2.6)
    p.drawEllipse(QPointF(12.0, 14.3), 3.6, 3.6)


def _passthrough(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.1)
    p.drawRoundedRect(QRectF(3.0, 4.2, 18.0, 15.6), 2.6, 2.6)
    p.drawLine(QPointF(12.0, 7.6), QPointF(12.0, 15.2))
    p.drawLine(QPointF(8.9, 12.2), QPointF(12.0, 15.2))
    p.drawLine(QPointF(15.1, 12.2), QPointF(12.0, 15.2))


def _hide(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.2)
    p.drawLine(QPointF(5.0, 8.6), QPointF(12.0, 15.0))
    p.drawLine(QPointF(12.0, 15.0), QPointF(19.0, 8.6))
    p.drawLine(QPointF(4.6, 19.4), QPointF(19.4, 19.4))


def _settings(p: QPainter, c: QColor) -> None:
    centre = QPointF(12.0, 12.0)
    _stroke(p, c, 2.1)
    p.drawEllipse(centre, 4.2, 4.2)
    for i in range(8):
        a = math.radians(i * 45.0)
        p.drawLine(
            QPointF(centre.x() + 6.0 * math.cos(a), centre.y() + 6.0 * math.sin(a)),
            QPointF(centre.x() + 8.8 * math.cos(a), centre.y() + 8.8 * math.sin(a)),
        )
    _fill(p, c)
    p.drawEllipse(centre, 1.7, 1.7)


def _palette(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.0)
    p.drawEllipse(QPointF(12.0, 12.0), 8.6, 8.6)
    _fill(p, c, 0.9)
    for x, y in ((9.0, 8.6), (14.6, 8.6), (9.0, 14.4), (14.6, 14.4)):
        p.drawEllipse(QPointF(x, y), 1.5, 1.5)


def _size(p: QPainter, c: QColor) -> None:
    _fill(p, c)
    p.drawEllipse(QPointF(6.4, 17.6), 1.7, 1.7)
    p.drawEllipse(QPointF(11.6, 12.4), 3.1, 3.1)
    p.drawEllipse(QPointF(17.8, 6.2), 4.6, 4.6)


def _shapes(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.1)
    p.drawRect(QRectF(4.0, 4.0, 9.0, 9.0))
    p.drawEllipse(QPointF(15.8, 15.8), 4.6, 4.6)


def _pages(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.1)
    p.drawRoundedRect(QRectF(3.6, 7.2, 13.0, 13.2), 2.2, 2.2)
    p.drawRoundedRect(QRectF(7.4, 3.6, 13.0, 13.2), 2.2, 2.2)


def _curtain(p: QPainter, c: QColor) -> None:
    _fill(p, c, 0.35)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(QRectF(2.6, 3.6, 18.8, 16.8))
    _stroke(p, c, 2.0)
    p.drawRect(QRectF(2.6, 3.6, 18.8, 16.8))
    _fill(p, c)
    p.drawRoundedRect(QRectF(8.0, 8.6, 8.0, 7.0), 1.6, 1.6)


def _library(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.1)
    p.drawRect(QRectF(3.4, 4.6, 17.2, 14.8))
    _fill(p, c)
    p.drawEllipse(QPointF(8.6, 9.4), 1.8, 1.8)
    _stroke(p, c, 2.1)
    p.drawPolyline(
        QPolygonF(
            [
                QPointF(5.0, 17.4),
                QPointF(10.4, 11.6),
                QPointF(14.2, 15.4),
                QPointF(16.4, 13.2),
                QPointF(19.4, 17.0),
            ]
        )
    )


def _info(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.0)
    p.drawEllipse(QPointF(12.0, 12.0), 8.6, 8.6)
    _fill(p, c)
    p.drawEllipse(QPointF(12.0, 7.6), 1.2, 1.2)
    _stroke(p, c, 2.0)
    p.drawLine(QPointF(12.0, 11.0), QPointF(12.0, 16.6))


def _grid(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 1.6)
    p.drawRect(QRectF(3.4, 3.4, 17.2, 17.2))
    p.drawLine(QPointF(9.1, 3.4), QPointF(9.1, 20.6))
    p.drawLine(QPointF(14.9, 3.4), QPointF(14.9, 20.6))
    p.drawLine(QPointF(3.4, 9.1), QPointF(20.6, 9.1))
    p.drawLine(QPointF(3.4, 14.9), QPointF(20.6, 14.9))


def _save(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.1)
    p.drawPolyline(
        QPolygonF(
            [
                QPointF(4.4, 19.6),
                QPointF(4.4, 4.4),
                QPointF(16.0, 4.4),
                QPointF(19.6, 8.0),
                QPointF(19.6, 19.6),
                QPointF(4.4, 19.6),
            ]
        )
    )
    p.drawRect(QRectF(7.6, 4.4, 8.8, 5.2))
    p.drawRect(QRectF(7.2, 13.4, 9.6, 6.2))


REGISTRY: dict[str, PainterFn] = {
    "pen": _pen,
    "marker": _marker,
    "eraser": _eraser,
    "undo": _undo,
    "redo": _redo,
    "clear": _clear,
    "screenshot": _screenshot,
    "passthrough": _passthrough,
    "hide": _hide,
    "settings": _settings,
    "palette": _palette,
    "size": _size,
    "shapes": _shapes,
    "pages": _pages,
    "curtain": _curtain,
    "library": _library,
    "info": _info,
    "grid": _grid,
    "save": _save,
}


def render(name: str, size: int, color: str | QColor) -> QPixmap:
    glyph = REGISTRY.get(name)
    pixmap = QPixmap(max(1, size), max(1, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    if glyph is None:
        return pixmap
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(size / VIEWBOX, size / VIEWBOX)
    glyph(painter, QColor(color))
    painter.end()
    return pixmap


def make_icon(name: str, size: int = 32, color: str | QColor = "#f2f4f8") -> QIcon:
    return QIcon(render(name, size, color))


def brush_pixmap(
    color: str | QColor,
    width: float,
    size: int,
    *,
    tool: str = "pen",
    padding_ratio: float = 0.22,
) -> QPixmap:
    """A diagonal stroke preview - what the pen button actually looks like."""
    pixmap = QPixmap(max(1, size), max(1, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    inset = size * padding_ratio
    c = QColor(color)
    if c.lightness() > 200 and not c.alpha():  # keep light inks visible on the chip
        c = QColor("#1b1d22")

    if tool == "eraser":
        pen = QPen(QColor("#c9ced8"))
        pen.setWidthF(max(2.0, size * 0.16))
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(inset, size - inset), QPointF(size - inset, inset))
    else:
        pen = QPen(c)
        pen.setWidthF(max(1.5, width))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(inset, size - inset), QPointF(size - inset, inset))
    painter.end()
    return pixmap


def make_brush_icon(color: str | QColor, width: float, size: int, *, tool: str = "pen") -> QIcon:
    return QIcon(brush_pixmap(color, width, size, tool=tool))


__all__ = ["REGISTRY", "render", "make_icon", "brush_pixmap", "make_brush_icon"]
