"""
Unified Feature Extraction Module for RAP Coach.

CRITICAL: Both Training (StateReconstructor) and Inference (GhostEngine) MUST use
this single implementation to ensure feature vector consistency.

Changes to the feature order or normalization MUST be made HERE ONLY.
"""

import hashlib
import math
import threading
import time
from collections import Counter, deque
from typing import Any, ClassVar, Dict, List, Optional, Union

import numpy as np

from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.vectorizer")


class DataQualityError(Exception):
    """Raised when data quality falls below acceptable thresholds for training."""

    pass


# P-VEC-01: one-time warning flag for missing map_name during z_penalty
_z_penalty_warned = False

# Feature vector dimension - this is the contract with the neural network
METADATA_DIM = 25

# CS2 weapon name -> weapon class mapping (normalized 0-1)
# Keys are lowercase. Includes both internal names (e.g. "ak47") and
# demoparser2 display names (e.g. "ak-47") for compatibility.
# Categories: 0.0=knife, 0.2=pistol, 0.4=SMG, 0.6=rifle, 0.8=sniper, 1.0=heavy
WEAPON_CLASS_MAP: Dict[str, float] = {
    # Knife = 0.0 (internal + display names + all skin variants)
    "knife": 0.0,
    "knife_t": 0.0,
    "bayonet": 0.0,
    "butterfly knife": 0.0,
    "classic knife": 0.0,
    "falchion knife": 0.0,
    "flip knife": 0.0,
    "gut knife": 0.0,
    "huntsman knife": 0.0,
    "karambit": 0.0,
    "kukri knife": 0.0,
    "m9 bayonet": 0.0,
    "navaja knife": 0.0,
    "nomad knife": 0.0,
    "paracord knife": 0.0,
    "shadow daggers": 0.0,
    "skeleton knife": 0.0,
    "stiletto knife": 0.0,
    "survival knife": 0.0,
    "talon knife": 0.0,
    "ursus knife": 0.0,
    # Pistols = 0.2
    "glock": 0.2,
    "glock-18": 0.2,
    "hkp2000": 0.2,
    "p2000": 0.2,
    "usp_silencer": 0.2,
    "usp-s": 0.2,
    "p250": 0.2,
    "elite": 0.2,
    "dual berettas": 0.2,
    "fiveseven": 0.2,
    "five-seven": 0.2,
    "tec9": 0.2,
    "tec-9": 0.2,
    "cz75a": 0.2,
    "cz75-auto": 0.2,
    "deagle": 0.2,
    "desert eagle": 0.2,
    "revolver": 0.2,
    "r8 revolver": 0.2,
    # SMGs = 0.4
    "mac10": 0.4,
    "mac-10": 0.4,
    "mp9": 0.4,
    "mp7": 0.4,
    "mp5sd": 0.4,
    "mp5-sd": 0.4,
    "ump45": 0.4,
    "ump-45": 0.4,
    "p90": 0.4,
    "bizon": 0.4,
    "pp-bizon": 0.4,
    # Rifles = 0.6
    "ak47": 0.6,
    "ak-47": 0.6,
    "m4a1": 0.6,
    "m4a4": 0.6,
    "m4a1_silencer": 0.6,
    "m4a1-s": 0.6,
    "famas": 0.6,
    "galilar": 0.6,
    "galil ar": 0.6,
    "sg556": 0.6,
    "sg 553": 0.6,
    "aug": 0.6,
    # Snipers = 0.8
    "awp": 0.8,
    "ssg08": 0.8,
    "ssg 08": 0.8,
    "scar20": 0.8,
    "scar-20": 0.8,
    "g3sg1": 0.8,
    # Heavy = 1.0
    "nova": 1.0,
    "xm1014": 1.0,
    "mag7": 1.0,
    "mag-7": 1.0,
    "sawedoff": 1.0,
    "sawed-off": 1.0,
    "m249": 1.0,
    "negev": 1.0,
    # Grenades / Utility = 0.1
    "flashbang": 0.1,
    "smokegrenade": 0.1,
    "smoke grenade": 0.1,
    "hegrenade": 0.1,
    "high explosive grenade": 0.1,
    "molotov": 0.1,
    "incgrenade": 0.1,
    "incendiary grenade": 0.1,
    "decoy": 0.1,
    "decoy grenade": 0.1,
    # Special equipment = 0.05
    "taser": 0.05,
    "zeus x27": 0.05,
    "c4": 0.05,
    "c4 explosive": 0.05,
}

# H-12: Sentinel for truly unknown weapons — logged at WARNING on first occurrence
_UNKNOWN_WEAPON_DEFAULT = 0.5
_unknown_weapons_seen: set = set()

# P-VEC-02: Track NaN/Inf occurrences for upstream bug visibility
_nan_inf_clamp_count: int = 0
_nan_inf_lock = __import__("threading").Lock()
# 26-VEC-01: per-batch clamp counter (thread-local). The P3-A gate must measure only
# the clamps produced by ITS OWN extract_batch() call, not those of concurrent batches
# running on other threads. The global _nan_inf_clamp_count above stays a cumulative
# telemetry counter; this thread-local is the per-batch, race-free signal for the gate.
_batch_clamp_local = threading.local()

