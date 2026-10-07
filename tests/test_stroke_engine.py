"""Stroke sampling, pressure mapping and dash generation."""

from __future__ import annotations

import unittest

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter

from fatih_kalem.core.models import PEN_TYPES, PenStyle, PenType, StrokePoint, Tool
from fatih_kalem.core.stroke_engine import (
    StrokeBuilder,
    has_pressure,
    hit_test,
    pressure_to_width,
    render_stroke,
    stroke_bounds,
    width_profile,
)
from fatih_kalem.ui.theme import PEN_WIDTHS
from tests import SRC  # noqa: F401  - puts src/ on sys.path


def make_points(count: int = 50, start: float = 0.0, step: float = 4.0, pressure: float = 1.0):
    return [
        StrokePoint(start + i * step, start + i * step, pressure, 0.0, i * 8) for i in range(count)
    ]


def solid(width: float = 6.0, color: str = "#ff0000") -> PenStyle:
    return PenStyle(tool=Tool.PEN, color=QColor(color), width=width, pen_type=PenType.SOLID)


def alpha_map(image: QImage):
    return lambda x, y: image.pixelColor(int(x), int(y)).alpha()


class StrokeBuilderTests(unittest.TestCase):
    def test_first_point_is_always_kept(self):
        b = StrokeBuilder(solid(), min_distance=10.0, smoothing=0.0)
        b.add(5, 5)
        self.assertEqual(len(b.points), 1)
        self.assertTrue(b.build() is not None)

    def test_min_distance_decimates_but_flush_keeps_the_end(self):
        b = StrokeBuilder(solid(), min_distance=10.0, smoothing=0.0)
        for i in range(20):
            b.add(i, i)
        pts = b.flush()
        self.assertLess(len(pts), 20)
        self.assertEqual((pts[-1].x, pts[-1].y), (19.0, 19.0))

    def test_smoothing_lowers_peak_deviation(self):
        raw = StrokeBuilder(solid(), min_distance=0.0, smoothing=0.0)
        smooth = StrokeBuilder(solid(), min_distance=0.0, smoothing=0.9)
        for i in range(30):
            raw.add(0, i)
            smooth.add(0, i)
        jitter = [(0, 0), (25, 5), (0, 10), (25, 15), (0, 20)]
        for x, y in jitter:
            raw.add(x, y)
            smooth.add(x, y)
        self.assertLessEqual(
            max(abs(p.x) for p in smooth.points), max(abs(p.x) for p in raw.points)
        )

    def test_timestamps_strictly_increase(self):
        b = StrokeBuilder(solid(), min_distance=0.0)
        for _ in range(5):
            b.add(1, 1, 1.0, 0.0, 1000)
        times = [p.time for p in b.points]
        self.assertEqual(times, sorted(times))
        self.assertEqual(len(set(times)), len(times))

    def test_empty_builder_yields_no_stroke(self):
        self.assertIsNone(StrokeBuilder(solid()).build())


class PressureTests(unittest.TestCase):
    def test_disabled_returns_base_width(self):
        self.assertEqual(pressure_to_width(10, 0.2, enabled=False), 10)

    def test_full_pressure_returns_base_width(self):
        self.assertEqual(pressure_to_width(10, 1.0), 10)

    def test_zero_pressure_returns_min_factor_width(self):
        self.assertAlmostEqual(pressure_to_width(10, 0.0, min_factor=0.3), 3.0, places=5)

    def test_width_is_monotonic_in_pressure(self):
        widths = [pressure_to_width(20, p / 10) for p in range(11)]
        self.assertEqual(widths, sorted(widths))

    def test_has_pressure_detects_constant_full_as_false(self):
        self.assertFalse(has_pressure(make_points(10, pressure=1.0)))
        self.assertTrue(has_pressure(make_points(10, pressure=0.5)))
        self.assertFalse(has_pressure([]))

    def test_width_profile_falls_back_when_no_pressure(self):
        profile = width_profile(make_points(5, pressure=1.0), solid(width=8))
        self.assertTrue(all(abs(w - 8) < 1e-6 for w in profile))


class GeometryTests(unittest.TestCase):
    def test_bounds_include_half_width_plus_antialias(self):
        pts = [StrokePoint(0, 0), StrokePoint(100, 0)]
        rect = stroke_bounds(pts, 10.0)
        self.assertLessEqual(rect.left(), -5.0)
        self.assertGreaterEqual(rect.right(), 105.0)
        self.assertLess(rect.left(), -5.0, "the nib must stick out past the centre line")

    def test_bounds_of_empty_points_is_empty(self):
        self.assertTrue(stroke_bounds([], 6.0).isEmpty())

    def test_hit_test_near_and_far(self):
        pts = [StrokePoint(0, 0), StrokePoint(100, 0)]
        self.assertTrue(hit_test(pts, QPointF(50, 4), 10))
        self.assertFalse(hit_test(pts, QPointF(50, 40), 10))

    def test_hit_test_single_point(self):
        pts = [StrokePoint(20, 20)]
        self.assertTrue(hit_test(pts, QPointF(22, 22), 5))
        self.assertFalse(hit_test([], QPointF(0, 0), 100))


