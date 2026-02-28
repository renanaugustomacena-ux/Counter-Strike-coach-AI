import numpy as np


def compute_trend(values):
    x = np.arange(len(values))
    y = np.array(values)

    slope = np.polyfit(x, y, 1)[0]
    volatility = y.std()

    confidence = min(1.0, len(values) / 30)

    return slope, volatility, confidence