# D2: log-EMISSION throttle for clamp events. The first _CLAMP_VERBOSE_LIMIT
# occurrences log verbosely with full attribution; afterwards one aggregate
# line per _CLAMP_AGGREGATE_WINDOW_S summarizes what was suppressed. An
# upstream bug therefore cannot turn the log into a disk-filling storm.
# Throttling affects emission ONLY — every counter stays exact (D2.2).
_CLAMP_VERBOSE_LIMIT = 10
_CLAMP_AGGREGATE_WINDOW_S = 60.0
_clamp_suppressed_since_flush = 0
_clamp_suppressed_features: Counter = Counter()
_clamp_window_started = 0.0

# R4-14-01 emission throttle (same D2 discipline as the clamp log above):
# a teacher-daemon pass over sparse data can hit thousands of (0,0,0)
# ticks and turn the warning into a disk-filling storm. Verbose for the
# first occurrences, then one aggregate line per window; the counter
# stays exact regardless.
_zero_pos_count = 0
_zero_pos_suppressed_since_flush = 0
_zero_pos_window_started = 0.0

# D1: sliding-window quality gate for the SINGLE-sample path (extract()).
# The batch path has the P3-A gate; inference-time extracts previously had
# none — live coaching could silently consume garbage vectors. If more than
# _SINGLE_GATE_THRESHOLD of the last _SINGLE_WINDOW_N single extracts
# clamped, emit CRITICAL + a StateManager notification. Degrade LOUDLY,
# never raise in the live coaching path (Law 3). Hysteresis: re-arms only
# after the rate falls below half the threshold.
_SINGLE_WINDOW_N = 1000
_SINGLE_GATE_THRESHOLD = 0.05
_single_clamp_window: deque = deque(maxlen=_SINGLE_WINDOW_N)
_single_gate_tripped = False


def _reset_quality_gate_state_for_tests() -> None:
    """Test-only: reset D1/D2 module state (never call from production code)."""
    global _clamp_suppressed_since_flush, _clamp_window_started, _single_gate_tripped
    global _zero_pos_count, _zero_pos_suppressed_since_flush, _zero_pos_window_started
    with _nan_inf_lock:
        _clamp_suppressed_since_flush = 0
        _clamp_suppressed_features.clear()
        _clamp_window_started = 0.0
        _single_clamp_window.clear()
        _single_gate_tripped = False
        _zero_pos_count = 0
        _zero_pos_suppressed_since_flush = 0
        _zero_pos_window_started = 0.0


def _log_zero_position_throttled() -> None:
    """R4-14-01: (0,0,0)-position warning with D2-style emission throttling."""
    global _zero_pos_count, _zero_pos_suppressed_since_flush, _zero_pos_window_started
    emit_verbose = False
    emit_aggregate = None
    with _nan_inf_lock:
        _zero_pos_count += 1
        count_snapshot = _zero_pos_count
        if count_snapshot <= _CLAMP_VERBOSE_LIMIT:
            emit_verbose = True
        else:
            _zero_pos_suppressed_since_flush += 1
            now = time.monotonic()
            if _zero_pos_window_started == 0.0:
                _zero_pos_window_started = now
            elif now - _zero_pos_window_started >= _CLAMP_AGGREGATE_WINDOW_S:
                emit_aggregate = (_zero_pos_suppressed_since_flush, count_snapshot)
                _zero_pos_suppressed_since_flush = 0
                _zero_pos_window_started = now
    if emit_verbose:
        _logger.warning(
            "R4-14-01: Position (0,0,0) — likely missing data, not a valid "
            "coordinate (occurrence #%d)",
            count_snapshot,
        )
    elif emit_aggregate is not None:
        _logger.warning(
            "R4-14-01/D2: %d further (0,0,0)-position ticks suppressed over "
            "the last %.0fs (total %d). Counter remains exact; fix upstream data.",
            emit_aggregate[0],
            _CLAMP_AGGREGATE_WINDOW_S,
            emit_aggregate[1],
        )


# P-X-01: Feature schema names — single source of truth for train/infer parity.
# Length MUST equal METADATA_DIM.  If you add/remove a feature, update BOTH.
FEATURE_NAMES: tuple = (
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
)
assert len(FEATURE_NAMES) == METADATA_DIM, (
    f"P-X-01: FEATURE_NAMES has {len(FEATURE_NAMES)} entries but "
    f"METADATA_DIM={METADATA_DIM}. Feature schema is out of sync."
)


# ---------------------------------------------------------------------------
# Per-slot fillers (private helpers used by FeatureExtractor.extract).
# Each helper mutates `vec` in place; ordering / slot indices MUST match the
# FEATURE_NAMES tuple above (training-serving contract — P-X-01).
# ---------------------------------------------------------------------------


