"""Stroke sampling, smoothing and rendering.

Rendering strategy for 4K boards: a committed stroke is rasterised into the ink
layer once (see :mod:`fatih_kalem.ui.canvas`); only the in-progress stroke is
repainted per pointer event, and it is drawn from an incremental decimated path
so the cost is proportional to the *new* segment, not to the whole board.
"""

from __future__ import annotations

import math
import time

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
)

from .models import PEN_TYPES, PenStyle, Stroke, StrokePoint, Tool

#: A single tap should still leave a visible dot.
DOT_RADIUS_SCALE = 0.5
#: A dash gap must be at least this multiple of the nib width to stay visible.
MIN_GAP_RATIO = 1.15


class StrokeBuilder:
    """Incrementally samples pointer input into a decimated, smoothed polyline."""

    __slots__ = (
        "style",
        "min_distance",
        "smoothing",
        "_points",
        "_smooth",
        "_has",
        "_last_time",
        "_count",
    )

    def __init__(
        self, style: PenStyle, *, min_distance: float = 1.5, smoothing: float = 0.45
    ) -> None:
        self.style = style
        self.min_distance = max(0.0, float(min_distance))
        self.smoothing = min(0.95, max(0.0, float(smoothing)))
        self._points: list[StrokePoint] = []
        self._smooth: StrokePoint | None = None
        self._has = False
        self._last_time = 0
        self._count = 0

    @property
    def points(self) -> list[StrokePoint]:
        return self._points

    @property
    def is_empty(self) -> bool:
        return not self._points

    def add(
        self, x: float, y: float, pressure: float = 1.0, tilt: float = 0.0, t: int | None = None
    ) -> None:
        now = int(t if t is not None else time.monotonic() * 1000)
        if self._last_time:
            now = max(now, self._last_time + 1)
        self._last_time = now

        raw = StrokePoint(float(x), float(y), float(pressure), float(tilt), now)
        if not self._has:
            self._smooth = raw
            self._has = True
            self._points.append(raw)
            self._count += 1
            return

        s = self._smooth
        assert s is not None
        alpha = 1.0 - self.smoothing
        filtered = StrokePoint(
            s.x + (raw.x - s.x) * alpha,
            s.y + (raw.y - s.y) * alpha,
            raw.pressure,
            s.tilt + (raw.tilt - s.tilt) * alpha,
            now,
        )
        self._smooth = filtered
        self._count += 1
        if filtered.distance_to(self._points[-1]) >= self.min_distance:
            self._points.append(filtered)

    def flush(self) -> list[StrokePoint]:
        """Append the final interpolated position (so the stroke ends exactly)."""
        if self._has and self._smooth is not None:
            last = self._points[-1]
            s = self._smooth
            if math.hypot(s.x - last.x, s.y - last.y) > 0.01:
                self._points.append(s)
        return self._points

    def build(self) -> Stroke | None:
        pts = self.flush()
        if not pts:
            return None
        return Stroke(points=list(pts), style=self.style)


def pressure_to_width(
    base_width: float,
    pressure: float,
    *,
    enabled: bool = True,
    gamma: float = 1.4,
    min_factor: float = 0.35,
) -> float:
    """Map stylus pressure (0..1) onto a pen width.

    ``enabled=False`` (or a device that reports no pressure) yields ``base_width``.
    """
    if not enabled:
        return base_width
    p = max(0.0, min(1.0, pressure))
    shaped = (p**gamma) if gamma else p
    factor = min_factor + (1.0 - min_factor) * shaped
    return max(0.5, base_width * factor)


def has_pressure(points: list[StrokePoint], epsilon: float = 1e-4) -> bool:
    """True when the device reported anything other than constant full pressure."""
    if not points:
        return False
    lo = min(p.pressure for p in points)
    hi = max(p.pressure for p in points)
    if hi <= epsilon:
        return False
    return (hi - lo) > epsilon or hi < 1.0 - epsilon


def width_profile(
    points: list[StrokePoint],
    style: PenStyle,
    *,
    pressure_enabled: bool = True,
    gamma: float = 1.4,
    min_factor: float = 0.35,
) -> list[float]:
    use_pressure = pressure_enabled and has_pressure(points)
    return [
        pressure_to_width(
            style.width, p.pressure, enabled=use_pressure, gamma=gamma, min_factor=min_factor
        )
        for p in points
    ]


