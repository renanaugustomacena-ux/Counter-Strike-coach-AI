"""DOCK-01 — coach dock floating-state restore contract.

Root cause of the 2026-08-03 "mini window" report: COACH_DOCK_FLOATING=true
was restored via dock.setFloating(True) with NO saved geometry, so Qt spawned
the dock as a small default-size floating window (min+close only on GNOME
Wayland CSD, close merely hides a dock) in front of the main window.

Contract: floating restores ONLY together with a restorable geometry;
anything else re-docks. Geometry persists so a deliberate float survives.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _make_dock(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDockWidget, QLabel, QMainWindow

    win = QMainWindow()
    dock = QDockWidget("Coach", win)
    dock.setWidget(QLabel("chat"))
    win.addDockWidget(Qt.RightDockWidgetArea, dock)
    return win, dock


class TestRestoreDockState:
    def test_geometryless_float_restores_docked(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.main_window import _restore_dock_state

        win, dock = _make_dock(qapp)
        applied = _restore_dock_state(dock, floating=True, geometry_b64="")
        assert applied is False
        assert dock.isFloating() is False

    def test_not_floating_stays_docked(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.main_window import _restore_dock_state

        win, dock = _make_dock(qapp)
        applied = _restore_dock_state(dock, floating=False, geometry_b64="whatever")
        assert applied is False
        assert dock.isFloating() is False

    def test_float_with_saved_geometry_restores_floating(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.main_window import _restore_dock_state

        win, dock = _make_dock(qapp)
        dock.setFloating(True)
        dock.resize(400, 500)
        geo = bytes(dock.saveGeometry().toBase64()).decode("ascii")
        dock.setFloating(False)

        applied = _restore_dock_state(dock, floating=True, geometry_b64=geo)
        assert applied is True
        assert dock.isFloating() is True

    def test_corrupt_geometry_falls_back_docked(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.main_window import _restore_dock_state

        win, dock = _make_dock(qapp)
        applied = _restore_dock_state(dock, floating=True, geometry_b64="!!notb64!!")
        assert applied is False
        assert dock.isFloating() is False
