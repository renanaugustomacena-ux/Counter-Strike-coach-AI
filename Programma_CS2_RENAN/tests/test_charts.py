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


# ═══════════════════════════════════════════════════════════════════════════════
# 2. RatingSparkline (Task 12)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRatingSparkline:
    def test_y_mapping_extremes_and_midpoint(self):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.rating_sparkline import _y

        # 6px padding top and bottom of the drawable band.
        assert abs(_y(1.5, 0.5, 1.5, 100.0) - 6.0) < 1e-6  # max -> top pad
        assert abs(_y(0.5, 0.5, 1.5, 100.0) - 94.0) < 1e-6  # min -> bottom pad
        assert abs(_y(1.0, 0.5, 1.5, 100.0) - 50.0) < 1e-6  # midpoint -> center

    def test_y_mapping_zero_span_is_safe(self):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.rating_sparkline import _y

        assert abs(_y(1.0, 1.0, 1.0, 100.0) - 50.0) < 1e-6  # flat data -> center

    def test_sparkline_state_and_render(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.rating_sparkline import RatingSparkline

        spark = RatingSparkline()
        assert spark.minimumHeight() >= 64
        spark.set_values([1.02, 1.06, 0.98, 1.09, 1.05, 1.12, 1.08, 1.17])
        spark.set_reference_lines((0.90, 1.00, 1.10))
        assert spark._values[-1] == pytest.approx(1.17)
        assert spark._refs == (0.90, 1.00, 1.10)
        spark.resize(400, 120)
        assert not spark.grab().isNull()
        spark.set_values([])  # must stay safe on empty input
        assert not spark.grab().isNull()
        spark.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. UtilityBarChart (Task 13)
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtilityBarChart:
    def test_w_mapping_proportional(self):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.utility_bar_chart import _w

        assert _w(5.0, 10.0, 200.0) == pytest.approx(100.0)
        assert _w(10.0, 10.0, 200.0) == pytest.approx(200.0)

    def test_w_mapping_zero_and_clamps(self):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.utility_bar_chart import _w

        assert _w(5.0, 0.0, 200.0) == 0.0  # zero-max guard
        assert _w(-3.0, 10.0, 200.0) == 0.0  # negative values clamp to 0
        assert _w(15.0, 10.0, 200.0) == pytest.approx(200.0)  # overshoot clamps

    def test_grouped_and_single_modes(self, qapp):
        from PySide6.QtGui import QColor

        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.utility_bar_chart import UtilityBarChart

        chart = UtilityBarChart()
        chart.set_rows(
            [
                ("HE", 12.4, 15.2),
                ("Moly", 5.8, 5.9),
                ("Flash", 3.2, 2.6),
                ("Waste", 1.2, 0.91, QColor("#ff4444")),  # optional you-bar override
            ]
        )
        assert len(chart._rows) == 4
        assert chart._mode == "grouped"
        assert chart.minimumHeight() >= 4 * 34
        chart.resize(520, 240)
        assert not chart.grab().isNull()

        chart.set_single(
            [
                ("Flashes thrown", 24, QColor("#00D9FF")),
                ("Smokes thrown", 18, QColor("#00D9FF")),
            ]
        )
        assert chart._mode == "single"
        assert len(chart._rows) == 2
        chart.resize(520, 160)
        assert not chart.grab().isNull()
        chart.set_rows([])  # empty input stays safe
        assert not chart.grab().isNull()
        chart.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. EconomyChart + MomentumChart QPainter rewrite (Task 14)
# ═══════════════════════════════════════════════════════════════════════════════


def _sample_rounds(n: int = 24) -> list:
    rounds = []
    for i in range(n):
        rounds.append(
            {
                "round_number": i + 1,
                "side": "T" if i < n // 2 else "CT",
                "equipment_value": 3800 + (i % 5) * 400,
                "kills": i % 4,
                "deaths": (i + 1) % 3,
                "damage_dealt": 80 * (i % 4),
                "opening_kill": i % 6 == 0,
                "round_won": i % 3 != 1,
            }
        )
    return rounds


class TestEconomyChart:
    def test_half_x_proportional(self):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.economy_chart import _half_x

        # Boundary sits at the LEFT edge of round_no's slot.
        assert _half_x(13, 24, 480.0) == pytest.approx(240.0)
        assert _half_x(1, 24, 480.0) == pytest.approx(0.0)
        assert _half_x(7, 12, 300.0) == pytest.approx(150.0)

    def test_bar_rect_non_negative(self):
        from PySide6.QtCore import QRectF

        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.economy_chart import _bar_rect

        plot = QRectF(10.0, 10.0, 240.0, 100.0)
        rect = _bar_rect(0, 24, 4000.0, 8000.0, plot)
        assert rect.height() == pytest.approx(50.0)
        assert rect.bottom() == pytest.approx(plot.bottom())
        assert _bar_rect(3, 24, 0.0, 8000.0, plot).height() >= 0.0
        assert _bar_rect(3, 24, 500.0, 0.0, plot).height() >= 0.0  # zero-max guard

    def test_economy_plot_api_preserved(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.economy_chart import EconomyChart

        chart = EconomyChart()
        chart.plot(_sample_rounds())  # pre-rewrite public API
        chart.set_half_marker(13)  # Task 14 addition
        chart.resize(900, 360)
        assert not chart.grab().isNull()
        chart.plot([])  # empty input stays safe
        assert not chart.grab().isNull()
        chart.deleteLater()


class TestMomentumChart:
    def test_momentum_plot_api_preserved(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.charts.momentum_chart import MomentumChart

        chart = MomentumChart()
        chart.plot(_sample_rounds())  # pre-rewrite public API
        chart.resize(700, 300)
        assert not chart.grab().isNull()
        chart.plot([])
        assert not chart.grab().isNull()
        chart.deleteLater()


class TestQtChartsRetired:
    def test_no_qtcharts_references_in_qt_app_code(self):
        """License gate: QtCharts is GPL-only — zero code references allowed."""
        qt_app = _project_root / "Programma_CS2_RENAN" / "apps" / "qt_app"
        offenders = []
        for path in qt_app.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "QtCharts" in text or "QChart" in text:
                offenders.append(str(path))
        assert offenders == [], f"QtCharts references linger in: {offenders}"
