"""Boot round (WP3) — the splash must be gone the moment the dashboard is up.

The user reported "a little weird window that opens as well": the 520x320
frameless, always-on-top splash.  It stayed alive through backend boot and
a blocking SBERT download, and nothing guaranteed ``finish()`` on error
paths.  These tests pin the new contract: build the UI under the splash,
show the window, close the splash in ``finally`` — and everything slow
(Console boot, daemon spawn, SBERT) happens AFTER the window is visible.
"""

from __future__ import annotations

import logging
import os
import sys

import pytest
from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtWidgets import QApplication, QSplashScreen

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MACENA_UI_ANIMATIONS", "0")

# Same skip as test_ui_smoke: the GitHub Windows runner cannot host the full
# MainWindow composition (native crash).  Ubuntu CI + every local run cover it.
pytestmark = pytest.mark.skipif(
    bool(os.environ.get("CI")) and sys.platform == "win32",
    reason="GitHub Windows runner cannot host the full MainWindow composition",
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def theme(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine

    engine = ThemeEngine()
    engine.register_fonts()
    yield engine
    # _boot_ui applies the user's saved theme; leave the process on the
    # default palette so later modules see the tokens they expect.
    engine.apply_theme("CS2", qapp)


class _RecordingHandler(logging.Handler):
    """The ``cs2analyzer`` logger tree does not propagate to root, so caplog
    never sees it; attach directly to the boot logger instead."""

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.messages: list[str] = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@pytest.fixture
def boot_log():
    logger = logging.getLogger("cs2analyzer.boot")
    handler = _RecordingHandler()
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


def _flush(qapp, rounds: int = 8) -> None:
    for _ in range(rounds):
        qapp.processEvents()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()


def _release(window) -> None:
    """Destroy a MainWindow NOW (D-37): no hidden C++ window may outlive the module."""
    window.close()
    window.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QApplication.processEvents()


def _visible_splashes():
    return [
        w for w in QApplication.topLevelWidgets() if isinstance(w, QSplashScreen) and w.isVisible()
    ]


def test_splash_is_gone_once_the_main_window_shows(qapp, theme, boot_log):
    from Programma_CS2_RENAN.apps.qt_app import app as app_module
    from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow

    window, screens = app_module._boot_ui(qapp, theme, "1.0.0")
    try:
        _flush(qapp)
        assert isinstance(window, MainWindow)
        assert window.isVisible()
        assert set(screens) >= {"home", "wizard", "help", "performance", "coach"}
        assert _visible_splashes() == []
        # The ONLY visible top-level window is the dashboard. This is the
        # assertion that caught the stray parentless QLabel ("Pick a pro
        # from the comparison screen.") shown at boot as its own window.
        visible = [w for w in QApplication.topLevelWidgets() if w.isVisible() and w.isWindow()]
        assert visible == [window], [
            (type(w).__name__, getattr(w, "text", lambda: "")()) for w in visible
        ]
        assert any("boot phase" in msg for msg in boot_log.messages)
    finally:
        _release(window)


def test_walking_every_screen_opens_no_extra_window(qapp, theme):
    """Navigation must never turn a child widget into its own window."""
    from Programma_CS2_RENAN.apps.qt_app import app as app_module

    window, screens = app_module._boot_ui(qapp, theme, "1.0.0")
    try:
        strays: dict[str, list[str]] = {}
        for name in screens:
            window.switch_screen(name)
            _flush(qapp)
            assert window.current_screen_name() == name
            extra = [
                f"{type(w).__name__}:{getattr(w, 'text', lambda: '')()}"
                for w in QApplication.topLevelWidgets()
                if w.isVisible() and w.isWindow() and w is not window
            ]
            if extra:
                strays[name] = extra
        assert strays == {}
    finally:
        _release(window)


def test_splash_closes_even_when_composition_fails(qapp, theme, monkeypatch):
    from Programma_CS2_RENAN.apps.qt_app import app as app_module
    from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow

    def _boom(_theme):
        raise RuntimeError("screen construction failed")

    monkeypatch.setattr(app_module, "_create_screens", _boom)
    with pytest.raises(RuntimeError, match="screen construction failed"):
        app_module._boot_ui(qapp, theme, "1.0.0")
    _flush(qapp)
    assert _visible_splashes() == []
    survivors = [w for w in QApplication.topLevelWidgets() if isinstance(w, MainWindow)]
    assert survivors == [], "a half-built MainWindow must not survive a failed boot"


class _WizardStub(QObject):
    setup_completed = Signal()


def test_backend_boot_waits_for_the_wizard_on_first_run(qapp, monkeypatch):
    import Programma_CS2_RENAN.core.config as config
    from Programma_CS2_RENAN.apps.qt_app import app as app_module

    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: False if key == "SETUP_COMPLETED" else default,
    )
    calls: list[str] = []
    wizard = _WizardStub()

    started_now = app_module._schedule_backend_boot(
        {"wizard": wizard}, start=lambda: calls.append("boot")
    )

    assert started_now is False
    assert calls == []
    wizard.setup_completed.emit()
    qapp.processEvents()
    assert calls == ["boot"]


def test_backend_boot_starts_immediately_after_setup(qapp, monkeypatch):
    import Programma_CS2_RENAN.core.config as config
    from Programma_CS2_RENAN.apps.qt_app import app as app_module

    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: True if key == "SETUP_COMPLETED" else default,
    )
    calls: list[str] = []
    wizard = _WizardStub()

    started_now = app_module._schedule_backend_boot(
        {"wizard": wizard}, start=lambda: calls.append("boot")
    )

    assert started_now is True
    assert calls == ["boot"]
    wizard.setup_completed.emit()
    qapp.processEvents()
    assert calls == ["boot"], "the wizard signal must not boot a second time"


