"""Translation lookup.

Source strings are written in English (the project's second language) and looked
up through a per-locale catalog, so the app is bilingual from the first commit
without needing ``lrelease`` during development. ``scripts/update-translations.sh``
extracts the same catalog into Qt ``.ts`` files for external translators.
"""

from __future__ import annotations

import locale
import os
from pathlib import Path

SUPPORTED_LOCALES = ("tr_TR", "en_US")
DEFAULT_LOCALE = "tr_TR"

CATALOGS: dict[str, dict[str, str]] = {
    "tr_TR": {
        # -- app / dialogs
        "Fatih Kalem": "Fatih Kalem",
        "Draw with your finger or stylus on the board": "Ekrana parmağınızla veya kaleminizle yazabilirsiniz",
        "Session not fully supported": "Oturum tam olarak desteklenmiyor",
        "On Wayland the overlay cannot cover other windows. Switch to the X11 (Cinnamon) session for full features.": (
            "Wayland'da katman diğer pencerelerin üzerini kapatamaz. Tam özellikler için X11 (Cinnamon) oturumuna geçin."
        ),
        "Settings (coming in M2)": "Ayarlar (M2 ile geliyor)",
        # -- tools
        "Pen": "Kalem",
        "Highlighter": "Foslu kalem",
        "Eraser": "Silgi",
        "Undo": "Geri al",
        "Redo": "Yinele",
        "Clear": "Temizle",
        "Capture": "Ekran görüntüsü",
        "Pass to application": "Uygulamaya geç",
        "Hide": "Gizle",
        "Settings": "Ayarlar",
        # -- status
        "Nothing to undo": "Geri alınacak işlem yok",
        "Nothing to redo": "Yinelenecek işlem yok",
        "Screen cleared": "Ekran temizlendi",
        "Passed through to the application - pen hidden": "Uygulamaya geçildi - kalem gizli",
        "Pen visible": "Kalem açık",
        "Only the drawing was saved": "Yalnızca çizim kaydedildi",
        "Screenshot saved": "Ekran görüntüsü kaydedildi",
        "Could not save": "Kaydedilemedi",
        "Capture failed": "Görüntü alınamadı",
        "Nothing recorded yet": "Henüz çizim yok",
        # -- state words
        "pen": "Kalem",
        "marker": "Foslu kalem",
        "eraser": "Silgi",
    },
    "en_US": {},
}


def detect_system_locale() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return normalise_locale(value)
    try:
        return normalise_locale(locale.getlocale()[0] or "")
    except (ValueError, TypeError):  # pragma: no cover - exotic locale strings
        return ""


def normalise_locale(value: str) -> str:
    if not value:
        return ""
    tag = value.replace("-", "_").split(".")[0].split("@")[0]
    for supported in SUPPORTED_LOCALES:
        if tag.lower() == supported.lower():
            return supported
    prefix = tag.split("_")[0].lower()
    for supported in SUPPORTED_LOCALES:
        if supported.lower().startswith(prefix + "_"):
            return supported
    return ""


def resolve_locale(preference: str = "system") -> str:
    if preference in SUPPORTED_LOCALES:
        return preference
    return detect_system_locale() or DEFAULT_LOCALE


class I18n:
    """Minimal translator; one instance is created by :mod:`fatih_kalem.app`."""

    def __init__(self, locale_name: str = DEFAULT_LOCALE) -> None:
        self.locale_name = locale_name if locale_name in SUPPORTED_LOCALES else DEFAULT_LOCALE

    @property
    def catalog(self) -> dict[str, str]:
        return CATALOGS.get(self.locale_name, {})

    def tr(self, source: str) -> str:
        return self.catalog.get(source, source)

    def available(self) -> list[str]:
        return list(SUPPORTED_LOCALES)


def write_ts_skeleton(target: Path, locale_name: str) -> int:
    """Emit a Qt ``.ts`` file for external translators. Returns message count."""
    if locale_name not in SUPPORTED_LOCALES:
        raise ValueError(f"unsupported locale: {locale_name}")
    context = "<fatih_kalem.ui.overlay>"
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<!DOCTYPE TS>",
        f'<TS version="2.1" language="{locale_name.replace("_", "-")}">',
        "<context>",
        f"    <name>{context}</name>",
    ]
    catalog = CATALOGS.get(locale_name, {})
    unique = sorted(set(CATALOGS["en_US"]) | set(catalog) | set(_all_sources()))
    for message in unique:
        lines.append("    <message>")
        lines.append(f"        <source>{_escape(message)}</source>")
        lines.append(f"        <translation>{_escape(catalog.get(message, ''))}</translation>")
        lines.append("    </message>")
    lines += ["</context>", "</TS>", ""]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return len(unique)


def _all_sources() -> set[str]:
    out: set[str] = set()
    for catalog in CATALOGS.values():
        out.update(catalog)
    return out


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


#: Process-wide translator, replaced once at startup by :func:`install`.
_CURRENT = I18n()


def install(locale_name: str) -> I18n:
    global _CURRENT
    _CURRENT = I18n(locale_name)
    return _CURRENT


def current() -> I18n:
    return _CURRENT


def tr(source: str) -> str:
    return _CURRENT.tr(source)


__all__ = [
    "CATALOGS",
    "DEFAULT_LOCALE",
    "I18n",
    "SUPPORTED_LOCALES",
    "current",
    "detect_system_locale",
    "install",
    "normalise_locale",
    "resolve_locale",
    "tr",
    "write_ts_skeleton",
]