def _fill_vitals_movement(vec: np.ndarray, get_val, cfg) -> None:
    """Slots 0-7: health, armor, helmet, defuser, equipment, crouch, scope, blinded."""
    vec[0] = float(get_val("health", 100)) / cfg.health_max
    vec[1] = float(get_val("armor", 0)) / cfg.armor_max

    has_helmet = get_val("has_helmet", None)
    if has_helmet is None:
        # Fallback heuristic: armor > 0 often means helmet
        has_helmet = get_val("armor", 0) > 0
    vec[2] = 1.0 if has_helmet else 0.0

    vec[3] = 1.0 if get_val("has_defuser", False) else 0.0
    vec[4] = float(get_val("equipment_value", 0)) / cfg.equipment_value_max

    vec[5] = 1.0 if get_val("is_crouching", False) else 0.0
    vec[6] = 1.0 if get_val("is_scoped", False) else 0.0

    # Feature #7 (is_blinded): demoparser2 populates flash_duration (float seconds
    # >= 0). Prefer flash_duration > 0 as source of truth; fall back to is_blinded
    # for legacy demos parsed with a different extractor.
    _flash_dur = get_val("flash_duration", 0.0)
    try:
        _flash_dur = float(_flash_dur) if _flash_dur is not None else 0.0
    except (TypeError, ValueError):
        _flash_dur = 0.0
    vec[7] = 1.0 if (_flash_dur > 0.0 or get_val("is_blinded", False)) else 0.0


def _fill_awareness_position_view(vec: np.ndarray, get_val, cfg) -> float:
    """Slots 8-14: enemies_visible, position xyz, view yaw sin/cos + pitch.

    Returns pos_z so the caller can pass it to _fill_z_penalty without re-reading.
    """
    enemies_visible = float(get_val("enemies_visible", 0))
    vec[8] = min(enemies_visible / cfg.enemies_visible_max, 1.0)

    pos_x = float(get_val("pos_x", get_val("x", get_val("X", 0))))
    pos_y = float(get_val("pos_y", get_val("y", get_val("Y", 0))))
    pos_z = float(get_val("pos_z", get_val("z", get_val("Z", 0))))
    if pos_x == 0.0 and pos_y == 0.0 and pos_z == 0.0:
        # R4-14-01: On standard CS2 maps, (0,0,0) is outside the playable area.
        _log_zero_position_throttled()

    vec[9] = np.clip(pos_x / cfg.pos_xy_extent, -1.0, 1.0)
    vec[10] = np.clip(pos_y / cfg.pos_xy_extent, -1.0, 1.0)
    vec[11] = np.clip(pos_z / cfg.pos_z_extent, -1.0, 1.0)

    # View angles (12-14) — sin/cos encoding for yaw to avoid ±180° discontinuity
    yaw_deg = float(get_val("view_x", 0))
    yaw_rad = math.radians(yaw_deg)
    vec[12] = math.sin(yaw_rad)
    vec[13] = math.cos(yaw_rad)
    vec[14] = float(get_val("view_y", 0)) / cfg.pitch_max
    return pos_z


def _fill_z_penalty(vec: np.ndarray, pos_z: float, map_name: Optional[str]) -> None:
    """Slot 15: z_penalty (vertical awareness; lazy import avoids circular dep)."""
    if map_name:
        from Programma_CS2_RENAN.core.spatial_data import compute_z_penalty

        vec[15] = compute_z_penalty(pos_z, map_name)
        return

    # P-VEC-01: z_penalty defaults to 0.0 when map_name unavailable. Callers SHOULD
    # provide map_name for feature parity with training. Warn once per process.
    global _z_penalty_warned
    if not _z_penalty_warned:
        _logger.warning(
            "P-VEC-01: map_name not provided — z_penalty defaults to 0.0. "
            "Feature parity with training may be degraded."
        )
        _z_penalty_warned = True
    vec[15] = 0.0


def _fill_round_metadata(vec: np.ndarray, get_val, cfg, map_name: Optional[str]) -> None:
    """Slots 16-18: KAST, map_id hash, round_phase."""
    # 16: KAST — uses real KAST data when available (training pipeline injects from
    # playermatchstats.avg_kast or round-level computation). Defaults to 0.0; the
    # old estimate_kast_from_stats() heuristic was retired (was 0.91 vs real 0.71).
    kast_val = get_val("kast", get_val("avg_kast", None))
    if kast_val is not None:
        vec[16] = float(kast_val)

    # 17: map identity (deterministic hash; Python's built-in hash() is NOT
    # deterministic across sessions — must use hashlib for reproducibility).
    if map_name:
        h = int(hashlib.md5(map_name.encode(), usedforsecurity=False).hexdigest(), 16)
        vec[17] = (h % 10000) / 10000.0

    # 18: round phase (economic phase from equipment value)
    equip_val = float(get_val("equipment_value", 0))
    if equip_val > 0:
        if equip_val < cfg.round_phase_eco_threshold:
            vec[18] = 0.0  # pistol
        elif equip_val < cfg.round_phase_force_threshold:
            vec[18] = 0.33  # eco
        elif equip_val < cfg.round_phase_full_threshold:
            vec[18] = 0.66  # force
        else:
            vec[18] = 1.0  # full_buy


