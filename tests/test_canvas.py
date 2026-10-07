"""End-to-end canvas behaviour: drawing, erasing, history and export.

These exercise the real widgets under the ``offscreen`` platform plugin, which is
the same code path a board runs - only the display server differs.
"""

from __future__ import annotations

import math
import unittest

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from fatih_kalem.config import Config
from fatih_kalem.core.models import PenType, Tool
from fatih_kalem.export import png as png_export
from fatih_kalem.platform.base import DesktopBackend
from fatih_kalem.ui.overlay import Overlay
from tests import SRC  # noqa: F401

W, H = 800, 600


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


class CanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        cfg = Config()
        cfg.set("overlay/boardColor", "")
        self.overlay = Overlay(cfg, DesktopBackend(), sandbox=True, size=(W, H))
        self.overlay.show_overlay()
        self.canvas = self.overlay.canvas
        self.canvas.clear_all()

    def tearDown(self):
        self.overlay.close()

    # -- helpers ---------------------------------------------------------
    def draw(self, points, tool=Tool.PEN, width=8.0, color="#1f6feb", pen_type=PenType.SOLID):
        self.canvas.set_tool(tool)
        if tool is Tool.ERASER:
            self.canvas.set_eraser_size(width)
        else:
            self.canvas.set_color(color)
            self.canvas.set_width(width)
            self.canvas.set_pen_type(pen_type)
        self.canvas._begin(QPointF(*points[0]), 1.0, "mouse")
        for p in points[1:]:
            self.canvas._extend(QPointF(*p), 1.0)
        self.canvas._end()

    def alpha(self, x: float, y: float) -> int:
        return self.canvas.ink_image().pixelColor(int(x), int(y)).alpha()

    @staticmethod
    def curve(n=60, y0=200.0, step=3.0):
        return [(100 + i * step, y0 + math.sin(i / 4) * 30) for i in range(n)]

    # -- drawing ---------------------------------------------------------
    def test_layer_matches_the_canvas_size(self):
        self.assertEqual(self.canvas.ink_image().size(), self.canvas.size())

    def test_stroke_marks_ink_and_document(self):
        pts = self.curve()
        self.draw(pts)
        self.assertEqual(len(self.canvas.document.strokes), 1)
        self.assertGreater(self.alpha(*pts[20]), 0)

    def test_single_tap_leaves_a_dot(self):
        self.draw([(400, 300)])
        self.assertEqual(len(self.canvas.document.strokes), 1)
        self.assertGreater(self.alpha(400, 300), 0)

    def test_marker_is_semi_transparent(self):
        self.draw([(100, 100), (400, 100)], tool=Tool.MARKER, width=40, color="#ffee00")
        self.assertLess(self.alpha(250, 100), 255)

    def test_dashed_nib_leaves_gaps(self):
        self.draw([(100, 400), (700, 400)], width=6, pen_type=PenType.DASHED)
        gaps = sum(1 for x in range(100, 700) if self.alpha(x, 400) == 0)
        self.assertGreater(gaps, 20)

    # -- erasing ---------------------------------------------------------
    def test_eraser_clears_ink_without_touching_the_document(self):
        self.draw([(100, 300), (700, 300)], width=20)
        self.draw([(400, 300)], tool=Tool.ERASER, width=120)
        self.assertEqual(self.alpha(400, 300), 0)
        self.assertEqual(
            len(self.canvas.document.strokes), 1, "pixel erase must not delete strokes"
        )

    def test_eraser_leaves_the_rest_intact(self):
        pts = self.curve()
        self.draw(pts, width=20)
        self.draw(
            [(pts[0][0] - 40, pts[0][1]), (pts[0][0] - 20, pts[0][1])], tool=Tool.ERASER, width=60
        )
        self.assertGreater(self.alpha(*pts[40]), 0)

    # -- history ---------------------------------------------------------
    def test_undo_removes_ink_entirely(self):
        pts = self.curve()
        self.draw(pts)
        self.assertTrue(self.canvas.undo())
        self.assertEqual(self.alpha(*pts[20]), 0, "undo must erase the ink, not blend over it")
        self.assertEqual(self.canvas.document.strokes, [])

    def test_redo_restores_ink(self):
        pts = self.curve()
        self.draw(pts)
        self.canvas.undo()
        self.canvas.redo()
        self.assertGreater(self.alpha(*pts[20]), 0)
        self.assertEqual(len(self.canvas.document.strokes), 1)

    def test_undo_of_erase_puts_the_ink_back(self):
        pts = self.curve()
        self.draw(pts, width=20)
        self.draw([(pts[20][0], pts[20][1])], tool=Tool.ERASER, width=120)
        self.assertEqual(self.alpha(*pts[20]), 0)
        self.canvas.undo()
        self.assertGreater(self.alpha(*pts[20]), 0)

    def test_history_flags(self):
        self.assertFalse(self.canvas.can_undo())
        self.draw(self.curve())
        self.assertTrue(self.canvas.can_undo())
        self.assertFalse(self.canvas.can_redo())
        self.canvas.undo()
        self.assertFalse(self.canvas.can_undo())
        self.assertTrue(self.canvas.can_redo())

    def test_undo_on_empty_history_is_a_no_op(self):
        self.assertFalse(self.canvas.undo())
        self.assertFalse(self.canvas.redo())

    def test_clear_then_undo(self):
        pts = self.curve()
        self.draw(pts)
        self.draw(self.curve(y0=400.0))
        self.assertTrue(self.canvas.clear_all())
        self.assertEqual(self.canvas.document.strokes, [])
        self.assertEqual(self.alpha(*pts[20]), 0)
        self.canvas.undo()
        self.assertEqual(len(self.canvas.document.strokes), 2)
        self.assertGreater(self.alpha(*pts[20]), 0)

    def test_clear_on_empty_board_reports_no_change(self):
        self.assertFalse(self.canvas.clear_all())

    def test_new_stroke_drops_the_redo_tail(self):
        self.draw([(100, 100), (200, 100)])
        self.canvas.undo()
        self.assertTrue(self.canvas.can_redo())
        self.draw([(100, 300), (200, 300)])
        self.assertFalse(self.canvas.can_redo())

    # -- modes -----------------------------------------------------------
    def test_pass_mode_refuses_to_draw(self):
        self.canvas.set_pass_mode(True)
        self.draw(self.curve())
        self.assertEqual(self.canvas.document.strokes, [])
        self.assertEqual(self.alpha(300, 200), 0)

    def test_tool_switching_is_recorded(self):
        self.draw([(100, 100), (200, 100)])
        self.draw([(100, 150), (200, 150)], tool=Tool.MARKER, width=40)
        tools = [s.style.tool for s in self.canvas.document.strokes]
        self.assertEqual(tools, [Tool.PEN, Tool.MARKER])

    def test_style_is_frozen_at_stroke_start(self):
        self.draw([(100, 100), (200, 100)], color="#ff0000", width=8)
        self.canvas.set_color("#00ff00")
        self.canvas.set_width(30)
        self.assertEqual(self.canvas.document.strokes[0].style.color.name(), "#ff0000")
        self.assertAlmostEqual(self.canvas.document.strokes[0].style.width, 8.0)

    # -- pressure --------------------------------------------------------
    def test_pressure_widens_a_stylus_stroke(self):
        self.canvas.set_tool(Tool.PEN)
        self.canvas.set_color("#000000")
        self.canvas.set_width(20)
        self.canvas._begin(QPointF(100, 400), 0.05, "pen")
        self.canvas._extend(QPointF(200, 400), 0.05)
        self.canvas._extend(QPointF(300, 400), 1.0)
        self.canvas._end()
        stroke = self.canvas.document.strokes[0]
        self.assertLess(stroke.points[0].pressure, stroke.points[-1].pressure)

    # -- serialisation ----------------------------------------------------
    def test_document_round_trip_keeps_stroke_count(self):
        self.draw(self.curve())
        self.draw(self.curve(y0=420.0), color="#2f9e44")
        payload = self.canvas.document.to_dict()
        restored = type(self.canvas.document).from_dict(payload)
        self.assertEqual(len(restored.strokes), 2)

    # -- export -----------------------------------------------------------
    def test_export_ink_png_and_pdf(self):
        import tempfile
        from pathlib import Path

        self.draw(self.curve())
        with tempfile.TemporaryDirectory() as tmp:
            png_path = png_export.save_image(self.canvas.ink_image(), Path(tmp) / "a.png")
            pdf_path = png_export.save_pdf(self.canvas.ink_image(), Path(tmp) / "a.pdf")
            self.assertGreater(png_path.stat().st_size, 500)
            self.assertGreater(pdf_path.stat().st_size, 1000)
            written = QImage(str(png_path))
            self.assertFalse(written.isNull())
            self.assertEqual(written.size(), self.canvas.size())

    def test_export_never_overwrites(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "note.png"
            first = png_export.save_image(self.canvas.ink_image(), target)
            second = png_export.save_image(self.canvas.ink_image(), target)
            self.assertNotEqual(first, second)
            self.assertTrue(second.exists())

    def test_composite_places_ink_over_the_desktop(self):
        desktop = QImage(self.canvas.size(), QImage.Format.Format_ARGB32_Premultiplied)
        desktop.fill(0xFF204060)
        pts = self.curve()
        self.draw(pts)
        merged = png_export.composite(desktop, self.canvas.ink_image())
        self.assertEqual(merged.pixelColor(10, 10).rgb(), 0xFF204060, "untouched desktop")
        self.assertNotEqual(
            merged.pixelColor(int(pts[20][0]), int(pts[20][1])).rgb(),
            0xFF204060,
            "the annotation must land on top of the desktop",
        )


class ToolbarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.overlay = Overlay(Config(), DesktopBackend(), sandbox=True, size=(W, H))
        self.overlay.show_overlay()
        self.toolbar = self.overlay.toolbar

    def tearDown(self):
        self.overlay.close()

    def test_toolbar_fits_inside_the_window(self):
        self.assertLessEqual(self.toolbar.height(), self.overlay.height())

    def test_toolbar_fits_a_short_board(self):
        for height in (2160, 1440, 1200, 1080, 900, 720):
            self.toolbar.fit_to_height(height - 8)
            self.toolbar.adjustSize()
            self.assertLessEqual(self.toolbar.height(), height - 8, f"strip overflows at {height}")

    def test_toolbar_stays_touch_sized_when_possible(self):
        self.toolbar.fit_to_height(2160)
        self.assertGreaterEqual(self.toolbar._button_size, 40)

    def test_toolbar_snap_to_side(self):
        self.toolbar.snap_to_side(self.overlay.size(), "right")
        self.assertEqual(self.toolbar.side(), "right")
        self.assertGreater(self.toolbar.x(), self.overlay.width() // 2)

    def test_tool_signal_updates_the_canvas(self):
        self.toolbar._tool_group.button(2).click()  # eraser
        self.assertEqual(self.overlay.canvas.tool, Tool.ERASER)

    def test_history_buttons_follow_the_canvas(self):
        self.assertFalse(self.toolbar._btn_undo.isEnabled())
        self.overlay.canvas.set_tool(Tool.PEN)
        self.overlay.canvas._begin(QPointF(10, 10), 1.0, "mouse")
        self.overlay.canvas._extend(QPointF(80, 60), 1.0)
        self.overlay.canvas._end()
        self.assertTrue(self.toolbar._btn_undo.isEnabled())


if __name__ == "__main__":
    unittest.main()


class StartupTests(unittest.TestCase):
    """The overlay must honour persisted settings without a panel (M1)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(path=f"{self._tmp.name}/settings.ini", auto_seed=False)

    def tearDown(self):
        self._tmp.cleanup()

    def build(self):
        return Overlay(self.cfg, DesktopBackend(), sandbox=True, size=(400, 300))

    def test_persisted_tool_is_applied_to_canvas_and_strip(self):
        self.cfg.seed_missing()
        self.cfg.set("pen/tool", "eraser")
        ov = self.build()
        try:
            ov.apply_pen_settings()
            self.assertEqual(ov.canvas.tool, Tool.ERASER)
            self.assertTrue(ov.toolbar._btn_eraser.isChecked())
        finally:
            ov.close()

    def test_persisted_colour_and_width(self):
        self.cfg.seed_missing()
        self.cfg.set("pen/color", "#00ff88")
        self.cfg.set("pen/width", 17.0)
        ov = self.build()
        try:
            ov.apply_pen_settings()
            self.assertEqual(ov.canvas.color.name(), "#00ff88")
            self.assertAlmostEqual(ov.canvas.width, 17.0)
        finally:
            ov.close()

    def test_corrupt_tool_falls_back_to_pen(self):
        self.cfg.seed_missing()
        self.cfg._s.setValue("pen/tool", "broom")
        ov = self.build()
        try:
            ov.apply_pen_settings()
            self.assertEqual(ov.canvas.tool, Tool.PEN)
        finally:
            ov.close()

    def test_board_color_setting(self):
        self.cfg.seed_missing()
        self.cfg.set("overlay/boardColor", "#ffffff")
        ov = self.build()
        try:
            ov.show_overlay()
            self.assertIsNotNone(ov.canvas._board_color)
            self.assertEqual(ov.canvas._board_color.name(), "#ffffff")
        finally:
            ov.close()
