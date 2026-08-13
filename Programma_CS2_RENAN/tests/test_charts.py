"""Chart widget tests — QPainter chart geometry math and widget contracts.

Covers the P3 design-atlas chart set (RadarChart, RatingSparkline,
UtilityBarChart, EconomyChart, MomentumChart). Pure-function geometry
first (no QApplication needed), widget construction second (offscreen).
"""

import os
import sys
from pathlib import Path

import pytest

# Must be set BEFORE any PySide6 import — enables headless CI (no display server).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# ── Path stabilization (same pattern as test_qt_core.py) ──
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for the entire test session."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


# ═══════════════════════════════════════════════════════════════════════════════
# 1. RadarChart (Task 11)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRadarChart:
    def test_radar_vertex_positions(self):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.radar_chart import _vertex

        cx, cy, r = 100.0, 100.0, 80.0
        x, y = _vertex(cx, cy, r, idx=0, n=8, frac=1.0)  # top
        assert abs(x - 100.0) < 1e-6 and abs(y - 20.0) < 1e-6
        x, y = _vertex(cx, cy, r, idx=2, n=8, frac=0.5)  # right, half radius
        assert abs(x - 140.0) < 1e-6 and abs(y - 100.0) < 1e-6

    def test_radar_vertex_bottom_and_left(self):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.radar_chart import _vertex

        cx, cy, r = 50.0, 50.0, 40.0
        x, y = _vertex(cx, cy, r, idx=2, n=4, frac=1.0)  # bottom for n=4
        assert abs(x - 50.0) < 1e-6 and abs(y - 90.0) < 1e-6
        x, y = _vertex(cx, cy, r, idx=3, n=4, frac=1.0)  # left for n=4
        assert abs(x - 10.0) < 1e-6 and abs(y - 50.0) < 1e-6

    def test_radar_chart_series_state(self, qapp):
        from PySide6.QtGui import QColor

        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.radar_chart import RadarChart

        chart = RadarChart()
        chart.set_axes(["Aim", "Opening", "Utility", "Clutch", "Pos", "Aggro", "Eco", "Surv"])
        chart.add_series("ZywOo", [97, 88, 85, 90, 95, 72, 87, 80], QColor("#FF6A00"))
        chart.add_series("donk", [96, 85, 72, 76, 68, 80, 68, 60], QColor("#00D9FF"))
        assert len(chart._series) == 2
        chart.set_range(0.0, 100.0)
        chart.clear_series()
        assert chart._series == []
        chart.deleteLater()

    def test_radar_chart_exported_from_package(self):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts import RadarChart  # noqa: F401

    def test_radar_chart_renders_offscreen(self, qapp):
        from PySide6.QtGui import QColor

        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.radar_chart import RadarChart

        chart = RadarChart()
        chart.set_axes(["A", "B", "C"])
        chart.add_series("s", [50, 75, 100], QColor("#FF6A00"))
        chart.resize(300, 300)
        pixmap = chart.grab()
        assert not pixmap.isNull()
        chart.deleteLater()
