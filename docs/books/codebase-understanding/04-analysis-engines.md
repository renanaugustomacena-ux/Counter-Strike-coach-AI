# Chapter 4 -- Analysis Engines, Progress Tracking, and Reporting

This chapter provides an exhaustive reference for every class, function, constant, dataclass, and design decision found in the analysis, progress, and reporting subsystems of the Macena CS2 Analyzer.

---

## Part A: Analysis Engines (`Programma_CS2_RENAN/backend/analysis/`)

The analysis package contains twelve modules that provide advanced coaching analytics. They are organized into two logical generations: the original Phase 1B modules (win probability, role classification, utility/economy) and the Phase 6 "Game Theory" modules (belief model, blind spots, deception index, engagement range, entropy analysis, game tree, momentum, movement quality).

---

### A.1 Package Initialization (`__init__.py`)

The package `__init__.py` re-exports every public symbol from all twelve submodules. It serves as the canonical public API surface for the analysis subsystem.

#### Imports and `__all__`

The following symbols are exported and available via `from Programma_CS2_RENAN.backend.analysis import ...`:

**Win Probability group:**
- `WinProbabilityPredictor` -- main prediction engine class
- `WinProbabilityNN` -- PyTorch neural network model
- `GameState` -- dataclass representing round state
- `get_win_predictor` -- factory function

**Role Classifier group:**
- `RoleClassifier` -- weighted scoring + neural consensus classifier
- `PlayerRole` -- canonical enum (re-exported from `core.app_types`)
- `RoleProfile` -- dataclass with role metadata
- `ROLE_PROFILES` -- dict mapping `PlayerRole` to `RoleProfile`
- `get_role_classifier` -- factory function

**Utility and Economy group:**
- `UtilityAnalyzer` -- grenade/utility effectiveness scorer
- `EconomyOptimizer` -- buy decision recommender
- `UtilityType` -- enum (SMOKE, FLASH, MOLOTOV, HE)
- `UtilityReport` -- dataclass for full utility analysis
- `EconomyDecision` -- dataclass for buy recommendations
- `get_utility_analyzer` -- factory function
- `get_economy_optimizer` -- factory function

**Phase 6 Analysis Engines -- classes:**
- `DeathProbabilityEstimator` -- Bayesian death probability
- `DeceptionAnalyzer` -- tactical deception index
- `MomentumTracker` -- psychological momentum multiplier
- `EntropyAnalyzer` -- Shannon entropy of position distributions
- `ExpectiminimaxSearch` -- game tree search engine
- `BlindSpotDetector` -- recurring strategic weakness detector
- `EngagementRangeAnalyzer` -- kill distance profiling
- `MovementQualityAnalyzer` -- tick-level positioning mistake detection

**Phase 6 Analysis Engines -- factory functions:**
- `get_death_estimator`
- `get_deception_analyzer`
- `get_momentum_tracker`
- `get_entropy_analyzer`
- `get_game_tree_search`
- `get_blind_spot_detector`
- `get_engagement_range_analyzer`
- `get_movement_quality_analyzer`

---

### A.2 Belief Model (`belief_model.py`)

**Purpose:** Implements a Bayesian belief model that estimates P(death) for a player given the current game state, factoring in information asymmetry. Governance: Rule 1 S7.1 (Probabilistic reasoning over deterministic heuristics).

#### Module-Level Constants

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `_DEFAULT_PRIORS` | `Dict[str, float]` | `{"full": 0.35, "damaged": 0.55, "critical": 0.80}` | Default death-rate priors by HP bracket, sourced from CS2 round statistics |
| `_WEAPON_LETHALITY` | `Dict[str, float]` | rifle=1.0, awp=1.4, smg=0.75, pistol=0.6, shotgun=0.85, knife=0.3, unknown=1.0 | Relative weapon lethality multipliers against a rifle baseline |
| `MAX_CALIBRATION_SAMPLES` | `int` | `5_000` | Maximum rows fetched from RoundStats for belief calibration; prevents OOM (governance: F4-01) |

#### Dataclass: `BeliefState`

Represents the information-asymmetry state for a single player.

| Field | Type | Default | Description |
|---|---|---|---|
| `visible_enemies` | `int` | `0` | Number of enemies currently visible |
| `inferred_enemies` | `int` | `0` | Number of enemies inferred from information |
| `information_age` | `float` | `0.0` | Age of the most recent enemy position information |
| `positional_exposure` | `float` | `0.0` | How exposed the player's position is (0-1) |
| `THREAT_DECAY_LAMBDA` | `float` | `0.1` | Decay rate for inferred enemy credibility (P8-01). Hand-tuned for CS2 pacing at ~7-tick half-life at 64 Hz. Bounded [0.01, 1.0]. Can be overwritten by `AdaptiveBeliefCalibrator.calibrate_threat_decay()`. |

**Method: `threat_level() -> float`**
Computes combined threat from visible + inferred enemies, with inferred enemies decayed exponentially by `information_age`:
```
decay = exp(-THREAT_DECAY_LAMBDA * information_age)
threat = (visible_enemies + inferred_enemies * decay * 0.5) / 5.0
```
Division by 5.0 normalizes to [0, 1] given a maximum of 5 enemies.

#### Dataclass: `DeathProbabilityEstimator`

Bayesian estimator for P(death | belief, HP, armor, weapon_class). Uses calibrated priors from historical round data when available, falling back to domain-default priors.

| Field | Type | Default | Description |
|---|---|---|---|
| `priors` | `Dict[str, float]` | copy of `_DEFAULT_PRIORS` | HP bracket death-rate priors |
| `_calibrated` | `bool` | `False` | Whether priors have been calibrated from data |

**Class constant: `MIN_CALIBRATION_SAMPLES: int = 30`** (AC-05-01) -- minimum sample count for statistically meaningful calibration.

**Method: `estimate(belief, player_hp, armor, weapon_class) -> float`**

Estimates P(death) via a Bayesian-inspired logistic combination:

1. **Prior selection:** Maps `player_hp` to an HP bracket ("full" >= 80, "damaged" >= 40, else "critical") and looks up the prior death rate.
2. **Likelihood adjustments:**
   - `threat` from `belief.threat_level()`
   - `armor_factor`: 0.75 if armor, else 1.0
   - `weapon_mult`: from `_WEAPON_LETHALITY` dict
   - `exposure_factor`: `0.5 + 0.5 * belief.positional_exposure`
3. **Log-odds combination (P8-02):**
   ```
   log_odds = log(prior / (1 - prior))
   log_odds += threat * 2.0          # threat sensitivity
   log_odds += (weapon_mult - 1.0) * 1.5   # weapon lethality
   log_odds += (armor_factor - 1.0) * -1.0  # armor reduction
   log_odds += (exposure_factor - 0.5) * 1.0 # exposure risk
   ```
4. **Posterior:** sigmoid of log_odds, clamped to [0.0, 1.0].

The weights (2.0, 1.5, -1.0, 1.0) are hand-tuned. Future work: grid search or logistic regression on actual death outcomes.

**Method: `is_high_risk(probability, threshold=0.6) -> bool`**
Returns `True` if `probability > threshold`.

**Method: `estimate_with_uncertainty(belief, player_hp, armor, weapon_class, n_samples=20, dropout_rate=0.1) -> Dict[str, float]`**

MC Dropout uncertainty estimation (Gal & Ghahramani 2016). Runs N stochastic forward passes with random perturbation of belief state fields (mimicking dropout on Bayesian inputs). Uses a seeded RNG (`seed=42`) for determinism. Perturbations:
- `information_age`: scaled by `1.0 + Normal(0, 0.05)`
- `positional_exposure`: shifted by `Normal(0, dropout_rate)`, clipped to [0, 1]
- `player_hp`: shifted by `Normal(0, 3)`, floored at 1

Returns: `{"mean", "std", "ci_low" (5th percentile), "ci_high" (95th percentile)}`.

**Method: `calibrate(historical_rounds: pd.DataFrame) -> None`**

Learns priors from labeled historical round data. Expected columns: `health`, `died` (bool), `round_id`. Process:
1. Rejects empty DataFrames (warning).
2. Rejects DataFrames with fewer than `MIN_CALIBRATION_SAMPLES` rows (AC-05-01 warning).
3. Validates required columns `{"health", "died"}`.
4. Groups by HP bracket, updates priors for brackets with >= 10 samples.
5. Sets `_calibrated = True`.

**Static method: `_hp_to_bracket(hp: int) -> str`**
Returns "full" (>= 80), "damaged" (>= 40), or "critical" (< 40).

#### Singleton: `get_death_estimator() -> DeathProbabilityEstimator`

Thread-safe lazy singleton using double-checked locking (P3-10, AR-5). Protected by `_death_estimator_lock` (threading.Lock). On initialization failure, logs at exception level (A-02) and re-raises.

#### Class: `AdaptiveBeliefCalibrator`

Empirically calibrates belief model parameters from historical match data (Fusion Plan Proposal 6). Augments the existing `DeathProbabilityEstimator.calibrate()` with additional calibration axes.

**Class constants:**
| Constant | Value | Purpose |
|---|---|---|
| `MIN_SAMPLES` | `100` | Minimum required samples for any calibration |
| `_PRIOR_BOUNDS` | `(0.05, 0.95)` | Safety bounds for HP bracket priors |
| `_LETHALITY_BOUNDS` | `(0.1, 3.0)` | Safety bounds for weapon lethality multipliers |
| `_DECAY_BOUNDS` | `(0.01, 1.0)` | Safety bounds for threat decay lambda |

**Constructor: `__init__(estimator=None)`**
Accepts an optional existing `DeathProbabilityEstimator`; creates a new one if not provided.

**Method: `calibrate_hp_brackets(death_events: pd.DataFrame) -> Dict[str, float]`**
Delegates to `estimator.calibrate()` then applies `_PRIOR_BOUNDS` clamping. Returns calibrated priors dict, or empty dict if fewer than `MIN_SAMPLES` rows (AC-05-01 warning).

**Method: `calibrate_weapon_lethality(death_events: pd.DataFrame) -> Dict[str, float]`**
Calibrates weapon lethality multipliers from kill data. Process:
1. Requires `weapon_class` column and >= `MIN_SAMPLES` rows.
2. Filters to death events only (`died == True`).
3. Counts kills per weapon class.
4. Normalizes to rifle baseline: `raw_mult = count / rifle_count`.
5. Applies `_LETHALITY_BOUNDS` clamping.
6. Requires >= 10 per-class samples.

