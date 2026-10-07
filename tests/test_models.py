"""Document model, serialisation round-trips and undo payloads."""

from __future__ import annotations

import json
import unittest

from PyQt6.QtGui import QColor

from fatih_kalem.core.models import (
    PROJECT_FORMAT_VERSION,
    ClearAction,
    Document,
    PenStyle,
    PenType,
    Stroke,
    StrokeAction,
    StrokePoint,
    Tool,
)
from tests import SRC  # noqa: F401


def make_stroke(y: float = 10.0, n: int = 5, tool: Tool = Tool.PEN) -> Stroke:
    style = PenStyle(tool=tool, color=QColor("#1f6feb"), width=6.0, pen_type=PenType.DASHED)
    points = [StrokePoint(float(i), y + i, 0.5 + i / 10) for i in range(n)]
    return Stroke(points=points, style=style)


class PenStyleTests(unittest.TestCase):
    def test_eraser_flag(self):
        self.assertTrue(PenStyle(Tool.ERASER, QColor("#000"), 40).is_eraser)
        self.assertFalse(PenStyle(Tool.PEN, QColor("#000"), 4).is_eraser)

    def test_effective_color_applies_opacity(self):
        style = PenStyle(Tool.MARKER, QColor("#ffee00"), 30, opacity=0.35)
        self.assertAlmostEqual(style.effective_color().alphaF(), 0.35, places=2)


class StrokeTests(unittest.TestCase):
    def test_bounds_pad_by_half_width(self):
        s = make_stroke()
        rect = s.bounds()
        self.assertLessEqual(rect.left(), -3.0)
        self.assertGreaterEqual(rect.right(), 4.0 + 3.0)

    def test_length_of_straight_line(self):
        s = Stroke([StrokePoint(0, 0), StrokePoint(30, 40)], PenStyle(Tool.PEN, QColor("#000"), 1))
        self.assertAlmostEqual(s.length(), 50.0)

    def test_round_trip_preserves_geometry_and_style(self):
        original = make_stroke()
        restored = Stroke.from_dict(json.loads(json.dumps(original.to_dict())))
        self.assertEqual(len(restored.points), len(original.points))
        self.assertEqual(restored.style.pen_type, PenType.DASHED)
        self.assertEqual(restored.style.color.name(), original.style.color.name())
        self.assertAlmostEqual(restored.style.width, original.style.width)
        self.assertAlmostEqual(restored.points[3].pressure, original.points[3].pressure, places=3)
        self.assertAlmostEqual(restored.points[3].x, original.points[3].x, places=2)

    def test_points_are_rounded_for_compact_files(self):
        s = Stroke([StrokePoint(1.23456, 2.34567)], PenStyle(Tool.PEN, QColor("#000"), 1))
        x, y = s.to_dict()["points"][0][:2]
        self.assertEqual(x, 1.23)
        self.assertEqual(y, 2.35)


class DocumentTests(unittest.TestCase):
    def test_add_assigns_ids(self):
        doc = Document()
        doc.add(make_stroke())
        doc.add(make_stroke(y=50))
        self.assertEqual([s.id for s in doc.strokes], [1, 2])

    def test_clear(self):
        doc = Document()
        doc.add(make_stroke())
        doc.clear()
        self.assertEqual(doc.strokes, [])

    def test_bounds_unions_all_strokes(self):
        doc = Document()
        doc.add(make_stroke(y=0))
        doc.add(make_stroke(y=200))
        self.assertGreater(doc.bounds().height(), 190)

    def test_round_trip(self):
        doc = Document(background="grid", background_color="#ffffffff")
        doc.add(make_stroke())
        doc.add(make_stroke(y=90, tool=Tool.MARKER))
        restored = Document.from_dict(json.loads(json.dumps(doc.to_dict())))
        self.assertEqual(restored.background, "grid")
        self.assertEqual(restored.background_color, "#ffffffff")
        self.assertEqual(len(restored.strokes), 2)
        self.assertEqual(restored.strokes[1].style.tool, Tool.MARKER)

    def test_serialised_document_carries_the_format_version(self):
        self.assertEqual(Document().to_dict()["version"], PROJECT_FORMAT_VERSION)

    def test_empty_document_round_trips(self):
        self.assertEqual(Document.from_dict(Document().to_dict()).strokes, [])


class UndoPayloadTests(unittest.TestCase):
    def test_stroke_action_removes_and_restores(self):
        doc = Document()
        s = make_stroke()
        doc.add(s)
        action = StrokeAction(s)
        action.undo(doc)
        self.assertEqual(doc.strokes, [])
        action.redo(doc)
        self.assertEqual(doc.strokes, [s])

    def test_stroke_action_does_not_duplicate_on_redo(self):
        doc = Document()
        s = make_stroke()
        doc.add(s)
        StrokeAction(s).redo(doc)
        self.assertEqual(len(doc.strokes), 1)

    def test_stroke_action_recovers_if_not_the_last_element(self):
        doc = Document()
        first, second = make_stroke(), make_stroke(y=40)
        doc.add(first)
        doc.add(second)
        StrokeAction(first).undo(doc)
        self.assertEqual(doc.strokes, [second])

    def test_clear_action_restores_the_snapshot(self):
        doc = Document()
        strokes = [make_stroke(), make_stroke(y=40)]
        for s in strokes:
            doc.add(s)
        action = ClearAction(doc.strokes)
        action.redo(doc)
        self.assertEqual(doc.strokes, [])
        action.undo(doc)
        self.assertEqual(len(doc.strokes), 2)


if __name__ == "__main__":
    unittest.main()
