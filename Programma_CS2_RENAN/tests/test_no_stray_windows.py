"""Boot round (WP3) — a child widget must never become its own window.

Found by the boot test: ``EmptyState`` built its description label, CTA
buttons and link row WITHOUT a parent and only added them to the layout
when their text was non-empty at construction.  A later
``set_description("Pick a pro from the comparison screen.")`` called
``setVisible(True)`` on a parentless QLabel — which in Qt is a top-level
window.  That 133x29 px window at (0, 0) was the "little weird window"
the user saw at every launch (pro player detail screen, empty state).
``NumberedStep`` carried the same pattern.
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QWidget

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _flush(qapp) -> None:
    for _ in range(4):
        qapp.processEvents()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()


def _stray_windows(host: QWidget) -> list:
    return [
        w
        for w in QApplication.topLevelWidgets()
        if w.isVisible() and w.isWindow() and w is not host
    ]


_HOSTS: list[QWidget] = []


@pytest.fixture(scope="module", autouse=True)
def _release_hosts_at_module_end(qapp):
    yield
    for widget in _HOSTS:
        widget.close()
        widget.deleteLater()
    _HOSTS.clear()
    _flush(qapp)


@pytest.fixture
def host(qapp):
    """A shown top-level host; every component under test is parented to it."""
    widget = QWidget()
    widget.resize(600, 400)
    widget.show()
    _flush(qapp)
    _HOSTS.append(widget)
    yield widget
    widget.hide()
    # Anything that escaped as its own window (the bug under test) must
    # not leak into later modules' top-level assertions.
    for stray in _stray_windows(widget):
        stray.hide()
    _flush(qapp)


@pytest.mark.parametrize(
    "setter",
    ["set_description", "set_cta_text", "set_secondary_cta_text", "set_link_text"],
)
def test_empty_state_late_text_stays_inside_the_widget(qapp, host, setter):
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState

    state = EmptyState(icon_text="", title="Nothing here", description="", parent=host)
    state.show()
    _flush(qapp)
    assert _stray_windows(host) == []

    getattr(state, setter)("Pick a pro from the comparison screen.")
    _flush(qapp)

    assert _stray_windows(host) == [], [
        (type(w).__name__, getattr(w, "text", lambda: "")()) for w in _stray_windows(host)
    ]


def test_empty_state_children_share_the_host_window(qapp, host):
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState

    state = EmptyState(icon_text="", title="t", description="", parent=host)
    state.set_description("late description")
    state.set_cta_text("Go")
    state.set_secondary_cta_text("Later")
    state.set_link_text("Read the guide")
    for child in (
        state._desc_label,
        state._cta_button,
        state._secondary_button,
        state._link_button,
        state._icon_well,
    ):
        assert child.window() is host, type(child).__name__
        assert not child.isWindow()


def test_numbered_step_late_description_stays_inside_the_widget(qapp, host):
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.numbered_step import NumberedStep

    step = NumberedStep(1, "Set your name", "", parent=host)
    step.show()
    _flush(qapp)

    step.set_description("Settings → In-Game Name")
    _flush(qapp)

    assert _stray_windows(host) == []
    assert step._desc_label.window() is host
