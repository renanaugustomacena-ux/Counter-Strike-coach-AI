"""System tray integration (Q6, workbench round).

One tray icon, four actions:

    Open Macena  — show + raise the main window
    AI Coach     — show the window ON the coach screen (the "chatbot"
                   entry; a separate chat process is deliberately NOT
                   offered — the single-instance guard exists because two
                   processes mean concurrent SQLite writers)
    CLI Console  — launch ``console.py`` in a new terminal (source layout
                   on Windows only; the action hides itself elsewhere) so
                   the user can drive ingestion: ``ingest start`` etc.
    Quit         — real teardown via QApplication.quit() (aboutToQuit
                   stops polling, kills the session-engine daemon, closes
                   the Console — same path as before the tray existed)

The icon is painted at runtime from the active theme's tokens (no icon
asset ships in the repo — same asset-free pattern as the wallpaper cards).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_tray")

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONSOLE_PY = _REPO_ROOT / "console.py"


def render_tray_icon(size: int = 32) -> QIcon:
    """Paint the tray icon: accent rounded square + white crosshair."""
    tokens = get_tokens()
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    rect = QRectF(1, 1, size - 2, size - 2)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(tokens.accent_primary))
    painter.drawRoundedRect(rect, size * 0.22, size * 0.22)
    center = rect.center()
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor("#FFFFFF"), max(1.5, size * 0.055)))
    radius = size * 0.22
    painter.drawEllipse(center, radius, radius)
    gap, arm = size * 0.06, size * 0.44
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        painter.drawLine(
            int(center.x() + dx * (radius + gap)),
            int(center.y() + dy * (radius + gap)),
            int(center.x() + dx * arm),
            int(center.y() + dy * arm),
        )
    painter.end()
    return QIcon(pm)


def cli_console_available() -> bool:
    """The CLI action needs a source layout and a Windows console launcher."""
    return sys.platform == "win32" and _CONSOLE_PY.is_file()


def launch_cli_console() -> bool:
    """Open ``console.py`` in a fresh terminal window (Windows source runs)."""
    if not cli_console_available():
        return False
    try:
        subprocess.Popen(
            [sys.executable, str(_CONSOLE_PY)],
            cwd=str(_REPO_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        return True
    except OSError:
        logger.exception("Could not launch the CLI console")
        return False


def build_tray(window) -> QSystemTrayIcon | None:
    """Create and show the tray icon; returns None where no tray exists
    (some Linux sessions, the offscreen test harness)."""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logger.info("No system tray available — close-to-tray disabled")
        return None

    tray = QSystemTrayIcon(render_tray_icon(), window)
    tray.setToolTip("Macena CS2 Analyzer")

    menu = QMenu()

    def _show_window():
        window.showNormal()
        window.raise_()
        window.activateWindow()

    def _show_coach():
        _show_window()
        if hasattr(window, "switch_screen"):
            window.switch_screen("coach")

    open_action = menu.addAction(i18n.get_text("tray_open", "Open Macena"))
    open_action.triggered.connect(_show_window)
    coach_action = menu.addAction(i18n.get_text("tray_coach", "AI Coach"))
    coach_action.triggered.connect(_show_coach)
    if cli_console_available():
        cli_action = menu.addAction(i18n.get_text("tray_cli", "CLI Console"))
        cli_action.triggered.connect(launch_cli_console)
    menu.addSeparator()
    quit_action = menu.addAction(i18n.get_text("tray_quit", "Quit"))
    quit_action.triggered.connect(QApplication.instance().quit)

    tray.setContextMenu(menu)
    tray._menu = menu  # keep the menu alive alongside the tray

    def _on_activated(reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            _show_window()

    tray.activated.connect(_on_activated)
    tray.show()
    return tray
