"""Round-timeline heatmap — optional pyqtgraph backend with QtCharts fallback.

Factory returns a ``QWidget`` displaying round-by-round damage dealt vs
taken as a 2xN heatmap (top row = dealt, bottom row = taken, darker
cells = more damage). pyqtgraph gives a smoother gradient + zoom for
large match sets; QtCharts gets us the same data with stock widgets so
no user is broken if pyqtgraph is absent.

Wire via ``build_round_heatmap(rounds)`` — the returned widget decides
its own backend based on:

    1. ``AppState.use_pyqtgraph_heatmap`` toggle (default False)
    2. ``import pyqtgraph`` success

Any combination that fails lands on the QtCharts fallback with an
INFO-level log line so the reason is visible without a silent blank.
"""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCharts import QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.widgets.charts import token_color
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.qt_round_heatmap")


def _build_qtcharts_fallback(rounds: Iterable[dict]) -> QChartView:
    """QBarSeries: damage dealt + damage taken over rounds.

    Not a true heatmap (QtCharts doesn't ship one), but reads similarly
    at a glance and requires no extra dependencies.
    """
    tokens = get_tokens()
    chart = QChart()
    chart.setBackgroundBrush(token_color(tokens.chart_bg))
    chart.setPlotAreaBackgroundVisible(False)
    chart.legend().setLabelColor(QColor(tokens.text_secondary))

    dealt = QBarSet("Damage dealt")
    dealt.setColor(QColor(tokens.chart_line_primary))
    taken = QBarSet("Damage taken")
    taken.setColor(QColor(tokens.chart_line_secondary))

    rounds_list = list(rounds)
    for r in rounds_list:
        dealt.append(float(r.get("damage_dealt", 0) or 0))
        taken.append(float(r.get("damage_taken", 0) or 0))

    series = QBarSeries()
    series.append(dealt)
    series.append(taken)
    chart.addSeries(series)

    ax_x = QValueAxis()
    ax_x.setRange(0, max(1, len(rounds_list)))
    ax_x.setLabelFormat("%d")
    ax_x.setTitleText("Round")
    ax_x.setLabelsColor(QColor(tokens.text_secondary))
    ax_x.setGridLineColor(token_color(tokens.chart_grid))
    chart.addAxis(ax_x, Qt.AlignBottom)
    series.attachAxis(ax_x)

    ax_y = QValueAxis()
    ax_y.setLabelsColor(QColor(tokens.text_secondary))
    ax_y.setGridLineColor(token_color(tokens.chart_grid))
    ax_y.setTitleText("HP")
    chart.addAxis(ax_y, Qt.AlignLeft)
    series.attachAxis(ax_y)

    view = QChartView(chart)
    view.setRenderHint(QPainter.Antialiasing)
    view.setMinimumHeight(220)
    return view


def _build_pyqtgraph_heatmap(rounds: list[dict]) -> QWidget:
    """2xN ImageItem heatmap: dealt row on top, taken row on bottom.

    Called only after ``import pyqtgraph as pg`` has succeeded.
    """
    import numpy as np
    import pyqtgraph as pg

    tokens = get_tokens()
    pg.setConfigOption("background", tokens.chart_bg)
    pg.setConfigOption("foreground", tokens.text_secondary)

    # Build the 2×N matrix: row 0 = taken (bottom), row 1 = dealt (top).
    # pyqtgraph image items draw y+ downward by default, so we flip at
    # view level later.
    data = np.zeros((2, max(1, len(rounds))), dtype=float)
    for i, r in enumerate(rounds):
        data[0, i] = float(r.get("damage_taken", 0) or 0)
        data[1, i] = float(r.get("damage_dealt", 0) or 0)

    view = pg.PlotWidget()
    view.setMouseEnabled(x=True, y=False)
    view.setMinimumHeight(220)
    view.getPlotItem().hideAxis("left")
    view.getPlotItem().showGrid(x=True, y=False, alpha=0.15)
    view.setLabel("bottom", "Round")

    img = pg.ImageItem(image=data.T)
    # Colormap: accent-primary -> accent-hover -> bright red for high damage
    colors = np.array(
        [
            QColor(tokens.surface_sunken).getRgb()[:3],
            QColor(tokens.accent_primary).getRgb()[:3],
            QColor(tokens.error).getRgb()[:3],
        ],
        dtype=float,
    )
    positions = np.array([0.0, 0.5, 1.0])
    cmap = pg.ColorMap(positions, colors)
    img.setLookupTable(cmap.getLookupTable(0.0, 1.0, 256))

    view.addItem(img)
    # Labels overlaid explaining the two rows.
    text_dealt = pg.TextItem("Dealt", color=(200, 200, 200), anchor=(0, 0))
    text_dealt.setPos(0, 2)
    text_taken = pg.TextItem("Taken", color=(200, 200, 200), anchor=(0, 0))
    text_taken.setPos(0, 1)
    view.addItem(text_dealt)
    view.addItem(text_taken)
    return view


def build_round_heatmap(rounds: Iterable[dict]) -> QWidget:
    """Build the heatmap widget for a match's rounds.

    Honors the ``USE_PYQTGRAPH_HEATMAP`` toggle; falls back to the
    QtCharts bar view if the package is absent or the toggle is off.
    """
    want_pyqtgraph = get_app_state().use_pyqtgraph_heatmap
    if want_pyqtgraph:
        try:
            import pyqtgraph  # noqa: F401

            rounds_list = list(rounds)
            return _build_pyqtgraph_heatmap(rounds_list)
        except ImportError:
            _logger.info(
                "USE_PYQTGRAPH_HEATMAP=True but pyqtgraph is not installed; "
                "falling back to QtCharts bar view"
            )
    return _build_qtcharts_fallback(rounds)
