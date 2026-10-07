"""Screenshot and note export.

Two distinct products, both used constantly in class:

* *ink only* - a transparent PNG of the annotations, easy to drop into a slide;
* *composite* - the screen as the pupils saw it plus the annotations, which is
  what a teacher sends to a parent or archives as a lesson record.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from PyQt6.QtCore import QMarginsF, QRectF, QSizeF
from PyQt6.QtGui import QColor, QImage, QPageSize, QPainter, QPdfWriter

from ..config import Config

SUPPORTED_FORMATS = ("png", "jpg", "pdf")

#: A4 landscape in PostScript points - the natural page for a board capture.
A4_LANDSCAPE = QSizeF(841.89, 595.28)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def default_directory(config: Config) -> Path:
    return ensure_dir(config.get_str("capture/directory"))


def timestamped_path(directory: str | Path, prefix: str = "fatih-kalem", fmt: str = "png") -> Path:
    stamp = _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    suffix = "jpg" if fmt.lower() in {"jpg", "jpeg"} else fmt.lower()
    directory = ensure_dir(directory)
    candidate = directory / f"{prefix}_{stamp}.{suffix}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{prefix}_{stamp}-{counter}.{suffix}"
        counter += 1
    return candidate


def uniquify(path: str | Path) -> Path:
    """Append ``-2``, ``-3`` ... until the path is free."""
    p = Path(path)
    if not p.exists():
        return p
    stem, suffix, parent = p.stem, p.suffix, p.parent
    for i in range(2, 1000):
        candidate = parent / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate
    return parent / f"{stem}-{int(_dt.datetime.now().timestamp())}{suffix}"


def composite(background: QImage, ink: QImage, *, ink_origin: tuple[int, int] = (0, 0)) -> QImage:
    """Draw the transparent ink layer onto a background screenshot."""
    if background.isNull():
        return ink.copy()
    if ink.isNull():
        return background.copy()
    out = background.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(out)
    painter.drawImage(ink_origin[0], ink_origin[1], ink)
    painter.end()
    return out


def save_image(image: QImage, path: str | Path, quality: int = 92) -> Path:
    """Write PNG / JPEG, dropping the alpha channel for JPEG."""
    target = uniquify(path)
    ensure_dir(target.parent)
    fmt = target.suffix.lower().lstrip(".")
    if fmt in {"jpg", "jpeg"}:
        image = image.convertToFormat(QImage.Format.Format_RGB888)
        ok = image.save(str(target), "JPEG", quality)
    else:
        if image.hasAlphaChannel():
            image = image.convertToFormat(QImage.Format.Format_ARGB32)
        ok = image.save(str(target), "PNG")
    if not ok:
        raise OSError(f"could not write {target}")
    return target


def save_pdf(image: QImage, path: str | Path, page: QSizeF | None = None) -> Path:
    """Write a single-page PDF, scaling the image to fit A4 landscape."""
    target = uniquify(path)
    ensure_dir(target.parent)

    writer = QPdfWriter(str(target))
    page = page or A4_LANDSCAPE
    writer.setPageSize(QPageSize(page, QPageSize.Unit.Point))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0))
    writer.setResolution(96)
    writer.setTitle("Fatih Kalem")

    painter = QPainter(writer)
    if not image.isNull():
        margin = 8.0
        avail_w = page.width() - 2 * margin
        avail_h = page.height() - 2 * margin
        scale = min(avail_w / image.width(), avail_h / image.height())
        w = image.width() * scale
        h = image.height() * scale
        x = (page.width() - w) / 2.0
        y = (page.height() - h) / 2.0
        painter.fillRect(QRectF(0, 0, page.width(), page.height()), QColor(255, 255, 255))
        painter.drawImage(QRectF(x, y, w, h), image)
    painter.end()
    return target


__all__ = [
    "A4_LANDSCAPE",
    "SUPPORTED_FORMATS",
    "composite",
    "default_directory",
    "ensure_dir",
    "save_image",
    "save_pdf",
    "timestamped_path",
    "uniquify",
]