class RenderTests(unittest.TestCase):
    def render(self, points, style, **kwargs):
        image = QImage(400, 400, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor(0, 0, 0, 0))
        painter = QPainter(image)
        render_stroke(painter, points, style, **kwargs)
        painter.end()
        return image

    def test_solid_line_marks_pixels(self):
        img = self.render(make_points(40), solid(width=10, color="#ff0000"))
        self.assertGreater(alpha_map(img)(150, 150), 0)

    def test_single_point_draws_a_dot(self):
        img = self.render([StrokePoint(200, 200)], solid(width=20))
        self.assertGreater(img.pixelColor(200, 200).alpha(), 0)

    def test_dashed_pen_leaves_gaps(self):
        pts = [StrokePoint(20, 200), StrokePoint(380, 200)]
        dashed = PenStyle(tool=Tool.PEN, color=QColor("#0000ff"), width=12, pen_type=PenType.DASHED)
        img = self.render(pts, dashed)
        gaps = sum(1 for x in range(20, 380) if img.pixelColor(x, 200).alpha() == 0)
        self.assertGreater(gaps, 5, "a dashed nib must actually leave gaps along the line")

    def test_broken_pen_is_denser_than_dashed(self):
        pts = [StrokePoint(20, 200), StrokePoint(380, 200)]
        common = dict(tool=Tool.PEN, color=QColor("#000000"), width=6)
        dashed = self.render(pts, PenStyle(pen_type=PenType.DASHED, **common))
        broken = self.render(pts, PenStyle(pen_type=PenType.BROKEN, **common))
        gaps = lambda img: sum(1 for x in range(20, 380) if img.pixelColor(x, 200).alpha() == 0)  # noqa: E731
        self.assertGreater(gaps(broken), gaps(dashed))

    def test_dash_gap_survives_a_thick_nib(self):
        """Round caps must not swallow the gap at any of the six nib widths."""

        pts = [StrokePoint(20, 200), StrokePoint(380, 200)]
        for width in PEN_WIDTHS:
            style = PenStyle(
                tool=Tool.PEN, color=QColor("#000000"), width=width, pen_type=PenType.DASHED
            )
            img = self.render(pts, style)
            gaps = sum(1 for x in range(20, 380) if img.pixelColor(x, 200).alpha() == 0)
            self.assertGreater(gaps, 0, f"dashed nib at width {width} came out solid")

    def test_every_pen_type_drawn_on_one_image(self):
        for pen_type in PenType:
            style = PenStyle(tool=Tool.PEN, color=QColor("#ff8800"), width=8, pen_type=pen_type)
            img = self.render(make_points(40), style)
            painted = sum(1 for y in range(400) if img.pixelColor(150, y).alpha() > 0)
            self.assertGreater(painted, 5, pen_type)

    def test_marker_joins_do_not_accumulate_alpha(self):
        """Semi-transparent strokes are rasterised through a scratch layer."""
        style = PenStyle(tool=Tool.MARKER, color=QColor("#ffee00"), width=30, opacity=0.35)
        pts = make_points(40)
        img = self.render(pts, style)
        alphas = {img.pixelColor(150, y).alpha() for y in range(145, 156)}
        self.assertEqual(len(alphas), 1, f"alpha should be uniform along the mark, got {alphas}")

    def test_eraser_clears_previous_ink(self):
        layer = QImage(400, 400, QImage.Format.Format_ARGB32_Premultiplied)
        layer.fill(QColor(0, 0, 0, 0))
        painter = QPainter(layer)
        render_stroke(painter, make_points(40), solid(width=20))
        painter.end()
        self.assertGreater(layer.pixelColor(150, 150).alpha(), 0)

        eraser = PenStyle(tool=Tool.ERASER, color=QColor(0, 0, 0), width=60)
        painter = QPainter(layer)
        render_stroke(painter, [StrokePoint(150, 150)], eraser)
        painter.end()
        self.assertEqual(layer.pixelColor(150, 150).alpha(), 0)

    def test_empty_points_render_nothing(self):
        img = self.render([], solid())
        self.assertEqual(img.pixelColor(200, 200).alpha(), 0)


class PatternTableTests(unittest.TestCase):
    def test_solid_has_no_dash_pattern(self):
        self.assertEqual(PEN_TYPES[PenType.SOLID.value], [])

    def test_other_types_have_on_off_pairs(self):
        for pen_type in (PenType.DASHED, PenType.BROKEN):
            pattern = PEN_TYPES[pen_type.value]
            self.assertEqual(len(pattern), 2)
            self.assertGreater(pattern[0], 0)
            self.assertGreater(pattern[1], 0)


if __name__ == "__main__":
    unittest.main()
