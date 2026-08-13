"""Runtime smoke tests — boot the real UI and exercise it end-to-end.

These are the regression net the screenshot harness alone can't provide:
the FULL window composition (all screens registered, exactly as app.py
composes them) is driven through every screen's on_enter/on_leave
lifecycle, live theme switches, language round-trips, sidebar collapse,
and window resizes. Any crash in construction, navigation, theme_changed
handlers, retranslate, or paint scheduling fails loudly here.

Backend daemons / SBERT / polling are intentionally NOT started — the app
is designed to run degraded without them, and the UI layer must never
require them to stay alive.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MACENA_UI_ANIMATIONS", "0")  # deterministic end states

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_REPO / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO / "tools"))


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(scope="module")
def window(qapp):
    """Real MainWindow + every real screen, composed like app.main() minus backend."""
    from Programma_CS2_RENAN.apps.qt_app import app as qt_app_module
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
    from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow

    theme = ThemeEngine()
    theme.register_fonts()
    theme.apply_theme("CS2", qapp)

    win = MainWindow()
    win.set_wallpaper("")
    screens = qt_app_module._create_screens(theme)
    for name, widget in screens.items():
        win.register_screen(name, widget)
    win.resize(1440, 900)
    win.show()
    qapp.processEvents()

    win._smoke_screens = screens
    win._smoke_theme = theme
    yield win

    win.close()
    qapp.processEvents()


def _drain(qapp, rounds: int = 8):
    for _ in range(rounds):
        qapp.processEvents()


def test_walk_every_screen(qapp, window):
    """Every registered screen must survive on_enter/on_leave navigation."""
    for name in window._smoke_screens:
        window.switch_screen(name)
        _drain(qapp)
    # End on a data screen with fixtures injected so painted paths run too.
    import ui_fixtures

    window.switch_screen("match_history")
    _drain(qapp)
    assert ui_fixtures.inject("match_history", window._smoke_screens["match_history"])
    _drain(qapp)
    assert window.isVisible()


def test_live_theme_switching_on_every_theme(qapp, window):
    """apply_theme while the window is alive must restyle without crashing."""
    from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import THEME_NAMES

    window.switch_screen("home")
    _drain(qapp)
    for name in (*THEME_NAMES, "CS2"):
        window._smoke_theme.apply_theme(name, qapp)
        _drain(qapp)
        assert get_tokens(name).accent_primary in qapp.styleSheet()
    assert window.isVisible()


def test_language_roundtrip_retranslates(qapp, window):
    """en → it → pt → en must retranslate nav + screens without crashing."""
    from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n

    original = i18n.lang
    try:
        for lang in ("it", "pt", "en"):
            i18n.set_language(lang)
            _drain(qapp)
    finally:
        i18n.set_language(original)
        _drain(qapp)
    assert window.isVisible()


def test_sidebar_collapse_expand_and_resize(qapp, window):
    """Collapse/expand animation and window resizes must not crash layout."""
    sidebar = window._nav_sidebar
    sidebar.toggle_collapse()
    _drain(qapp, rounds=20)
    sidebar.toggle_collapse()
    _drain(qapp, rounds=20)
    for size in ((1280, 720), (1920, 1080), (1440, 900)):
        window.resize(*size)
        _drain(qapp)
    assert window.isVisible()
