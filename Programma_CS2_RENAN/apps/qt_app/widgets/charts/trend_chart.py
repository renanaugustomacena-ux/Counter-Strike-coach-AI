"""Rating + ADR dual-axis trend chart — replaces TrendGraphWidget (matplotlib)."""

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QMargins, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class TrendChart(QChartView):
    """Dual-axis line chart: Rating (left, cyan) + ADR (right, orange)."""

    def __init__(self, parent=None):
        chart = QChart()
        tokens = get_tokens()
        chart.setBackgroundBrush(QColor(tokens.chart_bg))
        chart.setBackgroundRoundness(8)
        chart.legend().setVisible(True)
        chart.legend().setLabelColor(QColor(tokens.text_primary))
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.setTitle("Performance Trend")
        chart.setTitleBrush(QColor(tokens.text_inverse))
        chart.setMargins(QMargins(8, 8, 8, 8))
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMinimumHeight(220)

    def plot(self, history: list):
        """Plot from list of dicts with 'rating' and 'avg_adr' keys."""
        chart = self.chart()
        chart.removeAllSeries()
        for axis in chart.axes():
            chart.removeAxis(axis)

        if not history:
            return

        tokens = get_tokens()

        # Rating series
        rating_series = QLineSeries()
        rating_series.setName("Rating")
        rating_series.setPen(QPen(QColor(tokens.chart_line_primary), 2))
        for i, h in enumerate(history):
            rating_series.append(i, h.get("rating", 1.0) or 1.0)

        # ADR series
        adr_series = QLineSeries()
        adr_series.setName("ADR")
        adr_series.setPen(QPen(QColor(tokens.chart_line_secondary), 2, Qt.DashLine))
        for i, h in enumerate(history):
            adr_series.append(i, h.get("avg_adr", 0) or 0)

        chart.addSeries(rating_series)
        chart.addSeries(adr_series)

        # X axis (match index)
        ax_x = QValueAxis()
        ax_x.setRange(0, max(len(history) - 1, 1))
        ax_x.setLabelFormat("%d")
        ax_x.setLabelsColor(QColor(tokens.text_secondary))
        ax_x.setGridLineColor(QColor(255, 255, 255, 30))
        chart.addAxis(ax_x, Qt.AlignBottom)
        rating_series.attachAxis(ax_x)
        adr_series.attachAxis(ax_x)

        # Rating Y axis (left)
        ratings = [h.get("rating", 1.0) or 1.0 for h in history]
        ax_rating = QValueAxis()
        ax_rating.setRange(max(0, min(ratings) - 0.1), max(ratings) + 0.1)
        ax_rating.setTitleText("Rating")
        ax_rating.setTitleBrush(QColor(tokens.chart_line_primary))
        ax_rating.setLabelsColor(QColor(tokens.chart_line_primary))
        ax_rating.setGridLineColor(QColor(255, 255, 255, 20))
        chart.addAxis(ax_rating, Qt.AlignLeft)
        rating_series.attachAxis(ax_rating)

        # ADR Y axis (right)
        adrs = [h.get("avg_adr", 0) or 0 for h in history]
        ax_adr = QValueAxis()
        ax_adr.setRange(max(0, min(adrs) - 10), max(adrs) + 10)
        ax_adr.setTitleText("ADR")
        ax_adr.setTitleBrush(QColor(tokens.chart_line_secondary))
        ax_adr.setLabelsColor(QColor(tokens.chart_line_secondary))
        ax_adr.setGridLineVisible(False)
        chart.addAxis(ax_adr, Qt.AlignRight)
        adr_series.attachAxis(ax_adr)
