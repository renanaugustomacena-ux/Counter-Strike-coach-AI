"""Theme-staleness regression (CP0 decision #4): instance-styled chips
restyle themselves on a LIVE theme switch via the module-level relay.

Pre-fix, FilterChip/StatusChip were styled once at construction; after
apply_theme() they kept the old theme's colors until recreated."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _restore_theme():
    from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import set_active_theme

    yield
    set_active_theme("CS2")


def _switch(name):
    from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import set_active_theme
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import get_theme_relay

    set_active_theme(name)
    get_theme_relay().theme_changed.emit(name)


def test_filter_chip_live_restyles(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import set_active_theme
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.filter_chip import FilterChip

    set_active_theme("CS2")
    chip = FilterChip("All", checked=True)
    before = chip.styleSheet()
    _switch("CSGO")
    assert chip.styleSheet() != before, "FilterChip kept the old theme"


def test_status_chip_live_restyles(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import set_active_theme
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip

    set_active_theme("CS2")
    chip = StatusChip("LIVE")
    # The frame sheet is theme-neutral; the theme-sensitive colors live on
    # the child label. Compare that.
    before = chip._label.styleSheet()
    _switch("CSGO")
    assert chip._label.styleSheet() != before, "StatusChip kept the old theme"


def test_engine_apply_theme_pings_the_relay(qapp):
    """apply_theme must reach relay subscribers (integration of the wire)."""
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine, get_theme_relay

    seen = []
    get_theme_relay().theme_changed.connect(lambda n: seen.append(n))
    engine = ThemeEngine()
    engine.apply_theme("CSGO", qapp)
    assert "CSGO" in seen
