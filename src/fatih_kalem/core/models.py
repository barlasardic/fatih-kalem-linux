"""Data model for strokes, tools and documents.

Kept free of widgets so the geometry and serialisation logic can be unit tested
without a display server.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor

#: Bumped when the on-disk project format changes incompatibly.
PROJECT_FORMAT_VERSION = 1
PROJECT_SUFFIX = ".fkl"


class Tool(StrEnum):
    PEN = "pen"
    MARKER = "marker"
    ERASER = "eraser"


class PenType(StrEnum):
    """Line style of the pen nib.

    ``BROKEN`` reproduces the "kesik uç" nib used by Arabic teachers, where the
    stroke must stay legible over stacked dots and harakat.
    """

    SOLID = "solid"
    DASHED = "dashed"
    BROKEN = "broken"


PEN_TYPES: dict[str, list[float]] = {
    # Dash pattern lengths in logical pixels: [on, off].
    # The off length is treated as a *minimum* - the renderer widens it when the
    # nib is thick, otherwise the round caps would close every gap.
    PenType.SOLID.value: [],
    PenType.DASHED.value: [20.0, 12.0],
    PenType.BROKEN.value: [5.0, 10.0],
}


@dataclass(slots=True)
class StrokePoint:
    """One sampled pointer position."""

    x: float
    y: float
    pressure: float = 1.0
    tilt: float = 0.0
    time: int = 0

    def to_point_f(self) -> QPointF:
        return QPointF(self.x, self.y)

    def distance_to(self, other: StrokePoint) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass(frozen=True, slots=True)
class PenStyle:
    """Immutable pen description captured at stroke start.

    A stroke keeps the style it was started with so that changing the toolbar
    mid-stroke (or undoing much later) never repaints old ink.
    """

    tool: Tool
    color: QColor
    width: float
    pen_type: PenType = PenType.SOLID
    opacity: float = 1.0

    @property
    def is_eraser(self) -> bool:
        return self.tool is Tool.ERASER

    def effective_color(self) -> QColor:
        c = QColor(self.color)
        c.setAlphaF(max(0.0, min(1.0, self.opacity)))
        return c


@dataclass(slots=True)
class Stroke:
    """A committed freehand mark."""

    points: list[StrokePoint]
    style: PenStyle
    created: float = field(default_factory=time.time)
    id: int = 0

    # -- geometry -------------------------------------------------------
    def bounds(self) -> QRectF:
        """Tight bounding box, widened by half the stroke width."""
        if not self.points:
            return QRectF()
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        pad = self.style.width / 2.0
        return QRectF(
            min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad
        )

    def length(self) -> float:
        return sum(
            self.points[i].distance_to(self.points[i - 1]) for i in range(1, len(self.points))
        )

    # -- serialisation --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tool": self.style.tool.value,
            "color": self.style.color.name(QColor.NameFormat.HexArgb),
            "width": round(self.style.width, 3),
            "pen_type": self.style.pen_type.value,
            "opacity": round(self.style.opacity, 3),
            "created": round(self.created, 4),
            # Round to 0.01px: plenty for a 4K board, keeps project files small.
            "points": [
                [round(p.x, 2), round(p.y, 2), round(p.pressure, 3), round(p.tilt, 2)]
                for p in self.points
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Stroke:
        points = [
            StrokePoint(x=float(p[0]), y=float(p[1]), pressure=float(p[2]), tilt=float(p[3]))
            for p in data.get("points", [])
        ]
        style = PenStyle(
            tool=Tool(data.get("tool", "pen")),
            color=QColor(data.get("color", "#ff000000")),
            width=float(data.get("width", 4.0)),
            pen_type=PenType(data.get("pen_type", "solid")),
            opacity=float(data.get("opacity", 1.0)),
        )
        return cls(
            points=points,
            style=style,
            created=float(data.get("created", time.time())),
            id=int(data.get("id", 0)),
        )


@dataclass
class Document:
    """Ordered collection of strokes. Page support lands in M3."""

    strokes: list[Stroke] = field(default_factory=list)
    background: str = "transparent"  # "transparent" | template id | file path
    background_color: str = "#00000000"

    def add(self, stroke: Stroke) -> None:
        stroke.id = len(self.strokes) + 1
        self.strokes.append(stroke)

    def clear(self) -> None:
        self.strokes.clear()

    def bounds(self) -> QRectF:
        rect = QRectF()
        for s in self.strokes:
            rect = rect.united(s.bounds())
        return rect

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": PROJECT_FORMAT_VERSION,
            "background": self.background,
            "background_color": self.background_color,
            "strokes": [s.to_dict() for s in self.strokes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        doc = cls(
            background=str(data.get("background", "transparent")),
            background_color=str(data.get("background_color", "#00000000")),
        )
        doc.strokes = [Stroke.from_dict(s) for s in data.get("strokes", [])]
        return doc


# ---------------------------------------------------------------------------
# Document-side undo payloads
#
# Pixels live in the canvas ink layer and are undone with image patches; the
# serialisable stroke list is kept in lockstep through these payloads, which are
# attached to their patch as ``meta``.
# ---------------------------------------------------------------------------
class StrokeAction:
    """A single appended stroke."""

    __slots__ = ("stroke",)

    def __init__(self, stroke: Stroke) -> None:
        self.stroke = stroke

    def undo(self, doc: Document) -> None:
        if doc.strokes and doc.strokes[-1] is self.stroke:
            doc.strokes.pop()
        elif self.stroke in doc.strokes:
            doc.strokes.remove(self.stroke)

    def redo(self, doc: Document) -> None:
        if self.stroke not in doc.strokes:
            doc.strokes.append(self.stroke)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"StrokeAction(#{self.stroke.id}, {len(self.stroke.points)} pts)"


class ClearAction:
    """Removal of every stroke at once (needs the old list to be undoable)."""

    __slots__ = ("snapshot",)

    def __init__(self, snapshot: list[Stroke]) -> None:
        self.snapshot = list(snapshot)

    def undo(self, doc: Document) -> None:
        doc.strokes = list(self.snapshot)

    def redo(self, doc: Document) -> None:
        doc.strokes = []

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ClearAction({len(self.snapshot)} strokes)"
