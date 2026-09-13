"""
Application entry point — launches the PySide6 Qt frontend.

Usage:
    python -m Programma_CS2_RENAN.apps.qt_app.app              # the dashboard
    python -m Programma_CS2_RENAN.apps.qt_app.app --daemon     # Session Engine (spawned by the GUI)
    python -m Programma_CS2_RENAN.apps.qt_app.app --selftest   # headless runtime probe (build/CI)

Boot contract (WP3, 2026-09): the splash lives only while the UI is
composed; the window is shown, the splash is closed in ``finally``, and
everything slow — Console boot, the daemon spawn, the SBERT model check —
runs afterwards on the thread pool. On a first run the backend waits for
the setup wizard so no data is created at a location the user has not
chosen yet.
"""

import logging
import os
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from typing import Callable, Optional

from PySide6.QtCore import QObject, QProcess, Qt, QThreadPool, QTimer, Slot
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow
from Programma_CS2_RENAN.apps.qt_app.screens.placeholder import create_placeholder_screens

# Local-socket name the first instance listens on; a second launch sends
# RAISE here instead of showing "already running" (core/instance_guard.py).
INSTANCE_NAME = "MacenaCS2Analyzer"

from Programma_CS2_RENAN.observability.logger_setup import get_logger  # noqa: E402

_boot_log = get_logger("cs2analyzer.boot")


class _PhaseTimer:
    """Boot timeline: one INFO line per phase so reports carry evidence."""

    def __init__(self) -> None:
        self._start = time.monotonic()
        self._last = self._start

    def mark(self, phase: str) -> None:
        now = time.monotonic()
        _boot_log.info(
            "boot phase %-16s %6.0f ms (total %6.0f ms)",
            phase,
            (now - self._last) * 1000,
            (now - self._start) * 1000,
        )
        self._last = now


def _create_splash(app_version: str) -> QSplashScreen:
    """Create a themed splash screen with gradient background and branding.

    Colors come from the saved theme's design tokens so the splash never
    drifts from the app palette (it used to hardcode the pre-atlas hexes).
    Call AFTER ThemeEngine.register_fonts() so the display stack resolves.
    """
    from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
    from Programma_CS2_RENAN.core.config import get_setting

    tokens = get_tokens(get_setting("ACTIVE_THEME", "CS2"))
    width, height = 520, 320
    pixmap = QPixmap(width, height)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Deep-surface gradient (base -> sunken)
    gradient = QLinearGradient(0, 0, 0, height)
    gradient.setColorAt(0.0, QColor(tokens.surface_base))
    gradient.setColorAt(1.0, QColor(tokens.surface_sunken))
    painter.fillRect(0, 0, width, height, gradient)

    # Accent bar at top
    painter.fillRect(0, 0, width, 4, QColor(tokens.accent_primary))

    # App title (display stack)
    painter.setPen(QColor(tokens.text_primary))
    painter.setFont(QFont("Space Grotesk", 22, QFont.Bold))
    painter.drawText(0, 70, width, 40, Qt.AlignCenter, "MACENA CS2 ANALYZER")

    # Subtitle
    painter.setPen(QColor(tokens.text_secondary))
    painter.setFont(QFont("Inter", 11))
    painter.drawText(0, 110, width, 25, Qt.AlignCenter, "AI-Powered Coaching Platform")

    # Version
    painter.setPen(QColor(tokens.text_tertiary))
    painter.setFont(QFont("JetBrains Mono", 9))
    painter.drawText(0, 145, width, 20, Qt.AlignCenter, f"v{app_version}")

    # Divider accent line
    painter.fillRect(160, 180, 200, 1, QColor(tokens.accent_primary))

    # Bottom border
    painter.fillRect(0, height - 2, width, 2, QColor(tokens.accent_primary))

    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    return splash


