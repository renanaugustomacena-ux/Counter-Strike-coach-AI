"""
Application entry point — launches the PySide6 Qt frontend.

Usage:
    python -m Programma_CS2_RENAN.apps.qt_app.app
"""

import logging
import sys
from importlib.metadata import PackageNotFoundError, version

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow
from Programma_CS2_RENAN.apps.qt_app.screens.placeholder import create_placeholder_screens


def _create_splash(app_version: str) -> QSplashScreen:
    """Create a themed splash screen with gradient background and branding."""
    width, height = 520, 320
    pixmap = QPixmap(width, height)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Dark gradient background matching CS2 theme
    gradient = QLinearGradient(0, 0, 0, height)
    gradient.setColorAt(0.0, QColor("#14141e"))
    gradient.setColorAt(1.0, QColor("#0a0a14"))
    painter.fillRect(0, 0, width, height, gradient)

    # Accent bar at top (CS2 orange)
    painter.fillRect(0, 0, width, 4, QColor("#d96600"))

    # App title
    painter.setPen(QColor("#dcdcdc"))
    painter.setFont(QFont("Roboto", 22, QFont.Bold))
    painter.drawText(0, 70, width, 40, Qt.AlignCenter, "MACENA CS2 ANALYZER")

    # Subtitle
    painter.setPen(QColor("#a0a0b0"))
    painter.setFont(QFont("Roboto", 11))
    painter.drawText(0, 110, width, 25, Qt.AlignCenter, "AI-Powered Coaching Platform")

    # Version
    painter.setPen(QColor("#3a3a5a"))
    painter.setFont(QFont("JetBrains Mono", 9))
    painter.drawText(0, 145, width, 20, Qt.AlignCenter, f"v{app_version}")

    # Divider accent line
    painter.fillRect(160, 180, 200, 1, QColor("#d96600"))

    # Bottom border
    painter.fillRect(0, height - 2, width, 2, QColor("#d96600"))

    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    return splash


def _splash_status(splash: QSplashScreen, message: str) -> None:
    """Update splash screen status message and process events."""
    splash.showMessage(
        f"  {message}",
        Qt.AlignBottom | Qt.AlignLeft,
        QColor("#a0a0b0"),
    )
    QApplication.processEvents()


def _resolve_app_version() -> str:
    """Resolve installed package version with fallback."""
    try:
        return version("macena-cs2-analyzer")
    except PackageNotFoundError:
        return "1.0.0"


def _install_quit_handler(app: QApplication) -> None:
    """Wire graceful shutdown for app_state polling, lifecycle daemon, and Console.

    Ordering matters: stop polling first, then halt the Session Engine subprocess
    (Scanner/Digester/Teacher/Pulse) so its DB handles release before the Console
    closes its own database connections.
    """

    def _on_app_quit():
        from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
        from Programma_CS2_RENAN.backend.control.console import get_console
        from Programma_CS2_RENAN.core.lifecycle import lifecycle

        get_app_state().stop_polling()
        lifecycle.shutdown()
        get_console().shutdown()

    app.aboutToQuit.connect(_on_app_quit)


def _apply_theme(app: QApplication, splash: QSplashScreen) -> ThemeEngine:
    """Register fonts and apply the active theme; returns engine for later reuse."""
    _splash_status(splash, "Loading theme engine...")
    theme = ThemeEngine()
    theme.register_fonts()

    from Programma_CS2_RENAN.core.config import get_setting

    font_type = get_setting("FONT_TYPE", "Roboto")
    font_sizes = {"Small": 11, "Medium": 13, "Large": 16}
    font_pt = font_sizes.get(get_setting("FONT_SIZE", "Medium"), 13)
    theme._font_family = font_type
    theme._font_size = font_pt

    active_theme = get_setting("ACTIVE_THEME", "CS2")
    theme.apply_theme(active_theme, app)
    return theme


def _create_screens(theme: ThemeEngine) -> dict:
    """Instantiate all real screens (Phase 2). Returns name -> widget mapping.

    Screen imports are deferred so this module loads cheaply during tests that
    only need the helpers, and so a single broken screen surfaces as a focused
    ImportError rather than blocking module-level import.
    """
    from Programma_CS2_RENAN.apps.qt_app.screens.coach_screen import CoachScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.faceit_config_screen import FaceitConfigScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.help_screen import HelpScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.home_screen import HomeScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.match_detail_screen import MatchDetailScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.match_history_screen import MatchHistoryScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.performance_screen import PerformanceScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import ProComparisonScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.pro_player_detail_screen import (
        ProPlayerDetailScreen,
    )
    from Programma_CS2_RENAN.apps.qt_app.screens.profile_screen import ProfileScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.settings_screen import SettingsScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.steam_config_screen import SteamConfigScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.tactical_viewer_screen import TacticalViewerScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.user_profile_screen import UserProfileScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.wizard_screen import WizardScreen

    return {
        "match_history": MatchHistoryScreen(),
        "match_detail": MatchDetailScreen(),
        "performance": PerformanceScreen(),
        "settings": SettingsScreen(theme_engine=theme),
        "wizard": WizardScreen(),
        "user_profile": UserProfileScreen(),
        "profile": ProfileScreen(),
        "home": HomeScreen(),
        "coach": CoachScreen(),
        "steam_config": SteamConfigScreen(),
        "faceit_config": FaceitConfigScreen(),
        "help": HelpScreen(),
        "tactical_viewer": TacticalViewerScreen(),
        "pro_comparison": ProComparisonScreen(),
        "pro_player_detail": ProPlayerDetailScreen(),
    }


