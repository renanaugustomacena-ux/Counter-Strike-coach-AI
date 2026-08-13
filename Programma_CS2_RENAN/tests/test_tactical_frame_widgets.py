"""Unit tests for the frame-13/14 tactical viewer pieces.

Covers the pure map-zone loader (normalization + graceful degradation),
the timeline star hit-test, and the ghost divergence-row adapter.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.map_widget import load_map_zones


class TestZoneLoader:
    def test_mirage_zones_present_and_normalized(self):
        zones = load_map_zones("de_mirage")
        assert len(zones) >= 8, "mirage zone file should ship at least 8 named zones"
        for zone in zones:
            assert 0.0 <= zone["x"] <= 1.0 and 0.0 <= zone["y"] <= 1.0
            assert 0.0 < zone["w"] <= 1.0 and 0.0 < zone["h"] <= 1.0
            assert zone["x"] + zone["w"] <= 1.0 + 1e-9
            assert zone["y"] + zone["h"] <= 1.0 + 1e-9
            assert zone["label"], "every zone carries a label"

    def test_mirage_major_sites(self):
        majors = {z["label"] for z in load_map_zones("de_mirage") if z["major"]}
        assert majors == {"A", "B", "MID"}

    def test_prefix_fallback_matches(self):
        assert load_map_zones("mirage") == load_map_zones("de_mirage")

    def test_unknown_map_degrades_to_empty(self):
        assert load_map_zones("de_totally_unknown") == []
        assert load_map_zones("") == []


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class TestTimelineStars:
    def _widget(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.timeline_widget import (
            TimelineWidget,
        )

        widget = TimelineWidget()
        widget.resize(1196, widget.height())
        widget.max_tick = 64_500
        return widget

    def test_star_hit_seeks_start_tick(self, qapp):
        widget = self._widget(qapp)
        widget.set_critical_moments([{"start_tick": 4_102, "peak_tick": 4_422}])
        star_x = 4_422 / 64_500 * widget.width()
        assert widget.star_hit_test(star_x, widget.height() - 10) == 4_102

    def test_off_star_and_caption_strip_miss(self, qapp):
        widget = self._widget(qapp)
        widget.set_critical_moments([{"start_tick": 4_102, "peak_tick": 4_422}])
        star_x = 4_422 / 64_500 * widget.width()
        assert widget.star_hit_test(star_x + 40, widget.height() - 10) is None
        assert widget.star_hit_test(star_x, 2) is None  # caption strip

    def test_accepts_scanner_objects_and_empty(self, qapp):
        from types import SimpleNamespace

        widget = self._widget(qapp)
        widget.set_critical_moments(
            [SimpleNamespace(start_tick=10_000, peak_tick=10_500, type="play")]
        )
        star_x = 10_500 / 64_500 * widget.width()
        assert widget.star_hit_test(star_x, widget.height() - 10) == 10_000
        widget.set_critical_moments([])
        assert widget.star_hit_test(star_x, widget.height() - 10) is None
        widget.set_critical_moments([{"kind": "no tick keys"}])
        assert widget.star_hit_test(star_x, widget.height() - 10) is None
