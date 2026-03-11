from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import numpy as np
import pandas as pd

from Programma_CS2_RENAN.observability.logger_setup import get_logger

LOGGER_NAME = "cs2analyzer.drift"
logger = get_logger(LOGGER_NAME)

# Minimum std used as epsilon when past_std == 0, aligning functional and class-based
# DriftMonitor behaviour: if the past was constant, a tiny shift = high z-score.
_STD_EPSILON = 0.01

DRIFT_FEATURES = ["avg_adr", "kd_ratio", "impact_rounds", "avg_hs", "avg_kast"]


def detect_feature_drift(history: pd.DataFrame, window: int = 10, z_threshold: float = 2.5) -> dict:
    """
    Detects feature drift using rolling Z-score distance.
    """
    logger.info("Feature drift detection started")
    if history.shape[0] < window * 2:
        logger.warning("Insufficient history for drift detection")
        return {}

    recent = history.tail(window)
    past = history.iloc[:-window]
    drift_scores = {}

    for feature in DRIFT_FEATURES:
        _process_feature_drift(feature, history, recent, past, drift_scores, z_threshold)

    logger.info("Feature drift detection completed")
    return drift_scores


def _process_feature_drift(feature, history, recent, past, drift_scores, z_threshold):
    if feature not in history.columns:
        return

    past_mean = past[feature].mean()
    past_std = past[feature].std(ddof=0)
    recent_mean = recent[feature].mean()

    if np.isnan(past_std):
        drift_scores[feature] = 0.0
        return
    if past_std == 0:
        # Past distribution was constant; use epsilon so any shift registers as high drift.
        # Aligns with DriftMonitor class which uses ref_std = 0.01 as fallback.
        past_std = _STD_EPSILON

    z = abs(recent_mean - past_mean) / past_std
    drift_scores[feature] = z
    _log_drift_warning(feature, z, z_threshold)


def _log_drift_warning(feature, z, threshold):
    if z >= threshold:
        logger.warning("Drift detected | %s | z=%s", feature, format(z, ".2f"))


@dataclass
class DriftReport:
    """
    Structured report of feature drift detection results.

    Attributes:
        is_drifted: True if drift exceeds threshold
        drifted_features: List of feature names that drifted
        max_z_score: Maximum Z-score across all features
        timestamp: When the drift check was performed
    """

    is_drifted: bool
    drifted_features: List[str]
    max_z_score: float
    timestamp: datetime


class DriftMonitor:
    """
    Statistical drift monitor for detecting distribution shifts in incoming data.

    Task 2.19.3: Automatically triggers model retraining when drift exceeds thresholds,
    preventing model staleness.
    """

    def __init__(self, z_threshold: float = 2.5):
        """
        Args:
            z_threshold: Z-score threshold for drift detection (default 2.5).
        """
        self.z_threshold = z_threshold

    def check_drift(self, new_batch: pd.DataFrame, reference_stats: dict) -> DriftReport:
        """
        Check if new batch exhibits drift relative to reference statistics.

        Args:
            new_batch: DataFrame of new incoming data.
            reference_stats: Dict with {feature: {"mean": float, "std": float}}.

        Returns:
            DriftReport with drift status and details.
        """
        drifted = []
        z_scores = []

        for feature in DRIFT_FEATURES:
            if feature not in new_batch.columns or feature not in reference_stats:
                continue

            ref = reference_stats[feature]
            ref_mean = ref["mean"]
            ref_std = ref.get("std", 1.0)

            if ref_std == 0 or np.isnan(ref_std):
                ref_std = _STD_EPSILON  # Shared epsilon constant (see module level)

            new_mean = new_batch[feature].mean()
            z = abs(new_mean - ref_mean) / ref_std
            z_scores.append(z)

            if z >= self.z_threshold:
                drifted.append(feature)
                logger.warning(
                    "Drift detected: %s (z=%.2f, ref_mean=%.2f, new_mean=%.2f)",
                    feature,
                    z,
                    ref_mean,
                    new_mean,
                )

        max_z = max(z_scores) if z_scores else 0.0
        is_drifted = len(drifted) > 0

        return DriftReport(
            is_drifted=is_drifted,
            drifted_features=drifted,
            max_z_score=max_z,
            timestamp=datetime.now(timezone.utc),
        )


def should_retrain(drift_history: List[DriftReport], window: int = 5) -> bool:
    """
    Determines if model retraining should be triggered based on drift history.

    Args:
        drift_history: List of recent DriftReport instances.
        window: Number of recent reports to consider.

    Returns:
        True if ≥3 of the last `window` reports indicate drift (prevents spurious triggers).
    """
    if len(drift_history) < window:
        return False

    recent = drift_history[-window:]
    drift_count = sum(1 for report in recent if report.is_drifted)

    if drift_count >= 3:
        logger.warning(
            "Retraining recommended: %d/%d recent drift detections (threshold: 3/%d)",
            drift_count,
            window,
            window,
        )
        return True

    return False