def _splash_status(splash: QSplashScreen, message: str) -> None:
    """Update splash screen status message and process events."""
    from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

    # Token, not a literal — the old hardcoded #a0a0b0 was pre-atlas text_secondary.
    splash.showMessage(
        f"  {message}",
        Qt.AlignBottom | Qt.AlignLeft,
        QColor(get_tokens().text_secondary),
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


def _apply_theme(app: QApplication, splash: QSplashScreen, theme: ThemeEngine) -> ThemeEngine:
    """Apply the active theme via a pre-built engine (fonts already registered
    in main() so the splash can use the display stack)."""
    _splash_status(splash, "Loading theme engine...")

    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import normalize_font_family
    from Programma_CS2_RENAN.core.config import get_setting

    font_type = normalize_font_family(get_setting("FONT_TYPE", "Roboto"))
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
    """Wire cross-screen routing: history/home → match_detail, match_detail
    moments → tactical_viewer, pro_comparison → pro_player_detail.

    The wizard → home hop is NOT wired here: on a first run the backend boots
    only after the wizard, and home is entered once that boot has finished
    (see ``_run_gui``), so its view-models never query a database whose
    tables do not exist yet.
    """
    match_detail = screens["match_detail"]

    def _on_match_selected(demo_name: str):
        match_detail.load_demo(demo_name)
        window.switch_screen("match_detail")

    screens["match_history"].match_selected.connect(_on_match_selected)
    screens["home"].match_selected.connect(_on_match_selected)

    # Highlights "Open in Tactical Viewer" deep-link: seek (when that demo
    # is loaded) then switch — the viewer logs/toasts the miss otherwise.
    tactical = screens["tactical_viewer"]

    def _on_moment(demo: str, tick: int) -> None:
        tactical.open_moment(demo, tick)
        window.switch_screen("tactical_viewer")

    match_detail.moment_selected.connect(_on_moment)

    # Cluster C — drill-down from pro_comparison Details button.
    pro_detail = screens["pro_player_detail"]
    pro_compare = screens["pro_comparison"]

    def _on_pro_detail_requested(hltv_id: int) -> None:
        pro_detail.load_pro(hltv_id)
        window.switch_screen("pro_player_detail")

    pro_compare.pro_detail_requested.connect(_on_pro_detail_requested)
    pro_detail.back_requested.connect(lambda: window.switch_screen("pro_comparison"))


def _boot_backend_services() -> bool:
    """Boot Console + Session Engine daemon. Errors logged, never raised.

    Runs on the thread pool AFTER the window is visible (never under the
    splash). Without the Session Engine daemon, the Pulse thread never
    writes CoachState.last_heartbeat — the GUI would show "Service offline"
    and the Coach card would stall at "Idle".
    """
    from Programma_CS2_RENAN.backend.control.console import get_console

    boot_ok = True
    _boot_log.info("backend: starting Console")
    try:
        get_console().boot()
    except Exception:
        logging.exception("Backend boot failed")
        boot_ok = False

    _boot_log.info("backend: starting Session Engine daemon")
    try:
        from Programma_CS2_RENAN.core.lifecycle import lifecycle

        if lifecycle.launch_daemon() is None:
            logging.error("Session Engine daemon failed to launch")
            boot_ok = False
    except Exception:
        logging.exception("Session Engine daemon launch failed")
        boot_ok = False

    return boot_ok


_SBERT_MODEL = "all-MiniLM-L6-v2"


def _sbert_model_cached() -> bool:
    """Cheap directory probe (WR-10) — safe on the GUI thread."""
    from Programma_CS2_RENAN.backend.knowledge.rag_knowledge import KnowledgeEmbedder

    return bool(KnowledgeEmbedder.is_model_cached(_SBERT_MODEL))


def _download_sbert_model() -> bool:
    """WR-10: download the SBERT RAG model on first run. Thread-pool job, toasts around it."""
    from Programma_CS2_RENAN.backend.knowledge.rag_knowledge import KnowledgeEmbedder
    from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

    try:
        get_state_manager().add_notification(
            "knowledge",
            "INFO",
            "Downloading the AI language model (~90 MB, first time only) in the background.",
        )
    except Exception:  # noqa: BLE001 — a toast must never block the download
        logging.debug("SBERT start notification skipped", exc_info=True)

    ok = KnowledgeEmbedder.download_model(_SBERT_MODEL)
    try:
        get_state_manager().add_notification(
            "knowledge",
            "INFO" if ok else "WARNING",
            (
                "AI language model ready."
                if ok
                else "AI language model download failed — the coach falls back to dense similarity."
            ),
        )
    except Exception:  # noqa: BLE001
        logging.debug("SBERT finish notification skipped", exc_info=True)
    return ok


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


class _BootCoordinator(QObject):
    """Owns the post-window boot chain: backend -> landing screen -> SBERT.

    Every cross-thread signal lands on a real QObject slot, and the SBERT
    step is scheduled through the event loop rather than started from
    inside the backend callback. The first version chained a second
    Worker with lambda receivers from inside that callback; with the
    model cached the new worker's signals object was created and destroyed
    on a pool thread while the main thread was still in the callback —
    a native access violation in ``app.exec()`` two seconds after boot
    (caught with faulthandler on a real pythonw launch).
    """

    def __init__(self, window, then: Optional[Callable[[], None]] = None, parent=None):
        super().__init__(parent)
        self._window = window
        self._then = then
        self.backend_ok: Optional[bool] = None
        self.sbert_checked = False

    def start(self) -> None:
        from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker

        worker = Worker(_boot_backend_services)
        worker.signals.result.connect(self._on_backend_result)
        worker.signals.error.connect(self._on_backend_error)
        QThreadPool.globalInstance().start(worker)

    @Slot(object)
    def _on_backend_result(self, ok) -> None:
        self._finish(bool(ok))

    @Slot(str)
    def _on_backend_error(self, msg: str) -> None:
        logging.error("Backend boot crashed: %s", msg)
        self._finish(False)

    def _finish(self, ok: bool) -> None:
        self.backend_ok = ok
        _boot_log.info("backend: boot %s", "complete" if ok else "FAILED")
        _show_boot_failure_warning_if_needed(self._window, ok)
        if self._then is not None:
            self._then()
        # Next step from the event loop, never nested inside this callback.
        QTimer.singleShot(0, self._start_sbert)

    @Slot()
    def _start_sbert(self) -> None:
        from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker

        self.sbert_checked = True
        try:
            cached = _sbert_model_cached()
        except Exception:  # noqa: BLE001 — never let the RAG check hurt boot
            logging.exception("SBERT cache probe failed — coach falls back to dense similarity")
            return
        if cached:
            return
        worker = Worker(_download_sbert_model)
        worker.signals.error.connect(self._on_sbert_error)
        QThreadPool.globalInstance().start(worker)

    @Slot(str)
    def _on_sbert_error(self, msg: str) -> None:
        logging.error(
            "SBERT model download failed — coach will fall back to dense similarity: %s", msg
        )


def _start_backend_async(
    window: MainWindow, then: Optional[Callable[[], None]] = None
) -> _BootCoordinator:
    """Console boot + daemon spawn on the thread pool, then landing + SBERT check."""
    coordinator = _BootCoordinator(window, then=then, parent=window)
    coordinator.start()
    return coordinator


def _schedule_backend_boot(screens: dict, start: Callable[[], None], window=None) -> bool:
    """Start the backend now, or after the setup wizard on a first run.

    Returns True when ``start`` ran immediately. On a first run nothing is
    booted (no database, no daemon, no downloads) until the user either
    finishes the wizard (``setup_completed``) or leaves it through the
    sidebar (``window.screen_changed`` to any other screen) — skipping the
    wizard means accepting the default data location. ``start`` runs once.
    """
    from Programma_CS2_RENAN.core.config import get_setting

    wizard = screens.get("wizard")
    if get_setting("SETUP_COMPLETED", False) or wizard is None:
        start()
        return True

    fired = {"done": False}

    def _once() -> None:
        if fired["done"]:
            return
        fired["done"] = True
        start()

    wizard.setup_completed.connect(_once)
    if window is not None:
        window.screen_changed.connect(lambda name: name != "wizard" and _once())
    return False


def _data_root_changed() -> bool:
    """True when the wizard saved a brain root other than the one config
    resolved at import (WP4a).  Paths are import-time constants, so the
    choice can only take effect in a fresh process."""
    from Programma_CS2_RENAN.core import config

    chosen = str(config.get_setting("BRAIN_DATA_ROOT", "") or "").strip()
    if not chosen:
        return False

    def _norm(path: str) -> str:
        return os.path.normcase(os.path.normpath(os.path.expanduser(path)))

    return _norm(chosen) != _norm(config.USER_DATA_ROOT)


def _start_detached(program: str, args: list) -> bool:
    result = QProcess.startDetached(program, list(args))
    return bool(result[0]) if isinstance(result, tuple) else bool(result)


def _relaunch_for_new_data_root(app, spawn=None) -> bool:
    """Apply a brain root chosen in the wizard by restarting the GUI.

    Returns False, and changes nothing, when the root is unchanged.  Otherwise
    the single-instance lock is released, a fresh GUI process is started and
    this one quits; nothing has been booted yet at this point (backend boot
    waits for the wizard, D-48).  If the new process cannot be started the
    lock is re-armed and the current process carries on with the root it has.
    """
    if not _data_root_changed():
        return False
    from Programma_CS2_RENAN.core.lifecycle import lifecycle

    argv = lifecycle.relaunch_command()
    lifecycle.shutdown()
    if not (spawn or _start_detached)(argv[0], argv[1:]):
        _boot_log.error("relaunch failed, keeping this process: %s", argv)
        lifecycle.ensure_single_instance()
        return False
    _boot_log.info("boot phase relaunch          data root changed: %s", argv)
    app.quit()
    return True


def _init_database_schema() -> None:
    """Schema-only step (create_all + missing columns) before the UI queries anything."""
    try:
        from Programma_CS2_RENAN.backend.storage.database import init_database

        init_database()
    except Exception:
        logging.exception("Database schema init failed — screens will show error states")


def _boot_ui(app: QApplication, theme: ThemeEngine, app_version: str):
    """Compose and show the dashboard under the splash. Returns (window, screens).

    The splash is closed in ``finally`` — on the success path via
    ``finish(window)`` once the window is exposed, on every error path via
    ``close()`` — so no boot failure can strand it on screen. A half-built
    MainWindow is destroyed on failure (D-37: no hidden window survives).
    """
    phases = _PhaseTimer()
    splash = _create_splash(app_version)
    splash.setAttribute(Qt.WA_DeleteOnClose, True)
    splash.show()
    QApplication.processEvents()
    phases.mark("splash")

    window: Optional[MainWindow] = None
    try:
        _apply_theme(app, splash, theme)
        phases.mark("theme")

        _splash_status(splash, "Creating main window...")
        window = MainWindow()
        window.apply_wallpaper_state(theme)
        phases.mark("main window")

        placeholders = create_placeholder_screens()
        _splash_status(splash, "Initializing screens...")
        real_screens = _create_screens(theme)
        placeholders.update(real_screens)
        _wire_screen_signals(window, real_screens)
        phases.mark("screens")

        _splash_status(splash, "Registering screens...")
        for name, widget in placeholders.items():
            window.register_screen(name, widget)

        # First-run gate
        from Programma_CS2_RENAN.core.config import get_setting

        window.switch_screen("home" if get_setting("SETUP_COMPLETED", False) else "wizard")

        # Store reference for theme switching from settings later
        window._theme_engine = theme

        _splash_status(splash, "Ready!")
        window.show()
        # DOCK-01: a restored floating window can steal first presentation —
        # the main window must end up in front and focused on every boot.
        window.raise_()
        window.activateWindow()
        phases.mark("window shown")
        return window, real_screens
    except BaseException:
        if window is not None:
            window.deleteLater()
        raise
    finally:
        if window is not None and window.isVisible():
            splash.finish(window)
        else:
            splash.close()


def _raise_window(window: MainWindow) -> None:
    window.showNormal()
    window.raise_()
    window.activateWindow()


def _run_gui(argv: list) -> int:
    if QApplication.instance() is None:
        # High-DPI support — must precede QApplication construction.
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    app = QApplication.instance() or QApplication([sys.argv[0], *argv])

    app_version = _resolve_app_version()
    app.setApplicationName(f"Macena CS2 Analyzer v{app_version}")
    app.setApplicationVersion(app_version)

    # Q6-TRAY: the single-instance guard — two GUI processes mean two
    # Consoles + two session-engine daemons writing the same SQLite files.
    from Programma_CS2_RENAN.apps.qt_app.core import instance_guard
    from Programma_CS2_RENAN.core.lifecycle import lifecycle

    if not lifecycle.ensure_single_instance():
        # Close-to-tray keeps the first instance alive; ask it to come to
        # the front instead of refusing with a dialog.
        if instance_guard.notify_running_instance(INSTANCE_NAME):
            logging.info("Macena is already running — raised the existing window")
            return 0
        QMessageBox.warning(
            None,
            "Macena CS2 Analyzer",
            "Macena is already running — check the system tray (bottom-right, near the clock).",
        )
        return 1

    # Fonts must precede the splash so its painter can use the display stack.
    theme = ThemeEngine()
    theme.register_fonts()

    # Connect graceful shutdown early — active even if boot fails
    _install_quit_handler(app)

    from Programma_CS2_RENAN.core.config import get_setting

    first_run = not get_setting("SETUP_COMPLETED", False)
    if not first_run:
        _init_database_schema()

    window, screens = _boot_ui(app, theme, app_version)

    guard = instance_guard.InstanceGuard(INSTANCE_NAME, parent=window)
    guard.listen(lambda: _raise_window(window))
    window._instance_guard = guard

    # Q6-TRAY: tray icon + close-to-tray. When a tray exists the app must
    # NOT die with the last hidden window — quit flows only through the
    # tray's Quit action (or an unarmed close falling through closeEvent).
    from Programma_CS2_RENAN.apps.qt_app.core.tray import build_tray

    tray = build_tray(window)
    if tray is not None:
        window.attach_tray(tray)
        app.setQuitOnLastWindowClosed(False)

    # Backend (Console, daemon, SBERT) after the window is up; on a first
    # run only once the wizard is finished or skipped, then land on home
    # (unless the user already navigated elsewhere).
    def _land_on_home() -> None:
        if window.current_screen_name() == "wizard":
            window.switch_screen("home")

    then = _land_on_home if first_run else None

    def _start_backend() -> None:
        if first_run and _relaunch_for_new_data_root(app):
            return
        window._boot_coordinator = _start_backend_async(window, then=then)

    _schedule_backend_boot(screens, start=_start_backend, window=window)

    # Background CoachState polling (10s interval)
    from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state

    get_app_state().start_polling()

    _install_qt_excepthook()

    return app.exec()


def _run_daemon() -> int:
    """``--daemon``: run the Session Engine in this process (spawned by the GUI)."""
    os.environ.setdefault("CS2_LOG_ROLE", "daemon")
    from Programma_CS2_RENAN.core.session_engine import run_session_loop

    run_session_loop()
    return 0


def _run_selftest() -> int:
    """``--selftest``: headless runtime probe for the packaged build."""
    from Programma_CS2_RENAN.core.selftest import main as selftest_main

    return selftest_main()


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    # Frozen-build hook: multiprocessing.freeze_support() + cwd stabilisation.
    # The module runs hook() on import; this is its production caller (it was
    # dead code — the PyInstaller spec declares no runtime hooks).
    from Programma_CS2_RENAN.core import frozen_hook  # noqa: F401

    if "--daemon" in args:
        return _run_daemon()
    if "--selftest" in args:
        return _run_selftest()
    return _run_gui([a for a in args if a not in ("--daemon", "--selftest")])


if __name__ == "__main__":
    sys.exit(main())
