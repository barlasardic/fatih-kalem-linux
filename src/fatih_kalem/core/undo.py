"""Undo/redo built from dirty-rectangle image patches.

A full-screen snapshot would cost ~33 MB per step on a 4K board, so instead each
action stores only the rectangle it touched, before and after. Erasing a corner
costs a few kilobytes; a full clear costs one frame, and oversized patches fall
back to PNG-compressed bytes so the stack stays bounded.
"""

from __future__ import annotations

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QRect
from PyQt6.QtGui import QImage

DEFAULT_MAX_BYTES = 192 * 1024 * 1024
DEFAULT_MAX_ENTRIES = 250
#: Patches at or above this many pixels are stored PNG-compressed.
COMPRESS_THRESHOLD_PX = 2_000_000


def _image_bytes(image: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, "PNG")
    buf.close()
    return bytes(buf.data())


def _bytes_image(data: bytes) -> QImage:
    img = QImage()
    img.loadFromData(QByteArray(data), "PNG")
    return img


class _StoredPatch:
    """Patch storage that transparently compresses large regions."""

    __slots__ = ("rect", "before_img", "after_img", "before_data", "after_data", "size", "meta")

    def __init__(
        self, rect: QRect, before: QImage, after: QImage, meta: object | None = None
    ) -> None:
        self.rect = rect
        self.meta = meta
        px = rect.width() * rect.height()
        if px >= COMPRESS_THRESHOLD_PX:
            self.before_img: QImage | None = None
            self.after_img: QImage | None = None
            self.before_data = _image_bytes(before)
            self.after_data = _image_bytes(after)
            self.size = len(self.before_data) + len(self.after_data)
        else:
            self.before_img = before
            self.after_img = after
            self.before_data = b""
            self.after_data = b""
            self.size = before.sizeInBytes() + after.sizeInBytes()

    def before_image(self) -> QImage:
        return self.before_img if self.before_img is not None else _bytes_image(self.before_data)

    def after_image(self) -> QImage:
        return self.after_img if self.after_img is not None else _bytes_image(self.after_data)


class PatchStack:
    """Bounded undo/redo stack of :class:`_StoredPatch` entries."""

    def __init__(
        self, max_bytes: int = DEFAULT_MAX_BYTES, max_entries: int = DEFAULT_MAX_ENTRIES
    ) -> None:
        self._entries: list[_StoredPatch] = []
        self._index = 0
        self._max_bytes = max_bytes
        self._max_entries = max_entries
        self._bytes = 0
        self._dropped = 0

    # -- state ----------------------------------------------------------
    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._entries)

    @property
    def undo_count(self) -> int:
        return self._index

    @property
    def redo_count(self) -> int:
        return len(self._entries) - self._index

    @property
    def bytes_used(self) -> int:
        return self._bytes

    @property
    def dropped_count(self) -> int:
        """Oldest steps that fell out of the memory budget and can no longer be undone."""
        return self._dropped

    # -- mutation -------------------------------------------------------
    def record(
        self, rect: QRect, before: QImage, after: QImage, meta: object | None = None
    ) -> None:
        """Store a reversible change. ``before``/``after`` are full ink-layer images."""
        if rect.isEmpty():
            return
        rect = rect.intersected(before.rect()).intersected(after.rect())
        if rect.isEmpty():
            return
        self.record_cropped(rect, before.copy(rect), after.copy(rect), meta)

    def record_cropped(
        self, rect: QRect, before: QImage, after: QImage, meta: object | None = None
    ) -> None:
        """Store a reversible change from images already cropped to ``rect``."""
        if rect.isEmpty():
            return
        if before.size() != after.size():
            return
        if before == after:
            return  # nothing actually changed
        self._truncate_redo()
        entry = _StoredPatch(rect, before, after, meta)
        self._entries.append(entry)
        self._bytes += entry.size
        self._index = len(self._entries)
        self._evict()

    def peek_meta(self) -> object | None:
        """Metadata of the step that ``undo()`` would revert."""
        if not self.can_undo:
            return None
        return self._entries[self._index - 1].meta

    def peek_undo_meta(self) -> object | None:
        """Metadata of the most recently applied step."""
        if self._index == 0:
            return None
        return self._entries[self._index - 1].meta

    def peek_redo_meta(self) -> object | None:
        """Metadata of the step that ``redo()`` would reapply."""
        if not self.can_redo:
            return None
        return self._entries[self._index].meta

    def _truncate_redo(self) -> None:
        for entry in self._entries[self._index :]:
            self._bytes -= entry.size
        del self._entries[self._index :]

    def _evict(self) -> None:
        while self._entries and (
            self._bytes > self._max_bytes or len(self._entries) > self._max_entries
        ):
            entry = self._entries.pop(0)
            self._bytes -= entry.size
            self._index = max(0, self._index - 1)
            self._dropped += 1

    # -- navigation -----------------------------------------------------
    def undo(self) -> tuple[QRect, QImage] | None:
        """Return ``(rect, image)`` that restores the state before the last action."""
        if not self.can_undo:
            return None
        self._index -= 1
        entry = self._entries[self._index]
        return entry.rect, entry.before_image()

    def redo(self) -> tuple[QRect, QImage] | None:
        if not self.can_redo:
            return None
        entry = self._entries[self._index]
        self._index += 1
        return entry.rect, entry.after_image()

    def clear(self) -> None:
        self._entries.clear()
        self._index = 0
        self._bytes = 0
        self._dropped = 0

    def prune_future(self) -> None:
        """Free the redo tail without touching the undo history."""
        self._truncate_redo()


__all__ = ["PatchStack", "DEFAULT_MAX_BYTES", "DEFAULT_MAX_ENTRIES"]
