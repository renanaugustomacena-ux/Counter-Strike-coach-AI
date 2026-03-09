from dataclasses import dataclass


@dataclass
class FeatureTrend:
    feature: str
    slope: float
    volatility: float
    confidence: float
