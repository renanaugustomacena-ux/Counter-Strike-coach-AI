"""
Unified Feature Extraction Module for RAP Coach.

CRITICAL: Both Training (StateReconstructor) and Inference (GhostEngine) MUST use
this single implementation to ensure feature vector consistency.

Changes to the feature order or normalization MUST be made HERE ONLY.
"""

import hashlib
import math
import threading
from typing import Any, ClassVar, Dict, List, Optional, Union

import numpy as np

from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.vectorizer")

# Feature vector dimension - this is the contract with the neural network
METADATA_DIM = 25

# CS2 weapon name -> weapon class mapping (normalized 0-1)
# Keys are lowercase demoparser2 weapon names.
# Categories: 0.0=knife, 0.2=pistol, 0.4=SMG, 0.6=rifle, 0.8=sniper, 1.0=heavy
WEAPON_CLASS_MAP: Dict[str, float] = {
    # Knife = 0.0
    "knife": 0.0,
    "knife_t": 0.0,
    "bayonet": 0.0,
    # Pistols = 0.2
    "glock": 0.2,
    "hkp2000": 0.2,
    "usp_silencer": 0.2,
    "p250": 0.2,
    "elite": 0.2,
    "fiveseven": 0.2,
    "tec9": 0.2,
    "cz75a": 0.2,
    "deagle": 0.2,
    "revolver": 0.2,
    # SMGs = 0.4
    "mac10": 0.4,
    "mp9": 0.4,
    "mp7": 0.4,
    "mp5sd": 0.4,
    "ump45": 0.4,
    "p90": 0.4,
    "bizon": 0.4,
    # Rifles = 0.6
    "ak47": 0.6,
    "m4a1": 0.6,
    "m4a1_silencer": 0.6,
    "famas": 0.6,
    "galilar": 0.6,
    "sg556": 0.6,
    "aug": 0.6,
    # Snipers = 0.8
    "awp": 0.8,
    "ssg08": 0.8,
    "scar20": 0.8,
    "g3sg1": 0.8,
    # Heavy = 1.0
    "nova": 1.0,
    "xm1014": 1.0,
    "mag7": 1.0,
    "sawedoff": 1.0,
    "m249": 1.0,
    "negev": 1.0,
}