def _fill_weapon_class(vec: np.ndarray, get_val) -> None:
    """Slot 19: weapon class encoding (from active_weapon string)."""
    weapon_name = str(get_val("active_weapon", get_val("weapon", "unknown"))).lower()
    # Strip prefixes demoparser2 may include (e.g. "weapon_ak47" -> "ak47")
    if weapon_name.startswith("weapon_"):
        weapon_name = weapon_name[7:]
    weapon_class = WEAPON_CLASS_MAP.get(weapon_name, None)
    if weapon_class is None:
        # H-12: Distinguish numeric entity handles (old ingestion artifact) from
        # genuinely unknown weapon strings. demoparser2 < ~0.40 returned the
        # active-weapon entity handle (large 32-bit int) instead of the display
        # name. 0xFFFFFF (16777215) is CS2's "no weapon equipped" sentinel.
        try:
            numeric_val = int(weapon_name)
            if numeric_val == 0xFFFFFF:
                weapon_class = 0.0
            else:
                _logger.debug(
                    "H-12: Numeric weapon handle %s — legacy ingestion data, re-ingest to fix",
                    weapon_name,
                )
                weapon_class = _UNKNOWN_WEAPON_DEFAULT
        except (ValueError, TypeError):
            if weapon_name != "unknown":
                if weapon_name not in _unknown_weapons_seen:
                    _unknown_weapons_seen.add(weapon_name)
                    _logger.warning(
                        "H-12: Unknown weapon '%s' — add to WEAPON_CLASS_MAP", weapon_name
                    )
            weapon_class = _UNKNOWN_WEAPON_DEFAULT
    vec[19] = weapon_class


def _fill_context_features(
    vec: np.ndarray, get_val, context: Optional[Dict[str, Any]], cfg=None
) -> None:
    """Slots 20-24: time_in_round, bomb_planted, teammates_alive, enemies_alive, team_economy.

    Reads from tick_data first (enriched during ingestion), falls back to the
    context dict (DemoFrame at inference). Eliminates the training/inference
    skew where these features were always 0.0 during training but populated
    during inference.

    D-07: normalisation bounds come from ``cfg`` (HeuristicConfig) when provided;
    hardcoded fallbacks preserve backward compatibility for callers that omit it.
    """
    ctx = context or {}
    time_max = cfg.time_in_round_max if cfg else 115.0
    team_max = cfg.teammates_alive_max if cfg else 4.0
    enemy_max = cfg.enemies_alive_max if cfg else 5.0
    econ_max = cfg.team_economy_max if cfg else 16000.0

    time_val = get_val("time_in_round", None)
    if time_val is None:
        time_val = ctx.get("time_in_round", 0.0)
    vec[20] = min(float(time_val or 0.0) / time_max, 1.0)

    bomb_val = get_val("bomb_planted", None)
    if bomb_val is None:
        bomb_val = ctx.get("bomb_planted", False)
    vec[21] = 1.0 if bomb_val else 0.0

    team_val = get_val("teammates_alive", None)
    if team_val is None:
        team_val = ctx.get("teammates_alive", 0)
    vec[22] = min(float(team_val or 0) / team_max, 1.0)

    enemy_val = get_val("enemies_alive", None)
    if enemy_val is None:
        enemy_val = ctx.get("enemies_alive", 0)
    vec[23] = min(float(enemy_val or 0) / enemy_max, 1.0)

    econ_val = get_val("team_economy", None)
    if econ_val is None:
        econ_val = ctx.get("team_economy", 0)
    vec[24] = min(float(econ_val or 0) / econ_max, 1.0)