**Method: `calibrate_threat_decay(engagement_windows: pd.DataFrame) -> Optional[float]`**
Fits the threat decay rate (lambda) from engagement data via least-squares. Process:
1. Requires `information_age` column and >= `MIN_SAMPLES` rows.
2. Bins `information_age` into 10 brackets.
3. Filters bins with >= 5 samples.
4. Requires >= 3 valid bins.
5. Log-linearizes: `ln(death_rate) = ln(P0) - lambda * age`.
6. Fits via `np.polyfit` (degree 1), extracts `-coeffs[0]` as lambda.
7. Guards against NaN/Inf (A-01).
8. Applies `_DECAY_BOUNDS` clamping.

**Method: `auto_calibrate(death_events: pd.DataFrame) -> Dict[str, Any]`**
Full auto-calibration pipeline. Calibrates each axis independently based on available columns:
- `health` + `died` -> HP priors
- `weapon_class` -> weapon lethality
- `information_age` -> threat decay

Post-calibration side effects (WR-65):
- Updates the global `_WEAPON_LETHALITY` dict in-place.
- Overwrites `BeliefState.THREAT_DECAY_LAMBDA` class attribute.
- Calls `_save_snapshot()` to persist to DB.

Returns a summary dict with keys `hp_priors`, `weapon_lethality`, `threat_decay`.

**Method: `_save_snapshot(summary, sample_count=0) -> None`**
Persists calibration parameters to the `CalibrationSnapshot` DB model via `get_db_manager()`. Each non-empty calibration type is stored as a separate row with JSON-serialized parameters and the sample count. Catches `OSError` and `SQLAlchemyError` gracefully.

#### Standalone Function: `extract_death_events_from_db() -> pd.DataFrame`

Extracts round-level death data for belief model calibration from the `RoundStats` table. Produces a DataFrame with `health` and `died` columns. HP bracket estimation uses equipment value as a proxy:
- Equipment > $4000 -> health=100 ("full")
- Equipment > $2000 -> health=60 ("damaged")
- Equipment <= $2000 -> health=30 ("critical")

Death detection: `rs.deaths > 0`. Limited to `MAX_CALIBRATION_SAMPLES` rows. Returns empty DataFrame on any error.

---

### A.3 Blind Spot Detection (`blind_spots.py`)

**Purpose:** Identifies recurring situations where a player consistently makes suboptimal decisions by comparing actual actions against game tree optimal actions. Governance: Rule 1 S8.2 (Pattern-based weakness identification), Rule 3 S3.1 (Actionable coaching output).

#### Dataclass: `BlindSpot`

Represents a recurring strategic weakness.

| Field | Type | Default | Description |
|---|---|---|---|
| `situation_type` | `str` | required | e.g., "2v1 retake", "eco rush", "post-plant" |
| `optimal_action` | `str` | required | Action recommended by game tree |
| `actual_action` | `str` | required | Action the player actually took |
| `frequency` | `int` | `0` | Number of occurrences |
| `impact_rating` | `float` | `0.0` | Average win-prob delta (optimal - actual) |

**Property: `priority -> float`**
Returns `frequency * impact_rating`. Used for coaching ranking -- higher priority means more frequent and more impactful deviations from optimal play.

#### Class: `BlindSpotDetector`

**Constructor: `__init__()`**
Creates an internal `ExpectiminimaxSearch` instance via lazy import (avoids circular imports).

**Method: `detect(player_history, game_tree=None) -> List[BlindSpot]`**

Core detection algorithm. Accepts a list of round dicts, each containing:
- `game_state`: Dict matching GameState fields
- `action_taken`: str
- `round_won`: bool
- Optional context fields (alive_players, enemy_alive, etc.)

Process:
1. For each round, builds a game tree (depth=2) and finds the optimal action.
2. If the player's actual action differs from optimal, classifies the situation and computes the impact (optimal_value - actual_value).
3. Wraps game tree analysis in try-except (B-01) -- malformed states skip the round rather than crashing.
4. Aggregates mismatches by situation type, then by optimal|actual action pattern.
5. Creates `BlindSpot` instances from the most common mismatch patterns with their frequencies and average impacts.
6. Sorts by priority (descending).

**Method: `_classify_situation(state: Dict) -> str`**

Classifies a game state into human-readable situation types based on:
- Bomb planted + player advantage -> "post-plant advantage/disadvantage/even"
- 1 alive vs 2+ enemies -> "1v{N} clutch"
- 2+ alive vs 1 enemy -> "{N}v1 retake"
- Player count disadvantage/advantage
- Economy differential (< -$3000 -> "eco round", > $3000 -> "economic advantage")
- Time remaining (< 30s -> "late round")
- Default: "standard"

**Method: `_evaluate_action(search, state, action) -> float`**
Delegates to `search.evaluate_single_action(state, action)` (F4-03: uses public API).

**Method: `generate_training_plan(blind_spots, top_n=3) -> str`**

Generates a natural-language coaching plan targeting the most impactful blind spots. For each of the top N spots, provides:
- Situation type and frequency
- What the player tends to do vs. what they should do
- Training advice mapped from a dict of action-specific recommendations (push, hold, rotate, use_utility).

Returns a multi-line Markdown-formatted string. Returns an "all clear" message if no blind spots detected.

#### Factory Function: `get_blind_spot_detector() -> BlindSpotDetector`
Creates a new instance on each call (not a singleton).

---

### A.4 Deception Index (`deception_index.py`)

**Purpose:** Quantifies tactical deception by measuring divergence between observable actions and true intent. Governance: Rule 1 S7.2 (Game-theoretic analysis), Rule 2 S8.1 (Novel metrics require validation).

#### Module-Level Constants

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `FAKE_EXECUTE_WINDOW` | `float` | `5.0` | Time window (seconds) to detect site-take fakes |
| `UTILITY_FOLLOWUP_WINDOW` | `float` | `3.0` | Time (seconds) after utility for expected engagement |
| `FLASH_BLIND_WINDOW_TICKS` | `int` | `128` | ~2 seconds at 64 tick; window after flash to check for blind events |
| `W_FAKE_FLASH` | `float` | `0.25` | Composite weight for flash bait detection (P8-04) |
| `W_ROTATION_FEINT` | `float` | `0.40` | Composite weight for rotation feints (highest: position > utility in CS2 info-war) |
| `W_SOUND_DECEPTION` | `float` | `0.35` | Composite weight for sound deception (fake-step/gun-switch noise) |

Weight rationale (P8-04): Sum = 1.0. Rotation feints get highest weight because positional deception is more impactful than utility baits in CS2. Sound deception follows because directional audio exploitation is powerful. Flash baits get lowest weight because they are common at all skill levels. Validation: compare distribution of indices for pro vs amateur matches.

#### Dataclass: `DeceptionMetrics`

| Field | Type | Default | Description |
|---|---|---|---|
| `fake_flash_rate` | `float` | `0.0` | Rate of flash throws that don't blind enemies |
| `rotation_feint_rate` | `float` | `0.0` | Rate of significant direction reversals |
| `sound_deception_score` | `float` | `0.0` | Inverse of crouch ratio (more noise = more deceptive) |
| `composite_index` | `float` | `0.0` | Weighted combination, capped at 1.0 |

#### Class: `DeceptionAnalyzer`

**Constructor: `__init__(fake_execute_window=5.0, utility_followup_window=3.0)`**

**Method: `analyze_round(round_data: pd.DataFrame) -> DeceptionMetrics`**

Analyzes a single round for deception patterns. Expected columns: `tick`, `player_name`, `pos_x`, `pos_y`, `event_type`, `event_detail`, `team`, `round_number`.

Computes three sub-scores, then combines with weighted sum:
```
composite = W_FAKE_FLASH * fake_flash + W_ROTATION_FEINT * rotation_feint + W_SOUND_DECEPTION * sound_deception
```
Capped at 1.0.

**Method: `_detect_flash_baits(df: pd.DataFrame) -> float`**

Detects flash throws that don't blind enemies. Uses vectorized computation:
1. Extracts all `flashbang_throw` events and `player_blind` events.
2. Sorts blind ticks and uses `np.searchsorted` for O(F*log B) matching.
3. For each flash, checks if any blind event occurs within `FLASH_BLIND_WINDOW_TICKS`.
4. Uses safe indexing (D-01): builds `in_bounds` mask before indexing `blind_ticks` to avoid silent out-of-bounds comparison.
5. Returns `1.0 - (effective_flashes / total_flashes)`.

**Method: `_detect_rotation_feints(df: pd.DataFrame) -> float`**

