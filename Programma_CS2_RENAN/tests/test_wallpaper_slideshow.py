"""Q6-SLIDESHOW regression — the rotating-wallpaper mode.

Pins the three contracts the feature added:
    1. ThemeEngine understands the ``::slideshow::`` sentinel (persisted
       BACKGROUND_IMAGE value) and survives theme switches with it.
    2. _BackgroundWidget rotates through real files, hard-cuts when
       animations are disabled (the harness contract), and a static
       set_image() call disarms the timer.
    3. Degenerate inputs (no files, one file) degrade without a timer.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def two_pngs(tmp_path, qapp):
    from PySide6.QtGui import QColor, QPixmap

    paths = []
    for name, color in (("a.png", "#112233"), ("b.png", "#445566")):
        pm = QPixmap(8, 8)
        pm.fill(QColor(color))
        p = tmp_path / name
        pm.save(str(p))
        paths.append(str(p))
    return paths


class TestThemeEngineSentinel:
    def test_set_wallpaper_sentinel_arms_slideshow(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import (
            WALLPAPER_SLIDESHOW,
            ThemeEngine,
        )

        engine = ThemeEngine()
        engine.set_wallpaper(WALLPAPER_SLIDESHOW)
        assert engine.wallpaper_is_slideshow is True
        engine.set_wallpaper("")
        assert engine.wallpaper_is_slideshow is False

    def test_update_wallpaper_honors_persisted_sentinel(self, qapp, monkeypatch):
        import Programma_CS2_RENAN.core.config as config
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import (
            WALLPAPER_SLIDESHOW,
            ThemeEngine,
        )

        monkeypatch.setattr(
            config,
            "get_setting",
            lambda key, default=None: (
                WALLPAPER_SLIDESHOW if key == "BACKGROUND_IMAGE" else default
            ),
        )
        engine = ThemeEngine()
        engine._update_wallpaper("CS2")
        assert engine.wallpaper_is_slideshow is True
        # Theme switch keeps the mode — it is theme-relative by construction.
        engine._update_wallpaper("CSGO")
        assert engine.wallpaper_is_slideshow is True


class TestBackgroundWidgetRotation:
    def test_rotation_hard_cuts_with_animations_disabled(self, qapp, two_pngs, monkeypatch):
        monkeypatch.setenv("MACENA_UI_ANIMATIONS", "0")
        from Programma_CS2_RENAN.apps.qt_app.main_window import _BackgroundWidget

        w = _BackgroundWidget()
        w.resize(64, 64)
        w.set_slideshow(two_pngs)
        assert w._slideshow_timer is not None
        first = w._pixmap.toImage()
        w._advance_slideshow()
        assert w._pixmap.toImage() != first  # rotated to the second file
        assert w._fade_anim is None  # hard cut, no animation object
        assert not w.grab().isNull()
        w.deleteLater()

    def test_static_choice_disarms_the_timer(self, qapp, two_pngs):
        from Programma_CS2_RENAN.apps.qt_app.main_window import _BackgroundWidget

        w = _BackgroundWidget()
        w.set_slideshow(two_pngs)
        assert w._slideshow_timer is not None
        w.set_image(two_pngs[0])
        assert w._slideshow_timer is None
        assert w._slideshow_paths == []
        w.deleteLater()

    def test_degenerate_lists_never_start_a_timer(self, qapp, two_pngs):
        from Programma_CS2_RENAN.apps.qt_app.main_window import _BackgroundWidget

        w = _BackgroundWidget()
        w.set_slideshow([])
        assert w._slideshow_timer is None and w._pixmap is None
        w.set_slideshow(["Z:/nowhere/ghost.png"])
        assert w._slideshow_timer is None and w._pixmap is None
        w.set_slideshow(two_pngs[:1])  # single image: shown, but no rotation
        assert w._slideshow_timer is None and w._pixmap is not None
        w.deleteLater()