def _finalize_vector(vec: np.ndarray) -> np.ndarray:
    """P-VEC-02 / R4-14-02 (+D1/D2): clamp NaN/Inf to safe defaults.

    D2: verbose ERROR (full attribution) for the first _CLAMP_VERBOSE_LIMIT
    occurrences, then one aggregate line per _CLAMP_AGGREGATE_WINDOW_S —
    counters stay exact regardless. D1: the single-sample path (extract()
    outside a batch) feeds a sliding window; a sustained clamp rate above
    _SINGLE_GATE_THRESHOLD escalates CRITICAL + user notification without
    ever raising (the batch path keeps its own P3-A raise-gate).
    """
    global _nan_inf_clamp_count, _clamp_suppressed_since_flush, _clamp_window_started
    global _single_gate_tripped
    in_batch = getattr(_batch_clamp_local, "in_batch", False)
    clamped = bool(np.any(~np.isfinite(vec)))

    if clamped:
        bad_indices = np.where(~np.isfinite(vec))[0].tolist()
        bad_names = [FEATURE_NAMES[i] for i in bad_indices if i < len(FEATURE_NAMES)]
        emit_verbose = False
        emit_aggregate = None
        with _nan_inf_lock:
            _nan_inf_clamp_count += 1
            count_snapshot = _nan_inf_clamp_count
            if count_snapshot <= _CLAMP_VERBOSE_LIMIT:
                emit_verbose = True
            else:
                _clamp_suppressed_since_flush += 1
                _clamp_suppressed_features.update(bad_names)
                now = time.monotonic()
                if _clamp_window_started == 0.0:
                    _clamp_window_started = now
                elif now - _clamp_window_started >= _CLAMP_AGGREGATE_WINDOW_S:
                    emit_aggregate = (
                        _clamp_suppressed_since_flush,
                        list(_clamp_suppressed_features.most_common(5)),
                    )
                    _clamp_suppressed_since_flush = 0
                    _clamp_suppressed_features.clear()
                    _clamp_window_started = now
        # 26-VEC-01: tally this clamp against the current thread's per-batch counter
        # (initialised by extract_batch) so the P3-A gate is isolated from other threads.
        _batch_clamp_local.count = getattr(_batch_clamp_local, "count", 0) + 1
        if emit_verbose:
            _logger.error(
                "P-VEC-02: Feature vector contains NaN/Inf BEFORE clamp "
                "(occurrence #%d) — indices: %s, features: %s. "
                "Clamping to defaults; fix upstream normalisation.",
                count_snapshot,
                bad_indices,
                bad_names,
            )
        elif emit_aggregate is not None:
            _logger.error(
                "P-VEC-02/D2: %d further NaN/Inf clamps suppressed over the last "
                "%.0fs (top features: %s). Counters remain exact; fix upstream.",
                emit_aggregate[0],
                _CLAMP_AGGREGATE_WINDOW_S,
                emit_aggregate[1],
            )

    # D1: sliding-window gate for the single-sample (inference) path only —
    # batch rows are P3-A's jurisdiction.
    if not in_batch:
        trip_rate = None
        with _nan_inf_lock:
            _single_clamp_window.append(1 if clamped else 0)
            if len(_single_clamp_window) == _SINGLE_WINDOW_N:
                rate = sum(_single_clamp_window) / _SINGLE_WINDOW_N
                if rate > _SINGLE_GATE_THRESHOLD and not _single_gate_tripped:
                    _single_gate_tripped = True
                    trip_rate = rate
                elif rate <= _SINGLE_GATE_THRESHOLD / 2 and _single_gate_tripped:
                    _single_gate_tripped = False  # hysteresis re-arm
        if trip_rate is not None:
            _logger.critical(
                "D1: single-sample NaN/Inf clamp rate %.1f%% over the last %d "
                "extracts exceeds %.0f%% — inference features are degraded; "
                "fix upstream data. (Degrading loudly, not raising: live "
                "coaching path.)",
                trip_rate * 100,
                _SINGLE_WINDOW_N,
                _SINGLE_GATE_THRESHOLD * 100,
            )
            try:
                from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

                get_state_manager().add_notification(
                    "data-quality",
                    "WARNING",
                    f"Feature quality degraded: {trip_rate * 100:.1f}% of recent "
                    "inference extracts contained NaN/Inf (clamped).",
                )
            except Exception:
                _logger.warning("D1: quality notification could not be delivered", exc_info=True)

    return np.nan_to_num(vec, nan=0.0, posinf=1.0, neginf=-1.0)


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
        _config_override: Optional[Any] = None,
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
            _config_override: P-VEC-03 — pre-snapshotted config for batch consistency.
                     If provided, bypasses class-level _config entirely.

        Returns:
            np.ndarray of shape (METADATA_DIM,) with float32 values
        """
        # P-VEC-03: Use override if provided (batch mode), else read class-level config
        if _config_override is not None:
            cfg = _config_override
        else:
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

        # P-VEC-01 fix: Auto-resolve map_name from tick_data when caller omits it.
        # training_orchestrator calls extract_batch() without map_name, but each
        # PlayerTickState has map_name as an attribute. This ensures z_penalty and
        # map_id are computed during training, not just inference.
        if map_name is None:
            _auto_map = get_val("map_name", None)
            if _auto_map and _auto_map != "de_unknown":
                map_name = _auto_map

        vec = np.zeros(METADATA_DIM, dtype=np.float32)

        # Slot fillers — order MUST match FEATURE_NAMES (training-serving contract).
        _fill_vitals_movement(vec, get_val, cfg)  # 0-7
        pos_z = _fill_awareness_position_view(vec, get_val, cfg)  # 8-14
        _fill_z_penalty(vec, pos_z, map_name)  # 15
        _fill_round_metadata(vec, get_val, cfg, map_name)  # 16-18
        _fill_weapon_class(vec, get_val)  # 19
        _fill_context_features(vec, get_val, context, cfg)  # 20-24

        return _finalize_vector(vec)

    @classmethod
    def extract_batch(
        cls,
        tick_data_list: List[Union[Dict[str, Any], Any]],
        map_name: Optional[str] = None,
        contexts: Optional[List[Dict[str, Any]]] = None,
    ) -> np.ndarray:
        """
        Extracts features for a batch of ticks.

        R4-14-03: Snapshots config at batch start to prevent mid-batch changes
        from update_heuristics() causing inconsistent features within a batch.

        Args:
            tick_data_list: List of tick data (dicts or objects)
            map_name: Optional map name for context features
            contexts: Optional list of context dicts (one per tick). If None,
                      all ticks get context=None (features 20-24 default to 0.0).

        Returns:
            np.ndarray of shape (len(tick_data_list), METADATA_DIM)
        """
        # R4-14-03: Snapshot config once for the entire batch
        with cls._config_lock:
            batch_config = cls._config
        if batch_config is None:
            from Programma_CS2_RENAN.backend.processing.feature_engineering.base_features import (
                HeuristicConfig,
            )

            batch_config = HeuristicConfig()

        if contexts is None:
            contexts = [None] * len(tick_data_list)

        # P-VEC-03: Pass snapshotted config directly to each extract() call
        # instead of mutating class-level state. This prevents cross-batch
        # contamination when multiple threads call extract_batch() concurrently.
        # 26-VEC-01: reset this thread's per-batch clamp counter so the P3-A gate below
        # counts only the clamps produced by THIS batch — immune to concurrent
        # extract_batch() calls on other threads (which previously contaminated the
        # shared global delta).
        _batch_clamp_local.count = 0
        # D1: mark this thread as batch-context so _finalize_vector routes
        # quality accounting to P3-A instead of the single-sample window.
        _batch_clamp_local.in_batch = True

        try:
            result = np.array(
                [
                    FeatureExtractor.extract(t, map_name, ctx, _config_override=batch_config)
                    for t, ctx in zip(tick_data_list, contexts)
                ],
                dtype=np.float32,
            )
        finally:
            _batch_clamp_local.in_batch = False

        # P3-A: Quality gate — refuse to produce batches with >5% NaN/Inf contamination.
        clamped_in_batch = getattr(_batch_clamp_local, "count", 0)
        batch_size = len(tick_data_list)
        if batch_size > 0 and clamped_in_batch > 0:
            contamination_rate = clamped_in_batch / batch_size
            if contamination_rate > 0.05:
                raise DataQualityError(
                    f"P3-A: NaN/Inf contamination rate {contamination_rate:.1%} "
                    f"({clamped_in_batch}/{batch_size}) exceeds 5% threshold. "
                    f"Fix upstream data before training."
                )

        return result

    @staticmethod
    def get_feature_names() -> List[str]:
        """Returns the ordered list of feature names for debugging/logging.

        P-X-01: Delegates to the canonical FEATURE_NAMES tuple to guarantee
        a single source of truth.
        """
        return list(FEATURE_NAMES)

    @staticmethod
    def validate_feature_parity(vec: np.ndarray, label: str = "unknown") -> None:
        """P-SR-01: Assert that a feature vector matches the expected schema.

        Call this at both training and inference boundaries to catch
        feature dimension mismatches early.

        Args:
            vec: Feature vector (last dim must equal METADATA_DIM).
            label: Human-readable label for error messages (e.g. "training", "inference").

        Raises:
            ValueError: If the last dimension doesn't match METADATA_DIM.
        """
        actual = vec.shape[-1]
        if actual != METADATA_DIM:
            raise ValueError(
                f"P-SR-01: Feature parity violation [{label}]: got {actual} features, "
                f"expected METADATA_DIM={METADATA_DIM}. Schema: {FEATURE_NAMES}"
            )


# ---------------------------------------------------------------------------
# v2 extraction path (D-06, CORREZIONE_NUCLEO_NEURALE Parte III §2.2)
# ---------------------------------------------------------------------------

_WEAPON_FLOAT_TO_CLASS: Dict[float, str] = {
    0.0: "knife",
    0.05: "other",
    0.1: "grenade",
    0.2: "pistol",
    0.4: "smg",
    0.6: "rifle",
    0.8: "sniper",
    1.0: "heavy",
}


def _weapon_to_class_name(weapon_name: str) -> str:
    """Map a weapon name string to its v2 categorical class name."""
    name = weapon_name.lower()
    if name.startswith("weapon_"):
        name = name[7:]
    val = WEAPON_CLASS_MAP.get(name)
    if val is not None:
        return _WEAPON_FLOAT_TO_CLASS.get(val, "other")
    try:
        if int(name) == 0xFFFFFF:
            return "none"
        return "other"
    except (ValueError, TypeError):
        return "other"


def _get_active_config():
    """Return the active HeuristicConfig (class-level or defaults)."""
    with FeatureExtractor._config_lock:
        cfg = FeatureExtractor._config
    if cfg is None:
        from Programma_CS2_RENAN.backend.processing.feature_engineering.base_features import (
            HeuristicConfig,
        )

        cfg = HeuristicConfig()
    return cfg


def extract_v2(
    tick_data: Union[Dict[str, Any], Any],
    map_name: Optional[str] = None,
    side: Optional[str] = None,
) -> tuple:
    """Extract v2 features from a single tick (D-06, Parte III §2.2).

    Returns ``(numeric np.float32[21], categorical np.int64[3])``.
    """
    from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

    cfg = _get_active_config()

    def gv(key: str, default: Any = 0) -> Any:
        if isinstance(tick_data, dict):
            return tick_data.get(key, default)
        return getattr(tick_data, key, default)

    if map_name is None:
        _auto = gv("map_name", None)
        if _auto and _auto != "de_unknown":
            map_name = _auto

    num = _extract_v2_numeric(gv, cfg, map_name)

    cat = np.zeros(3, dtype=np.int64)
    cat[0] = CS2_V2.vocab_index("map_id", map_name if map_name else "other")
    weapon = gv("active_weapon", None)
    if weapon is None or str(weapon).lower() in ("", "nan", "none"):
        cat[1] = 0
    else:
        cat[1] = CS2_V2.vocab_index("weapon_class", _weapon_to_class_name(str(weapon)))
    cat[2] = CS2_V2.vocab_index("side", side if side in ("CT", "T") else "unknown")
    return num, cat


def _extract_v2_numeric(gv, cfg, map_name: Optional[str]) -> np.ndarray:
    """Compute the 21 numeric v2 features (v1 slots [0..15, 20..24])."""
    num = np.zeros(21, dtype=np.float32)
    num[0] = float(gv("health", 100)) / cfg.health_max
    num[1] = float(gv("armor", 0)) / cfg.armor_max
    helmet = gv("has_helmet", None)
    if helmet is None:
        helmet = gv("armor", 0) > 0
    num[2] = 1.0 if helmet else 0.0
    num[3] = 1.0 if gv("has_defuser", False) else 0.0
    num[4] = float(gv("equipment_value", 0)) / cfg.equipment_value_max
    num[5] = 1.0 if gv("is_crouching", False) else 0.0
    num[6] = 1.0 if gv("is_scoped", False) else 0.0
    _flash = gv("flash_duration", 0.0)
    try:
        _flash = float(_flash) if _flash is not None else 0.0
    except (TypeError, ValueError):
        _flash = 0.0
    num[7] = 1.0 if (_flash > 0.0 or gv("is_blinded", False)) else 0.0
    num[8] = min(float(gv("enemies_visible", 0)) / cfg.enemies_visible_max, 1.0)
    px = float(gv("pos_x", gv("x", gv("X", 0))))
    py = float(gv("pos_y", gv("y", gv("Y", 0))))
    pz = float(gv("pos_z", gv("z", gv("Z", 0))))
    num[9] = np.clip(px / cfg.pos_xy_extent, -1.0, 1.0)
    num[10] = np.clip(py / cfg.pos_xy_extent, -1.0, 1.0)
    num[11] = np.clip(pz / cfg.pos_z_extent, -1.0, 1.0)
    yaw = math.radians(float(gv("view_x", 0)))
    num[12] = math.sin(yaw)
    num[13] = math.cos(yaw)
    num[14] = float(gv("view_y", 0)) / cfg.pitch_max
    if map_name:
        from Programma_CS2_RENAN.core.spatial_data import compute_z_penalty

        num[15] = compute_z_penalty(pz, map_name)
    tv = gv("time_in_round", 0.0)
    num[16] = min(float(tv or 0.0) / cfg.time_in_round_max, 1.0)
    num[17] = 1.0 if gv("bomb_planted", False) else 0.0
    ta = gv("teammates_alive", 0)
    num[18] = min(float(ta or 0) / cfg.teammates_alive_max, 1.0)
    ea = gv("enemies_alive", 0)
    num[19] = min(float(ea or 0) / cfg.enemies_alive_max, 1.0)
    ec = gv("team_economy", 0)
    num[20] = min(float(ec or 0) / cfg.team_economy_max, 1.0)
    return np.nan_to_num(num, nan=0.0, posinf=1.0, neginf=-1.0)


def _fill_z_penalty_frame(num: np.ndarray, pos_z: np.ndarray, map_name: Optional[str]) -> None:
    """Vectorised z_penalty (slot 15) — identical to ``compute_z_penalty``."""
    if not map_name:
        return
    from Programma_CS2_RENAN.core.spatial_data import get_map_metadata

    meta = get_map_metadata(map_name)
    if not meta or meta.z_cutoff is None:
        return
    num[:, 15] = np.minimum(np.abs(pos_z - meta.z_cutoff) / 500.0, 1.0)


def _fill_weapon_class_frame(cat: np.ndarray, df: "Any", n: int) -> None:  # noqa: ANN401
    """Vectorised weapon_class categorical (slot 1) for a frame."""
    from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

    if "active_weapon" not in df.columns:
        return
    weapons = df["active_weapon"].fillna("").astype(str).values
    unique_vals, inverse = np.unique(weapons, return_inverse=True)
    idx_map = np.empty(len(unique_vals), dtype=np.int64)
    for i, w in enumerate(unique_vals):
        w_clean = w.lower().strip()
        if not w_clean or w_clean in ("nan", "none"):
            idx_map[i] = 0
        else:
            idx_map[i] = CS2_V2.vocab_index("weapon_class", _weapon_to_class_name(w_clean))
    cat[:, 1] = idx_map[inverse]


def extract_frame_v2(
    df: "Any",  # pandas.DataFrame  # noqa: ANN401
    map_name: Optional[str] = None,
    side: Optional[str] = None,
) -> tuple:
    """Vectorised v2 extraction from a DataFrame (D-06, export hot path).

    Returns ``(numeric np.float32[N,21], categorical np.int64[N,3])``.
    All operations are numpy-vectorised — no per-row Python.
    """
    import pandas as pd

    from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

    cfg = _get_active_config()
    n = len(df)
    num = np.zeros((n, 21), dtype=np.float32)

    def _col(name: str, default: float = 0.0) -> np.ndarray:
        if name not in df.columns:
            return np.full(n, default)
        s = df[name]
        if s.dtype == object:
            s = pd.to_numeric(s, errors="coerce")
        return s.values.astype(np.float64)

    def _bcol(name: str) -> np.ndarray:
        if name not in df.columns:
            return np.zeros(n, dtype=np.float32)
        arr = df[name].values
        nan_mask = pd.isna(df[name]).values
        out = np.zeros(n, dtype=np.float32)
        out[~nan_mask] = np.asarray(arr[~nan_mask], dtype=bool).astype(np.float32)
        return out

    armor = _col("armor")
    num[:, 0] = _col("health", 100.0) / cfg.health_max
    num[:, 1] = armor / cfg.armor_max
    if "has_helmet" in df.columns:
        missing = pd.isna(df["has_helmet"]).values
        harr = df["has_helmet"].values
        hbool = np.zeros(n, dtype=bool)
        hbool[~missing] = np.asarray(harr[~missing], dtype=bool)
        num[:, 2] = np.where(missing, armor > 0, hbool).astype(np.float32)
    else:
        num[:, 2] = (armor > 0).astype(np.float32)
    num[:, 3] = _bcol("has_defuser")
    num[:, 4] = _col("equipment_value") / cfg.equipment_value_max
    num[:, 5] = _bcol("is_crouching")
    num[:, 6] = _bcol("is_scoped")
    num[:, 7] = np.where((_col("flash_duration") > 0) | (_bcol("is_blinded") > 0), 1.0, 0.0).astype(
        np.float32
    )
    num[:, 8] = np.minimum(_col("enemies_visible") / cfg.enemies_visible_max, 1.0)
    px, py, pz = _col("pos_x"), _col("pos_y"), _col("pos_z")
    num[:, 9] = np.clip(px / cfg.pos_xy_extent, -1.0, 1.0)
    num[:, 10] = np.clip(py / cfg.pos_xy_extent, -1.0, 1.0)
    num[:, 11] = np.clip(pz / cfg.pos_z_extent, -1.0, 1.0)
    yaw_rad = np.radians(_col("view_x"))
    num[:, 12] = np.sin(yaw_rad)
    num[:, 13] = np.cos(yaw_rad)
    num[:, 14] = _col("view_y") / cfg.pitch_max
    _fill_z_penalty_frame(num, pz, map_name)
    num[:, 16] = np.minimum(_col("time_in_round") / cfg.time_in_round_max, 1.0)
    num[:, 17] = _bcol("bomb_planted")
    num[:, 18] = np.minimum(_col("teammates_alive") / cfg.teammates_alive_max, 1.0)
    num[:, 19] = np.minimum(_col("enemies_alive") / cfg.enemies_alive_max, 1.0)
    num[:, 20] = np.minimum(_col("team_economy") / cfg.team_economy_max, 1.0)
    np.nan_to_num(num, copy=False, nan=0.0, posinf=1.0, neginf=-1.0)

    cat = np.zeros((n, 3), dtype=np.int64)
    cat[:, 0] = CS2_V2.vocab_index("map_id", map_name if map_name else "other")
    _fill_weapon_class_frame(cat, df, n)
    cat[:, 2] = CS2_V2.vocab_index("side", side if side in ("CT", "T") else "unknown")
    return num, cat


def remap_v1_to_v2(
    x25: np.ndarray,
    map_name: Optional[str],
    active_weapon: Optional[str],
    side: Optional[str],
) -> tuple:
    """Remap a v1 float32[25] vector to v2 representation (D-06).

    Numeric: v1 slots [0..15, 20..24] → float32[21].
    Categorical: computed from ``map_name``, ``active_weapon``, ``side``.
    """
    from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

    num = np.empty(21, dtype=np.float32)
    num[:16] = x25[:16]
    num[16:] = x25[20:]

    cat = np.zeros(3, dtype=np.int64)
    cat[0] = CS2_V2.vocab_index("map_id", map_name if map_name else "other")
    if active_weapon is None or str(active_weapon).lower() in ("", "nan", "none"):
        cat[1] = 0
    else:
        cat[1] = CS2_V2.vocab_index("weapon_class", _weapon_to_class_name(str(active_weapon)))
    cat[2] = CS2_V2.vocab_index("side", side if side in ("CT", "T") else "unknown")
    return num, cat