Detects fake executes via movement direction changes:
1. Requires `pos_x`, `pos_y` columns and >= 20 rows.
2. Samples positions at regular intervals (step = n // 20).
3. Computes minimum displacement threshold as `map_extent * 0.001` (AC-04-01: adaptive to map coordinate system).
4. For each triplet of consecutive sampled positions, computes the angle between direction vectors.
5. Counts "significant" direction changes (angle > 108 degrees = pi * 0.6).
6. Returns `significant_changes / direction_changes`, capped at 1.0.

**Method: `_detect_sound_deception(df: pd.DataFrame) -> float`**

Detects deliberate noise generation vs. silent movement. Uses `is_crouching` column:
- `crouch_ratio = crouching_ticks / total_ticks`
- Score = `1.0 - crouch_ratio * 2.0`, clamped to [0, 1].
- High crouch ratio -> stealthy (low score). Low crouch ratio -> noisy (high score = potentially deceptive).

**Method: `compare_to_baseline(metrics, pro_baseline) -> str`**

Generates natural-language comparison for coaching output. Compares composite index delta against +/- 0.15 threshold. Additionally checks if rotation feint rate is below pro baseline - 0.1 and suggests practice.

#### Factory Function: `get_deception_analyzer() -> DeceptionAnalyzer`
Creates a new instance on each call.

---

### A.5 Engagement Range Analytics (`engagement_range.py`)

**Purpose:** Kill distance analysis and named position registry. Fusion Plan Proposal 7: Spatial Intelligence Expansion. This module is ADDITIVE -- it does not modify `spatial_data.py`.

#### Module-Level Constants

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `RANGE_CLOSE` | `int` | `500` | Upper bound (world units) for close-range classification |
| `RANGE_MEDIUM` | `int` | `1500` | Upper bound for medium-range |
| `RANGE_LONG` | `int` | `3000` | Upper bound for long-range; above = "extreme" |

#### Re-exports from `core.map_callouts`

- `NamedPosition` -- dataclass for map callout positions
- `NamedPositionRegistry` -- registry class for named positions

#### Dataclass: `EngagementProfile`

Distribution of kill distances by range category.

| Field | Type | Default | Description |
|---|---|---|---|
| `close_pct` | `float` | `0.0` | Fraction of kills < 500 units |
| `medium_pct` | `float` | `0.0` | Fraction of kills 500-1500 units |
| `long_pct` | `float` | `0.0` | Fraction of kills 1500-3000 units |
| `extreme_pct` | `float` | `0.0` | Fraction of kills > 3000 units |
| `avg_distance` | `float` | `0.0` | Mean kill distance |
| `total_kills` | `int` | `0` | Total number of kills analyzed |

#### Module-Level Dict: `_ROLE_RANGE_BASELINES`

Expected engagement profiles by role, representing pro baselines:

| Role | close | medium | long | extreme |
|---|---|---|---|---|
| awper | 0.10 | 0.30 | 0.45 | 0.15 |
| entry_fragger | 0.40 | 0.40 | 0.15 | 0.05 |
| support | 0.25 | 0.45 | 0.25 | 0.05 |
| lurker | 0.35 | 0.35 | 0.20 | 0.10 |
| igl | 0.25 | 0.40 | 0.25 | 0.10 |
| flex | 0.25 | 0.40 | 0.25 | 0.10 |

#### Class: `EngagementRangeAnalyzer`

**Constructor: `__init__()`**
Creates a `NamedPositionRegistry` instance for callout annotation.

**Static method: `compute_kill_distance(killer_x, killer_y, killer_z, victim_x, victim_y, victim_z) -> float`**
3D Euclidean distance between killer and victim in world units.

**Static method: `classify_range(distance: float) -> str`**
Returns "close" (< 500), "medium" (< 1500), "long" (< 3000), or "extreme" (>= 3000).

**Method: `compute_profile(kill_distances: List[float]) -> EngagementProfile`**
Builds an `EngagementProfile` from a list of kill distances. Counts kills in each range bracket, computes percentages, and calculates average distance.

**Method: `compare_to_role(profile, role) -> List[str]`**
Compares a player's engagement profile to role-specific baseline. Requires >= 5 kills. Uses a 15% deviation threshold to generate observations about close-range and long-range engagement patterns relative to the expected role profile.

**Method: `annotate_kill_position(map_name, x, y, z=0.0) -> str`**
Annotates a kill position with the nearest named callout from the position registry. Returns the position name or "Unknown Position".

**Method: `analyze_match_engagements(kill_events, map_name, player_role="flex") -> Dict`**

Full engagement analysis for a player's kills in a match:
1. Validates `map_name` presence (O-03 warning if missing).
2. Validates each kill event has required coordinate keys (`killer_x`, `killer_y`, `victim_x`, `victim_y`).
3. Computes distances and annotates positions for each kill.
4. Builds profile and generates role-comparison observations.
5. Returns dict with `profile`, `observations`, and `annotated_kills`.

#### Factory Function: `get_engagement_range_analyzer() -> EngagementRangeAnalyzer`
Creates a new instance on each call.

---

### A.6 Entropy Analysis (`entropy_analysis.py`)

**Purpose:** Measures the information-theoretic impact of utility usage by computing Shannon entropy reduction in enemy position distributions. Governance: Rule 1 S7.4, Rule 2 S8.2.

#### Module-Level Constants

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `_MAX_DELTA` | `Dict[str, float]` | smoke=2.5, flash=1.8, molotov=2.0, he_grenade=1.5 | Maximum theoretical entropy reduction per utility type (bits). P8-07. |

Rationale (P8-07): Smoke gets highest (2.5 bits) because it blocks line-of-sight for ~18s, eliminating multiple position hypotheses. Molotov (2.0) for ~7s area denial. Flash (1.8) for brief ~3s blind window. HE (1.5) for momentary position reveal. Validation: compute 95th percentile of observed deltas from 100+ parsed demos.

#### Module-Level Dict: `_MAP_GRID_RESOLUTION`

Per-map grid resolution for entropy computation:

| Map | Resolution |
|---|---|
| de_dust2 | 32 |
| de_mirage | 32 |
| de_inferno | 36 |
| de_nuke | 40 |
| de_overpass | 36 |
| de_anubis | 32 |
| de_vertigo | 40 |
| de_ancient | 36 |
| de_train | 36 |

#### Dataclass: `UtilityImpact`

Information-theoretic impact of a single utility throw.

| Field | Type | Description |
|---|---|---|
| `pre_entropy` | `float` | Shannon entropy before utility |
| `post_entropy` | `float` | Shannon entropy after utility |
| `entropy_delta` | `float` | `pre - post` (positive = information gained) |
| `utility_type` | `str` | "smoke", "flash", "molotov", or "he_grenade" |
| `effectiveness_rating` | `float` | `delta / max_delta`, clamped to [0, 1] |

#### Class: `EntropyAnalyzer`

**Constructor: `__init__(grid_resolution=32, map_name=None)`**
If `map_name` is provided and `grid_resolution` is the default 32, looks up the map-specific resolution from `_MAP_GRID_RESOLUTION`. Pre-allocates a grid buffer (AC-03-01) and a threading lock (E-01) to protect it from concurrent access.

**Method: `compute_position_entropy(player_positions, grid_resolution=None) -> float`**

Computes Shannon entropy H of a set of (x, y) player positions:
1. Discretizes positions onto a 2D grid.
2. Computes coordinate ranges with +/- 1 padding.
3. Maps each position to a grid cell.
4. Normalizes grid to probability distribution.
5. Computes `H = -sum(p * log2(p))` for non-zero cells.

Thread safety (E-01): When using the shared grid buffer (default resolution), acquires `_buffer_lock`. For non-default resolutions, allocates a fresh array (no lock needed). The buffer is zero-filled before each use rather than reallocated.

Numerical safety (AC-06-01): Clips probabilities to `np.finfo(float32).tiny` minimum before `log2` to avoid log2(0).

Edge case (E-02-alt): Returns 0.0 if all probabilities are zero/sub-normal.

**Method: `analyze_utility_throw(pre_positions, post_positions, utility_type) -> UtilityImpact`**

Computes entropy before and after a utility throw. Effectiveness is the ratio of actual entropy reduction to the theoretical maximum for that utility type from `_MAX_DELTA`.

**Method: `rank_utility_usage(round_utilities: List[UtilityImpact]) -> List[UtilityImpact]`**
Sorts utility throws by effectiveness rating (descending). Useful for coaching: "Your best smoke reduced uncertainty by X bits."

#### Factory Function: `get_entropy_analyzer() -> EntropyAnalyzer`
Creates a new instance with default parameters.

---

### A.7 Game Tree Search (`game_tree.py`)

**Purpose:** Implements expectiminimax game tree search for CS2 round-level strategy. Governance: Rule 1 S8.1 (Game-theoretic foundations), Rule 2 S9.1 (Bounded computation).

#### Module-Level Constants

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `_MAX_ACTIONS` | `list` | `["push", "hold", "rotate", "use_utility"]` | Available tactical actions for max (our team) nodes |
| `_MIN_ACTIONS` | `list` | `["push", "hold", "rotate", "use_utility"]` | Available tactical actions for min (opponent) nodes |
| `_DEFAULT_OPPONENT_PROBS` | `Dict[str, float]` | push=0.30, hold=0.40, rotate=0.20, use_utility=0.10 | Cold-start default opponent action probabilities |
| `DEFAULT_NODE_BUDGET` | `int` | `1000` | Maximum nodes before tree expansion stops |
| `_TT_MAX_SIZE` | `int` | `10_000` | Maximum entries in the transposition table |

#### Free Function: `_state_hash(state: Dict) -> int`

Creates a deterministic hash from a game state dict for transposition table memoization. Extracts only the numeric fields that affect evaluation:
- `alive_players`, `enemy_alive`, `team_economy`, `enemy_economy`
- `map_control_pct` (rounded to 2 decimals), `time_remaining`
- `utility_remaining`, `is_ct`

Uses `hashlib.md5` with `usedforsecurity=False` (silences bandit B324). Converts hex digest to int.

#### Class: `OpponentModel`

Adaptive opponent modeling for game tree search. Learns opponent action distributions from context.

**Class constants:**
- `_ECONOMY_PRIORS`: Economy-tier action distributions:
  - eco: push=0.50, hold=0.15, rotate=0.10, use_utility=0.25
  - force: push=0.40, hold=0.25, rotate=0.15, use_utility=0.20
  - full_buy: push=0.25, hold=0.35, rotate=0.25, use_utility=0.15
- `_SIDE_ADJUSTMENTS`: T-side opponents push more (+0.05 push, -0.05 hold), CT-side hold more.

**Instance state:**
- `_learned_profiles`: `Dict[str, Dict[str, float]]` -- keyed by `"map_name:economy_tier"`
- `_learned_counts`: `Dict[str, int]` -- sample counts per profile key

**Method: `get_opponent_probs(game_state, map_name=None) -> Dict[str, float]`**

Builds context-adapted opponent probabilities through a layered process:
1. **Economy-based priors:** Classifies enemy economy into eco/force/full_buy.
2. **Side adjustments:** Applies T/CT modifiers to the opposing side.
3. **Player advantage:** If enemy has fewer players, increases hold + rotate, decreases push. If enemy has more players, increases push.
4. **Time pressure:** Under 30s remaining, boosts push (+0.15), reduces hold (-0.10), boosts utility (+0.05).
5. **Learned profile blending:** If a profile exists for `"map_name:economy_tier"` with >= 10 samples, blends with `blend_weight = min(count/100, 0.7)` via linear interpolation.
6. **Normalization:** Ensures all probabilities >= 0.01 and sum to 1.0.

**Method: `learn_from_match(match_events, map_name) -> None`**

Updates opponent model from observed match events:
1. Groups events by economy tier.
2. Infers action from event type (`first_kill`/`entry_frag` -> push, `flash_thrown`/`smoke_thrown`/`molotov_thrown` -> use_utility, `rotation_detected` -> rotate, else hold).
3. Requires >= 5 events per economy tier.
4. EMA-blends new probabilities with existing learned profiles: `alpha = min(total / (total + old_count), 0.5)`.

**Method: `_classify_economy(state) -> str`**
Returns "eco" (< $2000), "force" (< $4000), or "full_buy" (>= $4000) based on `enemy_economy`.

**Method: `_infer_action_from_event(event) -> str`**
Maps event types to tactical actions.

#### Dataclass: `GameNode`

A node in the expectiminimax game tree.

| Field | Type | Default | Description |
|---|---|---|---|
| `node_type` | `str` | required | "max" (our team), "min" (opponent), or "chance" (stochastic) |
| `state` | `Dict` | required | Game state snapshot |
| `children` | `List[GameNode]` | `[]` | Child nodes |
| `value` | `Optional[float]` | `None` | Evaluated utility value |
| `action` | `Optional[str]` | `None` | Action that led to this node |

**Property: `is_leaf -> bool`**
True when `children` is empty.

#### Class: `ExpectiminimaxSearch`

The core game tree search engine.

**Constructor: `__init__(node_budget=1000, opponent_probs=None, opponent_model=None, map_name=None)`**
- `_static_opponent_probs`: fallback static probs (default or provided)
- `_opponent_model`: optional adaptive `OpponentModel`
- `_map_name`: map context for opponent model
- `_nodes_created`: counter for budget enforcement
- `_predictor`: lazy-loaded `WinProbabilityPredictor`
- `_tt`: transposition table `Dict[int, Tuple[float, int]]` mapping state_hash to (value, depth)
- `_tt_hits`: counter for cache hit statistics

**Property: `opponent_probs -> Dict[str, float]`**
Backward-compatible property returning the static opponent probabilities.

**Method: `_get_predictor()`**
Lazy-loads `WinProbabilityPredictor` to avoid circular imports.

**Method: `build_tree(initial_state, depth=3) -> GameNode`**
Builds a game tree from the initial state. Resets counters and transposition table. Creates a root "max" node and expands recursively.

**Method: `_expand(node, depth, is_max) -> None`**

Recursive tree expansion:
- For max nodes (our turn): creates a "chance" child for each action, then expands the chance node.
- For min nodes (opponent turn, though not directly created -- see chance expansion): creates "max" children and recurses.
- Stops when depth reaches 0 or node budget is exhausted.

**Method: `_expand_chance(node, depth) -> None`**
Expands a chance node with probabilistic opponent responses. Uses adaptive opponent model if available, otherwise static probabilities. Each opponent action creates a "max" child node (for the next team decision).

**Method: `_apply_action(state, action, is_max) -> Dict`**

Simplified state transitions:
- **push:** Both sides lose 1 player. Map control shifts +/- 0.15. Design note: modeled as symmetric; WinProbabilityPredictor at leaves provides asymmetric correction.
- **hold:** Time decreases by 15 seconds.
- **rotate:** Time decreases by 10 seconds. Map control shifts +/- 0.10.
- **use_utility:** Utility count decreases by 1. Map control +0.05.

**Method: `evaluate(node, depth=0) -> float`**

Recursive expectiminimax evaluation with transposition table:
1. **TT lookup:** If cached at >= current depth, returns cached value (increments `_tt_hits`).
2. **Leaf:** Delegates to `_evaluate_leaf`.
3. **Max node:** Returns max of children evaluations.
4. **Min node:** Returns min of children evaluations.
5. **Chance node:** Weighted expectation using opponent probabilities.
6. **TT store:** Evicts oldest entry (FIFO via `next(iter(...))`) when table exceeds `_TT_MAX_SIZE`.

**Method: `_evaluate_leaf(state) -> float`**
Evaluates a leaf node using `WinProbabilityPredictor.predict_from_dict()`. Falls back to a heuristic `alive / (alive + enemy)` if the predictor fails. Returns 0.0 if all teammates dead, 1.0 if all enemies dead.

**Method: `evaluate_single_action(state, action) -> float`**
Public API (F4-03): Evaluates a single action by applying it to the state and evaluating the resulting leaf. Used by `BlindSpotDetector._evaluate_action()`.

**Method: `get_best_action(root) -> Tuple[str, float]`**
Returns the action with the highest evaluated utility from the root node. Defaults to ("hold", 0.5) if no children.

**Method: `suggest_strategy(game_state, map_name=None) -> str`**
High-level API: builds tree (depth=3), evaluates, and returns a natural-language recommendation. Includes:
- Action description (push/hold/rotate/use_utility)
- Win probability percentage
- Confidence label (high > 0.6, moderate > 0.3, marginal)
- Opponent model type (adaptive vs static)
- Tree exploration statistics (nodes created, TT hits)

#### Factory Function: `get_game_tree_search(map_name=None, use_adaptive=True) -> ExpectiminimaxSearch`
Creates an `ExpectiminimaxSearch` with an optional `OpponentModel` (enabled by default).

---

### A.8 Momentum Tracker (`momentum.py`)

**Purpose:** Models psychological momentum as a time-decaying multiplier that influences expected performance based on recent round outcomes. Governance: Rule 1 S7.3, Rule 2 S6.1.

#### Module-Level Constants

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `HALF_SWITCH_MR12` | `int` | `13` | MR12 half-switch round (CS2 default since Sep 2023) |
| `HALF_SWITCH_MR13` | `int` | `16` | MR13 half-switch round (legacy 30-round format) |
| `MULTIPLIER_MIN` | `float` | `0.7` | Maximum 30% performance drop |
| `MULTIPLIER_MAX` | `float` | `1.4` | Maximum 40% performance boost |
| `MOMENTUM_WIN_PER_STREAK` | `float` | `0.05` | Win multiplier increment per streak round (P8-03) |
| `MOMENTUM_LOSS_PER_STREAK` | `float` | `0.04` | Loss multiplier decrement per streak round. Win asymmetry (+0.05 vs -0.04) reflects CS2 economy advantage on win streaks. |
| `TILT_THRESHOLD` | `float` | `0.85` | Player is "tilted" when multiplier below this (~3-round loss streak) |

#### Module-Level Dict: `ROUND_TYPE_WEIGHT`

Weights for momentum impact by round type:

| Round Type | Win Weight | Loss Weight | Rationale |
|---|---|---|---|
| eco | 1.4 | 0.6 | Winning eco = big upset = big morale boost |
| force_buy | 1.3 | 0.8 | Low-economy upset carries weight |
| full_buy | 1.0 | 1.2 | Losing full-buy is more demoralizing |
| pistol | 1.2 | 1.0 | Pistol wins matter, losses are expected |

#### Dataclass: `MomentumState`

Current momentum state for a player/team.

| Field | Type | Default | Description |
|---|---|---|---|
| `current_multiplier` | `float` | `1.0` | Performance multiplier |
| `streak_length` | `int` | `0` | Length of current streak |
| `streak_type` | `str` | `"neutral"` | "win", "loss", or "neutral" |
| `decay_rate` | `float` | `0.15` | Inter-round gap decay rate |

**Property: `is_tilted -> bool`**
True when `current_multiplier < TILT_THRESHOLD` (0.85).

**Property: `is_hot -> bool`**
True when `current_multiplier > 1.2`.

#### Class: `MomentumTracker`

Tracks psychological momentum across rounds within a match.

**Constructor: `__init__(decay_rate=0.15)`**
Initializes state, sets `_last_round = 0`, creates empty `_history` list.

**Properties:**
- `state -> MomentumState`: current state
- `history -> List[MomentumState]`: copy of historical snapshots

**Method: `update(round_won, round_number, round_type="full_buy") -> MomentumState`**

Core update logic:
1. **Half-switch check:** Resets momentum at round 13 (MR12) or 16 (MR13).
2. **Gap decay:** `decay = exp(-decay_rate * gap)` where gap = distance from last round. Design note: gap=0 for consecutive rounds means decay=1.0 (no dampening within a half). This is intentional -- half-switch resets handle cross-half dampening.
3. **Streak tracking:** Increments streak if same outcome type; resets to 1 if outcome type changes.
4. **Multiplier computation:**
   - Win streak: `raw = 1.0 + WIN_PER_STREAK * streak * decay * rt_weight`
   - Loss streak: `raw = 1.0 - LOSS_PER_STREAK * streak * decay * rt_weight`
   - Where `rt_weight` comes from `ROUND_TYPE_WEIGHT[round_type][outcome_key]`.
5. **Clamping:** to `[MULTIPLIER_MIN, MULTIPLIER_MAX]`.
6. **Archive:** Appends snapshot to history.
7. **Tilt logging:** Logs info if `is_tilted`.

**Method: `_is_half_switch(round_number) -> bool`**
Returns True if `round_number in (HALF_SWITCH_MR12, HALF_SWITCH_MR13)`.

**Method: `_reset() -> None`**
Resets multiplier to 1.0, streak to 0, type to "neutral".

#### Free Function: `predict_performance_adjustment(momentum, base_rating) -> float`
Returns `base_rating * momentum.current_multiplier`.

#### Free Function: `from_round_stats(round_stats_list: List[dict]) -> List[MomentumState]`

Builds a momentum timeline from RoundStats records for a single player:
1. Creates a new `MomentumTracker`.
2. Sorts rounds by `round_number` (handles both dict and model instances).
3. Updates tracker for each round.
4. Returns the history list.

#### Factory Function: `get_momentum_tracker() -> MomentumTracker`
Creates a new instance on each call.

---

### A.9 Movement Quality Analysis (`movement_quality.py`)

**Purpose:** Detects 4 common positioning mistakes from tick-level data, based on MLMove paper (SIGGRAPH 2024, Stanford/Activision/NVIDIA). This module is ADDITIVE -- it does not modify METADATA_DIM=25.

#### Module-Level Constants

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `_TICKS_PER_SECOND` | `int` | `128` | CS2 tick rate |
| `_ESTABLISHED_HOLD_TICKS` | `int` | `384` | 3 seconds hold to count as "established position" |
| `_HIGH_GROUND_DROP` | `float` | `100.0` | Minimum Z descent (units) to flag high ground abandonment |
| `_COMBAT_PROXIMITY_TICKS` | `int` | `64` | Ticks around kill/death events considered "in combat" |
| `_TRADE_SUPPORT_DISTANCE` | `float` | `800.0` | Distance to count as "nearby" teammate for trading |
| `_AUDIO_RANGE_DISTANCE` | `float` | `1500.0` | Distance for "within audio range" of engagement |
| `_ADVANCE_THRESHOLD` | `float` | `100.0` | Minimum movement to count as "advanced" toward engagement |
| `_MOVEMENT_THRESHOLD` | `float` | `300.0` | Position change threshold to count as "moved" |
| `_TRADE_WINDOW_SECONDS` | `int` | `5` | Seconds after teammate death to check for push |
| `_TRADE_WINDOW_TICKS` | `int` | `640` | = 5 * 128 |

#### Helper Functions

**`_distance_2d(x1, y1, x2, y2) -> float`**: 2D Euclidean distance.

**`_distance_3d(x1, y1, z1, x2, y2, z2) -> float`**: 3D Euclidean distance.

#### Dataclass: `MovementMistake`

A detected movement/positioning mistake.

| Field | Type | Default | Description |
|---|---|---|---|
| `mistake_type` | `str` | required | "high_ground_abandoned", "position_abandoned", "over_aggressive_trade", "over_passive_support" |
| `round_number` | `int` | required | Round where mistake occurred |
| `tick` | `int` | required | Tick number |
| `time_in_round` | `float` | required | Seconds into the round |
| `description` | `str` | required | Human-readable description |
| `callout` | `str` | required | Map position name |
| `severity` | `float` | `0.5` | 0.0 to 1.0 scale |

#### Dataclass: `MovementMetrics`

Aggregate movement quality metrics.

| Field | Type | Default | Description |
|---|---|---|---|
| `map_coverage_score` | `float` | `0.0` | Fraction of callout positions visited |
| `high_ground_utilization` | `float` | `0.0` | Time in elevated positions / total alive time |
| `position_stability` | `float` | `0.0` | Mean time (sec) at each position before moving |
| `total_rounds_analyzed` | `int` | `0` | Number of rounds analyzed |
| `mistakes` | `List[MovementMistake]` | `[]` | All detected mistakes |

**Property: `mistake_count -> int`**: `len(mistakes)`.

**Property: `mistakes_per_round -> float`**: `len(mistakes) / total_rounds_analyzed` (0.0 if no rounds).

**Method: `summary() -> str`**: One-line summary for coaching context. Groups mistakes by type and counts.

#### Class: `MovementQualityAnalyzer`

**Method: `analyze_round_ticks(ticks, map_name, player_name="", round_number=0) -> List[MovementMistake]`**

Analyzes a single round's tick data. Requires >= 128 ticks (1 second of data). Builds a combat tick set, then runs all four detectors.

**Method: `analyze_match_ticks(all_ticks, map_name, player_name="") -> MovementMetrics`**

Analyzes an entire match:
1. Partitions ticks by round number.
2. Runs `analyze_round_ticks` on each round.
3. Computes aggregate metrics:
   - **Map coverage:** `visited_callouts / total_callouts` from registry.
   - **High ground utilization:** `elevated_ticks / alive_ticks` (z > 50 = elevated).
   - **Position stability:** Mean hold time at each callout position.

**Detector 1: `_detect_high_ground_abandonment(ticks, map_name, round_number, combat_ticks) -> List[MovementMistake]`**

Flags when player descends >= `_HIGH_GROUND_DROP` (100) units from an elevated position without combat context:
- Skips dead player ticks.
- Checks if the descent tick is in the combat tick set (justified descent).
- Severity: `min(z_drop / 300.0, 1.0)`.

**Detector 2: `_detect_premature_position_abandonment(ticks, map_name, round_number) -> List[MovementMistake]`**

Flags when player leaves a held position without new information:
- Tracks position via 2D distance threshold (`_MOVEMENT_THRESHOLD` = 300 units).
- A position is "established" after `_ESTABLISHED_HOLD_TICKS` (3 seconds).
- Checks for "new information" (any `enemies_visible > 0` in the past 1 second).
- If no new info and position was established, flags as mistake.
- Severity: `min(hold_seconds / 10.0, 1.0)`.

**Detector 3: `_detect_over_aggressive_trading(ticks, map_name, round_number) -> List[MovementMistake]`**

Flags solo pushes after teammate death:
- Detects teammate death via `teammates_alive` drop.
- Checks if player advances > `_MOVEMENT_THRESHOLD` within `_TRADE_WINDOW_TICKS` (5 seconds).
- Only flags if remaining teammates < 2 (no coordination).
- Severity: fixed at 0.7.

**Detector 4: `_detect_over_passive_supporting(ticks, map_name, round_number) -> List[MovementMistake]`**

Flags when player doesn't advance after teammate creates opening:
- Detects enemy elimination via `enemies_alive` drop.
- Checks if player's maximum movement in next 3 seconds is below `_ADVANCE_THRESHOLD` (100 units).
- Only flags if team has numerical advantage (not justified passivity).
- Severity: fixed at 0.5.

**Method: `_find_combat_ticks(ticks) -> set`**

Builds a set of tick numbers near combat events. A tick is "combat" if:
- Health dropped from previous tick, OR
- `enemies_visible > 0`.

For each combat tick, adds a window of +/- `_COMBAT_PROXIMITY_TICKS` (64) ticks to the set.

#### Singleton: `get_movement_quality_analyzer() -> MovementQualityAnalyzer`
Module-level singleton pattern (`_analyzer: Optional[MovementQualityAnalyzer] = None`). Not thread-safe (no lock).

---

### A.10 Role Classifier (`role_classifier.py`)

**Purpose:** Classifies player roles from match statistics. Identifies AWPer, Entry Fragger, Support, IGL, Lurker, and Flex. Uses statistical analysis with optional ML enhancement. Target accuracy from Phase 1B Roadmap: 80%+ agreement with manual labels.

#### Enum: `PlayerRole`

Re-exported from `Programma_CS2_RENAN.core.app_types`. Values: AWPER, ENTRY, SUPPORT, IGL, LURKER, FLEX.

#### Dataclass: `RoleProfile`

Profile of typical role characteristics.

| Field | Type | Description |
|---|---|---|
| `role` | `PlayerRole` | The role enum value |
| `description` | `str` | Human-readable role description |
| `key_stats` | `Dict[str, str]` | Stat name -> expected range (e.g., "High") |
| `coaching_focus` | `List[str]` | Populated dynamically from Knowledge Base (RAG) |

#### Module-Level Dict: `_FALLBACK_TIPS`

Cold-start fallback coaching tips per role, used when the RAG knowledge base is unavailable. Contains 2 generic CS2 fundamental tips per role (AWPER, ENTRY, SUPPORT, IGL, LURKER, FLEX).

#### Module-Level Dict: `ROLE_PROFILES`

Maps each `PlayerRole` to a `RoleProfile` instance with static metadata. The `coaching_focus` lists are intentionally empty (populated dynamically from Knowledge Base). Anti-Mock: profiles contain static metadata but coaching tips must be learned/retrieved.

Profiles defined for: AWPER (primary sniper), ENTRY (first into sites), SUPPORT (trades/utility), IGL (in-game leader), LURKER (off-angle, catches rotations), FLEX (adaptable, fills gaps).

#### Class: `RoleClassifier`

**Class constants:**
- `_CONSENSUS_BOOST = 0.1` (R-01): Confidence bonus when heuristic and neural classifiers agree.
- `_NEURAL_MARGIN = 0.1` (R-01): Minimum confidence margin for neural to override heuristic.

**Constructor: `__init__(threshold_store=None)`**

Initializes with a `RoleThresholdStore` (from `backend.processing.baselines.role_thresholds`). If none provided, uses the singleton. Logs a warning if in cold-start state.

**Method: `classify(player_stats) -> Tuple[PlayerRole, float, RoleProfile]`**

Main classification pipeline:
1. **Cold start guard:** If `threshold_store.is_cold_start()`, returns `(FLEX, 0.0, ROLE_PROFILES[FLEX])` immediately. This prevents decisions based on non-existent data.
2. **Heuristic scoring:** Calls `_calculate_role_scores()` to get affinity scores per role.
3. **Neural secondary opinion:** Calls `_neural_classify()` for consensus.
4. **Consensus logic:** If neural result available, runs `_consensus()` to reconcile. Otherwise uses heuristic result.
5. Returns `(best_role, confidence, profile)`.

**Method: `_calculate_role_scores(stats) -> Dict[PlayerRole, float]`**

Computes affinity scores for each role:
- **AWPER:** `awp_kills / total_kills` ratio, scored via `_score_awper()`
- **ENTRY:** `entry_frags / rounds_played` rate, scored via `_score_entry()`
- **SUPPORT:** `assists / rounds_played` rate, scored via `_score_support()`
- **IGL:** `rounds_survived / rounds_played` rate, scored via `_score_igl()`
- **LURKER:** `solo_kills / total_kills` ratio, scored via `_score_lurker()`

Normalizes scores to sum to 1.0.

**Method: `_score_awper(awp_ratio, stats) -> float`**
If AWP ratio exceeds threshold: `0.8 + (ratio - threshold) * 0.5`. Otherwise: `ratio * 1.5`.

**Method: `_score_entry(entry_rate, stats) -> float`**
If entry rate exceeds threshold: `0.7 + (rate - threshold) * 0.8`. Otherwise: `rate * 2.5`. Adds bonus for first deaths: `first_death_rate * 0.3`.

**Method: `_score_support(assist_rate, stats) -> float`**
If assist rate exceeds threshold: `0.7 + (rate - threshold) * 0.6`. Otherwise: `rate * 2.0`. Adds bonus for utility damage: `min(util_dmg / 50 * 0.2, 0.3)`.

**Method: `_score_igl(survival_rate, stats) -> float`**
If survival rate exceeds threshold: `0.6 + (rate - threshold) * 0.5`. Otherwise: `rate * 0.8`. Adds `0.2` bonus for balanced K/D (0.9-1.2 range).

**Method: `_score_lurker(solo_kills, stats) -> float`**
If solo kill ratio exceeds threshold: `0.7 + (ratio - threshold) * 0.8`. Otherwise: `ratio * 2.5`.

**Method: `_neural_classify(player_stats) -> Optional[Tuple[PlayerRole, float]]`**

Runs neural role prediction (Proposal 10):
1. Imports and loads the role head model via `load_role_head()`.
2. Extracts features via `extract_role_features_from_stats()`.
3. Normalizes features using training statistics (mean/std).
4. Runs forward pass (no grad).
5. Validates output shape (R-03).
6. If max probability < `FLEX_CONFIDENCE_THRESHOLD`, returns FLEX.
7. Returns `(ROLE_OUTPUT_ORDER[max_idx], confidence)`.
8. Returns `None` on any exception.

**Static method: `_consensus(heuristic_role, heuristic_conf, neural_role, neural_conf) -> Tuple[PlayerRole, float]`**

Consensus rules:
1. **Both agree:** Combined confidence = `min((heuristic_conf + neural_conf) / 2 + _CONSENSUS_BOOST, 1.0)`.
2. **Disagree, neural has > _NEURAL_MARGIN margin:** Neural wins with its confidence.
3. **Otherwise:** Heuristic wins (established system, breaks ties).

**Method: `get_role_coaching(role, map_name=None) -> List[str]`**

Retrieves role-specific coaching tips from Knowledge Base (RAG) via `KnowledgeRetriever`. Uses role-specific semantic queries (e.g., "AWP positioning angles peek timing sniper discipline"). Falls back to `_FALLBACK_TIPS` when RAG is unavailable.

**Method: `classify_team(team_stats: List[Dict[str, float]]) -> Dict[str, Tuple[PlayerRole, float]]`**

Classifies roles for an entire team:
1. Sorts players by `impact_rating` (descending).
2. Assigns preferred roles.
3. Constraint: max 1 AWPer per team (fallback to FLEX with 0.5 confidence if AWPer already assigned).

**Method: `audit_team_balance(team_roles) -> List[Dict[str, str]]`**

Team Balance Audit (Task 2.6.1). Detects structural weaknesses:
- **Multiple AWPers:** HIGH severity. Recommends 1 primary AWPer.
- **No Entry Fragger:** HIGH severity. Recommends designating an aggressive player.
- **No Support Player:** MEDIUM severity. Recommends assigning a trader.
- **No Role Diversity:** CRITICAL severity. All players same role = data issue or imbalance.
- **Multiple Lurkers:** MEDIUM severity. Weakens site executes.

Returns list of issue dicts with `type`, `severity`, `title`, `message`, `recommendation`.

#### Factory Function: `get_role_classifier() -> RoleClassifier`
Creates a new instance on each call.

---

### A.11 Utility and Economy Analysis (`utility_economy.py`)

**Purpose:** Analyzes grenade/utility usage effectiveness and optimizes buy decisions.

#### Enum: `UtilityType`

| Value | String |
|---|---|
| `SMOKE` | `"smoke"` |
| `FLASH` | `"flash"` |
| `MOLOTOV` | `"molotov"` |
| `HE` | `"he_grenade"` |

#### Dataclass: `UtilityStats`

| Field | Type | Description |
|---|---|---|
| `utility_type` | `UtilityType` | Type of utility |
| `total_thrown` | `int` | Count of throws |
| `damage_dealt` | `float` | Total damage dealt |
| `enemies_affected` | `int` | Total enemies affected |
| `effectiveness_score` | `float` | 0-1 normalized score |

#### Dataclass: `UtilityReport`

| Field | Type | Description |
|---|---|---|
| `overall_score` | `float` | Mean effectiveness across all utility types |
| `utility_stats` | `Dict[UtilityType, UtilityStats]` | Per-type stats |
| `recommendations` | `List[str]` | Improvement recommendations |
| `economy_impact` | `float` | Dollar value of utility effectiveness |

#### Class: `UtilityAnalyzer`

**Class constant: `PRO_BASELINES`** (P8-06)

Hand-estimated from pro match VOD analysis:

| Type | Metric | Pro Value |
|---|---|---|
| Molotov | damage_per_throw | 35 |
| Molotov | usage_rate | 0.7 |
| HE | damage_per_throw | 25 |
| HE | usage_rate | 0.5 |
| Flash | enemies_per_flash | 1.2 |
| Flash | usage_rate | 0.8 |
| Smoke | strategic_value | 0.9 |
| Smoke | usage_rate | 0.9 |

**Method: `analyze(player_stats) -> UtilityReport`**

For each `UtilityType`:
1. Calls `_analyze_utility_type()` to compute stats.
2. Generates recommendation if `effectiveness_score < 0.5`.
3. Computes `overall_score` as mean of all effectiveness scores.
4. Computes `economy_impact` as dollar value of effectiveness.

**Method: `_analyze_utility_type(stats, util_type) -> UtilityStats`**

Effectiveness calculation by type:
- **Molotov/HE:** `damage_per_throw / baseline_damage_per_throw`, capped at 1.0.
- **Flash:** `affected_per_throw / baseline_enemies_per_flash`, capped at 1.0.
- **Smoke:** `usage_rate / baseline_usage_rate`, capped at 1.0.

Looks up stats using `"{type_value}_{metric}"` keys (e.g., `"molotov_thrown"`, `"molotov_damage"`).

**Method: `_generate_recommendation(util_type, stats) -> str`**
Returns type-specific improvement advice (e.g., "Practice damage lineups. Target 35+ damage per molly.").

**Method: `_calculate_economy_impact(utility_stats) -> float`**

Dollar value calculation: `sum(cost * effectiveness * thrown)` for each utility type.

Costs: Molotov=$400, HE=$300, Flash=$200, Smoke=$300.

#### Factory Function: `get_utility_analyzer() -> UtilityAnalyzer`

---

#### Dataclass: `EconomyDecision`

| Field | Type | Description |
|---|---|---|
| `action` | `str` | "full-buy", "force-buy", "eco", "half-buy", "pistol" |
| `confidence` | `float` | Decision confidence |
| `reasoning` | `str` | Human-readable reasoning |
| `recommended_weapons` | `List[str]` | Recommended loadout |

#### Class: `EconomyOptimizer`

**Class constants:**
- `WEAPON_COSTS`: Dict mapping weapon names to prices (AK-47=$2700, M4A4=$3100, M4A1-S=$2900, AWP=$4750, Galil=$1800, Famas=$2050, MAC-10=$1050, MP9=$1250, UMP=$1200, Deagle=$700, P250=$300, Five-Seven=$500).
- `FULL_BUY_THRESHOLD = 4000`
- `FORCE_BUY_THRESHOLD = 2000`
- `HALF_ROUND`: MR format to second-half pistol round number. `{12: 13, 13: 16}` (P3-12).
- `MR_FORMAT_DEFAULT = 12`

**Method: `recommend(current_money, round_number, is_ct=True, score_diff=0, loss_bonus=1900, mr_format=12) -> EconomyDecision`**

Decision tree:
1. Round 1 -> `_pistol_round_decision`.
2. Half-switch round (configurable via `mr_format`, P3-12) -> `_overtime_decision`.
3. Money >= $5000 -> `_full_buy_decision`.
4. Money >= $2000 + (round <= 3 or score_diff <= -5) -> `_force_buy_decision`.
5. Money >= $2000 (otherwise) -> `_half_buy_decision`.
6. Money < $2000 -> `_eco_decision`.

**Method: `_pistol_round_decision(money, is_ct) -> EconomyDecision`**
CT: USP-S + Kevlar + Kit (confidence 0.95). T: Glock + Kevlar + Flash x2 (confidence 0.95).

**Method: `_full_buy_decision(money, is_ct) -> EconomyDecision`**
CT: M4A4 + Kevlar+Helmet + Full utility. T: AK-47 + Kevlar+Helmet + Full utility. Confidence 0.9.

**Method: `_force_buy_decision(money, is_ct) -> EconomyDecision`**
CT: Famas + Kevlar + Flash. T: Galil + Kevlar + Flash. Confidence 0.7.

**Method: `_half_buy_decision(money, is_ct) -> EconomyDecision`**
SMG (UMP for CT, MAC-10 for T) + Kevlar + Flash. Confidence 0.65.

**Method: `_eco_decision(money, is_ct, loss_bonus) -> EconomyDecision`**
P250 + Flash if money >= $500, else default pistol. Reasoning includes projected next-round money. Confidence 0.85.

**Method: `_overtime_decision(money, is_ct) -> EconomyDecision`**
Always full buy regardless. Confidence 0.95.

#### Factory Function: `get_economy_optimizer() -> EconomyOptimizer`

#### Self-Test (`if __name__ == "__main__"`)
Exercises both `UtilityAnalyzer` and `EconomyOptimizer` with synthetic test data and logs results.

---

### A.12 Win Probability Prediction (`win_probability.py`)

**Purpose:** Predicts round win probability from current game state using a neural network trained on pro demo data. Features: real-time probability updates, economy-aware predictions, player advantage modeling, time remaining factor. Target accuracy from Phase 1B Roadmap: 72%+ on test set.

#### Module-Level Constant

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `WIN_PROB_PREDICTOR_INPUT_DIM` | `int` | `12` | Input dimension for the predictor neural network |

#### Dataclass: `GameState`

Current game state for win probability prediction.

| Field | Type | Default | Description |
|---|---|---|---|
| `team_economy` | `int` | required | Team's total economy ($) |
| `enemy_economy` | `int` | required | Enemy team's economy ($) |
| `alive_players` | `int` | required | Number of alive teammates (0-5) |
| `enemy_alive` | `int` | required | Number of alive enemies (0-5) |
| `utility_remaining` | `int` | `0` | Number of utility items remaining |
| `map_control_pct` | `float` | `0.5` | Percentage of map controlled (0-1) |
| `time_remaining` | `int` | `115` | Seconds remaining in round |
| `bomb_planted` | `bool` | `False` | Whether bomb is planted |
| `is_ct` | `bool` | `True` | Whether team is CT side |

#### Class: `WinProbabilityNN(nn.Module)`

PyTorch neural network for real-time round win probability prediction.

**Architecture:**
- Input: 12 normalized game state features
- Linear(12, 64) -> ReLU -> Dropout(0.2)
- Linear(64, 32) -> ReLU -> Dropout(0.1)
- Linear(32, 1) -> Sigmoid

Note: This is the production predictor model. The offline training model in `backend/nn/win_probability_trainer.py::WinProbabilityTrainerNN` uses 9 raw features and 32/16 hidden dims. Checkpoints are NOT interchangeable.

**Constructor: `__init__(input_dim=12, hidden_dim=64)`**
Builds the sequential network and applies Xavier initialization.

**Method: `_init_weights()`**
Xavier uniform initialization for all Linear layers; zeros for biases.

**Method: `forward(x: Tensor) -> Tensor`**
Standard forward pass. Input: `[batch, 12]`, Output: `[batch, 1]`.

#### Dataclass: `PlattScaler`

Platt scaling (Platt 1999): logistic regression on raw model logits for probability calibration.

| Field | Type | Default | Description |
|---|---|---|---|
| `a` | `float` | `-1.0` | Logistic parameter A |
| `b` | `float` | `0.0` | Logistic parameter B |
| `fitted` | `bool` | `False` | Whether calibration has been performed |

Transform: `p_cal = 1 / (1 + exp(A * logit(p) + B))` where `logit(p) = log(p / (1-p))`.

**Method: `fit(raw_probs, labels, max_iter=100) -> None`**

Fits A, B via Newton's method on binary cross-entropy:
1. Clips raw probabilities to avoid log(0).
2. Computes logits.
3. Iteratively updates A and B using gradient and Hessian.
4. Sets `fitted = True`.

**Method: `calibrate(raw_prob) -> float`**
If not fitted, returns raw probability unchanged. Otherwise applies the logistic transform.

#### Class: `WinProbabilityPredictor`

Main prediction engine.

**Constructor: `__init__(model_path=None)`**

Creates a `WinProbabilityNN` and a `PlattScaler`. If `model_path` provided:
1. Loads checkpoint with `weights_only=True`.
2. Validates checkpoint dimensions (A-12): checks first layer input dim matches `WIN_PROB_PREDICTOR_INPUT_DIM`. Raises `ValueError` if mismatched (prevents loading trainer checkpoint into predictor).
3. Loads state dict and sets `_checkpoint_loaded = True`.

If no checkpoint loaded, logs at error level (W-02) warning that predictions use random weights. Sets model to eval mode.

**Method: `predict(game_state) -> Tuple[float, str]`**

Full prediction pipeline:
1. `_extract_features()` to normalize game state.
2. Forward pass through neural network (no grad).
3. `_apply_heuristics()` for rule-based adjustments.
4. Platt scaling if calibrated.
5. `_generate_explanation()` for human-readable output.

**Method: `fit_calibration(game_states, outcomes) -> None`**
Fits the Platt scaler on a calibration set of (GameState, did_win) pairs. Runs inference on each state to get raw probabilities, then calls `_platt.fit()`.

**Method: `_extract_features(state) -> np.ndarray`**

Extracts 12 normalized features:
1. `team_economy / 16000`
2. `enemy_economy / 16000`
3. `(team_economy - enemy_economy) / 16000` (economy differential)
4. `alive_players / 5`
5. `enemy_alive / 5`
6. `(alive_players - enemy_alive) / 5` (player differential)
7. `utility_remaining / 5` (W-03: CS2 max 5 = 2 smokes + 2 flashes + 1 HE)
8. `map_control_pct` (already 0-1)
9. `time_remaining / 115`
10. `1.0 if bomb_planted else 0.0`
11. `1.0 if is_ct else 0.0`
12. `min(team_economy / max(enemy_economy, 1), 2) / 2` (equipment value ratio)

**Method: `_apply_heuristics(prob, state) -> float`**

Rule-based adjustments applied AFTER neural prediction:
1. **Deterministic boundaries first:** 0 alive = 0.0, 0 enemies = 1.0.
2. **Player advantage:** >= 3 advantage -> floor at 0.85; <= -3 -> ceiling at 0.15.
3. **Bomb planted (W-01):** T-side +0.10 (additive, clamped), CT-side -0.10 (additive, clamped). Additive to stay within [0,1] at every step.
4. **Economy heuristics:** > $8000 advantage -> floor at 0.65; < -$8000 -> ceiling at 0.35.
5. Final clamp to [0, 1].

**Method: `_generate_explanation(prob, state) -> str`**

Returns human-readable string:
- > 70%: "Favorable position"
- > 50%: "Slight advantage"
- > 30%: "Slight disadvantage"
- <= 30%: "Unfavorable position"

**Method: `predict_from_dict(state_dict) -> Tuple[float, str]`**
Convenience method that constructs a `GameState` from a dict with default values and calls `predict()`.

#### Factory Function: `get_win_predictor() -> WinProbabilityPredictor`
Creates a new instance on each call (no model path -- untrained by default).

---

#### Elo Rating System (KT-07)

Per-player Elo with recency weighting. References: Elo (1978), Glickman (1999), Herbrich et al. (2006, TrueSkill).

**Module-Level Constants:**
| Constant | Type | Value | Purpose |
|---|---|---|---|
| `_ELO_INITIAL` | `float` | `1500.0` | Default starting Elo |
| `_ELO_K_FACTOR` | `float` | `32.0` | Base K-factor |
| `_ELO_RECENCY_HALF_LIFE` | `int` | `20` | Matches for recency weight to halve |

#### Dataclass: `MatchResult`

| Field | Type | Default | Description |
|---|---|---|---|
| `opponent_elo` | `float` | required | Opponent's Elo at match time |
| `won` | `bool` | required | Whether the player won |
| `match_index` | `int` | `0` | Chronological index (0 = oldest) |

#### Class: `EloRatingCalculator`

**Constructor: `__init__(initial_elo=1500.0, k_factor=32.0, recency_half_life=20)`**
Clamps `recency_half_life` to minimum 1.

**Method: `compute_elo(match_history: List[MatchResult]) -> float`**

Computes Elo from chronologically ordered match history:
```
For each match:
  expected = 1 / (1 + 10^((opp_elo - elo) / 400))
  actual = 1.0 if won else 0.0
  recency_weight = 2^((match_index - (N-1)) / half_life)
  elo += K * recency_weight * (actual - expected)
```
Most recent match (index N-1) gets weight 1.0; a match `half_life` games earlier gets weight 0.5.

**Method: `compute_elo_differential(team_histories, enemy_histories) -> float`**

Computes normalized team Elo differential:
```
diff = (mean(team_elos) - mean(enemy_elos)) / 400
```
Division by 400 (one Elo "class") normalizes to roughly [-3, +3]. Positive favors the team.

**Static method: `elo_win_probability(elo_a, elo_b) -> float`**
Standard logistic Elo formula: `P(A wins) = 1 / (1 + 10^((elo_b - elo_a) / 400))`.

#### Class: `EloAugmentedPredictor`

Wraps `WinProbabilityPredictor` and optionally blends its output with an Elo-based prior.

**Constructor: `__init__(base_predictor=None, elo_calculator=None, elo_blend_alpha=0.15)`**
- `elo_blend_alpha` clamped to [0.0, 1.0] via `np.clip`.

**Blending formula:**
```
final_prob = (1 - alpha) * nn_prob + alpha * elo_prob
```
Default alpha=0.15 means Elo has a subtle influence. The core 12-feature model is unchanged -- Elo serves as a supplementary Bayesian adjustment.

**Method: `predict_with_elo(game_state, team_elo, enemy_elo) -> Tuple[float, str]`**
Runs base prediction, computes Elo prior, blends, and generates enhanced explanation including Elo differential.

**Method: `predict(game_state) -> Tuple[float, str]`**
Fallback: delegates to base predictor (maintains interface compatibility).

#### Self-Test (`if __name__ == "__main__"`)
Tests the `WinProbabilityPredictor` on 4 scenarios: even match, man advantage (4v2), economy disadvantage, and bomb planted (T side).

---

## Part B: Progress Tracking (`Programma_CS2_RENAN/backend/progress/`)

### B.1 Package Initialization (`__init__.py`)

Empty file (0 lines of content). Serves as a namespace marker making `backend.progress` a Python package.

### B.2 Longitudinal Progress (`longitudinal.py`)

Contains a single dataclass for trend feature representation.

#### Dataclass: `FeatureTrend`

| Field | Type | Description |
|---|---|---|
| `feature` | `str` | Name of the feature being tracked |
| `slope` | `float` | Linear trend slope (from polynomial fit) |
| `volatility` | `float` | Standard deviation of values |
| `confidence` | `float` | Confidence in the trend (sample-size dependent) |

### B.3 Trend Analysis (`trend_analysis.py`)

Provides a single function for computing linear trends from time-series data.

#### Module-Level Constant

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `TREND_CONFIDENCE_SAMPLE_SIZE` | `int` | `30` | Number of samples at which trend confidence reaches 1.0 |

#### Function: `compute_trend(values) -> Tuple[float, float, float]`

Computes a linear trend from a sequence of values:
1. **Guard (AC-39-01):** Returns `(0.0, 0.0, 0.0)` if fewer than 2 values (insufficient data for polynomial fit).
2. Creates an index array `x = [0, 1, ..., n-1]`.
3. Fits a degree-1 polynomial via `np.polyfit` to extract slope.
4. Computes volatility as `y.std()`.
5. Computes confidence as `min(1.0, len(values) / TREND_CONFIDENCE_SAMPLE_SIZE)`. Linearly scales from 0.0 (2 samples) to 1.0 (30+ samples).
6. Returns `(slope, volatility, confidence)`.

---

## Part C: Reporting (`Programma_CS2_RENAN/backend/reporting/` and `Programma_CS2_RENAN/reporting/`)

Note: There are TWO reporting-related packages:
- `Programma_CS2_RENAN/backend/reporting/` -- contains `AnalyticsEngine` (data aggregation)
- `Programma_CS2_RENAN/reporting/` -- contains `MatchReportGenerator` and `MatchVisualizer` (report generation and visualization)

### C.1 Backend Reporting Package (`backend/reporting/__init__.py`)

Empty file. Namespace marker.

### C.2 Analytics Engine (`backend/reporting/analytics.py`)

**Purpose:** Centralized math engine for Dashboard Analytics. Decouples data aggregation from UI rendering.

#### Class: `AnalyticsEngine`

**Constructor: `__init__()`**
Acquires the database manager singleton via `get_db_manager()`.

**Method: `_player_filter(player_name) -> tuple`**

Builds a WHERE clause with fallback logic:
1. Counts the player's personal (non-pro) matches in `PlayerMatchStats`.
2. If personal matches exist, filters to `player_name + is_pro=False`.
3. If no personal matches, returns `(True,)` -- no filter, showing all data including pro matches.

This ensures the Performance screen always shows data rather than an empty state.

**Method: `get_player_trends(player_name, limit=20) -> pd.DataFrame`**

Fetches historical performance metrics for trend graphs:
1. Queries `PlayerMatchStats` with player filter.
2. Orders by `processed_at` descending, limited to `limit` rows.
3. Converts to DataFrame and reverses to chronological order.

**Method: `get_skill_radar(player_name) -> dict`**

Computes normalized skill attributes (0-100) compared to pro baseline. Queries averages of: accuracy, headshot %, KAST, utility blinded, blind time, flash assists, ADR, clutch win %.

Heuristic mapping to 5 radar axes:
- **Aim:** `(accuracy * 100 * 0.5) + (hs% * 100 * 0.5)`
- **Utility:** `(util_blind / 2.0 * 100 * 0.6) + (flash_assists / 1.0 * 100 * 0.4)`, capped at 100
- **Positioning:** `KAST / 0.75 * 100`, capped at 100
- **Map Sense:** `ADR / 100.0 * 100`, capped at 100
- **Clutch:** `clutch_win_pct * 100`, capped at 100

Returns `{"Aim": int, "Utility": int, "Positioning": int, "Map Sense": int, "Clutch": int}`.

Note (SA-03): Uses integer indexing for aggregate Row objects, not attribute access.

**Method: `get_training_metrics() -> dict`**

Fetches latest training telemetry from `CoachState` table (in the "knowledge" DB session). Returns `{"epoch", "total_epochs", "loss", "val_loss", "confidence"}`.

**Method: `get_rating_history(player_name, limit=50) -> list`**

Returns list of `{rating, match_date, demo_name}` ordered chronologically. Queries `PlayerMatchStats`, reverses desc order to asc.

**Method: `get_per_map_stats(player_name) -> dict`**

Aggregates per-map performance. Map extraction from demo filenames uses two strategies:
1. Regex pattern `(de_\w+|cs_\w+|ar_\w+)` for standard map prefixes.
2. Fallback: checks for known map names (`mirage`, `inferno`, `dust2`, etc.) embedded in filename (e.g., "furia-vs-navi-m1-mirage.dem").

Returns `{map_name: {rating, adr, kd, matches}}`.

**Method: `get_strength_weakness(player_name) -> dict`**

Computes Z-score deviations vs. pro baseline:
1. Queries average stats for the player.
2. Fetches pro baseline via `get_pro_baseline()`.
3. Calls `calculate_deviations(player_stats, baseline)` to get Z-scores.
4. Strengths: Z-score > 0.5 (sorted descending, top 5).
5. Weaknesses: Z-score < -0.5 (sorted ascending, top 5).

Display name mapping: rating, K/D Ratio, ADR, KAST, Headshot %, Accuracy, Clutch Win %, Opening Duel %.

**Method: `get_utility_breakdown(player_name) -> dict`**

Per-utility comparison: user vs. pro baseline for 6 metrics:
- HE damage per round
- Molotov damage per round
- Smokes per round
- Flash blind time
- Flash assists
- Unused utility per round

Pro baseline is queried from DB (`is_pro=True`). If no pro data exists, returns empty pro dict rather than fabricating values (Anti-Fabrication Rule). Returns `{"user": {...}, "pro": {...}}`.

**Method: `get_hltv2_breakdown(player_name) -> dict`**

Returns the 5 HLTV 2.0 rating components:
1. **Kill:** `kpr / BASELINE_KPR`
2. **Survival:** `compute_survival_rating(dpr) / BASELINE_DPR_COMPLEMENT`
3. **KAST:** `kast / BASELINE_KAST`
4. **Impact:** `compute_impact_rating(kpr, adr) / BASELINE_IMPACT`
5. **Damage:** `adr / BASELINE_ADR`

Imports rating computation helpers from `backend.processing.feature_engineering.rating`.

#### Module-Level Singleton

```python
analytics = AnalyticsEngine()
```
A global instance created at import time.

---

### C.3 Reporting Package Initialization (`reporting/__init__.py`)

Empty file. Namespace marker.

### C.4 Match Report Generator (`reporting/report_generator.py`)

**Purpose:** Generates full match reports: Parse -> Analyze -> Visualize -> Report.

#### Class: `MatchReportGenerator`

**Constructor: `__init__(db_manager)`**

Sets up:
- `self.db`: database manager instance
- `self.viz`: `MatchVisualizer` instance
- `self.output_dir`: `Path(USER_DATA_ROOT) / "reports"`, resolved to absolute path

Security (DA-RG-01): Uses absolute path anchored to config, not relative to cwd.
Security (RG-01): Validates that `output_dir` stays under `USER_DATA_ROOT`; resets if it escapes.

Creates the output directory if it doesn't exist.

**Method: `generate_report(demo_path) -> Optional[str]`**

Full pipeline:
1. **Parse Demo:** Uses `DemoLoader().load_demo(demo_path)`. Returns None on error or empty result.
2. **Validate:** Checks map_name is not "unknown" and frames are not empty.
3. **Extract Data:** Collects player positions and death locations from parsed frames.
4. **Generate Visuals:** Calls `self.viz.generate_heatmap()`.
5. **Generate Text Report:** Writes a Markdown file with:
   - Header (map name, date)
   - Positioning heatmap reference (RG-02: uses relative path to avoid exposing absolute filesystem structure)
   - Fundamental errors section (currently template)
   - Footer

Returns the report file path as a string, or None on any failure.

---

### C.5 Match Visualizer (`reporting/visualizer.py`)

**Purpose:** Generates visual artifacts for CS2 Match Reports: heatmaps, death locations, trajectory plots, differential overlays, and critical moment annotations.

#### Class: `MatchVisualizer`

**Constructor: `__init__(output_dir="reports/assets")`**

Sets up:
- `self.output_dir`: creates directory if needed
- `self.map_config`: loads from `data/map_tensors.json` (fallback to empty dict)
- `self.assets_dir`: path to map background images
- `self.map_bounds`: fallback bounds `{"unknown": (-4000, 4000, -4000, 4000)}`

**Method: `generate_heatmap(positions, map_name, title="Player Heatmap") -> str`**

Generates a 2D histogram heatmap of player positions:
1. Extracts x/y values from position tuples.
2. Sets up map background via `_setup_map_plot()`.
3. Creates hist2d with 64 bins, "magma" colormap, minimum count 1.
4. Saves to PNG file.
5. Safety (DA-VZ-01): try/finally ensures figure is closed even on savefig error.

**Method: `plot_round_errors(round_id, deaths, bad_decisions, map_name) -> str`**

Plots death locations (red X markers) and coach-flagged decisions (orange + markers) on the map. Returns path to saved PNG.

**Method: `_setup_map_plot(map_name)`**

Sets up map background and bounds:
1. Loads bounds from `_get_bounds()`.
2. Attempts to load background image from `map_config` JSON.
3. Security (VZ-02): Prevents path traversal via malicious `image_file` values by verifying the resolved path starts with `assets_dir.resolve()`.

**Method: `render_differential_overlay(user_positions, pro_positions, map_name, resolution=128, sigma=5.0, title="Pro vs User") -> Optional[str]`**

Generates a diverging heatmap comparing user vs. pro positional patterns:
1. Converts positions to density grids via Gaussian KDE (`gaussian_filter` with configurable sigma).
2. Normalizes each density grid to [0, 1].
3. Computes difference: `d_pro - d_user`.
4. Masks areas with no activity (threshold 0.02).
5. Uses diverging colormap `RdBu_r`: Blue = user-heavy, Red = pro-heavy, White = equal.
6. Uses `TwoSlopeNorm` centered at 0 for symmetric scaling.
7. Overlays on map background with alpha=0.7.
8. Safety (VZ-01): try/finally ensures figure is closed.

Returns path to saved PNG (150 DPI), or None if insufficient data.

**Method: `_get_bounds(map_name) -> tuple`**

Returns `(x_min, x_max, y_min, y_max)` for known maps:
- de_mirage: (-3230, 1910, -3200, 1700)
- de_inferno: (-2000, 3800, -1200, 3800)
- de_dust2: (-2476, 2000, -1200, 3300)
- de_nuke: (-3000, 4000, -4000, 4000)
- de_overpass: (-4800, 2000, -1000, 1700)
- de_ancient: (-3000, 2000, -2000, 3000)
- Default: (-4000, 4000, -4000, 4000)

**Static method: `_build_critical_moments_legend() -> List[Line2D]`**

Builds legend handles for severity + scale markers:
- Critical Play (^ red, size 10)
- Critical Mistake (v red, size 10)
- Significant (o orange, size 10)
- Notable (o gold, size 10)
- Micro scale (o gray, size 6)
- Standard scale (o gray, size 9)
- Macro scale (o gray, size 12)

**Method: `render_critical_moments(moments, map_name, title="Critical Moments") -> Optional[str]`**

Renders critical moments as labeled markers on a map image:
1. Maps severity to colors: critical=red, significant=orange, notable=gold.
2. Maps type to markers: mistake=downward triangle, play=upward triangle.
3. Maps scale to marker sizes: micro=100, standard=200, macro=350.
4. Uses position from annotation dict if available; otherwise distributes markers evenly along a horizontal line at 80% map height.
5. Annotates with description text (truncated to 50 chars), offset 15 points above marker.
6. Adds legend via `_build_critical_moments_legend()`.
7. Safety (VZ-01): try/finally.

Returns path to saved PNG (150 DPI), or None if no moments.

#### Standalone Function: `generate_highlight_report(match_id, map_name="de_mirage") -> Optional[str]`

Integration function that connects the ChronovisorScanner (RAP model) with the MatchVisualizer:
1. Checks `USE_RAP_MODEL` setting; returns None if disabled.
2. Scans match for critical moments via `ChronovisorScanner.scan_match()`.
3. Converts to highlight annotations.
4. Renders via `MatchVisualizer.render_critical_moments()`.
5. Returns path to generated image, or None on failure.

---

## Part D: Cross-Cutting Design Patterns

### D.1 Factory Functions and Singletons

Every analysis module exports a `get_*()` factory function. Some implement true singletons:
- **Thread-safe singleton with double-checked locking:** `get_death_estimator()` (belief_model.py)
- **Module-level singleton (no thread safety):** `get_movement_quality_analyzer()` (movement_quality.py)
- **New instance per call:** All other `get_*()` factories (blind_spots, deception, engagement_range, entropy, game_tree, momentum, role_classifier, utility_economy, win_probability)
- **Import-time singleton:** `analytics = AnalyticsEngine()` (analytics.py)

### D.2 Governance Codes

Throughout the analysis engines, governance codes appear as comments documenting design decisions, safety guards, and audit anchors:
- **P-series (P3-xx, P8-xx):** Phase implementation codes
- **AC-series:** Audit corrections
- **A-series:** Architecture safety guards
- **B-series:** Bug/crash prevention guards
- **D-series:** Data integrity guards
- **E-series:** Concurrency/entropy guards
- **F-series:** Feature/functionality guards
- **O-series:** Observability guards
- **R-series:** Role classifier design codes
- **W-series:** Win probability design codes
- **WR-series:** Write-back / side-effect codes
- **DA-series, RG-series, VZ-series, SA-series:** Module-specific audit codes

### D.3 Anti-Fabrication and Cold-Start

The codebase follows strict anti-fabrication rules:
- `RoleClassifier`: Returns FLEX with 0% confidence during cold start (no learned thresholds).
- `AnalyticsEngine.get_utility_breakdown()`: Returns empty pro dict rather than fabricating values when no pro data exists in DB.
- `UtilityAnalyzer.PRO_BASELINES`: Hand-estimated baselines are explicitly documented as needing empirical validation from parsed pro demos.
- All calibration methods in `AdaptiveBeliefCalibrator` have minimum sample requirements.

### D.4 Numerical Safety

- **NaN/Inf guards:** `AdaptiveBeliefCalibrator.calibrate_threat_decay()` (A-01), `DeathProbabilityEstimator.estimate()` (epsilon clamp in log_odds).
- **Log(0) prevention:** `EntropyAnalyzer.compute_position_entropy()` clips probabilities to float32 tiny value (AC-06-01).
- **Division by zero prevention:** Widespread use of `max(1, denominator)` and `max(1e-6, value)` patterns.
- **Clamping/bounding:** All calibrated parameters have safety bounds. Win probability clamped to [0, 1]. Momentum multiplier bounded to [0.7, 1.4].

### D.5 Security Guards

- **VZ-02 (visualizer.py):** Path traversal prevention for map image files loaded from JSON config.
- **RG-01 (report_generator.py):** Validates report output directory stays under `USER_DATA_ROOT`.
- **RG-02 (report_generator.py):** Uses relative paths in reports to avoid exposing absolute filesystem structure.
- **DA-RG-01 (report_generator.py):** Uses absolute paths anchored to config, not relative to cwd.