def _make_pen(style: PenStyle, width: float, color: QColor | None = None) -> QPen:
    """Solid round-capped pen.

    Dash patterns are *not* applied here: a pen-level pattern restarts on every
    ``drawLine`` call, so dashes are produced along the centre line instead (see
    :func:`_render_dashed`).
    """
    pen = QPen(color if color is not None else style.color)
    pen.setWidthF(max(0.5, width))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCosmetic(False)
    pen.setStyle(Qt.PenStyle.SolidLine)
    return pen


def polyline_path(points: list[StrokePoint]) -> QPainterPath:
    """Quadratic-smoothed centre-line path, used for hit-testing and bounding."""
    path = QPainterPath()
    if not points:
        return path
    path.moveTo(points[0].x, points[0].y)
    if len(points) == 1:
        return path
    for i in range(1, len(points)):
        prev = points[i - 1]
        cur = points[i]
        mid = QPointF((prev.x + cur.x) / 2.0, (prev.y + cur.y) / 2.0)
        path.quadTo(QPointF(prev.x, prev.y), mid)
    path.lineTo(points[-1].x, points[-1].y)
    return path


def render_stroke(
    painter: QPainter,
    points: list[StrokePoint],
    style: PenStyle,
    *,
    pressure_enabled: bool = True,
    gamma: float = 1.4,
    min_factor: float = 0.35,
) -> None:
    """Draw ``points`` with ``style`` using the current painter transform.

    Semi-transparent styles are rasterised through a scratch layer so that the
    overlapping joins of a single stroke do not accumulate alpha.
    """
    if not points:
        return

    if style.is_eraser:
        _render_eraser(painter, points, style.width)
        return

    opaque = style.opacity >= 0.999
    scratch: QImage | None = None
    if not opaque:
        area = _stroke_area(points, style.width).toAlignedRect()
        scratch = QImage(area.size(), QImage.Format.Format_ARGB32_Premultiplied)
        scratch.fill(Qt.GlobalColor.transparent)
        sp = QPainter(scratch)
        sp.translate(-area.topLeft())
        _render_opaque(sp, points, style, pressure_enabled, gamma, min_factor)
        sp.end()
        prev_op = painter.opacity()
        painter.setOpacity(prev_op * style.opacity)
        painter.drawImage(area.topLeft(), scratch)
        painter.setOpacity(prev_op)
        return

    _render_opaque(painter, points, style, pressure_enabled, gamma, min_factor)


def _draw_polyline(
    painter: QPainter, pts: list[tuple[float, float]], widths: list[float], style: PenStyle
) -> None:
    """Draw consecutive points, interpolating the pen width between them."""
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        if x0 == x1 and y0 == y1:
            continue
        painter.setPen(_make_pen(style, widths[i]))
        painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))


def _render_dashed(
    painter: QPainter, points: list[StrokePoint], style: PenStyle, widths: list[float]
) -> None:
    """Walk the dash pattern along the centre line, then draw each run.

    Drawing each input segment with its own ``CustomDashLine`` pen would restart
    the pattern every few pixels and produce a solid line; measuring arc length
    along the centre line is what makes ``dashed`` and the Arabic ``broken`` nib
    actually look dashed.
    """
    pattern = PEN_TYPES.get(style.pen_type.value) or []
    if len(pattern) < 2:
        _render_opaque(painter, points, style, True, 1.0, 0.0)
        return

    segments: list[tuple[float, float, float, float, float, int]] = []
    for i in range(1, len(points)):
        p0, p1 = points[i - 1], points[i]
        dx, dy = p1.x - p0.x, p1.y - p0.y
        length = math.hypot(dx, dy)
        if length > 1e-9:
            segments.append((p0.x, p0.y, dx, dy, length, i))
    if not segments:
        return

    on_len = abs(pattern[0])
    # Round caps extend width/2 past each end, so an off phase shorter than the
    # nib width would be swallowed and the stroke would come out solid.
    off_len = max(abs(pattern[1]), style.width * MIN_GAP_RATIO)
    state_on = True
    remaining = on_len if on_len > 0 else off_len
    run: list[tuple[float, float]] = []
    run_w: list[float] = []
    eps = 1e-6

    for x0, y0, dx, dy, length, idx in segments:
        w0, w1 = widths[idx - 1], widths[idx]
        travelled = 0.0
        while travelled < length - eps:
            take = min(remaining, length - travelled)
            t_a = travelled / length
            t_b = (travelled + take) / length
            if state_on:
                if not run:
                    run.append((x0 + dx * t_a, y0 + dy * t_a))
                    run_w.append(w0 + (w1 - w0) * t_a)
                run.append((x0 + dx * t_b, y0 + dy * t_b))
                run_w.append(w0 + (w1 - w0) * t_b)
            travelled += take
            remaining -= take
            if remaining <= eps:
                if state_on and len(run) > 1:
                    _draw_polyline(painter, run, run_w, style)
                run, run_w = [], []
                state_on = not state_on
                remaining = on_len if state_on else off_len
                if remaining <= eps:  # a zero-length phase would loop forever
                    remaining = eps * 10
    if state_on and len(run) > 1:
        _draw_polyline(painter, run, run_w, style)


