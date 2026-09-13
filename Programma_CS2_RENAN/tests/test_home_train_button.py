"""Train-in-app round (WP4b) — the Home training card always offers the Train
action, shows the active local model honestly, and mirrors the Teacher's
state; Settings carries the same button next to Start Ingestion.
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MACENA_UI_ANIMATIONS", "0")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _flush(qapp):
    for _ in range(4):
        qapp.processEvents()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()


@pytest.fixture
def home(qapp):
    from Programma_CS2_RENAN.apps.qt_app.screens.home_screen import HomeScreen

    screen = HomeScreen()
    screen.resize(1280, 900)
    screen.show()
    _flush(qapp)
    yield screen
    screen.close()
    screen.deleteLater()
    _flush(qapp)


def test_the_training_card_is_always_offered_and_progress_only_while_training(qapp, home):
    assert home._training_card.isVisibleTo(home)
    home._on_training({"current_epoch": 0, "total_epochs": 0})
    _flush(qapp)
    assert home._training_card.isVisibleTo(home)
    assert not home._training_progress_box.isVisibleTo(home)

    home._on_training(
        {
            "current_epoch": 12,
            "total_epochs": 40,
            "train_loss": 0.1,
            "val_loss": 0.2,
            "eta_seconds": 30,
        }
    )
    _flush(qapp)
    assert home._training_progress_box.isVisibleTo(home)
    assert "12 / 40" in home._epoch_label.text()
    assert home._training_footer.text().startswith("jepa_v2")


def test_the_buttons_follow_the_teacher_state(qapp, home):
    home._on_ml_status("Idle")
    _flush(qapp)
    assert home._train_btn.isEnabled()
    assert not home._train_stop_btn.isVisibleTo(home)

    home._on_ml_status("Learning")
    _flush(qapp)
    assert not home._train_btn.isEnabled()
    assert home._train_stop_btn.isVisibleTo(home)

    home._on_ml_status("Queued")
    _flush(qapp)
    assert not home._train_btn.isEnabled()


def test_the_active_model_line_is_honest(qapp, home):
    home._on_trained_model({})
    assert "No model" in home._active_model_label.text()

    home._on_trained_model(
        {
            "version_name": "jepa_v2_encoder",
            "steps": 2000,
            "demos_train": 12,
            "demos_val": 2,
            "finished_at": "2026-09-13T10:05:00+00:00",
        }
    )
    text = home._active_model_label.text()
    assert "jepa_v2_encoder" in text and "2000" in text and "2026-09-13" in text and "12" in text


def test_train_and_stop_go_through_the_view_model(qapp, home, monkeypatch):
    requested: list[int] = []
    stops: list[bool] = []
    monkeypatch.setattr(
        home._training_vm, "request_training", lambda steps: requested.append(steps)
    )
    monkeypatch.setattr(home._training_vm, "request_stop", lambda: stops.append(True))

    home._train_steps_combo.setCurrentIndex(0)
    expected = home._train_steps_combo.currentData()
    assert isinstance(expected, int) and expected > 0
    home._train_btn.click()
    assert requested == [expected]

    home._on_ml_status("Learning")
    home._train_stop_btn.click()
    assert stops == [True]

    home._on_training_message("warning", "Service offline")
    assert home._train_message.text() == "Service offline"


def test_settings_offers_the_same_train_action(qapp, monkeypatch):
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
    from Programma_CS2_RENAN.apps.qt_app.screens.settings_screen import SettingsScreen

    screen = SettingsScreen(theme_engine=ThemeEngine())
    try:
        requested: list[int] = []
        monkeypatch.setattr(
            screen._training_vm, "request_training", lambda steps: requested.append(steps)
        )
        screen._train_btn.click()
        assert requested and requested[0] > 0
    finally:
        screen.deleteLater()
        _flush(qapp)


def test_app_state_reports_the_teacher_status_and_the_active_model(monkeypatch):
    from Programma_CS2_RENAN.apps.qt_app.core import app_state as app_state_module

    state = app_state_module.AppState.__new__(app_state_module.AppState)
    assert hasattr(app_state_module.AppState, "ml_status_changed")
    assert hasattr(app_state_module.AppState, "trained_model_changed")
    del state
