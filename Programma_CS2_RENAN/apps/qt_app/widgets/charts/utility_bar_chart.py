"""Utility comparison bar chart — You vs Pro average, horizontal grouped bars."""

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSet,
    QChart,
    QChartView,
    QHorizontalBarSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class UtilityBarChart(QChartView):
    """Horizontal grouped bars: user metrics vs pro average."""

    def __init__(self, parent=None):
        chart = QChart()
        tokens = get_tokens()
        chart.setBackgroundBrush(QColor(tokens.chart_bg))
        chart.setBackgroundRoundness(8)
        chart.setTitle("Utility: You vs Pro")
        chart.setTitleBrush(QColor(tokens.text_inverse))
        chart.legend().setVisible(True)
        chart.legend().setLabelColor(QColor(tokens.text_primary))
        chart.legend().setAlignment(Qt.AlignBottom)
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMinimumHeight(250)

    def plot(self, utility: dict):
        """Plot from dict with 'user' and optional 'pro' sub-dicts."""
        chart = self.chart()
        chart.removeAllSeries()
        for axis in chart.axes():
            chart.removeAxis(axis)

        user_data = utility.get("user", {})
        pro_data = utility.get("pro", {})
        if not user_data:
            return

        tokens = get_tokens()
        metrics = list(user_data.keys())

        user_set = QBarSet("You")
        user_set.setColor(QColor(tokens.chart_line_primary))
        pro_set = QBarSet("Pro Avg")
        pro_set.setColor(QColor(tokens.chart_line_secondary))

        for m in metrics:
            user_set.append(user_data.get(m, 0))
            pro_set.append(pro_data.get(m, 0))

        series = QHorizontalBarSeries()
        series.append(user_set)
        series.append(pro_set)
        chart.addSeries(series)

        # Y axis (categories — metric names)
        ax_cat = QBarCategoryAxis()
        ax_cat.append([m.replace("_", " ").title() for m in metrics])
        ax_cat.setLabelsColor(QColor(tokens.text_primary))
        chart.addAxis(ax_cat, Qt.AlignLeft)
        series.attachAxis(ax_cat)

        # X axis (values)
        all_vals = list(user_data.values()) + list(pro_data.values())
        ax_val = QValueAxis()
        ax_val.setRange(0, max(all_vals) * 1.15 if all_vals else 10)
        ax_val.setTitleText("Value")
        ax_val.setTitleBrush(QColor(tokens.text_secondary))
        ax_val.setLabelsColor(QColor(tokens.text_secondary))
        ax_val.setGridLineColor(QColor(255, 255, 255, 20))
        chart.addAxis(ax_val, Qt.AlignBottom)
        series.attachAxis(ax_val)
