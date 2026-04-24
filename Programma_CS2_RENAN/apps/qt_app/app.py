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


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    try:
        _version = version("macena-cs2-analyzer")
    except PackageNotFoundError:
        _version = "1.0.0"

    app.setApplicationName(f"Macena CS2 Analyzer v{_version}")
    app.setApplicationVersion(_version)

    # Show splash screen immediately
    splash = _create_splash(_version)
    splash.show()
    QApplication.processEvents()

    # Connect graceful shutdown early — active even if boot fails
    def _on_app_quit():
        from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
        from Programma_CS2_RENAN.backend.control.console import get_console
        from Programma_CS2_RENAN.core.lifecycle import lifecycle

        get_app_state().stop_polling()
        # Stop the Session Engine subprocess (Scanner/Digester/Teacher/Pulse)
        # before tearing down the Console so its DB handles are free.
        lifecycle.shutdown()
        get_console().shutdown()

    app.aboutToQuit.connect(_on_app_quit)

    # Register custom fonts and apply theme + font
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

    # Create main window
    _splash_status(splash, "Creating main window...")
    window = MainWindow()

    # Set initial wallpaper
    window.set_wallpaper(theme.wallpaper_path)

    # Register placeholder screens for pages not yet ported
    placeholders = create_placeholder_screens()

    # ── Phase 2: Real data screens ──
    _splash_status(splash, "Initializing screens...")
    from Programma_CS2_RENAN.apps.qt_app.screens.coach_screen import CoachScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.faceit_config_screen import FaceitConfigScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.help_screen import HelpScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.home_screen import HomeScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.match_detail_screen import MatchDetailScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.match_history_screen import MatchHistoryScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.performance_screen import PerformanceScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import ProComparisonScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.profile_screen import ProfileScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.settings_screen import SettingsScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.steam_config_screen import SteamConfigScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.tactical_viewer_screen import TacticalViewerScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.user_profile_screen import UserProfileScreen
    from Programma_CS2_RENAN.apps.qt_app.screens.wizard_screen import WizardScreen

    match_history = MatchHistoryScreen()
    match_detail = MatchDetailScreen()
    performance = PerformanceScreen()
    settings = SettingsScreen(theme_engine=theme)
    wizard = WizardScreen()
    user_profile = UserProfileScreen()
    profile = ProfileScreen()
    home = HomeScreen()
    coach = CoachScreen()
    steam_config = SteamConfigScreen()
    faceit_config = FaceitConfigScreen()
    help_screen = HelpScreen()
    tactical_viewer = TacticalViewerScreen()
    pro_comparison = ProComparisonScreen()

    # Wire match selection: history → detail
    def _on_match_selected(demo_name: str):
        match_detail.load_demo(demo_name)
        window.switch_screen("match_detail")

    match_history.match_selected.connect(_on_match_selected)

    # Replace placeholders with real screens
    placeholders["match_history"] = match_history
    placeholders["match_detail"] = match_detail
    placeholders["performance"] = performance
    placeholders["settings"] = settings
    placeholders["wizard"] = wizard
    placeholders["user_profile"] = user_profile
    placeholders["profile"] = profile
    placeholders["home"] = home
    placeholders["coach"] = coach
    placeholders["steam_config"] = steam_config
    placeholders["faceit_config"] = faceit_config
    placeholders["help"] = help_screen
    placeholders["tactical_viewer"] = tactical_viewer
    placeholders["pro_comparison"] = pro_comparison

    # Wire wizard completion: wizard → home
    wizard.setup_completed.connect(lambda: window.switch_screen("home"))

    # Register all screens
    _splash_status(splash, "Registering screens...")
    for name, widget in placeholders.items():
        window.register_screen(name, widget)

    # First-run gate: show wizard if setup not completed
    if get_setting("SETUP_COMPLETED", False):
        window.switch_screen("home")
    else:
        window.switch_screen("wizard")

    # Store references for theme switching later
    window._theme_engine = theme

    # Boot backend console (DB audit, conditional FlareSolverr/Hunter)
    _splash_status(splash, "Starting backend services...")
    from Programma_CS2_RENAN.backend.control.console import get_console

    try:
        get_console().boot()
    except Exception:
        logging.exception("Backend boot failed")

    # Launch the Session Engine daemon (Scanner/Digester/Teacher/Pulse). Without
    # this the Pulse thread never writes CoachState.last_heartbeat, so the GUI
    # shows "Service offline" and the Coach card stalls at "Idle".
    _splash_status(splash, "Starting Session Engine daemon...")
    try:
        from Programma_CS2_RENAN.core.lifecycle import lifecycle

        if lifecycle.launch_daemon() is None:
            logging.error("Session Engine daemon failed to launch")
    except Exception:
        logging.exception("Session Engine daemon launch failed")

    # WR-10: Pre-download SBERT model with progress dialog if not cached
    _splash_status(splash, "Checking AI language model...")
    try:
        from Programma_CS2_RENAN.backend.knowledge.rag_knowledge import KnowledgeEmbedder

        if not KnowledgeEmbedder.is_model_cached():
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
        pass  # Don't block app startup over SBERT

    _splash_status(splash, "Ready!")
    window.show()
    splash.finish(window)

    # Show boot failure warning AFTER window is visible (modal dialog needs parent)
    try:
        get_console()  # already created above
    except Exception:
        QMessageBox.warning(
            window,
            "Backend Startup Error",
            "The backend failed to initialize.\n\n"
            "The application will continue, but some features "
            "(demo ingestion, coaching) may not work.\n\n"
            "Check the log file for details.",
        )

    # Start background CoachState polling (10s interval)
    from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state

    get_app_state().start_polling()

    # Install global exception handler for uncaught exceptions in signal/slot dispatch
    _original_excepthook = sys.excepthook

    def _qt_excepthook(exc_type, exc_value, exc_tb):
        logging.error("Uncaught exception in Qt", exc_info=(exc_type, exc_value, exc_tb))
        _original_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = _qt_excepthook

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