class _WindowStub(QObject):
    screen_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.switched: list[str] = []
        self._current = "wizard"

    def current_screen_name(self) -> str:
        return self._current

    def switch_screen(self, name: str) -> None:
        self._current = name
        self.switched.append(name)


def test_backend_boot_chain_completes_on_the_event_loop(qapp, monkeypatch):
    """Backend result -> land on home -> SBERT check, with QObject slots only.

    The first version chained a second Worker (lambda receivers) from inside
    the backend worker's result callback; with the SBERT model cached that
    worker's signals object was created and destroyed on a pool thread while
    the main thread was still inside the callback — access violation in
    ``app.exec()`` two seconds after boot (real pythonw run, faulthandler).
    """
    import time

    from Programma_CS2_RENAN.apps.qt_app import app as app_module

    monkeypatch.setattr(app_module, "_boot_backend_services", lambda: True)
    sbert_calls: list[str] = []
    monkeypatch.setattr(
        app_module, "_sbert_model_cached", lambda: sbert_calls.append("checked") or True
    )
    window = _WindowStub()

    coordinator = app_module._start_backend_async(window, then=lambda: window.switch_screen("home"))

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not coordinator.sbert_checked:
        qapp.processEvents()
        time.sleep(0.01)
    assert coordinator.backend_ok is True
    assert window.switched == ["home"]
    assert coordinator.sbert_checked is True
    assert sbert_calls == ["checked"]


def test_backend_boot_starts_when_the_user_leaves_the_wizard_unfinished(qapp, monkeypatch):
    """The wizard is a stacked screen: the sidebar lets users skip it. Skipping
    means accepting the defaults — the backend must boot on the first hop away."""
    import Programma_CS2_RENAN.core.config as config
    from Programma_CS2_RENAN.apps.qt_app import app as app_module

    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: False if key == "SETUP_COMPLETED" else default,
    )
    calls: list[str] = []
    wizard = _WizardStub()
    window = _WindowStub()

    started_now = app_module._schedule_backend_boot(
        {"wizard": wizard}, start=lambda: calls.append("boot"), window=window
    )
    assert started_now is False

    window.screen_changed.emit("wizard")  # landing on the wizard itself is not a hop away
    qapp.processEvents()
    assert calls == []

    window.screen_changed.emit("home")
    qapp.processEvents()
    assert calls == ["boot"]

    wizard.setup_completed.emit()
    window.screen_changed.emit("coach")
    qapp.processEvents()
    assert calls == ["boot"], "boot happens exactly once"


def test_main_dispatches_the_daemon_flag_without_a_gui(monkeypatch):
    from Programma_CS2_RENAN.apps.qt_app import app as app_module

    calls: list[str] = []
    monkeypatch.setattr(app_module, "_run_daemon", lambda: calls.append("daemon") or 0)
    monkeypatch.setattr(app_module, "_run_gui", lambda argv: calls.append("gui") or 0)
    assert app_module.main(["--daemon"]) == 0
    assert calls == ["daemon"]


def test_main_dispatches_the_selftest_flag_without_a_gui(monkeypatch):
    from Programma_CS2_RENAN.apps.qt_app import app as app_module

    calls: list[str] = []
    monkeypatch.setattr(app_module, "_run_selftest", lambda: calls.append("selftest") or 0)
    monkeypatch.setattr(app_module, "_run_gui", lambda argv: calls.append("gui") or 0)
    assert app_module.main(["--selftest"]) == 0
    assert calls == ["selftest"]


def test_main_defaults_to_the_gui(monkeypatch):
    from Programma_CS2_RENAN.apps.qt_app import app as app_module

    calls: list[str] = []
    monkeypatch.setattr(app_module, "_run_gui", lambda argv: calls.append(tuple(argv)) or 0)
    assert app_module.main([]) == 0
    assert calls == [()]


def test_second_launch_raises_the_running_instance_instead_of_a_dialog(qapp, monkeypatch):
    """Close-to-tray + relaunch used to show 'Macena is already running'."""
    from PySide6.QtWidgets import QMessageBox

    from Programma_CS2_RENAN.apps.qt_app import app as app_module
    from Programma_CS2_RENAN.apps.qt_app.core import instance_guard
    from Programma_CS2_RENAN.core.lifecycle import lifecycle

    monkeypatch.setattr(lifecycle, "ensure_single_instance", lambda: False)
    notified: list[str] = []
    monkeypatch.setattr(
        instance_guard, "notify_running_instance", lambda name, **kw: notified.append(name) or True
    )

    def _no_dialog(*args, **kwargs):
        raise AssertionError("no dialog when the running instance could be raised")

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(_no_dialog))

    assert app_module._run_gui([]) == 0
    assert notified == [app_module.INSTANCE_NAME]


def test_no_main_window_survives_this_module(qapp):
    from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow

    _flush(qapp)
    survivors = [w for w in QApplication.topLevelWidgets() if isinstance(w, MainWindow)]
    assert survivors == []
