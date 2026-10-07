"""Colours, sizes and the QSS stylesheet.

Palette and widths are tuned for a 65" 4K board viewed from across a classroom:
large touch targets, high-contrast chrome, and 24 inks laid out in a 6x4 grid so
the whole palette is visible without scrolling.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QFont

#: 24 inks, grouped by hue family, row-major in a 6x4 grid.
PALETTE: list[str] = [
    # row 1 - primaries and neutrals
    "#000000",
    "#4b5563",
    "#9ca3af",
    "#ffffff",
    "#e11d2e",
    "#f97316",
    # row 2 - warm
    "#f59e0b",
    "#fbbf24",
    "#fde047",
    "#a3e635",
    "#22c55e",
    "#10b981",
    # row 3 - cool
    "#06b6d4",
    "#38bdf8",
    "#0ea5e9",
    "#3b82f6",
    "#6366f1",
    "#8b5cf6",
    # row 4 - accents
    "#a855f7",
    "#d946ef",
    "#ec4899",
    "#f43f5e",
    "#8b5a2b",
    "#78350f",
]

#: Extra teacher-friendly colours reachable from the colour panel.
CLASSROOM_PALETTE: list[str] = [
    "#ff0000",
    "#00ff00",
    "#0000ff",
    "#ffff00",
    "#ff00ff",
    "#00ffff",
    "#000000",
    "#ffffff",
    "#808080",
    "#ff6600",
    "#663399",
    "#0066cc",
]

PALETTE_COLUMNS = 6

#: Pen widths in logical pixels (Qt scales these by the board's device ratio).
PEN_WIDTHS: list[float] = [2.0, 4.0, 6.0, 9.0, 13.0, 20.0]

#: Eraser diameters in logical pixels.
ERASER_SIZES: list[float] = [24.0, 48.0, 96.0, 160.0]

#: Brush icon size inside a toolbar button, in logical pixels.
BRUSH_ICON_SIZES: list[float] = [8.0, 14.0, 22.0, 32.0, 46.0, 64.0]

ACCENT = "#2f6fdb"
ACCENT_DIM = "#24529f"
DANGER = "#d13b3b"
OK = "#2f9e44"

PANEL_BG = "rgba(24, 26, 31, 236)"
PANEL_BG_HI = "rgba(40, 44, 52, 245)"
PANEL_BORDER = "rgba(255, 255, 255, 42)"
PANEL_TEXT = "#f2f4f8"
PANEL_TEXT_DIM = "#a8b0bd"


def pen_color(value: str | QColor) -> QColor:
    if isinstance(value, QColor):
        return QColor(value)
    c = QColor(value)
    return c if c.isValid() else QColor("#000000")


def nearest_palette_index(color: QColor, palette: list[str] | None = None) -> int:
    """Index of the visually closest swatch (used by the two-finger colour swipe)."""
    pool = palette or PALETTE
    target = QColor(color)
    best, best_d = 0, None
    for i, hexv in enumerate(pool):
        c = QColor(hexv)
        dr = c.red() - target.red()
        dg = c.green() - target.green()
        db = c.blue() - target.blue()
        d = dr * dr * 0.30 + dg * dg * 0.59 + db * db * 0.11
        if best_d is None or d < best_d:
            best, best_d = i, d
    return best


def base_font() -> QFont:
    f = QFont()
    f.setPointSize(11)
    return f


def stylesheet(accent: str = ACCENT) -> str:
    return f"""
    QWidget#toolbar {{
        background: {PANEL_BG};
        border: 1px solid {PANEL_BORDER};
        border-radius: 18px;
    }}
    QPushButton {{
        background: transparent;
        border: 2px solid transparent;
        border-radius: 14px;
        color: {PANEL_TEXT};
    }}
    QPushButton:hover {{
        background: {PANEL_BG_HI};
        border-color: rgba(255, 255, 255, 70);
    }}
    QPushButton:pressed {{
        background: {accent};
    }}
    QPushButton:checked {{
        background: {accent};
        border-color: #ffffff;
        color: #ffffff;
    }}
    QPushButton:disabled {{
        color: rgba(255, 255, 255, 60);
    }}
    QToolTip {{
        background: {PANEL_BG_HI};
        color: {PANEL_TEXT};
        border: 1px solid {PANEL_BORDER};
        padding: 4px 8px;
    }}
    QLabel#toolbarGrip {{
        color: {PANEL_TEXT_DIM};
        font-size: 18px;
    }}
    QLabel#toolbarHint {{
        color: {PANEL_TEXT_DIM};
        font-size: 11px;
    }}
    """
