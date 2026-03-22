"""Rating sparkline — compact trend with reference lines."""

from PySide6.QtCharts import QAreaSeries, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class RatingSparkline(QChartView):
    """Rating trend with 1.0/1.1/0.9 reference lines and filled area."""

    def __init__(self, parent=None):
        chart = QChart()
        tokens = get_tokens()
        chart.setBackgroundBrush(QColor(tokens.chart_bg))
        chart.setBackgroundRoundness(8)
        chart.setTitle("Rating Trend")
        chart.setTitleBrush(QColor(tokens.text_inverse))
        chart.legend().setVisible(False)
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMinimumHeight(200)

    def plot(self, history: list):
        chart = self.chart()
        chart.removeAllSeries()
        for axis in chart.axes():
            chart.removeAxis(axis)

        if not history:
            return

        tokens = get_tokens()
        ratings = [h.get("rating", 1.0) if h.get("rating") is not None else 1.0 for h in history]
        n = len(ratings)

        # Rating line
        line = QLineSeries()
        line.setPen(QPen(QColor(tokens.chart_line_primary), 2))
        for i, r in enumerate(ratings):
            line.append(i, r)

        # Fill below the line
        baseline = QLineSeries()
        floor = min(ratings) - 0.05
        for i in range(n):
            baseline.append(i, floor)
        area = QAreaSeries(line, baseline)
        fill = QColor(tokens.chart_line_primary)
        fill.setAlphaF(0.15)
        area.setBrush(QBrush(fill))
        area.setPen(QPen(Qt.NoPen))

        chart.addSeries(area)
        chart.addSeries(line)

        # Reference lines
        for ref_val, ref_color, style in [
            (1.0, tokens.text_inverse, Qt.DashLine),
            (1.1, tokens.chart_fill_positive, Qt.DashLine),
            (0.9, tokens.chart_fill_negative, Qt.DashLine),
        ]:
            ref = QLineSeries()
            pen = QPen(QColor(ref_color), 1, style)
            pen.setColor(QColor(ref_color))
            ref.setPen(pen)
            ref.setOpacity(0.4)
            ref.append(0, ref_val)
            ref.append(n - 1, ref_val)
            chart.addSeries(ref)

        # Axes
        ax_x = QValueAxis()
        ax_x.setRange(0, max(n - 1, 1))
        ax_x.setLabelsColor(QColor(tokens.text_secondary))
        ax_x.setGridLineColor(QColor(255, 255, 255, 20))
        ax_x.setLabelFormat("%d")
        chart.addAxis(ax_x, Qt.AlignBottom)

        ax_y = QValueAxis()
        ax_y.setRange(floor, max(ratings) + 0.05)
        ax_y.setTitleText("Rating")
        ax_y.setTitleBrush(QColor(tokens.text_secondary))
        ax_y.setLabelsColor(QColor(tokens.text_secondary))
        ax_y.setGridLineColor(QColor(255, 255, 255, 20))
        chart.addAxis(ax_y, Qt.AlignLeft)

        for s in chart.series():
            s.attachAxis(ax_x)
            s.attachAxis(ax_y)
