import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from Programma_CS2_RENAN.backend.processing.feature_engineering.rating import (
    compute_hltv2_rating,
    compute_impact_rating,
    compute_survival_rating,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger


@dataclass
class HeuristicConfig:
    """
    Configurable heuristic thresholds for feature engineering.

    Task 6.3: Replaces hardcoded "magic numbers" with learned/tunable parameters.
    Defaults match historical behavior (zero-regression guarantee).

    Each parameter documents its acceptable range and semantic purpose.
    """

    # --- Match Analysis Thresholds ---
    impact_kill_threshold: float = 1.0  # Kills > this → impact round. Range: [0.5, 3.0]
    impact_adr_threshold: float = 100.0  # ADR > this → impact round.  Range: [60.0, 150.0]

    # --- Feature Normalization Bounds ---
    # These control the divisor used when normalizing raw values to ~[0, 1].
    health_max: float = 100.0  # HP ceiling (game constant).      Range: [100, 100]
    armor_max: float = 100.0  # Armor ceiling (game constant).   Range: [100, 100]
    equipment_value_max: float = 10000.0  # Equip-value ceiling.             Range: [6000, 16000]
    enemies_visible_max: float = 5.0  # Max visible enemies (5v5).       Range: [5, 5]
    pos_xy_extent: float = 4096.0  # World-coord ±extent for X/Y.    Range: [3500, 5000]
    pos_z_extent: float = 1024.0  # World-coord extent for Z.       Range: [512, 2048]
    pitch_max: float = 90.0  # Max pitch angle in degrees.      Range: [90, 90]

    # --- Round Phase Thresholds (equipment value breakpoints) ---
    round_phase_eco_threshold: float = 1500.0   # Below = pistol round.       Range: [1000, 2000]
    round_phase_force_threshold: float = 3000.0  # Below = eco round.          Range: [2500, 3500]
    round_phase_full_threshold: float = 4000.0   # Below = force buy.          Range: [3500, 5000]

    # --- Model Hyperparameters ---
    context_gate_l1_weight: float = 1e-4  # L1 sparsity weight on context gate. Range: [1e-6, 1e-2]

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HeuristicConfig":
        """Deserialize from dict, ignoring unknown keys for forward compatibility."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def load_learned_heuristics(config_path: Optional[Path] = None) -> HeuristicConfig:
    """
    Load heuristic configuration from JSON file.

    Args:
        config_path: Path to JSON config. If None, uses default in backend/storage/.

    Returns:
        HeuristicConfig instance. Falls back to defaults if file doesn't exist.
    """
    if config_path is None:
        from Programma_CS2_RENAN.core.config import BASE_DIR

        config_path = Path(BASE_DIR) / "backend" / "storage" / "heuristic_config.json"

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return HeuristicConfig.from_dict(data)
        except Exception as e:
            get_logger("cs2analyzer.base_features").warning(
                "Failed to load heuristic config from %s: %s — using defaults", config_path, e
            )

    return HeuristicConfig()  # Default values


def save_heuristic_config(config: HeuristicConfig, config_path: Optional[Path] = None):
    """
    Save heuristic configuration to JSON file.

    Args:
        config: HeuristicConfig instance to persist.
        config_path: Optional path override.
    """
    if config_path is None:
        from Programma_CS2_RENAN.core.config import BASE_DIR

        config_path = Path(BASE_DIR) / "backend" / "storage" / "heuristic_config.json"

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)


def extract_match_stats(
    rounds_df: pd.DataFrame, heuristics: Optional[HeuristicConfig] = None
) -> dict:
    """
    Aggregates per-round data into match-level statistics,
    including new tactical metrics and Positional Aggression.

    Uses the unified HLTV 2.0 rating formula (shared with demo_parser.py)
    to prevent Inference-Training Skew.

    Args:
        rounds_df: Per-round data DataFrame.
        heuristics: Optional HeuristicConfig. If None, uses defaults.

    Returns:
        Dict of aggregated match statistics.
    """
    if rounds_df.empty:
        return {}

    if heuristics is None:
        heuristics = HeuristicConfig()

    # Base Stats
    # NOTE: .std() returns NaN for a single-row DataFrame (not 0.0). Use np.nan_to_num()
    # rather than `or 0.0` because `NaN or 0.0` evaluates to NaN (truthy in Python float).
    stats = {
        "avg_kills": rounds_df["kills"].mean(),
        "avg_deaths": rounds_df["deaths"].mean(),
        "avg_adr": rounds_df["adr"].mean(),
        "avg_hs": rounds_df["headshot_pct"].mean(),
        "avg_kast": rounds_df["kast"].mean(),
        "kill_std": float(np.nan_to_num(rounds_df["kills"].std(), nan=0.0)),
        "adr_std": float(np.nan_to_num(rounds_df["adr"].std(), nan=0.0)),
        "kd_ratio": rounds_df["kills"].sum() / max(1, rounds_df["deaths"].sum()),
    }

    # Opening Duels
    opening_duels = rounds_df[rounds_df["opening_duel"] != 0]
    stats["opening_duel_win_pct"] = (
        (opening_duels["opening_duel"] == 1).mean() if not opening_duels.empty else 0.0
    )

    # Utility
    stats["utility_blind_time"] = rounds_df["blind_time"].sum()
    stats["utility_enemies_blinded"] = rounds_df["enemies_blinded"].mean()

    # Clutches
    stats["clutch_win_pct"] = rounds_df["is_clutch_win"].mean()

    # Positional Aggression
    stats["positional_aggression_score"] = rounds_df["aggression_score"].mean()

    # Advanced Metrics (Notebook Concepts)
    total_hits = rounds_df["hits"].sum()
    total_shots = rounds_df["shots"].sum()
    stats["accuracy"] = total_hits / max(1, total_shots)

    # econ_rating: damage efficiency per monetary unit, normalised per round.
    # FIXED (F2-28): The old formula summed ADR values (already averages per round)
    # and divided by total money, producing a metric that grew with round count.
    # Correct formula: mean_ADR / mean_money_per_round — scale-invariant per round.
    avg_money_per_round = rounds_df["money_spent"].mean()
    stats["econ_rating"] = stats["avg_adr"] / max(1.0, avg_money_per_round)

    # Simple impact calculation (Task 6.3: Uses configurable thresholds)
    impact_rounds = rounds_df[
        (rounds_df["kills"] > heuristics.impact_kill_threshold)
        | (rounds_df["adr"] > heuristics.impact_adr_threshold)
    ].shape[0]
    stats["impact_rounds"] = float(impact_rounds)

    # --- HLTV 2.0 Rating (Unified with demo_parser.py) ---
    kpr = stats["avg_kills"]
    dpr = stats["avg_deaths"]
    kast = stats["avg_kast"]
    avg_adr = stats["avg_adr"]

    stats["rating_impact"] = compute_impact_rating(kpr, avg_adr)
    stats["rating_survival"] = compute_survival_rating(dpr)
    stats["rating"] = compute_hltv2_rating(
        kpr=kpr, dpr=dpr, kast=kast, avg_adr=avg_adr, impact=stats["rating_impact"]
    )

    stats["anomaly_score"] = 0.0
    stats["sample_weight"] = 1.0

    return stats