def _wire_screen_signals(window: MainWindow, screens: dict) -> None:
    """Wire cross-screen routing: history/home → match_detail, wizard → home,
    pro_comparison → pro_player_detail."""
    match_detail = screens["match_detail"]

    def _on_match_selected(demo_name: str):
        match_detail.load_demo(demo_name)
        window.switch_screen("match_detail")

    screens["match_history"].match_selected.connect(_on_match_selected)
    screens["home"].match_selected.connect(_on_match_selected)
    screens["wizard"].setup_completed.connect(lambda: window.switch_screen("home"))

    # Cluster C — drill-down from pro_comparison Details button.
    pro_detail = screens["pro_player_detail"]
    pro_compare = screens["pro_comparison"]

    def _on_pro_detail_requested(hltv_id: int) -> None:
        pro_detail.load_pro(hltv_id)
        window.switch_screen("pro_player_detail")

    pro_compare.pro_detail_requested.connect(_on_pro_detail_requested)
    pro_detail.back_requested.connect(lambda: window.switch_screen("pro_comparison"))


def _boot_backend_services(splash: QSplashScreen) -> bool:
    """Boot Console + Session Engine daemon. Errors logged, never raised.

    Without the Session Engine daemon, the Pulse thread never writes
    CoachState.last_heartbeat — the GUI would show "Service offline" and the
    Coach card would stall at "Idle".
    """
    _splash_status(splash, "Starting backend services...")
    from Programma_CS2_RENAN.backend.control.console import get_console

    boot_ok = True
    try:
        get_console().boot()
    except Exception:
        logging.exception("Backend boot failed")
        boot_ok = False

    _splash_status(splash, "Starting Session Engine daemon...")
    try:
        from Programma_CS2_RENAN.core.lifecycle import lifecycle

        if lifecycle.launch_daemon() is None:
            logging.error("Session Engine daemon failed to launch")
            boot_ok = False
    except Exception:
        logging.exception("Session Engine daemon launch failed")
        boot_ok = False

    return boot_ok


def _ensure_sbert_model(splash: QSplashScreen) -> None:
    """WR-10: pre-download the SBERT RAG model on first run; never block boot."""
    _splash_status(splash, "Checking AI language model...")
    try:
        from Programma_CS2_RENAN.backend.knowledge.rag_knowledge import KnowledgeEmbedder

        if KnowledgeEmbedder.is_model_cached():
            return

        _splash_status(splash, "Downloading AI language model (~90 MB, first time only)...")
        splash.repaint()
        QApplication.processEvents()

        # Download in foreground with splash visible — blocks but shows progress
        import threading

        download_done = threading.Event()
        download_ok = [False]

        def _do_download():
            download_ok[0] = KnowledgeEmbedder.download_model()
            download_done.set()

        t = threading.Thread(target=_do_download, daemon=True)
        t.start()

        # Keep splash responsive while downloading
        while not download_done.wait(timeout=0.1):
            QApplication.processEvents()

        if download_ok[0]:
            _splash_status(splash, "AI language model ready!")
        else:
            _splash_status(splash, "AI model download failed — using fallback")
    except Exception:
        # Don't block app startup over SBERT — coach falls back to dense
        # similarity. R4 MED: but never swallow silently (repo rule).
        logging.exception(
            "SBERT model check/download failed — coach will fall back to dense similarity"
        )


def _install_qt_excepthook() -> None:
    """Install a global excepthook that logs uncaught Qt signal/slot exceptions."""
    _original_excepthook = sys.excepthook

    def _qt_excepthook(exc_type, exc_value, exc_tb):
        logging.error("Uncaught exception in Qt", exc_info=(exc_type, exc_value, exc_tb))
        _original_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = _qt_excepthook


def _show_boot_failure_warning_if_needed(window: MainWindow, boot_ok: bool) -> None:
    """Show a modal warning if Console boot failed — needs visible parent window.

    R4 MED: the old probe re-called get_console() and caught exceptions —
    but boot failures happen inside .boot() (already logged by
    _boot_backend_services), while get_console() merely re-runs a
    construction that already succeeded, so the modal never showed. The
    boot outcome is now threaded through explicitly.
    """
    if not boot_ok:
        QMessageBox.warning(
            window,
            "Backend Startup Error",
            "The backend failed to initialize.\n\n"
            "The application will continue, but some features "
            "(demo ingestion, coaching) may not work.\n\n"
            "Check the log file for details.",
        )


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    app_version = _resolve_app_version()
    app.setApplicationName(f"Macena CS2 Analyzer v{app_version}")
    app.setApplicationVersion(app_version)

    splash = _create_splash(app_version)
    splash.show()
    QApplication.processEvents()

    # Connect graceful shutdown early — active even if boot fails
    _install_quit_handler(app)

    theme = _apply_theme(app, splash)

    _splash_status(splash, "Creating main window...")
    window = MainWindow()
    window.set_wallpaper(theme.wallpaper_path)

    placeholders = create_placeholder_screens()

    _splash_status(splash, "Initializing screens...")
    real_screens = _create_screens(theme)
    placeholders.update(real_screens)
    _wire_screen_signals(window, real_screens)

    _splash_status(splash, "Registering screens...")
    for name, widget in placeholders.items():
        window.register_screen(name, widget)

    # First-run gate
    from Programma_CS2_RENAN.core.config import get_setting

    if get_setting("SETUP_COMPLETED", False):
        window.switch_screen("home")
    else:
        window.switch_screen("wizard")

    # Store reference for theme switching from settings later
    window._theme_engine = theme

    boot_ok = _boot_backend_services(splash)
    _ensure_sbert_model(splash)

    _splash_status(splash, "Ready!")
    window.show()
    splash.finish(window)

    _show_boot_failure_warning_if_needed(window, boot_ok)

    # Background CoachState polling (10s interval)
    from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state

    get_app_state().start_polling()

    _install_qt_excepthook()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
