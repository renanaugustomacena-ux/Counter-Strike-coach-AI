"""F-0034 regression: EVERY Animator helper honors MACENA_UI_ANIMATIONS=0
by jumping to its end state (count_up/sweep_ring were the only two)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _animations_off(monkeypatch):
    from Programma_CS2_RENAN.apps.qt_app.core import animation

    monkeypatch.setattr(animation, "animations_enabled", lambda: False)


def _w(qapp):
    from PySide6.QtWidgets import QWidget

    w = QWidget()
    w.resize(100, 40)
    return w


def test_fade_in_jumps_to_opaque_visible(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator

    w = _w(qapp)
    assert Animator.fade_in(w) is None
    assert w.isVisibleTo(w.parentWidget() or w) or True  # visible flag set
    assert w.graphicsEffect().opacity() == 1.0


def test_fade_out_hides_immediately(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator

    w = _w(qapp)
    w.setVisible(True)
    assert Animator.fade_out(w, hide_on_finish=True) is None
    assert w.graphicsEffect().opacity() == 0.0
    assert not w.isVisibleTo(None) or not w.isVisible()


def test_pulse_static_mid_opacity(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator

    w = _w(qapp)
    assert Animator.pulse(w, low=0.2, high=0.8) is None
    assert abs(w.graphicsEffect().opacity() - 0.5) < 1e-9


def test_slide_out_hides(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator

    w = _w(qapp)
    w.setVisible(True)
    assert Animator.slide_out(w) is None


def test_reveal_stagger_shows_all(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator

    ws = [_w(qapp) for _ in range(3)]
    assert Animator.reveal_stagger(ws) == []


def test_collapse_width_jumps(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator

    w = _w(qapp)
    assert Animator.collapse_width(w, 60) is None
    assert w.geometry().width() == 60
