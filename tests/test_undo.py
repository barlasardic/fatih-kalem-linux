"""Patch-based undo/redo: reversibility, bounds and metadata."""

from __future__ import annotations

import unittest

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QColor, QImage, QPainter

from fatih_kalem.core.undo import PatchStack
from tests import SRC  # noqa: F401


def layer(size: tuple[int, int] = (200, 200)) -> QImage:
    image = QImage(size[0], size[1], QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    return image


def paint(image: QImage, rect: QRect, color: str) -> None:
    painter = QPainter(image)
    painter.fillRect(rect, QColor(color))
    painter.end()


def paste(image: QImage, rect: QRect, patch: QImage) -> None:
    """Apply a snapshot patch the way the canvas does: replace, not blend."""
    painter = QPainter(image)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    painter.drawImage(rect.topLeft(), patch)
    painter.end()


class PatchStackTests(unittest.TestCase):
    def test_empty_stack_cannot_move(self):
        stack = PatchStack()
        self.assertFalse(stack.can_undo)
        self.assertFalse(stack.can_redo)
        self.assertIsNone(stack.undo())
        self.assertIsNone(stack.redo())

    def test_undo_restores_the_previous_pixels(self):
        before = layer()
        after = layer()
        rect = QRect(10, 10, 50, 50)
        paint(after, rect, "#ff0000")

        stack = PatchStack()
        stack.record(rect, before, after)

        working = after.copy()
        undo_rect, image = stack.undo()
        paste(working, undo_rect, image)
        self.assertEqual(working.pixelColor(20, 20).alpha(), 0)
        self.assertTrue(stack.can_redo)

    def test_round_trip_redo(self):
        before = layer()
        after = layer()
        rect = QRect(0, 0, 20, 20)
        paint(after, rect, "#00ff00")
        stack = PatchStack()
        stack.record(rect, before, after)
        stack.undo()
        self.assertTrue(stack.can_redo)
        self.assertIsNotNone(stack.redo())

    def test_unchanged_region_is_not_recorded(self):
        image = layer()
        stack = PatchStack()
        stack.record(QRect(0, 0, 10, 10), image, image.copy())
        self.assertFalse(stack.can_undo)

    def test_out_of_bounds_rect_is_clamped(self):
        stack = PatchStack()
        stack.record(QRect(180, 180, 100, 100), layer(), layer())
        self.assertFalse(stack.can_undo)

    def test_empty_rect_is_ignored(self):
        stack = PatchStack()
        stack.record(QRect(), layer(), layer())
        self.assertFalse(stack.can_undo)

    def test_recording_after_undo_drops_the_redo_tail(self):
        stack = PatchStack()
        image = layer()
        rect = QRect(0, 0, 10, 10)
        first = image.copy()
        paint(image, rect, "#ff0000")
        stack.record(rect, first, image.copy())
        first_done = stack.undo_count
        self.assertEqual(first_done, 1)

        stack.undo()
        self.assertTrue(stack.can_redo)

        second = image.copy()
        paint(image, rect, "#00ff00")
        stack.record(rect, second, image.copy())
        self.assertFalse(stack.can_redo)
        self.assertEqual(stack.undo_count, first_done)

    def test_entry_limit_evicts_oldest(self):
        stack = PatchStack(max_entries=3)
        image = layer()
        for i in range(6):
            before = image.copy()
            paint(image, QRect(i, 0, 1, 1), "#ffffff")
            stack.record(QRect(i, 0, 1, 1), before, image.copy())
        self.assertLessEqual(len(stack._entries), 3)
        self.assertGreater(stack.dropped_count, 0)

    def test_byte_budget_evicts_oldest(self):
        stack = PatchStack(max_bytes=1, max_entries=1000)
        image = layer()
        for _ in range(4):
            before = image.copy()
            paint(image, QRect(0, 0, 40, 40), "#ffffff")
            stack.record(QRect(0, 0, 40, 40), before, image.copy())
        self.assertLessEqual(stack.bytes_used, 1)
        self.assertGreater(stack.dropped_count, 0)

    def test_meta_survives_undo_and_redo(self):
        before, after = layer(), layer()
        paint(after, QRect(0, 0, 10, 10), "#123456")
        marker = object()
        stack = PatchStack()
        stack.record(QRect(0, 0, 10, 10), before, after, meta=marker)
        self.assertTrue(stack.can_undo)
        self.assertFalse(stack.can_redo, "nothing is redoable before the first undo")

        stack.undo()
        self.assertIs(stack.peek_redo_meta(), marker)
        stack.redo()
        self.assertIs(stack.peek_undo_meta(), marker)

    def test_large_patch_is_compressed(self):
        big_a = QImage(4000, 4000, QImage.Format.Format_ARGB32_Premultiplied)
        big_a.fill(QColor(0, 0, 0, 0))
        big_b = QImage(4000, 4000, QImage.Format.Format_ARGB32_Premultiplied)
        big_b.fill(QColor(0, 0, 0, 0))
        rect = QRect(0, 0, 4000, 4000)
        big_b.fill(QColor(255, 0, 0))
        stack = PatchStack()
        stack.record(rect, big_a, big_b)
        # 2 x 16 MPix raw would be 128 MB; PNG of a flat fill is a few KB.
        self.assertLess(stack.bytes_used, 1_000_000)
        _, restored = stack.undo()
        self.assertEqual(restored.pixelColor(2000, 2000).alpha(), 0)

    def test_clear_resets_everything(self):
        image = layer()
        stack = PatchStack()
        stack.record(QRect(0, 0, 5, 5), image, image)
        stack.clear()
        self.assertFalse(stack.can_undo)
        self.assertFalse(stack.can_redo)
        self.assertEqual(stack.bytes_used, 0)


class PatchNavigationTests(unittest.TestCase):
    def make(self) -> tuple[PatchStack, list[QImage]]:
        stack = PatchStack()
        states = []
        image = layer()
        for i in range(4):
            before = image.copy()
            paint(image, QRect(i * 10, 0, 5, 5), "#0000ff")
            states.append(image.copy())
            stack.record(QRect(i * 10, 0, 5, 5), before, image.copy())
        return stack, states

    def test_full_undo_walk_restores_every_state(self):
        stack, states = self.make()
        seen = []
        for _ in range(4):
            rect, image = stack.undo()
            canvas = states[-1].copy()
            paste(canvas, rect, image)
            states.pop()
            seen.append(canvas.pixelColor(0, 0).alpha())
        self.assertFalse(stack.can_undo)
        self.assertEqual(seen[-1], 0)

    def test_redo_walk_returns_to_the_final_state(self):
        stack, states = self.make()
        for _ in range(4):
            stack.undo()
        final = states[0].copy()
        for _ in range(4):
            step = stack.redo()
            self.assertIsNotNone(step)
            rect, image = step
            paste(final, rect, image)
        self.assertFalse(stack.can_redo)
        self.assertEqual(final.pixelColor(32, 2).alpha(), 255)


if __name__ == "__main__":
    unittest.main()
