# Chapter 3: Processing, Feature Engineering, Baselines, and Validation

This chapter provides an exhaustive reference for every class, function, constant, and design mechanism found in the `Programma_CS2_RENAN.backend.processing` package and its subpackages: `feature_engineering`, `baselines`, and `validation`.

---

## Table of Contents

1. [Processing Package (`processing/`)](#1-processing-package)
   - 1.1 [`__init__.py`](#11-__init__py)
   - 1.2 [`bombsite_encoding.py`](#12-bombsite_encodingpy)
   - 1.3 [`connect_map_context.py`](#13-connect_map_contextpy)
   - 1.4 [`data_pipeline.py`](#14-data_pipelinepy)
   - 1.5 [`demo_prioritizer.py`](#15-demo_prioritizerpy)
   - 1.6 [`demo_quality.py`](#16-demo_qualitypy)
   - 1.7 [`external_analytics.py`](#17-external_analyticspy)
   - 1.8 [`heatmap_engine.py`](#18-heatmap_enginepy)
   - 1.9 [`player_knowledge.py`](#19-player_knowledgepy)
   - 1.10 [`rating.py`](#110-ratingpy)
   - 1.11 [`round_reconstructor.py`](#111-round_reconstructorpy)
   - 1.12 [`round_stats_builder.py`](#112-round_stats_builderpy)
   - 1.13 [`skill_assessment.py`](#113-skill_assessmentpy)
   - 1.14 [`state_reconstructor.py`](#114-state_reconstructorpy)
   - 1.15 [`tensor_factory.py`](#115-tensor_factorypy)
   - 1.16 [`tick_enrichment.py`](#116-tick_enrichmentpy)
2. [Feature Engineering Subpackage (`feature_engineering/`)](#2-feature-engineering-subpackage)
   - 2.1 [`__init__.py`](#21-__init__py-1)
   - 2.2 [`base_features.py`](#22-base_featurespy)
   - 2.3 [`kast.py`](#23-kastpy)
   - 2.4 [`rating.py`](#24-ratingpy)
   - 2.5 [`role_features.py`](#25-role_featurespy)
   - 2.6 [`vectorizer.py`](#26-vectorizerpy)
3. [Baselines Subpackage (`baselines/`)](#3-baselines-subpackage)
   - 3.1 [`__init__.py`](#31-__init__py-2)
   - 3.2 [`meta_drift.py`](#32-meta_driftpy)
   - 3.3 [`nickname_resolver.py`](#33-nickname_resolverpy)
   - 3.4 [`pro_baseline.py`](#34-pro_baselinepy)
   - 3.5 [`pro_player_linker.py`](#35-pro_player_linkerpy)
   - 3.6 [`role_thresholds.py`](#36-role_thresholdspy)
4. [Validation Subpackage (`validation/`)](#4-validation-subpackage)
   - 4.1 [`__init__.py`](#41-__init__py-3)
   - 4.2 [`dem_validator.py`](#42-dem_validatorpy)
   - 4.3 [`drift.py`](#43-driftpy)
   - 4.4 [`sanity.py`](#44-sanitypy)
   - 4.5 [`schema.py`](#45-schemapy)

---

## 1. Processing Package

### 1.1 `__init__.py`

**Path:** `Programma_CS2_RENAN/backend/processing/__init__.py`

Empty file. Marks the `processing` directory as a Python package. Contains no exports, classes, or functions.

---

### 1.2 `bombsite_encoding.py`

**Path:** `Programma_CS2_RENAN/backend/processing/bombsite_encoding.py`

**Purpose:** Implements bombsite-relative coordinate encoding (tagged KT-10). Instead of raw `(x, y)` positions normalized by map diagonal, positions are encoded as a signed differential distance to bombsite A vs B. Optionally flipped by team side to achieve CT/T equivariance. This module is ADDITIVE -- it does NOT modify `METADATA_DIM=25`.

**Design reference:** "Approximately Equivariant Networks" (ICLR 2026 submission). For CS2's discrete symmetries (|G| = 2), equivariance via projection is trivially cheap.

#### Constants

| Constant | Type | Description |
|---|---|---|
| `MAP_BOMBSITE_CENTERS` | `Dict[str, Dict]` | Bombsite center coordinates per active-duty map. Keys are map names (e.g., `"de_dust2"`). Each value contains `"A"` and `"B"` (tuples of `(x, y)` in world units) and `"diagonal"` (float, `sqrt(width^2 + height^2)` for normalization). Covers 9 maps: de_dust2, de_mirage, de_inferno, de_nuke, de_overpass, de_anubis, de_vertigo, de_ancient, de_train. |

#### Functions

**`get_bombsite_distances(pos_x: float, pos_y: float, map_name: str) -> Optional[Tuple[float, float]]`**

Computes the Euclidean distance from a position to each bombsite center (A and B). Returns `(distance_to_A, distance_to_B)` or `None` if the map is not in the registry.

**`normalize_position_equivariant(pos_x: float, pos_y: float, map_name: str, team_side: str = "CT") -> float`**

Computes the bombsite-relative equivariant position encoding as `(dist_A - dist_B) / diagonal`. For the T side, the value is negated to achieve semantic equivariance under team-swap symmetry. Returns a scalar clamped to `[-1, 1]`, or `0.0` if the map is unknown. Protects against a non-positive diagonal by returning `0.0`.

**`compute_site_proximity(pos_x: float, pos_y: float, map_name: str) -> Optional[Tuple[str, float]]`**

Determines which bombsite the player is closest to and the normalized distance. Returns `("A" or "B", normalized_distance)` where normalized distance is in `[0, 1]` (0 = at site, 1 = far away), using half the map diagonal as the normalizing denominator. Returns `None` if the map is unknown.

---

### 1.3 `connect_map_context.py`

**Path:** `Programma_CS2_RENAN/backend/processing/connect_map_context.py`

**Purpose:** Computes spatial features relative to map objectives (bombsites, spawns, mid-control). Includes Z-axis awareness for multi-level maps (Nuke, Vertigo) via a Z-penalty mechanism that prevents false proximity readings when players and objectives are on different floors.

#### Functions

**`distance_with_z_penalty(player_pos, target_pos, z_penalty_factor=Z_PENALTY_FACTOR, z_threshold=Z_LEVEL_THRESHOLD) -> float`**

Calculates Euclidean distance with an optional Z-axis penalty. Accepts 2D or 3D coordinates. If both positions are 3D and the Z-difference exceeds `z_threshold`, the Z-difference is multiplied by `z_penalty_factor` and added to the XY distance. Otherwise, standard 3D Euclidean distance is used. For 2D inputs, standard 2D Euclidean distance is returned.

**`calculate_map_context_features(player_pos, map_tensors, feature_dim=6) -> np.array`**

Produces a normalized feature vector of size `feature_dim` from spatial relationships:
- Feature 0-1: Distance to bombsite A and B (normalized by `max_distance`, default 4000 units unless overridden by `map_tensors["max_distance"]` per R4-11-02).
- Feature 2-3: Distance to T and CT spawns.
- Feature 4: Distance to mid control point.
- Remaining features padded with `0.0` or truncated to match `feature_dim`.

All distances use `distance_with_z_penalty` and are clipped to `[0, 1]`. Returns a zero vector if `map_tensors` is empty.

---

### 1.4 `data_pipeline.py`

**Path:** `Programma_CS2_RENAN/backend/processing/data_pipeline.py`

**Purpose:** Implements the data engine for cleaning, preprocessing, scaling, and splitting `PlayerMatchStats` records for MLP neural network training. Handles temporal splitting, player decontamination, outlier removal, and scaler persistence.

#### Constants

| Constant | Value | Description |
|---|---|---|
| `_MAX_PIPELINE_ROWS` | `50_000` | Hard upper bound for rows loaded into memory, preventing OOM on large deployments. |

#### Class: `ProDataPipeline`

**Attributes:**
- `scaler`: `StandardScaler` instance for feature normalization.
- `_pipeline_executed`: Boolean idempotency guard (P-DP-04). Prevents double-application of the scaler if `run_pipeline()` is called twice.
- `feature_cols`: List of 12 feature column names used for scaling: `avg_kills`, `avg_deaths`, `avg_adr`, `avg_hs`, `avg_kast`, `kill_std`, `adr_std`, `kd_ratio`, `impact_rounds`, `accuracy`, `econ_rating`, `rating`.
- `SCALER_PATH`: Class-level `Path` pointing to `backend/storage/fitted_scaler.joblib`.

**Methods:**

**`run_pipeline(self)`**
Main orchestrator. Loads `PlayerMatchStats` from the database (excluding `data_quality == "none"` per C-04, with deterministic ordering by ID per H-09, limited to `_MAX_PIPELINE_ROWS`). Converts results to a DataFrame, creates a `stratify_col`, splits data temporally, removes outliers (ADR < 400; kills beyond 3.0x IQR outer fence per P-DP-03), fits `StandardScaler` on training data only (P-DP-01), transforms all splits, persists the scaler, and updates splits in the database. Sets `_pipeline_executed = True` on completion.

**`_save_scaler(self)`**
Persists the fitted scaler as a dict containing both the `StandardScaler` and the `sklearn.__version__` string, using `joblib.dump`.

**`load_scaler(self) -> bool`**
Loads a previously fitted scaler from disk. Compares the major.minor sklearn version (P-DP-05) and warns if mismatched. Handles both modern (dict with version metadata) and legacy (bare scaler) formats. Returns `True` on success, `False` if file not found.

**`_split_data(self, df, temporal_split=True, train_cutoff_date=None, val_cutoff_date=None)`**
Splits data into train (70%), validation (15%), and test (15%). Two modes:
- **Temporal split** (default): Sorts by `match_date` or `processed_at`, separates pro and user data, applies chronological 70/15/15 ratios. Supports growing-window split when `train_cutoff_date` and `val_cutoff_date` are both provided. Calls `_decontaminate_player_splits` (C-06). Logs temporal boundaries for reproducibility.
- **Legacy random stratified split**: Uses `train_test_split` with stratification by `stratify_col` and `random_state=42`.

**`_decontaminate_player_splits(train, val, test)` [static]**
C-06 / P-DP-02: Ensures each player appears in exactly one split. Multi-split players are assigned to their **earliest** split (not majority) to preserve temporal ordering. Rows from later splits are dropped. Logs the number of multi-split players resolved and rows dropped.

**`_update_splits_in_db(self, df, split_name)`**
Bulk-updates `dataset_split` for all rows in the DataFrame. Uses chunked `UPDATE ... WHERE id IN (...)` with `_CHUNK = 500` to stay under SQLite's `SQLITE_MAX_VARIABLE_NUMBER` (999). Avoids N individual GET+SET+ADD queries (F2-22).

#### Module-level Function

**`generate_growing_windows(match_dates, n_windows=5, train_ratio=0.70, val_ratio=0.15)`**
Generator yielding `(train_cutoff_date, val_cutoff_date)` tuples for growing-window temporal cross-validation. Each successive window grows the training set forward in time. Returns nothing if fewer than 10 data points. The step size is `(1.0 - train_ratio - val_ratio) / n_windows`.

---

### 1.5 `demo_prioritizer.py`

**Path:** `Programma_CS2_RENAN/backend/processing/demo_prioritizer.py`

**Purpose:** Ranks available demos by expected coaching value. Uses prediction variance as a proxy for model uncertainty (active-learning inspired selection). Falls back to diversity-based ranking when no trained model is available.

#### Constants

| Constant | Value | Description |
|---|---|---|
| `_MIN_TICKS_FOR_VARIANCE` | `64` | Minimum tick records required for meaningful variance computation. |
| `_MAX_TICKS_SAMPLE` | `2048` | Maximum ticks sampled per demo to avoid OOM. |

#### Dataclass: `DemoPriorityResult`

Fields: `demo_name` (str), `priority_score` (float), `method` (str: "variance" or "diversity"), `tick_count` (int, default 0), `unique_players` (int, default 0).

#### Class: `DemoPrioritizer`

**Constructor:** `__init__(self, model=None)` -- Accepts an optional trained JEPA or coaching model. If `None`, diversity-based fallback is used automatically. Stores `_model` and resolves `_device` via `get_device()`.

**Methods:**

**`rank_demos(self, demo_names: list[str], top_k: int = 10) -> list[tuple[str, float]]`**
Main ranking entry point. Dispatches to variance-based or diversity-based ranking depending on whether `_model` is loaded. Sorts results descending by priority score and returns the top-k `(demo_name, priority_score)` pairs.

**`_rank_by_variance(self, demo_names) -> list[DemoPriorityResult]`**
Iterates over demo names, calling `_compute_demo_variance` for each. Failed demos receive score 0.0 (sinks to bottom, not silently dropped).

**`_compute_demo_variance(self, demo_name: str) -> Tuple[float, int]`**
Loads up to `_MAX_TICKS_SAMPLE` ticks from the database for the demo. If tick count is below `_MIN_TICKS_FOR_VARIANCE`, returns `(0.0, tick_count)`. Otherwise, converts ticks to features via `_ticks_to_features`, feeds through the model in eval mode with `torch.no_grad()`, and computes `predictions.var(dim=-1).mean().item()` as the variance score.

**`_ticks_to_features(ticks: list) -> np.ndarray` [static]**
Converts `PlayerTickState` rows to a raw numeric feature matrix of shape `(N, 25)`. Extracts positional and state fields aligned with the canonical 25-dim feature vector. Uses hardcoded normalizations (health/100, armor/100, equipment/10000, pos/4096, etc.). Several features default to 0.0 because they are not available in `PlayerTickState` (is_blinded, enemies_visible, z_penalty, kast, map_id, round_phase, weapon_class, time_in_round, bomb_planted, teammates_alive, enemies_alive, team_economy).

**`_rank_by_diversity(self, demo_names) -> list[DemoPriorityResult]`**
Fallback ranking using three components (each [0, 1]):
- Player count: normalized to max across all demos.
- Data completeness: mean quality score (complete=1.0, partial=0.5, else 0.0).
- Player rarity: inverse of how many demos each player appears in.

Weighted combination: `0.4 * player_score + 0.3 * quality_score + 0.3 * rarity_score`. Demos with no stats get score 0.01.

---

### 1.6 `demo_quality.py`

**Path:** `Programma_CS2_RENAN/backend/processing/demo_quality.py`

**Purpose:** Evaluates data quality of ingested demos using robust statistical methods based on the Huber contamination model. Detects incomplete demos, feature sparsity, and statistical outliers via IQR fencing.

#### Constants

| Constant | Value | Description |
|---|---|---|
| `_EXPECTED_TICKS_PER_DEMO` | `1_600_000` | Expected tick count for a full CS2 competitive match. |
| `_MIN_VIABLE_TICKS` | `512_000` | Minimum viable tick count (10 rounds * 80s * 64 tick/s * 10 players). |
| `_IQR_MULTIPLIER_MODERATE` | `1.5` | Tukey's standard outlier fence multiplier. |
| `_IQR_MULTIPLIER_EXTREME` | `3.0` | Tukey's extreme outlier fence multiplier. |
| `_QUALITY_THRESHOLD_USE` | `0.7` | Quality score threshold for "use" recommendation. |
| `_QUALITY_THRESHOLD_REVIEW` | `0.4` | Quality score threshold for "review" recommendation. Below this is "skip". |
| `_NONZERO_TICK_FIELDS` | list | Fields that should be non-zero in normal gameplay: `health`, `armor`, `pos_x`, `pos_y`, `pos_z`, `equipment_value`. |

#### Dataclass: `OutlierFlag`

Fields: `metric_name` (str), `value` (float), `lower_fence` (float), `upper_fence` (float), `severity` (Literal["moderate", "extreme"]).

Properties: `is_low` (value below lower fence), `is_high` (value above upper fence).

#### Dataclass: `DemoQualityReport`

Fields: `demo_name` (str), `quality_score` (float in [0,1]), `tick_coverage` (float), `feature_completeness` (float), `outlier_flags` (list of OutlierFlag), `recommendation` (Literal["use", "review", "skip"]), `detail` (str).

#### Class: `DemoQualityScorer`

**Methods:**

**`score_demo(self, demo_name: str) -> DemoQualityReport`**
Computes a comprehensive quality report combining three phases:
1. Tick coverage (weighted 0.45).
2. Feature completeness (weighted 0.35).
3. Outlier penalty: `min(len(outlier_flags) * 0.1, 0.4)`, contributing `0.20 * (1.0 - penalty)`.

Recommendation logic: "use" if score >= 0.7 and no extreme outliers; "review" if score >= 0.4; else "skip".

**`score_demos_batch(self, demo_names: list[str]) -> list[DemoQualityReport]`**
Scores multiple demos, returns sorted by quality descending. Failed scores get a 0.0 report with "skip" recommendation.

**`_compute_tick_coverage(self, demo_name: str) -> float`**
Counts ticks via `SELECT COUNT(id)` from `PlayerTickState` where `demo_name` matches. Returns `tick_count / _EXPECTED_TICKS_PER_DEMO`, clamped to `[0, 1]`.

**`_compute_feature_completeness(self, demo_name: str) -> float`**
Samples up to 500 ticks, checks each tick's `_NONZERO_TICK_FIELDS` for non-zero values. Returns the fraction of non-zero values among all checks.

**`_detect_outliers(self, demo_name: str) -> list[OutlierFlag]`**
Loads ALL `PlayerMatchStats` to build reference distributions. Checks 5 metrics: `avg_kills`, `avg_deaths`, `avg_adr`, `kd_ratio`, `avg_kast`. Computes IQR fences using the full reference distribution, then checks whether the target demo's mean metric value falls outside moderate or extreme fences. Requires at least 10 reference rows. Returns a list of `OutlierFlag` objects.

---

### 1.7 `external_analytics.py`

**Path:** `Programma_CS2_RENAN/backend/processing/external_analytics.py`

**Purpose:** Compares user metrics against Top 100 professional and historical data from CSV datasets. Provides z-score analysis and tournament baselines.

#### Class: `EliteAnalytics`

**Constructor:** `__init__(self)` -- Loads 7 CSV datasets and calls `_prepare_data()`. Tracks `_loaded_dataset_count` for health checking.

**Methods:**

**`is_healthy(self) -> bool`**
R4-12-01: Returns `True` if at least one reference CSV was loaded with expected columns. Verifies that `players_df` has a `"CS Rating"` column (not just non-empty).

**`_read_safe(self, filename) -> pd.DataFrame`**
Reads a CSV from `data/external/` via `get_resource_path()`. Returns an empty DataFrame if the file does not exist.

**`_load_datasets(self)`**
Loads 7 CSVs: `top_100_players.csv`, `match_players.csv`, `maps_statistics.csv`, `weapons_statistics.csv`, `cs2_playstyle_roles_2024.csv`, `all_Time_best_Players_Stats.csv`, `tournament_advanced_stats.csv`. Drops rows with missing `Name` in players_df.

**`_prepare_data(self)`**
Calls `_prepare_players()`, `_prepare_historical()`, and `_prepare_tournament()`.

**`_prepare_players(self)`**
Cleans `"CS Rating"` column (strips commas, converts to numeric). Computes `Win_Rate = Wins / Total_Matches`.

**`_prepare_historical(self)`**
Processes columns `adr`, `deaths`, `kills`, `rating`, `hs` in `match_players_df` using `_process_historical_columns`. Computes `historical_stats` (mean) and `historical_std`.

**`_prepare_tournament(self)`**
Computes `tournament_baselines` and `tournament_stds` from `accuracy`, `econ_rating`, `utility_value` columns.

**`analyze_user_vs_elite(self, user_stats) -> dict`**
Returns `{"elite_rating_avg": ..., "z_scores": {...}, "tournament_z_scores": {...}}`. Guarded by `is_healthy()` and required columns check (P-EA-02).

**`_calc_z_scores(self, user_stats) -> dict`** / **`_calc_tournament_z(self, user_stats) -> dict`**
Delegate to module-level helper functions.

**`get_player_role(self, player_name) -> str`**
Matches player name (case-insensitive) against `roles_df` to return `role_overall`. Returns `"Unknown"` if not found.

**`get_tournament_baseline(self) -> dict`** / **`get_available_extra_datasets(self) -> list`**
Accessor methods for tournament baseline stats and loaded dataset names.

#### Module-level Helpers

**`_clean_cs_rating_col(df)`** -- Strips commas, converts to numeric, fills NaN with 0.

**`_process_historical_columns(df, avail)`** -- Extracts numeric values using regex that handles scientific notation (P-EA-03), fills NaN with 0.

**`_compute_z_scores(u_stats, h_stats, h_std) -> dict`** -- Computes z-scores for `adr` and `rating`. Uses `_MIN_STD = 1e-8` epsilon guard (P-EA-01). Skips non-finite user stats (R4-12-02).

**`_compute_t_z_scores(u_stats, t_base, t_std) -> dict`** -- Computes tournament z-scores for `accuracy` and `econ_rating` with the same guards.

---

### 1.8 `heatmap_engine.py`

**Path:** `Programma_CS2_RENAN/backend/processing/heatmap_engine.py`

**Purpose:** High-performance Gaussian Occupancy Map generator. Converts discrete event points into smooth density textures. Includes support for differential heatmaps comparing user vs pro positioning.

#### Dataclasses

**`HeatmapData`**: Container for heatmap RGBA data. Fields: `rgba_bytes` (bytes), `resolution` (int).

**`DifferentialHeatmapData`**: Container for differential heatmap data. Fields: `rgba_bytes` (bytes), `resolution` (int), `diff_matrix` (np.ndarray, repr suppressed), `hotspots` (list of dicts).

#### Class: `HeatmapEngine`

All methods are `@staticmethod`. Thread safety is documented: `generate_heatmap_data` and `generate_differential_heatmap_data` are thread-safe. `create_texture_from_data` and `generate_heatmap_texture` must be called from the main OpenGL thread.

**Methods:**

**`generate_heatmap_data(map_name, points, resolution=512, sigma=8.0) -> Optional[HeatmapData]`**
Thread-safe. Projects world coordinates to grid using map metadata. Uses `np.add.at` for atomic accumulation, applies `gaussian_filter(sigma)`, normalizes to [0,1], and produces RGBA bytes with a red intensity colormap and non-linear alpha ramp (hides values below 0.05, max alpha 200/255).

**`create_texture_from_data(data: HeatmapData)`**
Must run on OpenGL thread. Imports `kivy.graphics.texture.Texture`, creates a texture of the given resolution, and blits the RGBA buffer. Raises `RuntimeError` if Kivy is not installed.

**`generate_differential_heatmap_data(map_name, user_positions, pro_positions, resolution=512, sigma=8.0) -> Optional[DifferentialHeatmapData]`**
Thread-safe. Computes density grids for both user and pro positions, normalizes each to [0,1], then subtracts: `pro_density - user_density`. Uses a diverging colormap (red = pro-heavy, blue = user-heavy). Activity mask suppresses noise where neither density exceeds 0.02. Extracts hotspot regions. Alpha is proportional to absolute difference, capped at 180/255.

**`_extract_hotspots(diff, activity, meta, resolution, top_n=5) -> List[dict]`**
Identifies the top-N grid cells with largest absolute difference. Reverse-projects grid coordinates to approximate world coordinates. Skips spots with absolute difference < 0.05. Each hotspot dict contains: `world_x`, `world_y`, `diff_value`, `label` ("pro-heavy" or "user-heavy"), `magnitude`.

**`generate_heatmap_texture(map_name, points, resolution=512, sigma=8.0)`**
Convenience wrapper. Calls `generate_heatmap_data` then `create_texture_from_data`. Must run on OpenGL thread.

---

### 1.9 `player_knowledge.py`

**Path:** `Programma_CS2_RENAN/backend/processing/player_knowledge.py`

**Purpose:** Implements the Player-POV Perception System -- what a player KNOWS at each tick, respecting the same sensorial limitations as the real player. The AI coach learns with the player's perspective, NOT with wallhacks.

**Sensorial model:**
- Own state: full access.
- Teammates: always known (radar/comms).
- Visible enemies: ONLY when `enemies_visible > 0` AND within FOV cone.
- Last-known enemies: memory with exponential decay (half-life ~2.5s).
- Sound inference: weapon_fire events within hearing range.
- Utility zones: active smokes, molotovs, recent flashes.
- Bomb state: known to all.

#### Constants

| Constant | Value | Description |
|---|---|---|
| `HEARING_RANGE_GUNFIRE` | `2000.0` | World units within which gunfire is audible. |
| `MAX_TRACKED_ENEMIES` | `10` | P-PK-02: Hard cap on tracked enemies in memory dict. CS2 is 5v5 so max 5 enemies; 10 allows for edge cases. |
| `MEMORY_DECAY_TAU` | Imported from `core.constants` as `MEMORY_DECAY_TAU_TICKS` | Backward-compatible alias (M-08). |
| `MAX_HISTORY_TICKS` | `512` | RAP-M-10: Cap on history ticks traversed in `_build_enemy_memory`. Prevents O(N*E) blowup. |
| `SMOKE_RADIUS` | `200.0` | Approximate smoke cloud radius. |
| `FLASH_RADIUS` | `400.0` | Approximate flash effective blind radius. |
| `MOLOTOV_RADIUS` | `100.0` | Approximate molotov fire radius. |

Imported from `core.constants`: `FLASH_DURATION_TICKS`, `FOV_DEGREES`, `MEMORY_CUTOFF_TICKS`, `MEMORY_DECAY_TAU_TICKS`, `Z_FLOOR_THRESHOLD`.

#### Dataclasses

**`VisibleEntity`**: `pos_x`, `pos_y`, `pos_z`, `distance`, `is_teammate` (bool), `health` (int, default 100), `weapon` (str, default "").

**`LastKnownEnemy`**: `pos_x`, `pos_y`, `pos_z`, `decay_factor` (1.0=just seen, 0.0=forgotten), `ticks_since_seen` (int, default 0).

**`HeardEvent`**: `pos_x`, `pos_y`, `pos_z`, `distance`, `direction_rad` (radians from player), `event_type` (str, default "gunfire").

**`UtilityZone`**: `pos_x`, `pos_y`, `pos_z`, `radius`, `utility_type` (str: "smoke", "molotov", "flash").

**`PlayerKnowledge`**: The core output. 30+ fields organized by category:
- Own state: `own_pos_x/y/z`, `own_yaw`, `own_health`, `own_armor`, `own_weapon`, `own_team`, `is_crouching`, `is_scoped`, `is_blinded`.
- Teammates: `teammate_positions` (list of VisibleEntity), `teammates_alive` (int).
- Visible enemies: `visible_enemies` (list of VisibleEntity), `visible_enemy_count` (int).
- Last-known enemies: `last_known_enemies` (list of LastKnownEnemy).
- Sound: `heard_events` (list of HeardEvent).
- Utility: `utility_zones` (list of UtilityZone).
- Bomb: `bomb_planted`, `bomb_pos_x/y/z`.
- R4-14-01: `position_is_fallback` (bool, True when position is (0,0,0) fallback).

#### Geometry Helpers (private)

**`_normalize_angle(angle) -> float`** -- Normalizes to [0, 360).

**`_angle_diff(a, b) -> float`** -- Shortest angular difference in [0, 180].

**`_is_in_fov(player_x, player_y, player_yaw, target_x, target_y, fov_degrees=FOV_DEGREES, player_z=0.0, target_z=0.0, z_floor_threshold=Z_FLOOR_THRESHOLD) -> bool`**
Checks if target is within the player's FOV cone. H-11: Z-level guard prevents cross-floor visibility (Nuke, Vertigo). PROC-02: Rejects (0,0) fallback positions. Uses `atan2` for direction and handles yaw wraparound. Same-position targets are considered visible.

**`_distance_2d(x1, y1, x2, y2) -> float`** -- Standard 2D Euclidean distance.

**`_direction_rad(from_x, from_y, to_x, to_y) -> float`** -- Angle in radians from one point to another via `atan2`.

#### Class: `PlayerKnowledgeBuilder`

**Constructor:** Accepts `fov_degrees`, `hearing_range_gunfire`, `memory_decay_tau`, `memory_cutoff_ticks` (all defaulting to imported constants).

**Methods:**

**`build_knowledge(self, player_tick, all_players_at_tick, recent_player_history=None, recent_all_players_history=None, active_events=None) -> PlayerKnowledge`**
Master builder method. Constructs the complete `PlayerKnowledge` for one player at one tick:
1. Sets own state from `player_tick` attributes. P-PK-03: Flags (0,0,*) positions as likely missing data.
2. Classifies all players at the tick into teammates and enemies based on team.
3. Teammates are always known (radar/comms).
4. Visible enemies: only processed when `enemies_visible_count > 0` and player is not blinded. Filters by FOV (including Z-level per P-PK-01), sorts by distance, caps at `enemies_visible_count`. P-PK-04: Warns when FOV filter disagrees with game's visibility count.
5. Builds enemy memory from `recent_all_players_history` (if provided).
6. Builds sound events and utility zones from `active_events` (if provided).

**`_build_enemy_memory(self, knowledge, player_name, player_team, current_tick, recent_all_players_history)`**
Walks historical ticks (capped to `MAX_HISTORY_TICKS`) to find the most recent tick where each enemy was visible. Pre-indexes history for O(1) lookup. Evicts oldest entry if dict exceeds `MAX_TRACKED_ENEMIES` (P-PK-02). Converts to `LastKnownEnemy` with exponential decay: `decay = exp(-ticks_elapsed / memory_decay_tau)`. Skips enemies beyond `memory_cutoff_ticks` and currently visible enemies (ticks_elapsed <= 0).

**`_build_sound_events(self, knowledge, events, current_tick, tick_rate=64)`**
Filters events to audible types (`weapon_fire`, `he_detonate`, `flash_detonate`, `bomb_planted`). Only events within 1 second (computed as `tick_rate` ticks, P3-05) and within `HEARING_RANGE_GUNFIRE` distance are included. Computes direction angle from player to event source.

**`_build_utility_zones(self, knowledge, events, current_tick)`**
Identifies active smokes and molotovs (between start and end events). Handles `entity_id=-1` via position-based matching with 100-unit radius (R4-06-02). Time-based expiry: smokes max 18s, molotovs max 7s (C-10). Recent flashes within `FLASH_DURATION_TICKS` are also added to utility zones.

---

### 1.10 `rating.py`

**Path:** `Programma_CS2_RENAN/backend/processing/rating.py`

**Purpose:** Provides complementary rating metrics beyond HLTV Rating 2.0: PlusMinus (net frag differential per round with team contribution bonus) and Role-Adjusted Bayesian Rating (applies role-specific priors so each role is evaluated against its own baseline). KT-06 implementation.

#### Constants

**`ROLE_PRIORS`**: Dict mapping role names (`"awper"`, `"entry"`, `"support"`, `"lurker"`, `"igl"`) to dicts containing `kd_prior`, `kast_prior`, `adr_prior`, `weight`. Values calibrated from HLTV top-30 team averages (2024-2025 season data). Each role has `weight = 5.0`.

**`_DEFAULT_PRIOR`**: Fallback prior for unknown roles: `kd_prior=1.00`, `kast_prior=0.72`, `adr_prior=73.0`, `weight=3.0`.

**`_TEAM_CONTRIBUTION_SCALE`**: `0.10`. Multiplied by `(team_win_rate - 0.5)` for the team contribution bonus.

#### Functions

**`compute_plus_minus(player_stats: dict, team_round_wins: int, team_round_losses: int) -> float`**
Formula: `(kills - deaths) / max(rounds_played, 1) + team_contribution_bonus`. The team contribution bonus is `_TEAM_CONTRIBUTION_SCALE * (win_rate - 0.5)`, rewarding players on winning teams. Raises `KeyError` if `kills` or `deaths` missing.

**`compute_role_adjusted_rating(stats: dict, role: str, *, prior_override=None) -> float`**
Bayesian posterior point estimates per metric: `adjusted_m = (weight * prior_m + n * observed_m) / (weight + n)`, where `n` is `maps_played`. ADR normalized by dividing by 120. Composite: `0.40 * adj_kd + 0.35 * adj_kast + 0.25 * adj_adr_norm`. Typical range [0.3, 1.5] for pro-level players. Supports `prior_override` for testing.

---

### 1.11 `round_reconstructor.py`

**Path:** `Programma_CS2_RENAN/backend/processing/round_reconstructor.py`

**Purpose:** WR-76: Converts raw `PlayerTickState` data into structured human-readable timelines that the coaching LLM can narrate. Produces callout positions, weapon sequences, engagement timing, and health deltas as grounded facts.

#### Constants

| Constant | Value | Description |
|---|---|---|
| `_POSITION_SAMPLE_INTERVAL` | `256` | Ticks between position samples (~2 seconds at 128 tick/s). |
| `_SIGNIFICANT_MOVEMENT` | `400.0` | Minimum position change (world units) for meaningful movement. |
| `_MAX_TICKS_PER_ROUND` | `20_000` | Safety cap on ticks loaded per round. |
| `_TICK_RATE` | `128` | CS2 tick rate. |
| `_DATA_LIMITATIONS` | list of 5 strings | Explicit list of what tick data cannot tell us (voice comms, callouts, opponent intent, crosshair interpolation, audio cues). Included in every timeline. |
| `_WEAPON_DISPLAY` | dict | Maps ~35 raw weapon IDs to human-readable display names (e.g., `"weapon_ak47"` -> `"AK-47"`). |

#### Private Event Emitter Functions

Each function appends 0-1 `RoundEvent` to an `events` list based on a tick transition:

- **`_emit_round_start(events, first_tick, map_name)`** -- Emits starting position with callout and weapon.
- **`_emit_health_delta(events, prev, tick, map_name)`** -- Emits damage taken events.
- **`_emit_death(events, prev, tick, map_name)`** -- Detects death (alive -> dead transition).
- **`_emit_weapon_switch(events, prev, tick)`** -- Detects weapon changes while alive.
- **`_emit_engagement(events, prev, tick, map_name)`** -- Detects first sighting of enemies (0 -> N transition).
- **`_emit_bomb_action(events, prev, tick, map_name)`** -- Detects bomb plant transition.
- **`_emit_teammate_lost(events, prev, tick)`** -- Detects teammate count drop.
- **`_emit_enemy_eliminated(events, prev, tick, map_name)`** -- Detects enemy count drop.

#### Dataclasses

**`RoundEvent`**: `tick` (int), `time_in_round` (float, seconds), `event_type` (str), `description` (str, human-readable with callout names), `details` (dict).

**`RoundTimeline`**: Complete timeline for a player's round. Fields: `player_name`, `demo_name`, `round_number`, `map_name`, `side`, `outcome`, `survived`, `kills`, `deaths`, `damage_dealt`, `equipment_value`, `events` (list of RoundEvent), `summary` (str), `data_limitations` (list, defaults to `_DATA_LIMITATIONS`), `tick_count` (int).

Has a `format_for_llm() -> str` method that formats the timeline as a structured text block for LLM context injection, including the round header, summary, events with timestamps, and data limitations.

#### Class: `RoundReconstructor`

**Methods:**

**`reconstruct_round(self, demo_name, round_number, player_name, map_name=None) -> Optional[RoundTimeline]`**
Convenience wrapper for single-round reconstruction. Delegates to `reconstruct_rounds`.

**`reconstruct_rounds(self, demo_name, player_name, round_numbers, map_name=None) -> List[RoundTimeline]`**
Fetches all ticks for the player in the demo in one query (avoids N+1 pattern), partitions by round, and builds timelines. Auto-detects map_name from tick data if not provided. Falls back to `"de_unknown"` if undetectable.

**`_fetch_round_stats(self, session, demo_name, player_name, round_numbers) -> Dict[int, RoundStats]`** -- Fetches `RoundStats` keyed by round_number.

**`_fetch_ticks_by_round(self, session, demo_name, player_name, round_numbers) -> Dict[int, List[PlayerTickState]]`** -- Fetches ticks partitioned by round_number, ordered by tick, limited to `_MAX_TICKS_PER_ROUND * len(round_numbers)`.

**`_build_timeline(self, ticks, round_stats, player_name, demo_name, round_number, map_name) -> RoundTimeline`**
Core timeline construction. Processes ticks sequentially, calling event emitters for each transition. Position is sampled every `_POSITION_SAMPLE_INTERVAL` ticks for significant movement. Events are sorted by tick at the end. Summary is generated via `_build_summary`.

**`_build_summary(self, events, side, outcome, kills, deaths, survived) -> str`**
Generates a one-line summary from the event sequence (starting position, engagement count, kill count, outcome/death location).

#### Module Singleton

**`_reconstructor`**: Module-level singleton instance.

**`get_round_reconstructor() -> RoundReconstructor`**: Lazy singleton factory.

---

### 1.12 `round_stats_builder.py`

**Path:** `Programma_CS2_RENAN/backend/processing/round_stats_builder.py`

**Purpose:** Constructs per-round, per-player statistics from demo events. Bridges raw demo event data (`player_death`, `player_hurt`, `weapon_fire`, `round_end`, `player_blind`) into the `RoundStats` isolation layer. Wires trade kills, kill enrichment, and utility effectiveness into the aggregation pipeline (Fusion Plan Proposals 1-4).

#### Constants

| Constant | Description |
|---|---|
| `HE_WEAPONS` | `{"hegrenade", "weapon_hegrenade"}` |
| `FIRE_WEAPONS` | `{"inferno", "molotov", "incgrenade", "weapon_molotov", "weapon_incgrenade"}` |
| `SMOKE_WEAPONS` | `{"smokegrenade", "weapon_smokegrenade"}` |
| `FLASH_WEAPONS` | `{"flashbang", "weapon_flashbang"}` |
| `ALL_GRENADE_WEAPONS` | Union of all above sets. |
| `_DEFAULT_FLASH_ASSIST_WINDOW_TICKS` | `128` (2 seconds at 64 tick/s). P-RSB-01: This is a default; per-demo value is derived at runtime. |

Q1-03 design note: demoparser2 uses inconsistent weapon naming (`"hegrenade"` vs `"weapon_hegrenade"` depending on event type). Both forms are included.

#### Private Functions

**`_parse_events_safe(parser, event_name) -> pd.DataFrame`** -- Wraps `parser.parse_events()` with error handling. Returns empty DataFrame on failure.

**`_build_round_boundaries(round_end_df) -> List[Dict]`** -- Builds round metadata from `round_end` events. Returns list of dicts with `round_number`, `start_tick`, `end_tick`, `winner`. H-18: Uses `previous end_tick + 1` as start to prevent overlap. H-06: Validates completeness and detects inverted boundaries.

**`_assign_round(tick, boundaries) -> Optional[int]`** -- P-RSB-04: Returns `None` for ticks outside all boundaries (warmup/overtime) instead of silently attributing them to the last round.

**`_get_team_roster(parser) -> Dict[str, int]`** -- Gets player -> team_num mapping via `build_team_roster`.

**`_team_num_to_side(team_num, round_number) -> str`** -- Converts team_num to CT/T side, accounting for half-switch at round 13 (MR12 format).

**`compute_round_rating(stats: Dict) -> float`** -- Computes HLTV 2.0 rating for a single round using the unified `compute_hltv2_rating` function. Per-round values: KPR=kills, DPR=deaths, ADR=damage_dealt. KAST is 1.0 if player got a Kill, Assist, Survived, or was Traded.

**`_derive_flash_assist_window(parser) -> int`** -- P-RSB-01: Derives per-demo flash assist window from header `tick_rate`. P-RSB-05: Validates tick_rate to [32, 256]. Returns `tick_rate * 2` (2-second window).

**`_collect_player_names(deaths_df, team_roster) -> set`** -- P-RSB-02: Collects unique player names from death events and roster, excluding empty strings and roster entries with invalid team_num (0 = spectator).

**`_init_round_player_accumulators(boundaries, all_players, team_roster, demo_name) -> Dict[Tuple[int, str], Dict]`** -- Creates zeroed stat accumulators for every (round, player) pair. Includes 30+ fields: kills, deaths, assists, damage_dealt, headshot_kills, trade_kills, was_traded, trade_response_ticks_sum (GAP-03), trade_response_count, thrusmoke/wallbang/noscope/blind kills, opening_kill, opening_death, he_damage, molotov_damage, flashes_thrown, smokes_thrown, flash_assists, blind_time_on_enemies (Q1-01), enemies_blinded (set), equipment_value, round_won, mvp, kast, round_rating. P-RSB-02: Skips players without valid team assignment.

**`_process_death_events(deaths_df, boundaries, round_player_stats)`** -- Accumulates kills, deaths, assists, headshot/thrusmoke/wallbang/noscope/blind kill flags, and opening duels. P-RSB-04: Skips ticks outside round boundaries.

**`_process_damage_events(hurt_df, boundaries, round_player_stats)`** -- Accumulates damage_dealt, he_damage, and molotov_damage from `player_hurt` events.

**`_process_utility_throws(parser, boundaries, round_player_stats)`** -- Counts flash and smoke throws from `weapon_fire` events. Q1-04: Tries `user_name` then `player_name` as actor column.

**`_process_blind_events(parser, deaths_df, boundaries, team_roster, flash_assist_window, round_player_stats)`** -- Q1-01: Accumulates `blind_time_on_enemies` and `enemies_blinded` from `player_blind` events. Only ENEMY blinds are counted. Detects flash assists by cross-referencing blind events with deaths within the assist window.

**`_integrate_trade_kills(parser, round_player_stats)`** -- Integrates trade kill / was-traded flags from `analyze_demo_trades`. GAP-03: Captures response ticks for trade kills. Failures are logged and skipped (trade data is enrichment, not critical path).

**`_compute_kast_and_ratings(round_player_stats)`** -- Computes per-round KAST flag (Kill, Assist, Survived, or Traded) and HLTV 2.0 rating.

#### Public Functions

**`build_round_stats(parser, demo_name, team_roster=None) -> List[Dict]`**
Main orchestrator. Parses events, builds boundaries, collects players, initializes accumulators, then delegates to all `_process_*` functions and `_compute_kast_and_ratings`. Returns list of stat dicts.

**`aggregate_round_stats_to_match(round_stats, player_name) -> Dict`**
Aggregates per-round stats into match-level enrichment fields for `PlayerMatchStats`. Computes: `trade_kill_ratio`, `was_traded_ratio`, `avg_trade_response_ticks` (GAP-03), `thrusmoke_kill_pct`, `wallbang_kill_pct`, `noscope_kill_pct`, `blind_kill_pct`, `he_damage_per_round`, `molotov_damage_per_round`, `smokes_per_round`, `flash_assists`, `utility_blind_time`, `utility_enemies_blinded` (Q1-01 union across rounds), `opening_duel_win_pct`.

**`enrich_from_demo(demo_path, demo_name, target_player=None) -> Tuple[Dict[str, Dict], List[Dict]]`**
Bridge function connecting the round_stats_builder to the ingestion pipeline. Creates a `DemoParser`, builds round stats, and aggregates per player. Returns `(enrichment_by_player, round_stats)`.

---

### 1.13 `skill_assessment.py`

**Path:** `Programma_CS2_RENAN/backend/processing/skill_assessment.py`

**Purpose:** Decomposes player statistics into 5 axes (Mechanics, Positioning, Utility, Timing, Decision) and projects onto a 1-10 curriculum level. Extracted from `rap_coach/skill_model.py` during P9-01 consolidation.

#### Class: `SkillAxes`

Class-level string constants for the 5 axes: `MECHANICS = "mechanics"`, `POSITIONING = "positioning"`, `UTILITY = "utility"`, `TIMING = "timing"`, `DECISION = "decision"`.

**`all()` [classmethod]**: Returns list of all 5 axis strings.

#### Class: `SkillLatentModel`

All methods are `@staticmethod`.

**`calculate_skill_vector(stats: PlayerMatchStats) -> Dict[str, float]`**
Computes normalized skill scores (0.0-1.0) for each axis using Gaussian normalization (Z-score to percentile). Lazy-imports `get_pro_baseline`. For each metric:
1. Computes Z-score: `(val - baseline_mean) / baseline_std`.
2. Applies sigmoid approximation of Gaussian CDF: `1 / (1 + exp(-1.702 * z))` (P-SA-01: 1.702 is NOT GELU).
3. Clips to [0, 1].

Axis compositions:
- **Mechanics**: Mean of accuracy and avg_hs z-scores.
- **Positioning**: Mean of rating_survival and rating_kast.
- **Utility**: Mean of utility_blind_time and utility_enemies_blinded.
- **Timing**: Mean of opening_duel_win_pct and positional_aggression_score.
- **Decision**: Mean of clutch_win_pct and rating_impact.

P-SA-01-2: Skips metrics when std <= 0. If all axes are empty, returns all 0.5 with a warning.

**`get_curriculum_level(skill_vec: Dict[str, float]) -> int`**
Maps average skill score to 1-10 index: `round(avg_skill * 9) + 1`, clamped to [1, 10]. P-SA-02: Uses `round()` for more uniform distribution.

**`get_skill_tensor(skill_vec: Dict[str, float]) -> torch.Tensor`**
Converts 5-axis vector to a 10-dim one-hot tensor for RAPPedagogy: `tensor[0, level-1] = 1.0`.

---

### 1.14 `state_reconstructor.py`

**Path:** `Programma_CS2_RENAN/backend/processing/state_reconstructor.py`

**Purpose:** State Reconstruction Engine that converts database tick records into tensors for RAP-Coach. Uses the unified `FeatureExtractor` and `TensorFactory` for training/inference feature parity.

#### Class: `RAPStateReconstructor`

**Constructor:** `__init__(self, sequence_length=32, map_name="de_mirage", require_pov=False, tensor_config=None)`
- `sequence_length`: Window length for temporal perception.
- `metadata_dim`: Set to `METADATA_DIM` (25).
- `require_pov`: If `True`, raises `ValueError` when `knowledge=None` (prevents silent training/inference skew).
- P-SR-02: Accepts explicit `tensor_config` to avoid skew; creates a `TensorFactory` with it.

**Methods:**

**`reconstruct_belief_tensors(self, ticks: list[PlayerTickState], knowledge=None) -> dict`**
Translates a sequence of ticks into perception and metadata tensors.
1. R4-04-01: Raises `ValueError` if `require_pov=True` and `knowledge=None`.
2. C-01: Builds explicit context dicts from enriched `PlayerTickState` fields (time_in_round, bomb_planted, teammates_alive, enemies_alive, team_economy) to ensure features 20-24 are populated during training.
3. Uses `FeatureExtractor.extract_batch()` for metadata.
4. P-SR-01: Validates feature parity via `FeatureExtractor.validate_feature_parity()`.
5. Generates vision tensors via `TensorFactory.generate_all_tensors()`.
6. Returns dict with keys `"view"`, `"map"`, `"motion"`, `"metadata"`, each with batch dimension added.

**`segment_match_into_windows(self, match_ticks) -> list`**
Applies temporal windowing with 50% overlap. Step size is `sequence_length // 2`. Only full-length windows are included; trailing ticks are intentionally omitted.

---

### 1.15 `tensor_factory.py`

**Path:** `Programma_CS2_RENAN/backend/processing/tensor_factory.py`

**Purpose:** Converts game state data into PyTorch tensors for neural network consumption. Implements a NO-WALLHACK sensorial model. Three rasterizers: MapRasterizer, VisionRasterizer, MotionEncoder. Supports Player-POV mode (with `PlayerKnowledge`) and legacy mode (without).

#### Constants

| Constant | Value | Description |
|---|---|---|
| `OWN_POSITION_INTENSITY` | `1.5` | Own position marker brightness on map tensor. |
| `ENTITY_TEAMMATE_DIMMING` | `0.7` | Teammates rendered dimmer than enemies on view tensor. |
| `ENTITY_MIN_INTENSITY` | `0.2` | Minimum intensity for visible entities at max distance. |
| `ENEMY_MIN_INTENSITY` | `0.3` | Minimum intensity for visible enemies. |
| `BOMB_MARKER_RADIUS` | `50.0` | World-unit radius for bomb marker. |
| `BOMB_MARKER_INTENSITY` | `0.8` | Intensity of bomb marker circle. |
| `TRAJECTORY_WINDOW` | `32` | Number of ticks for trajectory trail (~0.5s at 64 tick/s). |
| `VELOCITY_FALLOFF_RADIUS` | `20.0` | Grid cells over which velocity gradient fades. |
| `MAX_SPEED_UNITS_PER_TICK` | `4.0` | CS2 max player speed per tick at 64 tick/s. F2-03: Known limitation on 128 tick demos. |
| `MAX_YAW_DELTA_DEG` | `45.0` | Maximum yaw delta per tick for normalization (flick threshold). |

**`_gaussian_filter`**: Module-level lazy import of `scipy.ndimage.gaussian_filter` (R4-02-03: avoids hard crash on minimal installs).

**`_get_gaussian_filter()`**: Lazy-loads and caches `gaussian_filter`.

#### Dataclasses

**`TensorConfig`**: `map_resolution=128`, `view_resolution=224`, `sigma=3.0`, `fov_degrees=90.0`, `view_distance=2000.0`.

**`TrainingTensorConfig(TensorConfig)`**: Overrides for training efficiency: `map_resolution=64`, `view_resolution=64`. F2-02: Note that the 128-dim output contract depends on `RAPPerception`'s `AdaptiveAvgPool2d` layer.

#### Class: `TensorFactory`

**Constructor:** `__init__(self, config=None)` -- Uses `TensorConfig()` defaults if `config` is `None`.

**Public Methods:**

**`generate_map_tensor(self, ticks, map_name="de_mirage", knowledge=None) -> torch.Tensor`**
Returns `(3, map_resolution, map_resolution)` tensor.
- **Player-POV mode** (knowledge provided): Ch0=teammates (radar/comms, own position at `OWN_POSITION_INTENSITY`); Ch1=enemies (visible=full, last-known=decayed); Ch2=utility zones + bomb overlay.
- **Legacy mode**: Ch0=enemies, Ch1=teammates, Ch2=player position. All channels go through Gaussian blur and normalization.
- P-X-02: Shape assertion on output.

**`generate_view_tensor(self, ticks, map_name="de_mirage", knowledge=None) -> torch.Tensor`**
Returns `(3, view_resolution, view_resolution)` tensor.
- **Player-POV mode**: Ch0=FOV mask; Ch1=visible entities (teammates dimmed, enemies at distance-weighted intensity); Ch2=active utility zones.
- **Legacy mode**: Ch0=FOV mask; Ch1=danger zones (uncovered FOV accumulated over last 8 ticks); Ch2=safe zones.
- P-X-02: Shape assertion on output.

**`generate_motion_tensor(self, ticks, map_name="de_mirage") -> torch.Tensor`**
Returns `(3, view_resolution, view_resolution)` tensor. Requires at least 2 ticks.
- Ch0: Trajectory trail (last `TRAJECTORY_WINDOW` positions, intensity proportional to recency).
- Ch1: Velocity radial gradient centered on player position, modulated by movement speed.
- Ch2: Crosshair movement (yaw delta magnitude as gaussian blob).
- Falls back to `_generate_legacy_motion` if no map metadata.
- P-X-02: Shape assertion on output.

**`generate_all_tensors(self, ticks, map_name="de_mirage", knowledge=None) -> Dict[str, torch.Tensor]`**
Returns dict with `"map"`, `"view"`, `"motion"` tensors.

**Private Methods (Player-POV):**

**`_generate_pov_map(self, knowledge, meta, resolution) -> torch.Tensor`** -- Implements Player-POV map tensor. Plots teammates (Ch0), visible + last-known enemies with decay (Ch1), utility + bomb (Ch2). Skips own position if `position_is_fallback`.

**`_generate_pov_view(self, knowledge, fov_mask, meta, resolution) -> torch.Tensor`** -- Implements Player-POV view tensor. Teammates always visible (dimmed), enemies only those in `knowledge.visible_enemies`, utility zones drawn as circles.

**Private Methods (Motion Sub-Channels):**

**`_build_trajectory_channel(self, ticks, meta, resolution) -> np.ndarray`** -- Plots last N positions with recency-proportional intensity and light blur.

**`_build_velocity_channel(self, curr_tick, prev_tick, meta, resolution) -> np.ndarray`** -- P-TF-03: Smooth fade-in ramp [0, 0.02] using quadratic ramp instead of hard 0.01 cutoff. Radial gradient centered on player with intensity modulated by normalized speed.

**`_build_crosshair_channel(self, curr_tick, prev_tick, meta, resolution) -> np.ndarray`** -- Encodes yaw delta as gaussian blob at player position. P-TF-03: Same smooth fade-in ramp. Handles yaw wraparound (>180 degrees).

**`_generate_legacy_motion(self, ticks, resolution) -> torch.Tensor`** -- Uniform scalar velocity encoding when map metadata is unavailable: Ch0=norm_dx, Ch1=norm_dy, Ch2=speed magnitude.

**Private Utility Methods:**

**`_world_to_grid(self, x, y, meta, resolution) -> Tuple[int, int]`** -- Converts world coordinates to grid coordinates. C-03: single Y-flip (meta.pos_y - y already inverts).

**`_normalize(self, arr) -> np.ndarray`** -- P-TF-01/M-10: When `max_val < _MIN_NORMALIZATION_THRESHOLD` (1.0), divides by threshold instead of max_val to avoid amplifying sparse noise to 1.0.

**`_draw_circle(self, channel, world_x, world_y, radius, meta, resolution, intensity=1.0)`** -- Draws a filled circle on a channel. P-TF-02: caps grid_radius to `resolution//2` to prevent oversized masks.

**`_generate_fov_mask(self, player_x, player_y, yaw, meta, resolution) -> np.ndarray`** -- Creates a cone-shaped FOV mask. P-TF-04: Uses configurable sigma for edge blur (not hardcoded 1.5).

#### Module Singleton

**`_factory_instance`**: Module-level singleton, protected by `_factory_lock` (threading.Lock).

**`get_tensor_factory() -> TensorFactory`**: Thread-safe double-checked locking singleton factory.

---

### 1.16 `tick_enrichment.py`

**Path:** `Programma_CS2_RENAN/backend/processing/tick_enrichment.py`

**Purpose:** Computes cross-player and contextual features not directly available from demoparser2's per-player tick data. These features close the training/inference skew for `METADATA_DIM` features 20-24 (time_in_round, bomb_planted, teammates_alive, enemies_alive, team_economy, enemies_visible, map_name).

#### Function: `enrich_tick_data`

**`enrich_tick_data(df_all_players, demo_path, tick_rate=64.0, map_name="de_unknown") -> pd.DataFrame`**

Takes raw tick data for ALL players (not just target) and computes features requiring knowledge of the full game state. Returns the input DataFrame with added columns. Pipeline:
1. **Round context**: Calls `extract_round_context` and `assign_round_to_ticks` to add `round_number` and `time_in_round`.
2. **Bomb state**: Via `_compute_bomb_state`.
3. **Alive counts**: Via `_compute_alive_counts`.
4. **Team economy**: Via `_compute_team_economy`.
5. **Enemies visible**: Via `_compute_enemies_visible`.
6. **Map name**: Propagated to every row.

#### Private Functions

**`_compute_bomb_state(df, bomb_events, round_ctx) -> pd.DataFrame`**
Computes per-tick `bomb_planted` boolean. Logic: becomes True at `bomb_planted` event tick, stays True until `bomb_defused` or new round starts. Uses an efficient sweep through sorted unique ticks to build a tick -> bomb_state mapping.

**`_compute_alive_counts(df) -> pd.DataFrame`**
Computes `teammates_alive` (count of alive same-team players excluding self) and `enemies_alive` (count of alive opposing-team players) for each player at each tick. Uses groupby aggregations. Falls back to 4 teammates and 5 enemies if `team_name` column is missing.

**`_compute_team_economy(df) -> pd.DataFrame`**
Computes `team_economy` as the sum of `balance` for all players on the same team at each tick. Falls back to 0 if `balance` or `team_name` columns are missing.

**`_compute_enemies_visible(df, fov_degrees=90.0, max_distance=4000.0) -> pd.DataFrame`**
C-02: Numpy-vectorized FOV computation. For each player at each tick, computes pairwise direction vectors, dot products with look direction, and arccos angles. Counts alive enemies on different teams within FOV half-angle and distance. Processes per-tick batches (~10 players per tick). Logs progress every 50,000 ticks. This is a simplified geometric check (no wall/raycast occlusion).

---

## 2. Feature Engineering Subpackage

### 2.1 `__init__.py`

**Path:** `Programma_CS2_RENAN/backend/processing/feature_engineering/__init__.py`

**Purpose:** Uses lazy imports via `__getattr__` to prevent `_modulelock` deadlocks when daemon threads (ingestion workers) import submodules while the Kivy UI thread is active. Python's import lock is not reentrant across threads.

**Mechanism:** Defines three frozen sets mapping attribute names to their source submodules:
- `_KAST_NAMES`: `calculate_kast_for_round`, `calculate_kast_percentage`, `estimate_kast_from_stats` -> `kast` module.
- `_ROLE_NAMES`: `PlayerRole`, `classify_role`, `extract_role_features`, `get_role_coaching_focus` -> `role_features` module.
- `_VECTORIZER_NAMES`: `DataQualityError`, `FeatureExtractor`, `FEATURE_NAMES`, `METADATA_DIM` -> `vectorizer` module.

**`__getattr__(name)`**: Checks each name set and imports from the appropriate submodule on demand. Raises `AttributeError` for unknown names.

**`__all__`**: Lists all 11 publicly exported names.

---

### 2.2 `base_features.py`

**Path:** `Programma_CS2_RENAN/backend/processing/feature_engineering/base_features.py`

**Purpose:** Aggregates per-round data into match-level statistics, including configurable heuristic thresholds (Task 6.3) and the unified HLTV 2.0 rating formula.

#### Dataclass: `HeuristicConfig`

Configurable heuristic thresholds. Each parameter documents its acceptable range and semantic purpose. 15 fields:

**Match analysis:**
- `impact_kill_threshold`: 1.0 (kills > this -> impact round). Range [0.5, 3.0].
- `impact_adr_threshold`: 100.0. Range [60.0, 150.0].

**Feature normalization bounds:**
- `health_max`: 100.0 (game constant).
- `armor_max`: 100.0 (game constant).
- `equipment_value_max`: 10000.0. Range [6000, 16000].
- `enemies_visible_max`: 5.0 (5v5 game constant).
- `pos_xy_extent`: 4096.0. Range [3500, 5000].
- `pos_z_extent`: 1024.0. Range [512, 2048].
- `pitch_max`: 90.0 (game constant).

**Round phase thresholds (equipment value breakpoints):**
- `round_phase_eco_threshold`: 1500.0.
- `round_phase_force_threshold`: 3000.0.
- `round_phase_full_threshold`: 4000.0.

**Model hyperparameters:**
- `context_gate_l1_weight`: 1e-4. Range [1e-6, 1e-2].

**Methods:** `to_dict()` (serialize to JSON-compatible dict), `from_dict(data)` (deserialize, ignoring unknown keys for forward compatibility).

#### Functions

**`load_learned_heuristics(config_path=None) -> HeuristicConfig`**
Loads heuristic config from a JSON file in `backend/storage/`. Falls back to defaults if file does not exist or parsing fails.

**`save_heuristic_config(config, config_path=None)`**
Persists heuristic config to JSON.

**`extract_match_stats(rounds_df, heuristics=None) -> dict`**
Aggregates per-round data into match-level statistics:
- Base stats: avg_kills, avg_deaths, avg_adr, avg_hs, avg_kast, kill_std, adr_std, kd_ratio.
- Opening duels: opening_duel_win_pct.
- Utility: utility_blind_time (sum), utility_enemies_blinded (mean).
- Clutches: clutch_win_pct.
- Positional aggression: positional_aggression_score.
- Accuracy: total_hits / total_shots.
- Econ rating: F2-28 fix -- `avg_adr / avg_money_per_round` (scale-invariant per round).
- Impact rounds: rounds exceeding configurable kill/ADR thresholds.
- HLTV 2.0 rating via unified `compute_hltv2_rating`, `compute_impact_rating`, `compute_survival_rating`.
- Default anomaly_score=0.0, sample_weight=1.0.

---

### 2.3 `kast.py`

**Path:** `Programma_CS2_RENAN/backend/processing/feature_engineering/kast.py`

**Purpose:** KAST (Kill, Assist, Survive, Trade) calculation -- a key CS2 performance metric representing the percentage of rounds where a player had a positive impact.

#### Functions

**`calculate_kast_for_round(player_name, round_events, trade_window_seconds=5.0, ticks_per_second=64) -> bool`**
Determines if a player achieved KAST in a single round. Processes `player_death` events:
- **K**: Player got a kill (attacker matches, victim is not self).
- **A**: Player got an assist.
- **S**: Player survived (no deaths recorded).
- **T**: Player was traded (their killer was killed within `trade_window_seconds`).

The `ticks_per_second` parameter should be read from the demo header (64 for matchmaking, 128 for FACEIT/ESEA). Omitting it at 128 ticks/s halves the trade window to ~2.5s.

**`calculate_kast_percentage(player_name, rounds_events, ticks_per_second=64) -> float`**
Computes KAST ratio (0.0-1.0) across multiple rounds by counting rounds where `calculate_kast_for_round` returns True.

**`estimate_kast_from_stats(kills, assists, deaths, rounds_played) -> float`**
Estimates KAST from aggregate stats when round-level data is unavailable. F2-35: 0.8 weight on assists assumes ~80% occur in rounds that already have a kill. Estimates trade probability at ~30% of deaths at pro level. Uses inclusion-exclusion approximation.

---

### 2.4 `rating.py`

**Path:** `Programma_CS2_RENAN/backend/processing/feature_engineering/rating.py`

**Purpose:** Unified HLTV 2.0 Rating Calculator. CRITICAL: All rating computations across the pipeline MUST go through this module to prevent Inference-Training Skew.

#### Constants

| Constant | Value | Description |
|---|---|---|
| `BASELINE_KPR` | `0.679` | Part of the reverse-engineered HLTV 2.0 formula (formula constant, not population mean). |
| `BASELINE_DPR_COMPLEMENT` | `0.317` | `1 - avg_DPR` baseline. |
| `BASELINE_KAST` | `0.70` | R3-01: formula constant, not population mean (which is ~0.74). |
| `BASELINE_IMPACT` | `1.0` | |
| `BASELINE_ADR` | `73.3` | |
| `HLTV2_COEFF_KAST` | `0.00738764` | Regression coefficient for KAST percentage. |
| `HLTV2_COEFF_KPR` | `0.35912389` | |
| `HLTV2_COEFF_DPR` | `-0.53295080` | |
| `HLTV2_COEFF_IMPACT` | `0.23726030` | |
| `HLTV2_COEFF_ADR` | `0.00323970` | |
| `HLTV2_INTERCEPT` | `0.15872723` | R-squared=0.995, RMSE=0.0046, MAE=0.0021 on 80/20 holdout. |

**CONTRACT**: `compute_hltv2_rating()` takes kast as RATIO (0.0-1.0). `compute_hltv2_rating_regression()` takes kast_pct as PERCENTAGE (0-100). Confusing these produces a ~100x error on the KAST term.

#### Functions

**`compute_impact_rating(kpr, avg_adr=0.0, dpr=None) -> float`**
Formula: `2.13*KPR + 0.42*AssistPR - 0.41*SurvivalPR`. Survival penalty applied only when `dpr` is provided. Without it, result is ~0.1-0.2 pts higher than the true impact.

**`compute_survival_rating(dpr) -> float`**
Simply returns `1.0 - dpr`.

**`compute_hltv2_rating(kpr, dpr, kast, avg_adr, impact=None) -> float`**
Normalizes each of 5 components against pro baselines: `(kill + survival + kast + impact + damage) / 5`. F2-40: This per-component average deliberately diverges from the regression formula (by design -- each term is independently interpretable).

**`compute_hltv2_rating_regression(kpr, dpr, kast_pct, avg_adr, impact=None) -> float`**
F2-39: DEAD CODE (never called in production). Retained for reference. Reproduces HLTV's published rating to +/-0.01 using regression coefficients. Includes a runtime guard that auto-converts ratio to percentage if kast_pct <= 1.0.

---

### 2.5 `role_features.py`

**Path:** `Programma_CS2_RENAN/backend/processing/feature_engineering/role_features.py`

**Purpose:** Role-based feature extraction for CS2 roles (Entry, AWPer, Support, Lurker, IGL). Classifies roles, extracts role-specific features for coaching, and generates role-appropriate comparisons against pro baselines.

F2-20 design note: Role signatures are static heuristics that do not automatically adapt to meta-shifts. Meta-level drift is tracked by `meta_drift.py`.

#### Constants

**`ROLE_SIGNATURES`**: Dict mapping `PlayerRole` enum values to stat profile dicts (opening_attempts_per_round, first_kill_pct, first_death_pct, kpr, adr, plus role-specific stats like awp_kills_pct, flash_assists, utility_damage, clutch_success_rate, late_round_kills_pct, trade_kill_pct). Based on analysis of top 20 HLTV players per role.

#### Functions

**`classify_role(player_stats: Dict[str, float]) -> Tuple[PlayerRole, float]`**
P3-04: Delegates to the canonical `RoleClassifier` which uses learned thresholds + neural consensus. Falls back to `_heuristic_classify_role` on any exception (P-RF-02 logs the reason).

**`_heuristic_classify_role(player_stats) -> Tuple[PlayerRole, float]`**
Fallback Euclidean-distance classifier using 5 classification features (`opening_attempts_per_round`, `first_kill_pct`, `first_death_pct`, `kpr`, `adr`). Normalizes player stats and signature values to [0,1] range. Confidence is `exp(-min_distance * 2)`. P3-09: Prevents division by near-zero range.

**`extract_role_features(player_stats, role=None) -> Dict[str, float]`**
Extracts role-specific features for coaching. If role is None, auto-detects via `classify_role`. For each stat in the role's baseline, computes percentage deviation, player value, and baseline value. Includes `detected_role` key.

**`get_adaptive_signatures(map_name=None) -> Dict[PlayerRole, Dict[str, float]]`**
R4-18-01: Returns role signatures adjusted by current meta drift. When drift > 0.3 (confidence_mult < 0.85), widens tolerance bands by scaling signature values UP (P-RF-01), making classification more conservative.

**`get_role_coaching_focus(role: PlayerRole) -> List[str]`**
Returns priority coaching areas for each role. Entry: first_kill_pct, opening_attempts, kpr, trade_death_pct. AWPer: awp_kills_pct, opening_kill_with_awp, first_death_pct, save_success_rate. Support: flash_assists, utility_damage, trade_kill_pct, kast. Lurker: clutch_success_rate, late_round_kills_pct, info_kills, survival_rate. IGL: kast, utility_usage_efficiency, trade_coordination, eco_round_performance.

---

### 2.6 `vectorizer.py`

**Path:** `Programma_CS2_RENAN/backend/processing/feature_engineering/vectorizer.py`

**Purpose:** Unified feature extraction module for RAP Coach. CRITICAL: Both Training (StateReconstructor) and Inference (GhostEngine) MUST use this single implementation. Changes to feature order or normalization MUST be made HERE ONLY.

#### Exception

**`DataQualityError`**: Raised when data quality falls below acceptable thresholds for training (P3-A: >5% NaN/Inf contamination rate).

#### Constants

| Constant | Value | Description |
|---|---|---|
| `METADATA_DIM` | `25` | Feature vector dimension -- contract with the neural network. |
| `_UNKNOWN_WEAPON_DEFAULT` | `0.5` | H-12: Sentinel for truly unknown weapons. |
| `_z_penalty_warned` | `False` | P-VEC-01: One-time warning flag for missing map_name. |
| `_nan_inf_clamp_count` | `0` | P-VEC-02: Counter for NaN/Inf occurrences for upstream bug visibility. |

**`FEATURE_NAMES`**: Tuple of 25 strings defining the canonical feature schema (P-X-01):
`health`, `armor`, `has_helmet`, `has_defuser`, `equipment_value`, `is_crouching`, `is_scoped`, `is_blinded`, `enemies_visible`, `pos_x`, `pos_y`, `pos_z`, `view_yaw_sin`, `view_yaw_cos`, `view_pitch`, `z_penalty`, `kast_estimate`, `map_id`, `round_phase`, `weapon_class`, `time_in_round`, `bomb_planted`, `teammates_alive`, `enemies_alive`, `team_economy`.

An assertion verifies `len(FEATURE_NAMES) == METADATA_DIM`.

**`WEAPON_CLASS_MAP`**: Dict mapping ~80+ lowercase weapon names to float categories: 0.0=knife (20+ knife skin variants), 0.05=special (taser, C4), 0.1=grenades/utility, 0.2=pistol (15 entries), 0.4=SMG (7 entries), 0.6=rifle (8 entries), 0.8=sniper (4 entries), 1.0=heavy (6 entries). Includes both internal names (`"ak47"`) and demoparser2 display names (`"ak-47"`).

#### Private Slot Fillers

Each helper mutates `vec` in place; slot indices MUST match `FEATURE_NAMES`:

**`_fill_vitals_movement(vec, get_val, cfg)`** -- Slots 0-7. Normalizes health/armor by config max. Helmet has fallback heuristic (armor>0). Flash_duration preferred over is_blinded for blinded detection.

**`_fill_awareness_position_view(vec, get_val, cfg) -> float`** -- Slots 8-14. Enemies_visible normalized. Position xyz normalized and clipped. R4-14-01: Warns on (0,0,0) positions. View angles use sin/cos encoding for yaw (avoids +/-180 discontinuity). Returns `pos_z` for downstream z_penalty computation.

**`_fill_z_penalty(vec, pos_z, map_name)`** -- Slot 15. Lazy-imports `compute_z_penalty` from `core.spatial_data`. P-VEC-01: Defaults to 0.0 with one-time warning when map_name unavailable.

**`_fill_round_metadata(vec, get_val, cfg, map_name)`** -- Slots 16-18. KAST from real data when available (defaults to 0.0). Map identity via `hashlib.md5` (deterministic, unlike Python's `hash()`). Round phase: 0.0=pistol (<1500), 0.33=eco (<3000), 0.66=force (<4000), 1.0=full_buy.

**`_fill_weapon_class(vec, get_val)`** -- Slot 19. Strips `weapon_` prefix. H-12: Distinguishes numeric entity handles (legacy ingestion) from genuinely unknown weapons. `0xFFFFFF` is CS2's "no weapon equipped" sentinel.

**`_fill_context_features(vec, get_val, context)`** -- Slots 20-24. Reads from tick_data first (enriched during ingestion), falls back to context dict (DemoFrame at inference). Normalizations: time_in_round/115.0, bomb_planted binary, teammates_alive/4.0, enemies_alive/5.0, team_economy/16000.0.

**`_finalize_vector(vec) -> np.ndarray`** -- P-VEC-02 / R4-14-02: Logs NaN/Inf at ERROR with feature-name attribution. Clamps using `np.nan_to_num(nan=0.0, posinf=1.0, neginf=-1.0)`. Thread-safe counter increment.

#### Class: `FeatureExtractor`

**Class Variables:**
- `_config`: ClassVar HeuristicConfig (default None). Thread-safe via `_config_lock` (RLock).

**Class Methods:**

**`configure(cls, config)`** -- Sets class-level HeuristicConfig (once at startup). Thread-safe.

**`update_heuristics(cls, new_config)`** -- Runtime hot-swap of heuristic parameters. Thread-safe.

**`extract_batch(cls, tick_data_list, map_name=None, contexts=None) -> np.ndarray`**
R4-14-03: Snapshots config at batch start to prevent mid-batch changes. P-VEC-03: Passes snapshotted config to each `extract()` call. P3-A: Quality gate -- refuses batches with >5% NaN/Inf contamination (raises `DataQualityError`). Returns shape `(N, METADATA_DIM)`.

**Static Methods:**

**`extract(tick_data, map_name=None, context=None, _config_override=None) -> np.ndarray`**
Core extraction method. Supports both dict and object attribute access via helper `get_val`. P-VEC-01: Auto-resolves `map_name` from tick_data when caller omits it. Calls all slot fillers in order, then `_finalize_vector`. Returns shape `(METADATA_DIM,)`.

**`get_feature_names() -> List[str]`** -- P-X-01: Delegates to canonical `FEATURE_NAMES`.

**`validate_feature_parity(vec, label="unknown")`** -- P-SR-01: Asserts last dimension matches `METADATA_DIM`. Raises `ValueError` on mismatch.

---

## 3. Baselines Subpackage

### 3.1 `__init__.py`

**Path:** `Programma_CS2_RENAN/backend/processing/baselines/__init__.py`

Empty file. Marks the `baselines` directory as a Python package.

---

### 3.2 `meta_drift.py`

**Path:** `Programma_CS2_RENAN/backend/processing/baselines/meta_drift.py`

**Purpose:** Meta-Drift Surveillance Engine. Tracks shifts in professional playstyles over time. If pros start playing differently, the Coach adjusts its certainty.

#### Class: `MetaDriftEngine`

All methods are `@staticmethod`.

**`calculate_spatial_drift(map_name: str) -> float`**
Pillar 2 - Phase 3 (100%): Compares pro positions in the last 30 days vs historical positions. Uses simplified centroid drift computation:
1. P3-30: Uses COUNT instead of fetching all IDs.
2. Queries recent and historical tick positions (sampled every 128th tick, limited to 50,000 per query).
3. F2-44: Filters incomplete/None tuples.
4. Computes centroid distance between recent and historical point clouds.
5. P-MD-01: Uses actual map dimensions from `get_map_metadata` when available; falls back to observed data spread.
6. Normalizes: 10% of map extent drift = 1.0 coefficient. Floor threshold = 500.0.

**`calculate_drift_coefficient(map_name=None) -> float`**
Returns value in [0.0 (Stable), 1.0 (Meta Chaos)]. Combines:
1. Statistical drift: Compares recent 30-day avg `rating_2_0` from `ProPlayerStatCard` vs historical avg. P-MD-02: Returns 0 if historical avg is near-zero. Normalized by 20% change = 1.0.
2. Spatial drift (if map provided).
3. P-MD-03: Weighted combination: `0.4 * stat_drift + 0.6 * spatial_drift` (spatial weighted higher because positioning changes reflect meta shifts faster). Without map: returns stat_drift only.

**`get_meta_confidence_adjustment(map_name=None) -> float`**
Returns a multiplier for Coach Confidence: `1.0 - (drift * 0.5)`. Range [0.5, 1.0].

---

### 3.3 `nickname_resolver.py`

**Path:** `Programma_CS2_RENAN/backend/processing/baselines/nickname_resolver.py`

**Purpose:** Resolves in-game player names from demos to official HLTV ProPlayer records. Handles variations like `"Spirit donk"`, `"s1mple-G2-"`, etc.

#### Class: `NicknameResolver`

**Class Constant:** `FUZZY_THRESHOLD = 0.8` -- Minimum similarity ratio for fuzzy matching.

**Static Methods:**

**`find_pro_player_id(raw_name: str) -> Optional[int]`**
Resolution priority:
1. **Exact match** (case-insensitive): Cleans both query and DB values via `_clean()`. PROC-03: Handles separators.
2. **Substring match**: `pro.nickname.lower() in clean_name.lower()`. F2-41: O(n) per query, acceptable for <1000 registered pros.
3. **Fuzzy match**: Via `_fuzzy_match` with 0.8 threshold.

**`_fuzzy_match(query, candidates, threshold=0.8) -> Optional[str]`**
Uses `difflib.SequenceMatcher` for Levenshtein-like similarity (Task 2.18.2). Returns best match above threshold or None.

**`_clean(name: str) -> str`**
Removes clan tags and special characters: strips `[]()-._` and whitespace via regex, returns lowercase.

---

### 3.4 `pro_baseline.py`

**Path:** `Programma_CS2_RENAN/backend/processing/baselines/pro_baseline.py`

**Purpose:** Provides professional player baseline statistics by fusing multiple data sources. Supports map-specific filtering and temporal baseline decay.

#### Constants

**`EXTERNAL_DATA_DIR`**: `os.path.join(BASE_DIR, "data", "external")`.

**`HARD_DEFAULT_BASELINE`**: Dict of 16 metrics with `{"mean": ..., "std": ...}` values: rating, kd_ratio, avg_kills, avg_deaths, avg_adr, avg_hs, avg_kast, accuracy, positional_aggression_score, utility_blind_time, utility_enemies_blinded, opening_duel_win_pct, clutch_win_pct, rating_impact, rating_survival, rating_kast.

#### Functions

**`get_pro_baseline(map_name=None) -> dict`**
Fuses all available sources (ascending priority -- later layers override earlier):
1. `HARD_DEFAULT_BASELINE` (guaranteed coverage).
2. External CSV file (`all_Time_best_Players_Stats.csv`).
3. Ingested pro demo `PlayerMatchStats` (real match data).
4. HLTV `ProPlayerStatCard` (scraped web data).

Result includes `_provenance` key showing sources used. Warns if only hard defaults are available.

**`_load_pro_from_db(map_name=None) -> Optional[dict]`**
Aggregates `ProPlayerStatCard` into a Gaussian baseline. R4-20-01: Streams results in batches of 500. Groups by player_id first to prevent high-volume players from dominating. P-PB-01: Skips K/D for near-zero deaths. P-PB-02: Linear approximation of survival (1-dpr), clamped to [0,1].

**`_load_pro_from_demo_stats(map_name=None) -> Optional[dict]`**
Computes baseline from ingested pro demo `PlayerMatchStats` (is_pro=True). Requires at least 10 records. Computes per-player averages first, then global mean/std (prevents high-volume players from dominating). Supports map-specific filtering via demo_name substring matching.

**`_load_pro_from_csv(path) -> Optional[dict]`**
P-PB-03: Dynamically maps CSV columns to baseline keys via `_CSV_COLUMN_MAP` (Rating1.0->rating, K/D->kd_ratio, ADR->avg_adr, etc.). Requires at least 2 data points per column. Merges with hard defaults for missing keys.

**`_get_default_pro_baseline() -> dict`**
Warns about degraded coaching quality and returns `HARD_DEFAULT_BASELINE` with `_provenance = "hard_default"`.

**`get_pro_positions(map_name, max_positions=10000) -> list[tuple[float, float]]`**
Retrieves aggregated (x,y) world-coordinate positions from pro match databases. Scans per-match SQLite files for `is_pro_match=True` on the requested map. Samples alive-player ticks every 64th tick. R4-20-01: Limits per-match to 5000 positions. Caps total via uniform sampling.

**`calculate_deviations(player_stats, baseline) -> dict`**
Computes Z-scores for player stats vs baseline. Returns dict mapping feature -> (z_score, raw_deviation). Handles div-by-zero (std <= 0 -> z_score = 0, raw_dev returned).

#### Class: `TemporalBaselineDecay`

Time-weighted pro baselines so recent stats carry more influence. WRAPS (not replaces) `get_pro_baseline()`.

**Class Constants:**
- `HALF_LIFE_DAYS`: `90.0` -- Weight halves every 90 days.
- `MIN_WEIGHT`: `0.1` -- Floor weight for very old data.
- `META_SHIFT_THRESHOLD`: `0.05` -- 5% change flags a meta shift.
- `BASELINE_METRICS`: List of 9 metric names to track.

**Methods:**

**`compute_weight(self, stat_date, reference_date=None) -> float`**
Exponential decay: `exp(-0.693 * age_days / HALF_LIFE_DAYS)`, floored at `MIN_WEIGHT`. Returns 1.0 for future dates.

**`compute_weighted_baseline(self, stat_cards) -> dict`**
Weighted average with temporal decay. For each metric, computes weighted mean and weighted standard deviation. Maps ProPlayerStatCard field names to baseline keys via `_metric_to_baseline_key`. Minimum std floored at 0.01.

**`get_temporal_baseline(self, map_name=None) -> dict`**
Gets a time-weighted baseline. Requires at least 10 stat cards. Merges temporal baseline with legacy baseline. Falls back to `get_pro_baseline` on any failure.

**`detect_meta_shift(self, old_baseline, new_baseline) -> List[str]`**
Compares two baseline epochs. Returns list of metric names that shifted by more than `META_SHIFT_THRESHOLD` (5%). Skips non-numeric entries and zero values.

**`_metric_to_baseline_key(metric) -> str` [static]**
Maps ProPlayerStatCard field names to baseline dict key names (e.g., `"rating_2_0"` -> `"rating"`, `"kpr"` -> `"avg_kills"`).

---

### 3.5 `pro_player_linker.py`

**Path:** `Programma_CS2_RENAN/backend/processing/baselines/pro_player_linker.py`

**Purpose:** Links `PlayerMatchStats.pro_player_id` to `ProPlayer.hltv_id` via `NicknameResolver`. Supports both retroactive backfill and per-ingestion linking.

#### Class: `ProPlayerLinker`

**Methods:**

**`link_player(self, player_name: str) -> Optional[int]`**
Resolves a single player name to `hltv_id` via `NicknameResolver.find_pro_player_id`. Returns None on failure.

**`backfill_all(self) -> Dict`**
Retroactive linkage of all `is_pro=True` records with `pro_player_id=NULL`. Idempotent: skips already-linked rows.
1. Gets distinct unlinked pro player names.
2. Resolves each via `NicknameResolver`.
3. Batch updates matched rows.
4. Returns `{"linked": int, "unresolved": int, "unresolved_names": list}`.

---

### 3.6 `role_thresholds.py`

**Path:** `Programma_CS2_RENAN/backend/processing/baselines/role_thresholds.py`

**Purpose:** Dynamic threshold storage for role classification. Thresholds are LEARNED from real data (HLTV, demos), NEVER hardcoded. Anti-Mock Principle: all thresholds start as None; if insufficient data, classifier returns UNKNOWN with 0% confidence.

#### Dataclass: `LearnedThreshold`

Fields: `value` (Optional[float], None = not yet learned), `sample_count` (int), `last_updated` (Optional[datetime]), `source` (str: "unknown", "hltv", "demo_parser", "ml_model").

#### Class: `RoleThresholdStore`

**Class Constant:** `MIN_SAMPLES_FOR_VALIDITY = 30` (P-PB-04: 30 samples gives <=8% std error in 75th-percentile estimates via bootstrap CI).

**Constructor:** Initializes 9 named thresholds, all in cold-start state: `awp_kill_ratio`, `entry_rate`, `assist_rate`, `survival_rate`, `solo_kill_rate`, `first_death_rate`, `utility_damage_rate`, `clutch_rate`, `trade_rate`.

**Methods:**

**`get_threshold(self, stat_name) -> Optional[float]`** -- Returns threshold value only if it has sufficient samples (>= `MIN_SAMPLES_FOR_VALIDITY`).

**`is_cold_start(self) -> bool`** -- True if fewer than 3 valid thresholds exist.

**`validate_consistency(self) -> bool`** -- R4-23-01: Validates all valid thresholds are in [0.0, 1.0].

**`get_readiness_report(self) -> Dict[str, Any]`** -- Debug report with cold_start status and per-threshold details.

**`learn_from_pro_data(self, pro_stats, known_roles=None)`**
Learns thresholds from real pro player statistics. P-RT-02: Counts unique players (not total data points) for sample_count. P-RT-01: Uses consistent 75th percentile for all role thresholds. Computes: awp_kill_ratio, entry_rate, assist_rate, survival_rate, solo_kill_rate.

**`persist_to_db(self, db_session)`** -- P-RT-03: Validates consistency before persisting. Uses `RoleThresholdRecord` ORM model.

**`load_from_db(self, db_session) -> bool`** -- Loads previously learned thresholds. Returns True if any were loaded.

#### Module Singleton

**`_threshold_store`**: Module-level singleton protected by `_threshold_store_lock` (threading.Lock).

**`get_role_threshold_store() -> RoleThresholdStore`**: P3-06: Thread-safe lazy singleton with double-checked locking.

---

## 4. Validation Subpackage

### 4.1 `__init__.py`

**Path:** `Programma_CS2_RENAN/backend/processing/validation/__init__.py`

Empty file. Marks the `validation` directory as a Python package.

---

### 4.2 `dem_validator.py`

**Path:** `Programma_CS2_RENAN/backend/processing/validation/dem_validator.py`

**Purpose:** Validates CS2/CSGO demo files before ingestion. Fail-fast validation hierarchy: file existence, size, magic number, game version, header completeness. Includes security checks.

#### Exception

**`DEMValidationError`**: Raised when DEM file validation fails.

#### Class: `DEMValidator`

**Class Constants:**

| Constant | Value | Description |
|---|---|---|
| `MIN_FILE_SIZE` | `100 * 1024` (100 KB) | Minimum acceptable file size. |
| `MAX_FILE_SIZE` | `800 * 1024 * 1024` (800 MB) | Maximum acceptable file size. |
| `CS2_MAGIC` | `b"PBDEMS2\x00"` | CS2 demo header magic number. |
| `CSGO_MAGIC` | `b"HL2DEMO\x00"` | CSGO demo header magic number. |
| `FORBIDDEN_CHARS` | `{";", "&", "|", "`", "$", "(", ")", "<", ">", "\\"}` | Characters forbidden in filenames (command injection prevention). F2-26: Backslash blocks shell escape sequences but does not affect Windows directory separators (applies only to `filepath.name`). |

**Methods:**

**`validate(self, filepath: Path) -> Tuple[bool, str, Optional[str]]`**
Returns `(is_valid, game_version, error_message)`. Runs checks in fail-fast order.

**`_check_filename_integrity(self, filepath)`** -- Sanitizes filename: rejects forbidden characters, hidden files (starting with `.`), and suspicious double extensions (e.g., `payload.sh.dem`).

**`_check_file_exists(self, filepath)`** -- Verifies file exists, is not a symlink (security), is a regular file, and is readable.

**`_check_file_size(self, filepath)`** -- Validates size within [MIN_FILE_SIZE, MAX_FILE_SIZE].

**`_detect_game_version(self, filepath) -> str`** -- Reads first 8 bytes and matches against CS2_MAGIC or CSGO_MAGIC. Returns `"CS2"` or `"CSGO"`.

**`_verify_header_completeness(self, filepath, version)`** -- Deep validation. CSGO: reads 16 bytes of metadata after magic. CS2: probes 512 bytes of protobuf header. Ensures the file is not a dummy with only a correct magic number.

**`estimate_processing_time(self, filepath) -> int`** -- Heuristic: ~1 second per 10 MB.

#### Convenience Function

**`validate_dem_file(filepath: str) -> Tuple[bool, str, Optional[str]]`** -- Creates a `DEMValidator` and validates. Also includes a `__main__` self-test block.

---

### 4.3 `drift.py`

**Path:** `Programma_CS2_RENAN/backend/processing/validation/drift.py`

**Purpose:** Feature drift detection using rolling Z-score distance. Two complementary monitors: `DriftMonitor` (match-aggregate stats) and `TickFeatureDriftMonitor` (25-dim tick-level features). Includes retraining recommendation logic.

#### Constants

| Constant | Value | Description |
|---|---|---|
| `_STD_EPSILON` | `0.01` | Minimum std used when past_std == 0. A tiny shift against a constant past = high z-score. |
| `DRIFT_FEATURES` | list | 5 match-aggregate features: `avg_adr`, `kd_ratio`, `impact_rounds`, `avg_hs`, `avg_kast`. DRIFT-01 note: NOT the 25-dim tick feature vector -- use `TickFeatureDriftMonitor` for that. |

#### Function: `detect_feature_drift`

**`detect_feature_drift(history: pd.DataFrame, window=10, z_threshold=2.5) -> dict`**
Detects drift using rolling Z-score. Requires at least `window * 2` history rows. Computes z-score per feature as `|recent_mean - past_mean| / past_std`. Returns dict mapping feature -> z-score.

#### Private Helpers

**`_process_feature_drift(feature, history, recent, past, drift_scores, z_threshold)`** -- Processes one feature. Uses `_STD_EPSILON` when past_std == 0.

**`_log_drift_warning(feature, z, threshold)`** -- Logs warning when z >= threshold.

#### Dataclass: `DriftReport`

Fields: `is_drifted` (bool), `drifted_features` (List[str]), `max_z_score` (float), `timestamp` (datetime).

#### Class: `DriftMonitor`

**Constructor:** `__init__(self, z_threshold=2.5)`.

**`check_drift(self, new_batch: pd.DataFrame, reference_stats: dict) -> DriftReport`**
Checks if new batch exhibits drift relative to reference statistics. Reference stats format: `{feature: {"mean": float, "std": float}}`. Uses `_STD_EPSILON` when ref_std is 0 or NaN. Returns structured `DriftReport`.

#### Class: `TickFeatureDriftMonitor`

Operates on the 25-dim tick-level feature vector the encoders actually consume. Complements `DriftMonitor` by measuring drift in model-input space per dimension.

**Constructor:** `__init__(self, z_threshold=2.5)`.

**`fit_reference(self, feature_matrix: np.ndarray, feature_names=None)`**
Stores per-dimension mean/std from training data. Requires 2D input `[N, D]`. Floors zero-std dims to `_STD_EPSILON`.

**`check_drift(self, new_batch: np.ndarray) -> DriftReport`**
Scores a batch of tick feature vectors against reference stats. Validates dimensions match. Returns `DriftReport` with per-dimension drift flags (using `feature_names` or `"dim_{i}"` when unnamed).

#### Function: `should_retrain`

**`should_retrain(drift_history: List[DriftReport], window=5) -> bool`**
Returns True if >= 3 of the last `window` reports indicate drift (prevents spurious triggers from single outlier batches).

---

### 4.4 `sanity.py`

**Path:** `Programma_CS2_RENAN/backend/processing/validation/sanity.py`

**Purpose:** Validates statistical plausibility of demo data. Supports both strict mode (raises errors) and trim mode (clamps outliers to valid boundaries).

#### Constants

**`LIMITS`**: Dict mapping column names to `(min, max)` bounds:
- `kills`: (0, 10)
- `deaths`: (0, 10)
- `assists`: (0, 10)
- `adr`: (0.0, 200.0)
- `headshot_pct`: (0.0, 100.0)
- `kast`: (0.0, 1.0) -- R4-24-04: stored as ratio, NOT percentage.

#### Functions

**`validate_demo_sanity(df: pd.DataFrame) -> None`**
Strict mode. Raises `ValueError` if any value is outside limits. Does NOT modify the DataFrame.

**`validate_and_trim(df: pd.DataFrame, strict=False) -> pd.DataFrame`**
Task 2.19.2: If `strict=True`, delegates to `validate_demo_sanity`. If `strict=False`, creates a copy and clamps outliers to boundaries. P-SAN-01: Detects KAST values > 1.0 (stored as percentage) and auto-converts to ratio.

**`_check_column_limits(df, column, limits) -> None`** -- Checks if column values are within limits using `between()`.

**`_raise_sanity_error(col, bad_rows) -> None`** -- Logs error and raises `ValueError`.

---

### 4.5 `schema.py`

**Path:** `Programma_CS2_RENAN/backend/processing/validation/schema.py`

**Purpose:** Validates structural integrity of demo parser output. Supports versioned schemas (Task 2.19.1) so the validator auto-adapts when the parser is updated.

#### Constants

| Constant | Value | Description |
|---|---|---|
| `SCHEMA_VERSION` | `2` | Current schema version. Increment when demo_parser.py adds new required columns. |
| `EXPECTED_SCHEMA` | dict | Version 1 columns: round (int), kills (int), deaths (int), assists (int), adr (float), headshot_pct (float), kast (float). |
| `SCHEMA_V2_EXTENSIONS` | dict | Version 2 additions: accuracy (float). |
| `_SCHEMA_REGISTRY` | dict | Maps version number to cumulative required columns. Version 1 = EXPECTED_SCHEMA. Version 2 = EXPECTED_SCHEMA + V2_EXTENSIONS. |

#### Functions

**`get_active_schema(version=None) -> dict`**
Returns the expected schema for a given version (defaults to latest). Falls back to latest if version is unknown.

**`validate_demo_schema(df: pd.DataFrame, version=None) -> None`**
Validates column existence and type compatibility. Checks that all required columns exist and are numeric. F2-48: For int columns, verifies no fractional values (bare `astype(int)` silently truncates floats, masking upstream parser bugs). Raises `ValueError` for missing columns and `TypeError` for type mismatches.

**`_validate_column_type(df, column, expected_type)`** -- Per-column type validation. For int columns, checks `mod(1) != 0` to detect non-integer floats.

---

## Cross-Cutting Design Patterns

### Training/Inference Parity

The most critical architectural constraint across this codebase is the prevention of training/inference skew. This is enforced through:

1. **Single source of truth for features**: `vectorizer.py`'s `FeatureExtractor` is the ONLY place where feature extraction is defined. Both `StateReconstructor` (training) and `GhostEngine` (inference) use it.
2. **Unified rating formula**: `feature_engineering/rating.py` is the ONLY place where HLTV 2.0 ratings are computed.
3. **Feature parity validation**: `FeatureExtractor.validate_feature_parity()` asserts dimension matches at both training and inference boundaries (P-SR-01).
4. **Config snapshotting**: `extract_batch()` snapshots the `HeuristicConfig` at batch start (R4-14-03) to prevent mid-batch changes.
5. **Context features 20-24**: `tick_enrichment.py` computes these during ingestion/training so they match what `GhostEngine` provides at inference via `DemoFrame`.

### Player-POV (NO-WALLHACK) Model

The system enforces a sensorial model where the AI coach sees only what the player legitimately knows:
- `player_knowledge.py` computes the perception state.
- `tensor_factory.py` rasterizes it into tensors with two modes (POV and legacy).
- `state_reconstructor.py` bridges the two, with `require_pov=True` preventing silent skew.

### Pro Baseline Fusion

Rather than a strict cascade, `pro_baseline.py` layers all available data sources (hardcoded -> CSV -> demo stats -> HLTV) so each contributes unique metrics and stronger data overrides weaker fallbacks. Temporal decay via `TemporalBaselineDecay` ensures recency matters.

### Robust Statistics

The codebase uses robust statistical methods throughout:
- IQR fencing for outlier detection (`demo_quality.py`, `data_pipeline.py`).
- Huber contamination model assumptions (`demo_quality.py`).
- Z-score drift detection with epsilon guards (`drift.py`, `external_analytics.py`).
- NaN/Inf clamping with upstream bug visibility (`vectorizer.py`).

### Thread Safety

Several modules implement thread-safe singletons:
- `TensorFactory` via double-checked locking with `threading.Lock`.
- `RoleThresholdStore` via double-checked locking.
- `FeatureExtractor._config` via `threading.RLock`.
- `HeatmapEngine` documents which methods are thread-safe vs OpenGL-thread-only.
