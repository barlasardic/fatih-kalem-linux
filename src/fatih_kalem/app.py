"""Application bootstrap: argument parsing, single-instance guard, startup."""

from __future__ import annotations

import argparse
import os
import sys

from PyQt6.QtCore import QLockFile, QStandardPaths, Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from . import __version__, i18n
from .config import Config
from .core.models import Tool
from .platform.factory import backend_report, detect_backend, session_report
from .ui.overlay import Overlay

APP_NAME = "Fatih Kalem"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fatih-kalem",
        description=(
            "Fatih Kalem - transparent screen annotation for Pardus ETAP interactive boards."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="run in a normal sized window instead of covering the screen (development)",
    )
    parser.add_argument(
        "--sandbox-size",
        default="1280x720",
        help="window size used by --sandbox (default: 1280x720)",
    )
    parser.add_argument(
        "--print-session",
        action="store_true",
        help="print detected session/backend capabilities and exit",
    )
    parser.add_argument("--reset-config", action="store_true", help="restore default settings")
    parser.add_argument("--clear", action="store_true", help="start with an empty board")
    parser.add_argument(
        "--no-single-instance",
        action="store_true",
        help="allow several copies (development)",
    )
    parser.add_argument(
        "--color",
        default="",
        help="start with this pen colour, e.g. #e11d2e (hex)",
    )
    parser.add_argument(
        "--width", type=float, default=0.0, help="start with this pen width in logical pixels"
    )
    parser.add_argument(
        "--tool",
        choices=[t.value for t in Tool],
        default="",
        help="start with this tool active",
    )
    parser.add_argument(
        "--board",
        default="",
        help="background under the ink: 'transparent', 'white' or #rrggbb (default: transparent)",
    )
    return parser


def parse_size(text: str) -> tuple[int, int]:
    try:
        w, _, h = text.lower().partition("x")
        return max(320, int(w)), max(240, int(h))
    except (ValueError, TypeError):
        return 1280, 720


def _lock_path() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
    return os.path.join(base or "/tmp", "fatih-kalem-linux.lock")


def configure_qt() -> None:
    """Attributes that must be set before QApplication exists."""
    # Touch must not be silently converted into mouse events: pressure and the
    # two-finger gesture router need the raw QTouchEvent/QTabletEvent stream.
    QApplication.setAttribute(
        Qt.ApplicationAttribute.AA_SynthesizeMouseForUnhandledTouchEvents, False
    )
    QApplication.setAttribute(
        Qt.ApplicationAttribute.AA_SynthesizeTouchForUnhandledMouseEvents, False
    )
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)


def apply_overrides(config: Config, args: argparse.Namespace) -> None:
    if args.color:
        config.set("pen/color", args.color)
    if args.width > 0:
        config.set("pen/width", args.width)
    if args.tool:
        config.set("pen/tool", args.tool)
    if args.board:
        value = args.board.strip()
        if value.lower() in {"transparent", "none", ""}:
            value = ""
        elif value.lower() in {"white", "beyaz"}:
            value = "#ffffff"
        config.set("overlay/boardColor", value)


def warn_about_backend(app: QApplication, backend, sandbox: bool) -> None:
    if sandbox or backend.caps.global_overlay:
        return
    QMessageBox.warning(
        app,
        i18n.tr("Session not fully supported"),
        i18n.tr(
            "On Wayland the overlay cannot cover other windows. "
            "Switch to the X11 (Cinnamon) session for full features."
        )
        + "\n\n"
        + backend_report(backend),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_qt()
    app = QApplication([sys.argv[0]])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("fatih-kalem-linux")
    app.setQuitOnLastWindowClosed(False)

    config = Config()
    if args.reset_config:
        config.reset()
    config.seed_missing()

    if args.print_session:
        print(session_report())
        print()
        print(backend_report(detect_backend()))
        return 0

    i18n.install(i18n.resolve_locale(config.get_str("general/language")))
    apply_overrides(config, args)

    lock: QLockFile | None = None
    if (
        not args.sandbox
        and not args.no_single_instance
        and config.get_bool("general/singleInstance")
    ):
        lock = QLockFile(_lock_path())
        lock.setStaleLockTime(0)
        if not lock.tryLock(0):
            print("Fatih Kalem is already running.", file=sys.stderr)
            return 1

    backend = detect_backend()
    overlay = Overlay(config, backend, sandbox=args.sandbox, size=parse_size(args.sandbox_size))
    overlay.apply_pen_settings()
    if args.clear:
        overlay.canvas.clear_all()
    overlay.show_overlay()
    warn_about_backend(app, backend, args.sandbox)

    app.aboutToQuit.connect(config.sync)
    exit_code = app.exec()
    if lock is not None:
        lock.unlock()
    return exit_code


__all__ = ["main", "build_parser", "configure_qt", "parse_size"]
