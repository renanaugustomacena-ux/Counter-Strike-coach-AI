"""Q6-TRAY regression — tray icon, close-to-tray, single-instance wiring.

The offscreen platform reports no system tray, so build_tray's live path
is exercised by desktop runs; here we pin the harness-safe contracts:
graceful degradation, the painted icon, closeEvent's decision table, and
that app boot actually CALLS the single-instance guard (it was dead code
with zero production callers before this feature).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class _TrayStub:
    def __init__(self):
        self.messages = []

    def showMessage(self, title, body):
        self.messages.append((title, body))


def _release(window) -> None:
    """Destroy a MainWindow NOW, not "later" (D-37).

    ``deleteLater()`` only queues a DeferredDelete; pytest never returns to
    the Qt event loop, so the hidden C++ window outlives the module and the
    next test that pumps events (the splash test on the Windows CI runner)
    faults natively.  Flush the queue here so nothing survives.
    """
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    window.close()
    window.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QApplication.processEvents()


def test_render_tray_icon_paints(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.tray import render_tray_icon

    icon = render_tray_icon()
    assert not icon.isNull()
    assert not icon.pixmap(32, 32).isNull()


def test_build_tray_degrades_without_a_tray(qapp):
    """Offscreen has no tray — build_tray must return None, never raise."""
    from PySide6.QtWidgets import QSystemTrayIcon

    from Programma_CS2_RENAN.apps.qt_app.core.tray import build_tray

    if QSystemTrayIcon.isSystemTrayAvailable():
        pytest.skip("a real tray exists here; degradation path not reachable")
    assert build_tray(None) is None


def test_close_event_hides_to_tray_when_armed(qapp, monkeypatch):
    import Programma_CS2_RENAN.core.config as config
    from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow

    monkeypatch.setattr(
        config, "get_setting", lambda key, default=None: True if key == "CLOSE_TO_TRAY" else default
    )
    window = MainWindow()
    stub = _TrayStub()
    window.attach_tray(stub)
    window.show()
    window.close()
    assert window.isHidden(), "armed close must hide, not destroy"
    assert len(stub.messages) == 1, "first hide announces itself via the balloon"
    window.close()
    assert len(stub.messages) == 1, "the balloon shows once per process"
    window.attach_tray(None)  # allow real teardown
    _release(window)


def test_close_event_falls_through_when_disarmed(qapp, monkeypatch):
    import Programma_CS2_RENAN.core.config as config
    from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow

    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: False if key == "CLOSE_TO_TRAY" else default,
    )
    window = MainWindow()
    window.show()
    closed = window.close()  # no tray attached at all — plain close
    assert closed is True
    _release(window)


def test_app_boot_wires_the_single_instance_guard():
    """The guard was dead code (test-only callers). Pin the production call."""
    src = (REPO / "Programma_CS2_RENAN" / "apps" / "qt_app" / "app.py").read_text(encoding="utf-8")
    assert "ensure_single_instance" in src, (
        "app.py no longer calls lifecycle.ensure_single_instance — two GUI "
        "processes would mean concurrent SQLite writers (Q6-TRAY)"
    )


def test_no_main_window_survives_this_module(qapp):
    """D-37: the two MainWindows built above must be GONE when the module ends.

    ``deleteLater()`` only queues a DeferredDelete; nothing in this module
    pumps that queue, so both hidden C++ windows outlived the module.  The
    next module to pump events on the Windows CI runner was
    ``test_v1_blockers.py::TestSplashScreen::test_splash_status_updates``
    (``QSplashScreen.showMessage`` pumps internally) — red with a native
    access violation since de1af57, the commit that added this file.
    """
    from PySide6.QtWidgets import QApplication

    from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow

    survivors = [w for w in QApplication.topLevelWidgets() if isinstance(w, MainWindow)]
    assert survivors == [], f"{len(survivors)} MainWindow(s) still alive after teardown"