def _render_opaque(
    painter: QPainter,
    points: list[StrokePoint],
    style: PenStyle,
    pressure_enabled: bool,
    gamma: float,
    min_factor: float,
) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if len(points) == 1:
        w = pressure_to_width(style.width, points[0].pressure, enabled=False)
        painter.setPen(_make_pen(style, w))
        painter.drawEllipse(points[0].to_point_f(), w * DOT_RADIUS_SCALE, w * DOT_RADIUS_SCALE)
        return

    widths = width_profile(
        points, style, pressure_enabled=pressure_enabled, gamma=gamma, min_factor=min_factor
    )
    if PEN_TYPES.get(style.pen_type.value):
        _render_dashed(painter, points, style, widths)
        return
    _draw_polyline(painter, [(p.x, p.y) for p in points], widths, style)


def _render_eraser(painter: QPainter, points: list[StrokePoint], size: float) -> None:
    """Pixel eraser: punches a round-capped channel out of the ink layer."""
    previous_mode = painter.compositionMode()
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    # Colour is irrelevant in clear mode, but QPen still wants one.
    pen = QPen(QColor(255, 255, 255, 0))
    pen.setWidthF(max(1.0, size))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if len(points) == 1:
        painter.drawEllipse(points[0].to_point_f(), size / 2.0, size / 2.0)
    else:
        for i in range(1, len(points)):
            painter.drawLine(points[i - 1].to_point_f(), points[i].to_point_f())
    painter.setCompositionMode(previous_mode)


def _stroke_area(points: list[StrokePoint], width: float) -> QRectF:
    if not points:
        return QRectF()
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    pad = width
    return QRectF(
        min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad
    )


def stroke_bounds(points: list[StrokePoint], width: float) -> QRectF:
    """Public helper: antialias-safe bounds for a polyline."""
    if not points:
        return QRectF()
    return _stroke_area(points, width).adjusted(-2, -2, 2, 2)


def hit_test(points: list[StrokePoint], pos: QPointF, tolerance: float) -> bool:
    """True when ``pos`` lies within ``tolerance`` of the polyline."""
    if not points:
        return False
    if len(points) == 1:
        return math.hypot(points[0].x - pos.x(), points[0].y - pos.y()) <= tolerance
    for i in range(1, len(points)):
        ax, ay = points[i - 1].x, points[i - 1].y
        bx, by = points[i].x, points[i].y
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        if seg2 <= 1e-9:
            if math.hypot(pos.x() - ax, pos.y() - ay) <= tolerance:
                return True
            continue
        t = ((pos.x() - ax) * dx + (pos.y() - ay) * dy) / seg2
        t = max(0.0, min(1.0, t))
        px, py = ax + t * dx, ay + t * dy
        if math.hypot(pos.x() - px, pos.y() - py) <= tolerance:
            return True
    return False


def pressure_hint(points: list[StrokePoint]) -> float:
    """Average normalised pressure; useful for the status readout and for tests."""
    if not points:
        return 0.0
    return sum(max(0.0, min(1.0, p.pressure)) for p in points) / len(points)


__all__ = [
    "StrokeBuilder",
    "Tool",
    "has_pressure",
    "hit_test",
    "polyline_path",
    "pressure_hint",
    "pressure_to_width",
    "render_stroke",
    "stroke_bounds",
    "width_profile",
]
