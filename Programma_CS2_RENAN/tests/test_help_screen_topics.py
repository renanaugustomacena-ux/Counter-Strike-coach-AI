"""Guides round (WP2) — every help topic renders through the markdown article."""

from __future__ import annotations

import os
import sys

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
def screen(qapp):
    from Programma_CS2_RENAN.apps.qt_app.screens.help_screen import HelpScreen

    widget = HelpScreen()
    widget.resize(1280, 900)
    widget.show()
    widget.on_enter()
    _flush(qapp)
    yield widget
    widget.close()
    widget.deleteLater()
    _flush(qapp)


def test_every_real_topic_renders_as_rich_text(qapp, screen):
    ids = [t["id"] for t in screen._topics]
    assert {"getting_started", "features", "troubleshooting"} <= set(ids)
    for topic_id in ids:
        screen._select_topic(topic_id)
        _flush(qapp)
        plain = screen._article.toPlainText()
        assert plain.strip(), topic_id
        assert not any(line.lstrip().startswith("#") for line in plain.splitlines()), topic_id
        assert "**" not in plain and "```" not in plain, topic_id


def test_getting_started_keeps_the_structured_steps_and_the_others_do_not(qapp, screen):
    screen._select_topic("getting_started")
    _flush(qapp)
    assert screen._structured_box.isVisibleTo(screen)
    assert screen._article.toPlainText().strip(), "the markdown body renders under the steps"

    screen._select_topic("features")
    _flush(qapp)
    assert not screen._structured_box.isVisibleTo(screen)
    assert screen._article.isVisibleTo(screen)


def test_fallback_topics_go_through_the_same_renderer(qapp, monkeypatch):
    import Programma_CS2_RENAN.apps.qt_app.screens.help_screen as help_screen

    monkeypatch.setattr(help_screen, "_HELP_AVAILABLE", False)
    widget = help_screen.HelpScreen()
    try:
        widget.on_enter()
        widget._select_topic("ai_coach")
        _flush(qapp)
        plain = widget._article.toPlainText()
        assert "Ollama" in plain
        assert not any(line.lstrip().startswith("#") for line in plain.splitlines())
    finally:
        widget.deleteLater()
        _flush(qapp)


def test_demo_folder_callout_matches_the_platform(qapp, screen):
    path = screen._callout_path.text()
    assert "steamapps" in path
    if sys.platform == "win32":
        assert "\\" in path and "~/" not in path
    else:
        assert path.startswith("~/")


def test_search_filters_topics_by_title_and_body(qapp, screen):
    screen._search_input.setText("troubleshoot")
    _flush(qapp)
    assert [t["id"] for t in screen._visible_topics()] == ["troubleshooting"]
    screen._search_input.setText("")
    _flush(qapp)
    assert len(screen._visible_topics()) >= 3