class FeatureExtractor:
    """
    Unified feature extraction for RAP Coach training and inference.

    Normalization bounds are configurable via ``HeuristicConfig`` (Task 6.3).
    Call ``FeatureExtractor.configure(config)`` once at startup to override
    defaults.  All existing call-sites continue to work unchanged (backward
    compatible — class-level config defaults to ``None`` which triggers
    built-in defaults).

    Feature Order (25 dimensions):
        0: health (normalized /health_max)
        1: armor (normalized /armor_max)
        2: has_helmet (binary 0/1)
        3: has_defuser (binary 0/1)
        4: equipment_value (normalized /equipment_value_max)
        5: is_crouching (binary 0/1)
        6: is_scoped (binary 0/1)
        7: is_blinded (binary 0/1)
        8: enemies_visible (normalized /enemies_visible_max, clamped)
        9: pos_x (normalized ±pos_xy_extent)
        10: pos_y (normalized ±pos_xy_extent)
        11: pos_z (normalized /pos_z_extent, handles Nuke/Vertigo)
        12: view_x_sin (sin of yaw angle for cyclic continuity)
        13: view_x_cos (cos of yaw angle for cyclic continuity)
        14: view_y (pitch, normalized /pitch_max)
        15: z_penalty (vertical level distinctiveness, 0-1)
        16: kast_estimate (KAST participation ratio, 0-1)
        17: map_id (deterministic map hash, 0-1)
        18: round_phase (economic phase: 0=pistol, 0.33=eco, 0.66=force, 1=full)
        19: weapon_class (0=knife, 0.2=pistol, 0.4=SMG, 0.6=rifle, 0.8=sniper, 1.0=heavy)
        20: time_in_round (seconds / 115, clamped [0, 1])
        21: bomb_planted (binary 0/1)
        22: teammates_alive (count / 4, [0, 1])
        23: enemies_alive (count / 5, [0, 1])
        24: team_economy (team average money / 16000, clamped [0, 1])
    """

    _config: ClassVar[Optional[Any]] = (
        None  # HeuristicConfig; Optional[Any] to avoid circular import at class-definition time
    )
    _config_lock: ClassVar[threading.RLock] = threading.RLock()

    @classmethod
    def configure(cls, config) -> None:
        """
        Set the class-level HeuristicConfig for all subsequent extract() calls.

        Should be called once at application startup after loading config from disk.
        Thread-safe: acquires _config_lock before writing (Bug #6).
        """
        with cls._config_lock:
            cls._config = config

    @classmethod
    def update_heuristics(cls, new_config) -> None:
        """Runtime hot-swap of heuristic parameters (e.g. after learning new bounds).

        Thread-safe: acquires _config_lock before writing (Bug #6).
        """
        with cls._config_lock:
            cls._config = new_config

    @staticmethod
    def extract(
        tick_data: Union[Dict[str, Any], Any],
        map_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """
        Extracts the unified feature vector from tick data.

        Args:
            tick_data: Either a dict with tick fields, or an object (like PlayerTickState)
                       with tick fields as attributes.
            map_name: Optional map name to compute map-specific features (e.g. Z-penalty).
            context: Optional dict with game-level context (time_in_round, bomb_planted,
                     teammates_alive, enemies_alive, team_economy). Features 20-24
                     are first read from tick_data (enriched during ingestion), with
                     fallback to this context dict (DemoFrame at inference).

        Returns:
            np.ndarray of shape (METADATA_DIM,) with float32 values
        """
        # Resolve config: class-level override or built-in defaults (thread-safe read, Bug #6)
        with FeatureExtractor._config_lock:
            cfg = FeatureExtractor._config
        if cfg is None:
            from Programma_CS2_RENAN.backend.processing.feature_engineering.base_features import (
                HeuristicConfig,
            )

            cfg = HeuristicConfig()

        # Helper function to support both dict and object attribute access
        def get_val(key: str, default: Any = 0) -> Any:
            if isinstance(tick_data, dict):
                return tick_data.get(key, default)
            return getattr(tick_data, key, default)

        vec = np.zeros(METADATA_DIM, dtype=np.float32)

        # Core vitals (0-4)
        vec[0] = float(get_val("health", 100)) / cfg.health_max
        vec[1] = float(get_val("armor", 0)) / cfg.armor_max

        # Helmet: try has_helmet, fallback heuristic (armor > 0 often means helmet)
        has_helmet = get_val("has_helmet", None)
        if has_helmet is None:
            has_helmet = get_val("armor", 0) > 0
        vec[2] = 1.0 if has_helmet else 0.0

        vec[3] = 1.0 if get_val("has_defuser", False) else 0.0
        vec[4] = float(get_val("equipment_value", 0)) / cfg.equipment_value_max

        # Movement/Stance (5-7)
        vec[5] = 1.0 if get_val("is_crouching", False) else 0.0
        vec[6] = 1.0 if get_val("is_scoped", False) else 0.0
        vec[7] = 1.0 if get_val("is_blinded", False) else 0.0

        # Awareness (8)
        enemies_visible = float(get_val("enemies_visible", 0))
        vec[8] = min(enemies_visible / cfg.enemies_visible_max, 1.0)

        # Position (9-11)
        pos_x = float(get_val("pos_x", get_val("x", get_val("X", 0))))
        pos_y = float(get_val("pos_y", get_val("y", get_val("Y", 0))))
        pos_z = float(get_val("pos_z", get_val("z", get_val("Z", 0))))
        if pos_x == 0.0 and pos_y == 0.0 and pos_z == 0.0:
            # NOTE (F2-15): (0,0,0) could be a valid world position on some maps, so
            # this is logged at DEBUG to avoid false alarms.
            _logger.debug("Position data missing — all key variants (pos_x/x/X) returned 0")

        vec[9] = np.clip(pos_x / cfg.pos_xy_extent, -1.0, 1.0)
        vec[10] = np.clip(pos_y / cfg.pos_xy_extent, -1.0, 1.0)
        vec[11] = np.clip(pos_z / cfg.pos_z_extent, -1.0, 1.0)

        # View angles (12-14) - sin/cos encoding for yaw to avoid ±180° discontinuity
        yaw_deg = float(get_val("view_x", 0))
        yaw_rad = math.radians(yaw_deg)
        vec[12] = math.sin(yaw_rad)
        vec[13] = math.cos(yaw_rad)
        vec[14] = float(get_val("view_y", 0)) / cfg.pitch_max

        # 15: Z-Penalty (Vertical Awareness) — lazy import to avoid circular dependency
        if map_name:
            from Programma_CS2_RENAN.core.spatial_data import compute_z_penalty

            vec[15] = compute_z_penalty(pos_z, map_name)
        else:
            vec[15] = 0.0

        # 16: KAST estimate (Kill/Assist/Survive/Trade participation ratio)
        kast_val = get_val("kast", get_val("avg_kast", None))
        if kast_val is not None:
            vec[16] = float(kast_val)
        else:
            kills = float(get_val("kills", get_val("kills_total", 0)))
            assists = float(get_val("assists", get_val("assists_total", 0)))
            deaths = float(get_val("deaths", get_val("deaths_total", 0)))
            rounds_played = float(get_val("rounds_played", 1))
            if rounds_played > 0 and (kills + assists + deaths) > 0:
                from Programma_CS2_RENAN.backend.processing.feature_engineering.kast import (
                    estimate_kast_from_stats,
                )

                vec[16] = estimate_kast_from_stats(
                    int(kills), int(assists), int(deaths), int(rounds_played)
                )

        # 17: Map identity encoding (deterministic hash for map-specific learning)
        # NOTE: Python's built-in hash() is NOT deterministic across sessions
        # (PYTHONHASHSEED randomization). Use hashlib for reproducibility.
        if map_name:
            h = int(hashlib.md5(map_name.encode()).hexdigest(), 16)
            vec[17] = (h % 10000) / 10000.0

        # 18: Round phase indicator (economic phase from equipment value)
        equip_val = float(get_val("equipment_value", 0))
        if equip_val > 0:
            if equip_val < 1500:
                vec[18] = 0.0  # pistol
            elif equip_val < 3000:
                vec[18] = 0.33  # eco
            elif equip_val < 4000:
                vec[18] = 0.66  # force
            else:
                vec[18] = 1.0  # full_buy

        # 19: Weapon class encoding (from active_weapon string in DB or weapon in DemoFrame)
        weapon_name = str(get_val("active_weapon", get_val("weapon", "unknown"))).lower()
        # Strip common prefixes demoparser2 may include (e.g. "weapon_ak47" -> "ak47")
        if weapon_name.startswith("weapon_"):
            weapon_name = weapon_name[7:]
        weapon_class = WEAPON_CLASS_MAP.get(weapon_name, None)
        if weapon_class is None:
            _logger.debug("H-12: Unknown weapon '%s' — using default class 0.1", weapon_name)
            weapon_class = 0.1
        vec[19] = weapon_class

        # Context-dependent features (20-24): Read from tick_data first (enriched
        # during ingestion), fall back to context dict (DemoFrame at inference).
        # This eliminates the training/inference skew where these features were
        # always 0.0 during training but populated during inference.
        ctx = context or {}

        # 20: time_in_round
        time_val = get_val("time_in_round", None)
        if time_val is None:
            time_val = ctx.get("time_in_round", 0.0)
        vec[20] = min(float(time_val or 0.0) / 115.0, 1.0)

        # 21: bomb_planted
        bomb_val = get_val("bomb_planted", None)
        if bomb_val is None:
            bomb_val = ctx.get("bomb_planted", False)
        vec[21] = 1.0 if bomb_val else 0.0

        # 22: teammates_alive
        team_val = get_val("teammates_alive", None)
        if team_val is None:
            team_val = ctx.get("teammates_alive", 0)
        vec[22] = min(float(team_val or 0) / 4.0, 1.0)

        # 23: enemies_alive
        enemy_val = get_val("enemies_alive", None)
        if enemy_val is None:
            enemy_val = ctx.get("enemies_alive", 0)
        vec[23] = min(float(enemy_val or 0) / 5.0, 1.0)

        # 24: team_economy
        econ_val = get_val("team_economy", None)
        if econ_val is None:
            econ_val = ctx.get("team_economy", 0)
        vec[24] = min(float(econ_val or 0) / 16000.0, 1.0)

        # Warn if any feature produced Inf/NaN — the nan_to_num clamp is a safety net,
        # not a substitute for fixing the upstream bug that created the anomaly. (F2-16)
        if np.any(~np.isfinite(vec)):
            _logger.warning(
                "Feature vector contains non-finite values before clamp — "
                "indices: %s. Check upstream normalisation.",
                np.where(~np.isfinite(vec))[0].tolist(),
            )
        vec = np.nan_to_num(vec, nan=0.0, posinf=1.0, neginf=-1.0)
        return vec

    @staticmethod
    def extract_batch(
        tick_data_list: List[Union[Dict[str, Any], Any]],
        map_name: Optional[str] = None,
        contexts: Optional[List[Dict[str, Any]]] = None,
    ) -> np.ndarray:
        """
        Extracts features for a batch of ticks.

        Args:
            tick_data_list: List of tick data (dicts or objects)
            map_name: Optional map name for context features
            contexts: Optional list of context dicts (one per tick). If None,
                      all ticks get context=None (features 20-24 default to 0.0).

        Returns:
            np.ndarray of shape (len(tick_data_list), METADATA_DIM)
        """
        if contexts is None:
            contexts = [None] * len(tick_data_list)
        return np.array(
            [
                FeatureExtractor.extract(t, map_name, ctx)
                for t, ctx in zip(tick_data_list, contexts)
            ],
            dtype=np.float32,
        )

    @staticmethod
    def get_feature_names() -> List[str]:
        """Returns the ordered list of feature names for debugging/logging."""
        return [
            "health",
            "armor",
            "has_helmet",
            "has_defuser",
            "equipment_value",
            "is_crouching",
            "is_scoped",
            "is_blinded",
            "enemies_visible",
            "pos_x",
            "pos_y",
            "pos_z",
            "view_yaw_sin",
            "view_yaw_cos",
            "view_pitch",
            "z_penalty",
            "kast_estimate",
            "map_id",
            "round_phase",
            "weapon_class",
            "time_in_round",
            "bomb_planted",
            "teammates_alive",
            "enemies_alive",
            "team_economy",
        ]
