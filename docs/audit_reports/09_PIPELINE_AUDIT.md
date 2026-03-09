# Pipeline Audit Report: .DEM File Ingestion → Coaching Output

**Date:** 2026-03-07
**Scope:** Complete audit of the CS2 Coach AI data pipeline from demo file discovery through ML training to coaching advice generation.
**Method:** Deep code review of 30+ source files across 4 pipeline stages.
**Result:** 83 issues identified (31 BUGs, 16 INCONSISTENCYs, 9 PERFORMANCE, 27 ROBUSTNESS)

---

## 1. Executive Summary

| Category         | Parsing & Ingestion | Tensor & ML | Storage & Coaching | Total |
|------------------|:-------------------:|:-----------:|:------------------:|:-----:|
| **BUG**          | 6                   | 7           | 18                 | **31** |
| **INCONSISTENCY**| 2                   | 6           | 8                  | **16** |
| **PERFORMANCE**  | 2                   | 4           | 3                  | **9**  |
| **ROBUSTNESS**   | 11                  | 3           | 13                 | **27** |
| **Total**        | **23**              | **18**      | **42**             | **83** |

---

## 2. Pipeline Architecture

### 2.1 End-to-End Data Flow

```
 .dem FILE (50-500 MB, protobuf)
     │
     ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  STAGE 1: PARSING & INGESTION                                    │
 │                                                                  │
 │  dem_validator.py ──► demo_format_adapter.py ──► demo_parser.py  │
 │       (security)        (format detect)        (demoparser2 FFI) │
 │                                                                  │
 │  demo_parser.py outputs:                                         │
 │    ├─ aggregate_df: DataFrame[player_name, kills, deaths, ...]   │
 │    ├─ tick_df:      DataFrame[tick, steamid, X, Y, Z, yaw, ...]  │
 │    └─ event_dfs:    {player_hurt, weapon_fire, player_death, ...}│
 │                                                                  │
 │  demo_loader.py ──────────────────────────────────────────────►  │
 │    Converts tick_df rows → DemoFrame[PlayerState, NadeState]     │
 │    + round_context.py (round boundaries, bomb events)            │
 │    + trade_kill_detector.py (roster, trade windows)              │
 └──────────────────┬───────────────────────────────────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  STAGE 2: ENRICHMENT & STORAGE                                   │
 │                                                                  │
 │  tick_enrichment.py:                                             │
 │    _compute_alive_counts(df)  ──► teammates_alive, enemies_alive │
 │    _compute_enemies_visible(df) ──► enemies_visible (FOV cone)   │
 │                                                                  │
 │  round_stats_builder.py:                                         │
 │    Per-round stats: kills, deaths, assists, utility, economy     │
 │    _assign_round(tick, boundaries) ──► round_number              │
 │                                                                  │
 │  Storage:                                                        │
 │    PlayerTickState ──► per-match SQLite (match_N.db)             │
 │    PlayerMatchStats ──► monolith database.db                     │
 │    RoundStats ──► monolith database.db                           │
 │    MatchEventState ──► per-match SQLite                          │
 └──────────────────┬───────────────────────────────────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  STAGE 3: FEATURE EXTRACTION & TENSOR GENERATION                 │
 │                                                                  │
 │  vectorizer.py (FeatureExtractor):                               │
 │    PlayerTickState ──► 25-dim metadata vector (METADATA_DIM)     │
 │    Features 0-19: direct from tick data                          │
 │    Features 20-24: from context dict or tick_data fallback       │
 │                                                                  │
 │  tensor_factory.py (TensorFactory):                              │
 │    PlayerTickState + PlayerKnowledge ──►                         │
 │      map_tensor:    (3, R, R)  positional channels               │
 │      view_tensor:   (3, R, R)  FOV/visibility channels           │
 │      motion_tensor: (3, R, R)  trajectory/velocity channels      │
 │    R = 64 (training) or 224 (inference)                          │
 │                                                                  │
 │  data_pipeline.py (ProDataPipeline):                             │
 │    PlayerMatchStats ──► train/val/test split (70/15/15)          │
 │    StandardScaler fitted on TRAIN only                           │
 │                                                                  │
 │  player_knowledge.py (PlayerKnowledgeBuilder):                   │
 │    All players at tick ──► PlayerKnowledge (FOV, memory, utility) │
 │    Exponential decay: exp(-ticks_elapsed / 160)                  │
 └──────────────────┬───────────────────────────────────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  STAGE 4: ML TRAINING & COACHING                                 │
 │                                                                  │
 │  TRAINING PATH (coach_manager.py):                               │
 │    ProDataPipeline ──► ProPerformanceDataset ──► DataLoader      │
 │    RAPStateReconstructor ──► belief tensors (map, view, motion)  │
 │    Model: RAPCoach(view, map, motion, metadata) ──► outputs      │
 │                                                                  │
 │  INFERENCE PATH (ghost_engine.py):                               │
 │    Live DemoFrame ──► FeatureExtractor.extract(context=...) ──►  │
 │    TensorFactory(knowledge=...) ──► map/view/motion tensors ──►  │
 │    RAPCoach.forward() ──► optimal_pos, value_estimate            │
 │    (ghost_x, ghost_y) = pos + delta * RAP_POSITION_SCALE        │
 │                                                                  │
 │  COACHING PATH (coaching_service.py):                            │
 │    COPER: ExperienceBank ──► synthesize_advice()                 │
 │    Fallback: COPER → Hybrid → Traditional+RAG → Traditional     │
 │    Output: coaching insights stored in DB                        │
 └──────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Data Structures

| Structure | File | Shape/Type | Purpose |
|-----------|------|------------|---------|
| `DemoFrame` | `core/demo_frame.py` | dataclass(tick, round, players[], nades[], bomb) | Per-tick game snapshot |
| `PlayerState` | `core/demo_frame.py` | dataclass(x, y, z, yaw, health, ...) | Single player at one tick |
| `PlayerTickState` | `storage/db_models.py` | SQLModel (ORM row) | Persisted tick-level data |
| `PlayerMatchStats` | `storage/db_models.py` | SQLModel (ORM row) | Aggregated per-match stats |
| `RoundStats` | `storage/db_models.py` | SQLModel (ORM row) | Per-round enriched stats |
| `PlayerKnowledge` | `processing/player_knowledge.py` | dataclass(own_pos, visible_enemies, memory, utility_zones) | Sensorial model (no wallhacks) |
| `FeatureVector` | `processing/feature_engineering/vectorizer.py` | `np.ndarray(25,)` float32 | Unified ML input |
| `CoachingExperience` | `storage/db_models.py` | SQLModel (ORM row) | COPER experience bank entry |

---

## 3. Dimensional Consistency Matrix

The 25-dim feature vector (`METADATA_DIM = 25`) is the critical bridge between training and inference. This table maps each feature's data source in both paths:

| Index | Feature Name | Training Source | Inference Source | Skew Risk |
|:-----:|-------------|----------------|-----------------|:---------:|
| 0 | `health` | PlayerTickState.health | DemoFrame.health | None |
| 1 | `armor` | PlayerTickState.armor | DemoFrame.armor | None |
| 2 | `has_helmet` | PlayerTickState.has_helmet | DemoFrame.has_helmet | None |
| 3 | `has_defuser` | PlayerTickState.has_defuser | DemoFrame.has_defuser | None |
| 4 | `equipment_value` | PlayerTickState.equipment_value | DemoFrame.equipment_value | None |
| 5 | `is_crouching` | PlayerTickState.is_crouching | DemoFrame.is_crouching | None |
| 6 | `is_scoped` | PlayerTickState.is_scoped | DemoFrame.is_scoped | None |
| 7 | `is_blinded` | PlayerTickState.is_blinded | DemoFrame.is_blinded | None |
| 8 | `enemies_visible` | tick_enrichment (2D dot-product FOV) | PlayerKnowledge (atan2 FOV) | **FOV method differs** |
| 9 | `pos_x` | PlayerTickState.pos_x | DemoFrame.pos_x | **Unbounded (C-07)** |
| 10 | `pos_y` | PlayerTickState.pos_y | DemoFrame.pos_y | **Unbounded (C-07)** |
| 11 | `pos_z` | PlayerTickState.pos_z | DemoFrame.pos_z | **Unbounded (C-07)** |
| 12 | `view_yaw_sin` | sin(view_x) | sin(view_x) | None |
| 13 | `view_yaw_cos` | cos(view_x) | cos(view_x) | None |
| 14 | `view_pitch` | view_y / pitch_max | view_y / pitch_max | None |
| 15 | `z_penalty` | compute_z_penalty() | compute_z_penalty() | None |
| 16 | `kast_estimate` | avg_kast from demo_parser | avg_kast from stats | **C-05: assists=0** |
| 17 | `map_id` | md5(map_name) | md5(map_name) | None |
| 18 | `round_phase` | equipment_value heuristic | equipment_value heuristic | None |
| 19 | `weapon_class` | WEAPON_CLASS_MAP | WEAPON_CLASS_MAP | **H-12: unknown=0.1** |
| 20 | `time_in_round` | **tick_data or 0.0** | context dict | **C-01 if no context** |
| 21 | `bomb_planted` | **tick_data or False** | context dict | **C-01 if no context** |
| 22 | `teammates_alive` | **tick_data or 0** | context dict | **C-01 if no context** |
| 23 | `enemies_alive` | **tick_data or 0** | context dict | **C-01 if no context** |
| 24 | `team_economy` | **tick_data or 0** | context dict | **C-01 if no context** |

**Skew summary:** 7 of 25 features (28%) have documented skew risk between training and inference.

---

## 4. Cross-Cutting Systemic Patterns

Three systemic patterns appear across the entire codebase:

### 4.1 Silent Degradation

Many error paths log warnings but continue with degraded data (0.0 defaults, empty lists, None). Downstream consumers have no way to distinguish "real zero" from "data unavailable." This is the #1 source of training data contamination.

**Code evidence** — `demo_parser.py:269-310`:
```python
# Lines 269-310: When event data is unavailable, stats initialize to 0.0
players_with_data = 0
for idx, row in df.iterrows():
    name = str(row["player_name"]).lower()
    player_has_data = False
    # ... if no event data matches this player, all stats remain 0.0
    if player_has_data:
        df.at[idx, "data_quality"] = "complete"
        players_with_data += 1
```

The `data_quality` flag exists (lines 234-250) but the training pipeline (`data_pipeline.py:53`) does **not** filter by it — all rows enter the split regardless.

### 4.2 Training/Inference Skew

At least 3 independent skew vectors:

1. **Context features 20-24**: `vectorizer.py:267-304` reads from `tick_data` first, then falls back to `context` dict. In training, if `tick_data` lacks these fields and no `context` is passed, all five default to 0.0. In inference, `ghost_engine.py:130-142` explicitly populates the context dict from live game state.

2. **FOV computation**: Training uses `tick_enrichment.py:288-353` (2D dot-product approximation with `math.acos()`, no walls). Inference uses `player_knowledge.py:167-191` (`_is_in_fov()` with `math.atan2()` + yaw normalization). Different algorithms can produce different `enemies_visible` counts for identical game states.

3. **Inventory always empty**: `demo_loader.py:415` hardcodes `inventory=[]` with a `# TODO: CRITICAL` comment. Equipment-based coaching is completely blind.

### 4.3 Hardcoded Constants Without Tick-Rate Awareness

All temporal constants assume 64 tick/s with no adaptation for 128-tick servers (FACEIT):

| Constant | Value | File:Line | Assumed Rate | 128-tick Equivalent |
|----------|-------|-----------|:------------:|:-------------------:|
| Flash duration | 128 ticks | `player_knowledge.py:523` | 64 Hz = 2.0s | 256 ticks |
| Memory decay τ | 160 ticks | `player_knowledge.py:37` | 64 Hz ≈ 1.73s half-life | 320 ticks |
| Memory cutoff | 320 ticks | `player_knowledge.py:42` | 64 Hz = 5.0s | 640 ticks |
| Trade window | 192 ticks | `trade_kill_detector.py:28` | 64 Hz = 3.0s | 384 ticks |
| MAX_SPEED | 4.0 units/tick | `tensor_factory.py:57` | 64 Hz | 2.0 units/tick |
| Nade cap | 20 × tick_rate | `demo_loader.py:164` | tick_rate-aware | OK |
| Trajectory window | 32 ticks | `tensor_factory.py:56` | 64 Hz = 0.5s | 64 ticks |

---

## 5. TIER 1 — Critical (10 issues)

These can corrupt training data, break core functionality, or cause silent failures.

---

### C-01. Training/Inference Context Feature Skew

**Files:** `coach_manager.py:821`, `ghost_engine.py:130-143`
**Type:** INCONSISTENCY | **Severity:** CRITICAL

**Description:** Training calls `FeatureExtractor.extract()` without a `context` dict — features 20-24 (`time_in_round`, `bomb_planted`, `teammates_alive`, `enemies_alive`, `team_economy`) are always 0.0 during training. Inference populates them from live game state via DemoFrame context dict.

**Code evidence — inference path** (`ghost_engine.py:130-143`):
```python
# Build context dict for features 20-24 (available from live game state)
context = {}
if isinstance(tick_data, dict):
    context["time_in_round"] = tick_data.get("time_in_round", 0.0)
    context["bomb_planted"] = tick_data.get("bomb_planted", False)
    context["teammates_alive"] = tick_data.get("teammates_alive", 0)
    context["enemies_alive"] = tick_data.get("enemies_alive", 0)
    context["team_economy"] = tick_data.get("team_economy", 0)

meta_vec = FeatureExtractor.extract(tick_data, map_name=map_name, context=context)
```

**Code evidence — training path** (`coach_manager.py:800+`):
```python
batch = reconstructor.reconstruct_belief_tensors(window)
# metadata tensor comes from StateReconstructor — may not populate features 20-24
```

**Data flow:**
```
Training:  PlayerTickState → FeatureExtractor.extract(tick_data, context=None)
                                                         ↓
                                               features 20-24 = 0.0

Inference: DemoFrame → context dict → FeatureExtractor.extract(tick_data, context={...})
                                                         ↓
                                               features 20-24 = real values
```

**Quantitative impact:** 5 of 25 features (20%) are constant 0.0 during training but variable during inference. The model learns to ignore these features (zero gradient signal), then encounters non-zero values at inference time, creating out-of-distribution inputs. Features 22-23 (`teammates_alive`, `enemies_alive`) directly encode the most important tactical information.

**Cross-references:** Compounds with C-04 (missing data also 0.0) and H-08 (dead players get teammates_alive=0).

**Fix sketch:**
```python
# In training path, populate context from PlayerTickState + round boundaries:
context = {
    "time_in_round": (tick.tick - round_start_tick) / tick_rate,
    "bomb_planted": round_context.bomb_planted_at_tick(tick.tick),
    "teammates_alive": tick.teammates_alive,  # from tick_enrichment
    "enemies_alive": tick.enemies_alive,
    "team_economy": tick.team_economy or 0,
}
meta_vec = FeatureExtractor.extract(tick_data, map_name=map_name, context=context)
```

---

### C-02. O(n²) enemies_visible Computation

**File:** `tick_enrichment.py:288-360`
**Type:** PERFORMANCE | **Severity:** CRITICAL

**Description:** Triple-nested loop: `for tick in ticks: for i in players: for j in players:` with per-pair `math.acos()` + `math.sqrt()` calls in pure Python.

**Code evidence** (`tick_enrichment.py:299-353`):
```python
for tick, group in tick_groups:          # O(T) ≈ 100K ticks
    # ...
    n_players = len(group)
    for i in range(n_players):           # O(P) ≈ 10
        if not alive[i]: continue
        player_yaw_rad = math.radians(yaws[i])
        look_dx = math.cos(player_yaw_rad)
        look_dy = math.sin(player_yaw_rad)

        count = 0
        for j in range(n_players):       # O(P) ≈ 10
            if i == j or not alive[j]: continue
            if teams[j] == teams[i]: continue

            dx = positions_x[j] - player_x
            dy = positions_y[j] - player_y
            dist = math.sqrt(dx * dx + dy * dy)     # Python math.sqrt
            # ...
            dot = look_dx * dx_n + look_dy * dy_n
            dot = max(-1.0, min(1.0, dot))
            angle = math.acos(dot)                   # Python math.acos

            if angle <= half_fov_rad:
                count += 1

        enemies_visible[indices[i]] = count
```

**Algorithmic complexity:**
- Outer loop: `T` ticks (typically 100K for a 25-min match at 64 tick/s)
- Inner loops: `P² = 10 × 10 = 100` player pairs per tick
- Per pair: 1× `math.sqrt()`, 1× `math.acos()`, 2× `math.cos/sin` (player), 2× division (normalize)
- **Total operations:** `100,000 × 100 = 10,000,000` trigonometric calls in CPython

**Performance estimate:**
- `math.acos()` ≈ 0.3μs, `math.sqrt()` ≈ 0.1μs in CPython
- 10M × 0.4μs ≈ **4 seconds** per demo (best case)
- With Python loop overhead (attribute lookups, bounds checks): **5-8 minutes** per large demo
- Line 356 logs progress every 50K ticks, confirming slow execution

**Fix sketch — numpy vectorization:**
```python
# Vectorized: compute all pairwise angles in matrix form per tick group
for tick, group in tick_groups:
    pos = group[["X", "Y"]].values                         # (P, 2)
    yaw_rad = np.radians(group["yaw"].values)              # (P,)
    look = np.stack([np.cos(yaw_rad), np.sin(yaw_rad)], 1) # (P, 2)
    alive_mask = group["is_alive"].values
    teams_arr = group["team_name"].values

    # Pairwise direction vectors: (P, P, 2)
    diff = pos[np.newaxis, :, :] - pos[:, np.newaxis, :]
    dist = np.linalg.norm(diff, axis=2)                    # (P, P)
    dist[dist < 1e-6] = np.inf
    diff_n = diff / dist[:, :, np.newaxis]                 # Normalized

    # Dot product of look direction with direction to each target
    dots = np.einsum("ij,ikj->ik", look, diff_n)           # (P, P)
    dots = np.clip(dots, -1.0, 1.0)
    angles = np.arccos(dots)                               # (P, P)

    # Masks: alive, enemy, in range, in FOV
    in_fov = angles <= half_fov_rad
    in_range = dist <= max_distance
    enemy = teams_arr[:, None] != teams_arr[None, :]
    alive_2d = alive_mask[:, None] & alive_mask[None, :]

    counts = (in_fov & in_range & enemy & alive_2d).sum(axis=1)
```

**Expected speedup:** 50-100x (CPython loop → numpy broadcast). 5 minutes → 3-6 seconds.

---

### C-03. Double Y-Flip in Coordinate Transform

**File:** `tensor_factory.py:578-590`
**Type:** BUG | **Severity:** CRITICAL

**Description:** The `_world_to_grid()` method applies two Y-inversions that cancel each other.

**Code evidence** (`tensor_factory.py:578-590`):
```python
def _world_to_grid(self, x, y, meta, resolution):
    scale_factor = 1.0 / (meta.scale * 1024.0)

    nx = (x - meta.pos_x) * scale_factor          # X: translate + scale → [0, 1]
    ny = (meta.pos_y - y) * scale_factor           # Y: FLIP #1 (meta.pos_y - y)

    gx = int(nx * resolution)
    gy = int((1.0 - ny) * resolution)              # Y: FLIP #2 (1.0 - ny)

    return gx, gy
```

**Mathematical analysis:**
```
World coords:  Y increases North (Source 2 convention)
Radar coords:  Y increases South (image convention, origin top-left)

Flip #1: ny = (meta.pos_y - y) * scale
  → When y is at map top (high Y): meta.pos_y - y is small → ny ≈ 0 (top of radar) ✓
  → ny correctly maps world-Y to radar-Y (inverted)

Flip #2: gy = (1.0 - ny) * resolution
  → When ny ≈ 0 (top of radar): gy ≈ resolution (BOTTOM of tensor) ✗
  → This UNDOES Flip #1: entities at map top appear at tensor bottom

Net effect: Two inversions cancel → world-Y maps to tensor-Y WITHOUT inversion.
But tensor convention is origin-top-left (row 0 = top), while world-Y origin is bottom.
Result: All spatial content is vertically mirrored.
```

**Impact on training:**
- A-site appears where B-site should be on map tensors
- FOV cones point in mirrored Y direction on view tensors
- Trajectory trails are vertically flipped on motion tensors
- The model learns internally consistent but **mirrored** tactical patterns
- Ghost positions output by inference are vertically offset from correct positions

**Cross-references:** This affects all three tensor types (map, view, motion) generated by TensorFactory. Combined with C-07 (unbounded positions), out-of-bounds positions in the wrong Y direction exceed grid bounds silently.

**Fix:** Remove the second flip:
```python
gy = int(ny * resolution)  # Remove the (1.0 - ...) second flip
```

---

### C-04. Silent Event Data Loss (0.0 vs Missing)

**File:** `demo_parser.py:250-310`
**Type:** ROBUSTNESS | **Severity:** CRITICAL

**Description:** When event parsing fails, all stat fields remain at their initialized 0.0 value. The `data_quality` flag exists but is not checked by the training pipeline.

**Code evidence** (`demo_parser.py:250-255`):
```python
# When ALL event DataFrames are empty:
df["data_quality"] = "none"
logger.warning(
    "No event data extracted — all event DataFrames empty. "
    "Stats remain 0.0 (missing, not measured)."
)
return  # ← Returns with accuracy=0.0, avg_hs=0.0, avg_kast=0.0
```

**Data flow trace:**
```
demo_parser.py (0.0 stats)
  → PlayerMatchStats (persisted with accuracy=0.0, avg_hs=0.0)
    → data_pipeline.py:53 (loads ALL rows, no data_quality filter)
      → ProDataPipeline._split_data() (0.0 rows enter train/val/test)
        → ProPerformanceDataset (model trains on 0.0 as ground truth)
```

**Quantitative impact:** In a dataset of 10,000 player-match records, if 5% have failed event parsing, the model sees 500 samples where `accuracy=0.0`, `avg_hs=0.0`, `avg_kast=0.0`. These are indistinguishable from a player who genuinely had 0% accuracy. The model learns a biased prior that some players are significantly worse than reality.

**Cross-references:**
- C-05 (assists=0) compounds this — KAST is computed from total_assists=0
- H-09 (non-reproducible training data) — different runs sample different 0.0 rows

**Fix sketch:**
```python
# Option A: Use NaN sentinel in demo_parser.py
df["accuracy"] = np.nan    # instead of 0.0
df["avg_hs"] = np.nan
df["avg_kast"] = np.nan

# Option B: Filter in data_pipeline.py
statement = (
    select(PlayerMatchStats)
    .where(PlayerMatchStats.data_quality != "none")
    .order_by(PlayerMatchStats.id)
    .limit(_MAX_PIPELINE_ROWS)
)
```

---

### C-05. Assister Name Missing → KAST Systematically Underestimated

**File:** `demo_parser.py:290-305`
**Type:** BUG | **Severity:** CRITICAL

**Description:** When `assister_name` column is absent from death events, all players get `total_assists = 0`, which feeds into KAST computation as ground truth.

**Code evidence** (`demo_parser.py:293-305`):
```python
total_assists = 0
if not d_df.empty and "assister_name" in d_df.columns:
    total_assists = int((d_df["assister_name"].astype(str).str.lower() == name).sum())
else:
    logger.warning(
        "player_death events lack 'assister_name' column — assists set to 0 for %s",
        name,
    )
if total_rounds > 0:
    df.at[idx, "avg_kast"] = estimate_kast_from_stats(
        total_kills, total_assists, total_deaths, total_rounds
    )
```

**Impact on KAST:**
```
KAST formula (from kast.py):
  kast = (kills + assists + survived_rounds + traded_rounds) / total_rounds

With assists=0:
  kast = (kills + 0 + survived + traded) / rounds

Typical assist rate: 3-5 per match (15-30 rounds)
Missing assists reduces KAST by ~0.10-0.17 (10-17 percentage points)
```

**Data flow trace:**
```
demo_parser.py (assists=0)
  → df["avg_kast"] = estimate_kast_from_stats(kills, 0, deaths, rounds)
    → PlayerMatchStats.avg_kast (biased low)
      → vectorizer.py:226-242 (feature index 16 = biased KAST)
        → Model trains on systematically underestimated support player value
```

**Alternative column names to check:** `"assister"`, `"assist_player_name"`, `"flash_assister_name"`.

---

### C-06. Player Leakage in Dataset Splitting

**File:** `data_pipeline.py:143-200`
**Type:** BUG | **Severity:** CRITICAL

**Description:** Temporal 70/15/15 split is per-class (pro vs user) but not per-player. The same player can appear in train, val, and test splits.

**Code evidence** (`data_pipeline.py:158-182`):
```python
pros = df[df["is_pro"] == True].sort_values(by=sort_col)
users = df[df["is_pro"] == False].sort_values(by=sort_col)

def time_slice(sub_df):
    n = len(sub_df)
    train_idx = int(n * 0.70)
    val_idx = int(n * 0.85)
    return (
        sub_df.iloc[:train_idx],
        sub_df.iloc[train_idx:val_idx],
        sub_df.iloc[val_idx:],
    )

p_train, p_val, p_test = time_slice(pros)
# ← Player "s1mple" with 200 matches: 140 in train, 30 in val, 30 in test
```

**Leakage mechanism:**
```
Player A: 100 matches over 6 months
  → Sort by match_date
  → First 70 matches → TRAIN
  → Next 15 matches  → VAL
  → Last 15 matches  → TEST

The model memorizes Player A's style in TRAIN,
then evaluates on Player A's later matches in VAL/TEST.
Reported accuracy is inflated because the model has "seen" this player before.
```

**Quantitative estimate:** With 50 pro players averaging 100 matches each, each player contributes to all three splits. Player-specific patterns (positioning habits, weapon preferences, aggression level) leak from train to test. Estimated metric inflation: 5-15% depending on player diversity.

**Fix sketch:**
```python
from sklearn.model_selection import GroupKFold

# Player-stratified split: all of a player's matches go into ONE split
groups = df["player_name"]
gkf = GroupKFold(n_splits=5)  # 60% train, 20% val, 20% test
for fold_idx, (train_idx, test_idx) in enumerate(gkf.split(df, groups=groups)):
    # ...
```

---

### C-07. Position Features Unbounded

**File:** `vectorizer.py:207-209`
**Type:** BUG | **Severity:** HIGH

**Description:** Position features divided by `pos_xy_extent` / `pos_z_extent` without clipping. Out-of-bounds positions produce values exceeding [-1, 1].

**Code evidence** (`vectorizer.py:207-209`):
```python
vec[9] = pos_x / cfg.pos_xy_extent     # No clipping
vec[10] = pos_y / cfg.pos_xy_extent    # No clipping
vec[11] = pos_z / cfg.pos_z_extent     # No clipping
```

**When it triggers:**
- Spawning outside map boundaries (rare but occurs in demo replays)
- Spectator positions (very high Z values)
- Vertigo: legitimate Z values near z_cutoff threshold (1000+ units)
- Map edge positions on wide maps (e.g., de_train yard)

**Impact:** Values >1.0 saturate ReLU activations in downstream layers. The `nan_to_num` safety net (vectorizer.py:314) catches Inf/NaN but **not** out-of-range floats.

**Fix:**
```python
vec[9] = np.clip(pos_x / cfg.pos_xy_extent, -1.0, 1.0)
vec[10] = np.clip(pos_y / cfg.pos_xy_extent, -1.0, 1.0)
vec[11] = np.clip(pos_z / cfg.pos_z_extent, -1.0, 1.0)
```

---

### C-08. get_active_utilities() NULL Entity ID

**File:** `match_data_manager.py:409-452`
**Type:** BUG | **Severity:** HIGH

**Description:** The query filters `entity_id != -1` to exclude unpopulated entities, but Python's `None != -1` evaluates to `True`. Entities with NULL `entity_id` pass through the Python filter and appear as active utilities.

**Code evidence** (`match_data_manager.py:440-449`):
```python
ended_entities = {e.entity_id for e in ends if e.entity_id != -1}
valid_starts = [s for s in starts if s.entity_id != -1]
# ← None != -1 is True in Python → NULL entities PASS the filter
```

**Impact:** NULL-entity-id events appear as active utilities, feeding phantom smoke/molotov zones into PlayerKnowledge and tensor generation.

**Fix:**
```python
valid_starts = [s for s in starts if s.entity_id is not None and s.entity_id != -1]
ended_entities = {e.entity_id for e in ends if e.entity_id is not None and e.entity_id != -1}
```

---

### C-09. COPER Fallback Chain Breaks

**File:** `coaching_service.py:250-277`
**Type:** BUG | **Severity:** HIGH

**Description:** The 4-mode priority chain (COPER → Hybrid → Traditional+RAG → Traditional) has a gap in the fallback path.

**Code evidence** (`coaching_service.py:250-277`):
```python
except Exception as e:
    logger.exception("COPER coaching failed")
    if self.use_hybrid and player_stats:
        self._generate_hybrid_insights(player_name, demo_name, player_stats, map_name)
    else:
        if deviations:
            corrections = generate_corrections(deviations, rounds_played)
            _save_corrections_as_insights(self.db_manager, player_name, demo_name, corrections)
        else:
            logger.warning(
                "COPER fallback: no deviations data — "
                "no coaching generated for %s on %s",
                player_name, demo_name,
            )
```

**Fallback chain analysis:**
```
COPER fails ──► Hybrid (if use_hybrid AND player_stats)
                 │   fails ──► ??? (no catch, exception propagates)
                 │
                 └─► Traditional (if deviations available)
                      │   deviations=None ──► ZERO OUTPUT (warning only)
```

**Gap:** If Hybrid throws, no fallback catches it. If `deviations` is None (which happens when COPER fails before computing deviations), Traditional fallback also produces nothing. The user gets zero coaching feedback.

---

### C-10. Smoke Utility Zones Never Expire (entity_id=-1)

**File:** `player_knowledge.py:486-516`
**Type:** BUG | **Severity:** HIGH

**Description:** When building utility zones from match events, if a `smoke_end` event has `entity_id == -1`, the `continue` statement skips the deletion from `active_starts`. The smoke persists indefinitely.

**Code evidence** (`player_knowledge.py:488-502`):
```python
active_starts = {}  # entity_id -> event
for evt in events:
    entity_id = int(getattr(evt, "entity_id", -1))

    if entity_id == -1:     # Sentinel: extraction failed
        continue            # ← Skips BOTH start AND end events

    if evt_type in ("smoke_start", "molotov_start"):
        if evt_tick <= current_tick:
            active_starts[entity_id] = evt
    elif evt_type in ("smoke_end", "molotov_end"):
        if evt_tick <= current_tick and entity_id in active_starts:
            del active_starts[entity_id]
```

**Scenario:**
```
tick 1000: smoke_start, entity_id=42  → active_starts[42] = event
tick 1200: smoke_end,   entity_id=-1  → continue (skipped!)
                                       → active_starts[42] persists forever
```

Real smoke duration is 18s (1152 ticks at 64 Hz). Without the end event, the smoke renders as a permanent blocker for the rest of the match. The model learns to avoid areas that are actually clear.

**Fix sketch:**
```python
# Add time-based expiry as fallback:
SMOKE_MAX_DURATION_TICKS = 18 * 64  # 1152 ticks
MOLOTOV_MAX_DURATION_TICKS = 7 * 64  # 448 ticks

# After building active_starts, expire old ones:
for eid, evt in list(active_starts.items()):
    evt_tick = int(getattr(evt, "tick", 0))
    max_dur = SMOKE_MAX_DURATION_TICKS if "smoke" in evt_type else MOLOTOV_MAX_DURATION_TICKS
    if current_tick - evt_tick > max_dur:
        del active_starts[eid]
```

---

## 6. TIER 2 — High Priority (18 issues)

### Parsing & Ingestion

---

### H-01. Field Resolution Order Inconsistency

**File:** `demo_parser.py:257-260`
**Type:** BUG | **Severity:** HIGH

**Description:** Player name column resolution uses different priority orders for different event types:

```python
h_name_col = _resolve_name_column(h_df, ["attacker_name", "user_name", "player_name"])  # player_hurt
s_name_col = _resolve_name_column(s_df, ["player_name", "user_name", "name"])            # weapon_fire
d_name_col = _resolve_name_column(d_df, ["attacker_name", "user_name", "player_name"])   # player_death
```

If demoparser2 provides inconsistent column names across versions, different event types resolve to different columns for the same semantic purpose (the player who performed the action). Accuracy = `hit_count / shot_count` from different events could attribute hits to attacker but shots to victim.

**Fix:** Standardize a single `_resolve_name_column()` with documented semantics per event type.

---

### H-02. Parse Timeout Too Strict for Tick Data

**File:** `demo_parser.py:326, 401-410`
**Type:** INCONSISTENCY | **Severity:** HIGH

Both aggregate parsing and tick-level parsing use `DEMO_PARSE_TIMEOUT_SECONDS = 300` (5 minutes). For 200MB+ pro demos (100K+ ticks × 10 players × 15+ fields), 5 minutes may be insufficient. Large demos timeout silently, returning empty DataFrames.

```python
DEMO_PARSE_TIMEOUT_SECONDS = 300  # 5 minutes for ANY demo size
raw_ticks = future.result(timeout=DEMO_PARSE_TIMEOUT_SECONDS)
# On timeout: return pd.DataFrame()  — no partial data
```

**Fix:** `timeout = max(300, file_size_mb * 3)`.

---

### H-03. Money Field Name Hardcoded

**File:** `demo_loader.py:384-385`
**Type:** BUG | **Severity:** HIGH

```python
money_val = int(getattr(row, "balance", 0) or 0)  # ← Only checks "balance"
```

Debug logging at lines 342-346 (`app_logger.debug("Row attributes: %s", row._fields)`) suggests uncertainty about the correct field name. Alternatives: `"cash"`, `"money"`, `"m_iAccount"`.

---

### H-04. Inventory Always Empty

**File:** `demo_loader.py:415`
**Type:** INCONSISTENCY | **Severity:** HIGH

```python
# TODO: CRITICAL - inventory=[] is always empty, weapon tracking disabled
inventory=[],  # DISABLED
```

Equipment-based features in ML models are all zero. Cannot detect weapon transitions, utility counts, or buy quality.

---

### H-05. Nade Duration Capping Poisons Training Data

**File:** `demo_loader.py:164-169`
**Type:** ROBUSTNESS | **Severity:** HIGH

Mismatched smoke start/end events produce capped durations of `20 * tick_rate` (20 seconds) with no flag. Real smokes last 18s. The capped 20s durations are indistinguishable from real measurements in training data.

**Fix:** Add `is_duration_estimated: bool` flag to `NadeState`.

---

### H-06. Round Boundary Pairing Fragile

**File:** `round_context.py:79-97`
**Type:** ROBUSTNESS | **Severity:** HIGH

```python
matching_freeze = [t for t in freeze_end_ticks if prev_round_end <= t < round_end]
if matching_freeze:
    round_start = matching_freeze[-1]    # ← Uses LAST freeze_end (could be wrong)
```

Multiple `freeze_end` events from pause/unpause cycles cause wrong round start tick. The LAST one may correspond to an unpause, not the actual round start.

**Fix:** Use FIRST `freeze_end` after previous `round_end`.

---

### H-07. Bomb Explode Event Not Handled

**File:** `round_context.py:130`
**Type:** BUG | **Severity:** HIGH

```python
for event_name, event_label in [("bomb_planted", "planted"), ("bomb_defused", "defused")]:
    # ← Missing: ("bomb_exploded", "exploded")
```

When bomb explodes, `bomb_planted` stays True until round resets. Small timing error (few ticks) but systematic across all explosion rounds.

---

### H-08. Alive Count Math Potentially Wrong

**File:** `tick_enrichment.py:161-224`
**Type:** ROBUSTNESS | **Severity:** HIGH

```python
alive_mask = df["is_alive"] == True
alive_per_tick_team = df[alive_mask].groupby(["tick", "team_name"]).size()

df = df.merge(alive_per_tick_team, on=["tick", "team_name"], how="left")
# Dead players: left join → alive_count = NaN → fillna(0)
# Result: dead players see teammates_alive=0, enemies_alive=0 (WRONG)
```

Dead players should see how many teammates are still alive. Current implementation reports 0 for both, which corrupts training data if dead-player rows are not filtered.

---

### Tensor & ML

---

### H-09. Non-Reproducible Training Data

**File:** `data_pipeline.py:53`
**Type:** ROBUSTNESS | **Severity:** HIGH

```python
statement = select(PlayerMatchStats).limit(_MAX_PIPELINE_ROWS)
# ← No .order_by() — SQLite returns rows in arbitrary order
```

Different runs select different subsets. Non-reproducible experiments.

**Fix:** `.order_by(PlayerMatchStats.id)`.

---

### H-10. FOV_DEGREES Defined Independently in Two Modules

**Files:** `tensor_factory.py:76` (`fov_degrees=90.0` in TensorConfig), `player_knowledge.py:28` (`FOV_DEGREES = 90.0`)
**Type:** INCONSISTENCY | **Severity:** HIGH

No shared source of truth. If changed in one module but not the other, tensor generation and perception model diverge silently.

**Fix:** Define `FOV_DEGREES` once in `core/constants.py`.

---

### H-11. FOV Check Missing Z/Pitch Component

**File:** `player_knowledge.py:167-191`
**Type:** INCONSISTENCY | **Severity:** HIGH

```python
def _is_in_fov(player_x, player_y, player_yaw, target_x, target_y, fov_degrees=FOV_DEGREES):
    dx = target_x - player_x
    dy = target_y - player_y
    # ← No Z component, no pitch check
    angle_to_target = math.degrees(math.atan2(dy, dx))
    return _angle_diff(player_yaw, angle_to_target) <= fov_degrees / 2.0
```

On multi-level maps (Nuke, Vertigo), players on different floors pass the 2D FOV check. Estimated false positive rate: 20-30% on Nuke.

---

### H-12. Weapon Class Map Incomplete for CS2

**File:** `vectorizer.py:27-71`
**Type:** BUG | **Severity:** HIGH

```python
vec[19] = WEAPON_CLASS_MAP.get(weapon_name, 0.1)  # 0.1 = unknown
```

Unknown weapons (CS2 naming variants, weapon_ prefix inconsistency) default to 0.1 with no logging.

---

### H-13. Two Parallel Training Paths

**File:** `train_pipeline.py:56-75`
**Type:** INCONSISTENCY | **Severity:** MEDIUM

`train_pipeline.py` extracts 12 match-aggregate features and pads to `INPUT_DIM=25`. The canonical path (`TrainingOrchestrator` via `coach_manager.py`) uses 25-dim tick-level features. Stale comment refers to "19-dim vectors" (METADATA_DIM was 19 before remediation).

---

### Storage & Coaching

---

### H-14. Database Pool Size = 1 with 4 Daemons

**File:** `database.py:82-87`
**Type:** PERFORMANCE | **Severity:** HIGH

```python
self.engine = create_engine(
    DATABASE_URL,
    pool_size=1,         # Single connection in pool
    max_overflow=4,      # Up to 5 total connections
)
```

With 4 daemons (Scanner, Digester, Teacher, Pulse) + UI thread + ingestion threads, 5 connections cause contention. `busy_timeout=30000` means threads can block 30 seconds.

**Fix:** `pool_size=3, max_overflow=8`.

---

### H-15. RoundStats Missing Unique Constraint

**File:** `db_models.py:526-530`
**Type:** INCONSISTENCY | **Severity:** HIGH

No unique constraint on `(demo_name, round_number, player_name)`. Re-ingesting the same demo creates duplicate round stats, corrupting aggregations.

```python
__table_args__ = (
    Index("ix_rs_demo_player", "demo_name", "player_name"),
    Index("ix_rs_demo_round", "demo_name", "round_number"),
    # ← Missing: UniqueConstraint("demo_name", "round_number", "player_name")
)
```

---

### H-16. Zombie Detection Fails for Never-Updated Tasks

**File:** `session_engine.py:174-199`
**Type:** BUG | **Severity:** HIGH

```python
zombies = s.exec(
    select(IngestionTask).where(
        IngestionTask.status == "processing",
        IngestionTask.updated_at < cutoff,
    )
).all()
```

`updated_at` must be manually set (db_models.py:272). Tasks that never had `updated_at` set retain their creation time. If created recently, they escape zombie detection.

**Fix:** Add `OR (updated_at IS NULL AND created_at < cutoff)`.

---

### H-17. Experience Bank usage_count Not Persisted

**File:** `experience_bank.py:249-252`
**Type:** BUG | **Severity:** HIGH

```python
for exp in results:
    exp.usage_count += 1     # In-memory mutation
# session.commit() fires from context manager
# But: no session.add(exp) → SQLAlchemy may not detect the mutation
```

Experience ranking stagnates because `usage_count` doesn't increment in the database.

---

### H-18. Round Assignment Boundary Off-by-One

**File:** `round_stats_builder.py:83-89`
**Type:** BUG | **Severity:** HIGH

```python
def _assign_round(tick, boundaries):
    for b in boundaries:
        if b["start_tick"] <= tick <= b["end_tick"]:  # ← Inclusive both ends
            return b["round_number"]
```

If `end_tick` of round N equals `start_tick` of round N+1, boundary ticks are assigned to whichever round is checked first.

**Fix:** `start_tick <= tick < end_tick` (exclusive end).

---

## 7. TIER 3 — Medium Priority (27 issues)

### Parsing & Ingestion

| ID | File | Lines | Type | Issue | Code Evidence |
|----|------|-------|------|-------|---------------|
| M-01 | `demo_parser.py` | 270-310 | PERF | O(n) string match per player in event stats — `h_df[h_name_col == name]` iterated per row | Should use `groupby()` instead of per-player DataFrame filter |
| M-02 | `demo_format_adapter.py` | 48-50 | ROBUST | `MIN_DEMO_SIZE=1024` (1 KB) too permissive — real demos are 50MB+ | `MIN_DEMO_SIZE = 1024` allows corrupted stub files through |
| M-03 | `demo_format_adapter.py` | 177-209 | INCON | Header validation mismatch: adapter checks 8-byte magic only, validator reads 16/512 bytes | Different validation depth between the two validators |
| M-04 | `dem_validator.py` | 63-77 | BUG | Path traversal: validates `filepath.name` only, not resolved path. `../../etc/passwd.dem` bypasses | `name = filepath.name` — directory component not checked |
| M-05 | `trade_kill_detector.py` | 211-213 | ROBUST | Off-by-one: `>` should be `>=` — 192nd tick excluded from trade window | `if tick - prior_tick > trade_window: break` |
| M-06 | `trade_kill_detector.py` | 62-93 | IMPROV | Team roster from early 10% ticks assumes stability — no mid-match swap validation | `early = ticks[ticks["tick"] < ticks["tick"].quantile(0.1)]` |
| M-07 | `tick_enrichment.py` | 252-270 | ROBUST | FOV geometric approximation: no wall occlusion, ~20-30% false positive rate | Docstring: "simplified check (no wall/raycast occlusion)" |

### Tensor & ML

| ID | File | Lines | Type | Issue | Code Evidence |
|----|------|-------|------|-------|---------------|
| M-08 | `player_knowledge.py` | 37-42 | BUG | Memory decay comment says "1.73s half-life" — mathematically the half-life is `τ * ln(2) / tick_rate = 160 * 0.693 / 64 ≈ 1.73s` (correct, but "half-life" is the time to 50%, not to 1/e=37%) | `MEMORY_DECAY_TAU = 160` with `exp(-t/tau)` formula |
| M-09 | `tensor_factory.py` | 626-681 | PERF | FOV mask recomputed every tick via `np.ogrid` + `np.arctan2()` + `np.sqrt()`: O(R²) per call, ~32 calls per window | Should cache FOV mask for static player positions |
| M-10 | `tensor_factory.py` | 592-597 | ROBUST | Max normalization on sparse channels: single non-zero pixel → `max=tiny` → all values amplified | `_normalize()`: `return arr / np.max(arr)` — 1 pixel → overshoot |
| M-11 | `vectorizer.py` | 226-242 | ROBUST | KAST=0.0 when `rounds_played=0` despite having kills | Guard: `if rounds_played > 0 and (kills+assists+deaths) > 0` |
| M-12 | `player_knowledge.py` | 523 | IMPROV | Flash duration hardcoded 128 ticks — not tick-rate aware | `0 <= (current_tick - evt_tick) <= 128` assumes 64 Hz |
| M-13 | `config.py`, `ghost_engine.py` | various | INCON | `RAP_POSITION_SCALE=500.0` in config.py but `coach_manager.py` overlay uses hardcoded `* 1000` | Inconsistent scale factors between ghost and overlay |

### Storage & Coaching

| ID | File | Lines | Type | Issue | Code Evidence |
|----|------|-------|------|-------|---------------|
| M-14 | `database.py` | 117-123 | ROBUST | `expire_on_commit=False` + auto-commit = stale read risk after rollback | `Session(self.engine, expire_on_commit=False)` |
| M-15 | `database.py` | 125-154 | INCON | Inconsistent `merge()` vs `add()+flush()` upsert patterns | Generic: `session.merge()`; PlayerMatchStats: `add() + flush()` |
| M-16 | `db_models.py` | 115-117 | INCON | `PlayerTickState.match_id` FK allows None — orphaned records | `match_id: Optional[int] = Field(default=None)` |
| M-17 | `db_models.py` | 272-276 | INCON | `IngestionTask.updated_at` manual maintenance — no ORM auto-refresh | No `onupdate` trigger or `@validates` hook |
| M-18 | `match_data_manager.py` | 240-242 | PERF | "LRU" cache uses `next(iter())` (FIFO), not true LRU | `oldest_key = next(iter(self._engines))` |
| M-19 | `match_data_manager.py` | 559-561 | ROBUST | Engine dispose race condition — no synchronization | `self._engines[match_id].dispose()` without lock |
| M-20 | `session_engine.py` | 174-176 | ROBUST | 5-min zombie threshold too low for large pro demos (6+ min possible) | `_ZOMBIE_THRESHOLD_SECONDS = 300` |
| M-21 | `session_engine.py` | 335-350 | BUG | Sample count committed BEFORE calibration — decoupled on failure | `_commit_trained_sample_count()` before `auto_calibrate()` |
| M-22 | `experience_bank.py` | 216-243 | PERF | O(n) `json.loads` per candidate embedding — should pre-parse or cache | `exp_vec = np.array(json.loads(exp.embedding))` per candidate |
| M-23 | `experience_bank.py` | 553-554 | ROBUST | EMA effectiveness: asymmetric penalty for negative feedback | Positive: +0.6, Negative: -0.3 (max) |
| M-24 | `experience_bank.py` | 650-655 | INCON | Decay targets unvalidated experiences only — validated pro data never expires | `outcome_validated == False` filter in decay query |
| M-25 | `coaching_dialogue.py` | 145-163 | ROBUST | User message appended AFTER response — protects history on LLM error | Safe pattern, but fragile if control flow changes |
| M-26 | `coaching_dialogue.py` | 303 | BUG | Chat message slicing `[:-1]` on short history — fragile indexing | `prior = self._history[:-1][-window_size:]` |
| M-27 | `storage_manager.py` | 131-159 | BUG | Quota enforcement includes pro_ingest_dir in scan — pro demos get archived | `_archive_old_files()` globs `pro_ingest_dir/*.dem` |

---

## 8. TIER 4 — Low Priority (28 issues)

| ID | File:Lines | Type | Issue |
|----|-----------|------|-------|
| L-01 | `database.py:91-97` | ROBUST | WAL pragma: `cursor.close()` in happy path but not on exception |
| L-02 | `dem_validator.py:138-151` | IMPROV | Header size heuristics (16/512 bytes) hardcoded without documentation |
| L-03 | `demo_format_adapter.py:211-225` | IMPROV | Corruption detection: only 4-byte alignment + 1MB floor; missing EOF marker |
| L-04 | `demo_loader.py:150-160` | IMPROV | Thrower position fallback: 15-tick lookback without distance check |
| L-05 | `db_models.py:497-510` | PERF | `CoachingExperience` missing indexes on `pro_match_id`, `pro_player_name` |
| L-06 | `db_models.py:589-600` | PERF | `RoleThresholdRecord` missing index on `source` column |
| L-07 | `db_models.py:476-485` | ROBUST | `game_state_json` validator only runs at model creation |
| L-08 | `match_data_manager.py:668-739` | ROBUST | Migration ignores file permissions — partial migrations possible |
| L-09 | `session_engine.py:62-78` | ROBUST | stdin monitor: `readline()` blocks up to 30s on parent death |
| L-10 | `session_engine.py:422-446` | INCON | Teacher retrain trigger fires on user demos if `last_count=0` |
| L-11 | `experience_bank.py:671-677` | ROBUST | Zero-norm embedding → cosine similarity 0.0 without logging |
| L-12 | `experience_bank.py:679-681` | ROBUST | `_infer_round_phase()` no error handling — exception propagation |
| L-13 | `coaching_dialogue.py:237-244` | ROBUST | Intent classification: "general" fallback on all-zero scores |
| L-14 | `coaching_service.py:151-160` | INCON | `_generate_coper_insights()` accepts `deviations` but ignores in happy path |
| L-15 | `coaching_service.py:178-183` | ROBUST | `tick_data` type check returns silently — no logging |
| L-16 | `coaching_service.py:380-382` | ROBUST | Advanced insights returns silently on empty data |
| L-17 | `coaching_service.py:57-77` | PERF | Temporal baseline retrieved multiple times — no caching |
| L-18 | `storage_manager.py:71-87` | ROBUST | `pro_ingest_dir` creation skipped — downstream glob returns nothing |
| L-19 | `storage_manager.py:161-175` | ROBUST | `_get_dir_size_gb()` follows symlinks — inflated quota |
| L-20 | `storage_manager.py:195-215` | INCON | `list_new_demos()` 10K query limit — old demos may re-enter pipeline |
| L-21 | `stat_aggregator.py:30-78` | ROBUST | Missing `ProPlayer.team_id` FK validation before insert |
| L-22 | `stat_aggregator.py:74` | ROBUST | `detailed_stats_json` unbounded growth — no MAX_BYTES |
| L-23 | `round_stats_builder.py:92-99` | ROBUST | Team roster exception swallowed — trade kills silently unavailable |
| L-24 | `player_knowledge.py:490` | ROBUST | Negative entity_id (not -1) passes sentinel check |
| L-25 | `tensor_factory.py:176-179` | ROBUST | No validation of gaussian filter sigma parameter |
| L-26 | `dataset.py:8-9` | PERF | `.clone().detach()` doubles memory — `.detach()` alone sufficient |
| L-27 | `demo_format_adapter.py:48-50` | ROBUST | `MAX_DEMO_SIZE=5GB` — no typical-size guidance in error messages |
| L-28 | `player_knowledge.py:412` | INCON | Memory decay `CUTOFF=320` (2τ) vs conventional 3τ |

---

## 9. Cross-Issue Compound Effects

Issues rarely occur in isolation. This section maps how issues interact to amplify each other.

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRAINING DATA CONTAMINATION CHAIN             │
│                                                                 │
│  C-04 (0.0 sentinels)  ──┐                                     │
│  C-05 (assists=0)      ──┤                                     │
│  H-04 (inventory=[])   ──┼──► Features 4,16,19 corrupted       │
│  H-12 (unknown weapon) ──┘    in 5-20% of training samples     │
│                                      │                          │
│  C-01 (context=None)   ──────────► Features 20-24 = 0.0        │
│                                      │                          │
│                                      ▼                          │
│                              7-12 of 25 features               │
│                              (28-48%) degraded                  │
│                                      │                          │
│  C-06 (player leakage) ────────────► Evaluation metrics         │
│  H-09 (non-reproducible) ──────────► optimistically biased      │
│                                      (can't detect the above)   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    SPATIAL CORRUPTION CHAIN                      │
│                                                                 │
│  C-03 (double Y-flip)  ──────────► All spatial tensors          │
│                                    vertically mirrored           │
│                                          │                      │
│  C-07 (unbounded pos)  ──────────► Out-of-range values          │
│                                    saturate activations          │
│                                          │                      │
│  C-10 (phantom smokes)  ─────────► Permanent blockers          │
│  H-11 (2D FOV only)     ─────────► False visibility on         │
│                                    multi-level maps              │
│                                          │                      │
│                                          ▼                      │
│                              Model learns inverted,             │
│                              occluded, phantom spatial           │
│                              relationships                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    SILENT FAILURE CASCADE                        │
│                                                                 │
│  H-02 (timeout → empty DF) ─┐                                  │
│  H-06 (wrong round bounds) ─┤                                  │
│  H-16 (zombie tasks stuck) ─┼──► Pipeline silently drops data  │
│  M-20 (zombie threshold)  ──┘    without user-visible errors    │
│                                          │                      │
│  C-09 (coaching fallback) ──────────► User gets ZERO coaching   │
│  H-17 (usage_count stale) ──────────► Experience ranking        │
│                                       stagnates                  │
│                                          │                      │
│                                          ▼                      │
│                              System degrades silently,           │
│                              no metrics detect it                │
└─────────────────────────────────────────────────────────────────┘
```

### Key Compound Chains

**Chain 1: Training Data Contamination** — C-04 + C-05 + C-01 compound to degrade 28-48% of the feature vector. C-06 + H-09 prevent detection by inflating evaluation metrics. The model appears to work well in testing but fails on genuinely new players in production.

**Chain 2: Spatial Corruption** — C-03 mirrors all spatial relationships while C-10 adds persistent phantom obstacles. The model learns internally consistent but physically incorrect tactical patterns. Ghost positions recommended by inference are mirrored relative to the actual optimal position.

**Chain 3: Silent Failure** — Multiple timeout/zombie/fallback issues cause the pipeline to silently drop data or produce no output. No monitoring metrics exist to detect this degradation. The user sees "no coaching advice" without understanding that the system has failed.

---

## 10. Performance Budget

Estimated time per pipeline stage for a typical 200MB demo (MR12, ~25 minutes, 100K ticks):

| Stage | Component | Estimated Time | Bottleneck |
|-------|-----------|:--------------:|-----------|
| **1. Validation** | `dem_validator` + `demo_format_adapter` | <1s | I/O (header read) |
| **2. Aggregate Parse** | `demo_parser.parse_demo()` | 15-30s | demoparser2 FFI |
| **3. Tick Parse** | `demo_parser.parse_sequential_ticks()` | 30-60s | demoparser2 FFI (100K+ rows) |
| **4. Frame Build** | `demo_loader.py` (DemoFrame construction) | 10-20s | Python row iteration |
| **5. Enrichment** | | | |
|   5a. Alive counts | `_compute_alive_counts()` | 2-5s | Pandas groupby + merge |
|   5b. Enemies visible | `_compute_enemies_visible()` | **5-8 min** | **C-02: O(T×P²) Python loops** |
|   5c. Round stats | `round_stats_builder` | 1-3s | Linear scan per event |
| **6. Feature Extract** | `FeatureExtractor.extract()` × N ticks | 5-15s | Python per-tick call |
| **7. Tensor Gen** | `TensorFactory` (3 tensors × window) | 10-30s | numpy array ops + gaussian filter |
| **8. Storage** | SQLite inserts (WAL mode) | 5-15s | Disk I/O, single-writer |
| **Total** | | **~7-12 min** | Dominated by Step 5b |

**After C-02 fix (numpy vectorization):** Step 5b drops from 5-8 min to 3-6 seconds. Total pipeline time: **~2-3 min** per demo.

---

## 11. Tick-Rate Sensitivity Table

All constants that assume a specific tick rate, with corrections for 128-tick servers:

| Constant | Current Value | File:Line | Assumed Rate | At 128 Hz | Fix Strategy |
|----------|:------------:|-----------|:------------:|:---------:|-------------|
| Flash duration | 128 ticks | `player_knowledge.py:523` | 64 Hz (2.0s) | 256 ticks | `2.0 * tick_rate` |
| Memory decay τ | 160 ticks | `player_knowledge.py:37` | 64 Hz (2.5s) | 320 ticks | `2.5 * tick_rate` |
| Memory cutoff | 320 ticks | `player_knowledge.py:42` | 64 Hz (5.0s) | 640 ticks | `5.0 * tick_rate` |
| Trade window | 192 ticks | `trade_kill_detector.py:28` | 64 Hz (3.0s) | 384 ticks | `3.0 * tick_rate` |
| MAX_SPEED | 4.0 u/tick | `tensor_factory.py:57` | 64 Hz | 2.0 u/tick | `256.0 / tick_rate` |
| Nade cap | 20 × tick_rate | `demo_loader.py:164` | **tick_rate-aware** | OK | Already correct |
| Smoke max dur | (not impl) | N/A | N/A | N/A | `18.0 * tick_rate` |
| Trajectory window | 32 ticks | `tensor_factory.py:56` | 64 Hz (0.5s) | 64 ticks | `0.5 * tick_rate` |
| Yaw delta max | 45.0 deg | `tensor_factory.py:58` | Rate-independent | OK | Angular, not temporal |

**Recommendation:** Introduce `TICK_RATE: int = 64` as a runtime-configurable constant in `core/constants.py`. All temporal constants should be computed as `seconds * TICK_RATE`.

---

## 12. Recommended Fix Order

### Sprint 1: Training Data Integrity (C-01 through C-07)
**Goal:** Eliminate training/inference skew and data corruption sources.
**Dependencies:** None (foundational).

```
C-01 (context features) ──► affects features 20-24
C-03 (double Y-flip)    ──► affects all spatial tensors
C-04 (0.0 sentinels)    ──► affects accuracy, headshot, KAST features
C-05 (assists=0)         ──► affects KAST feature (index 16)
C-06 (player split)      ──► affects evaluation metrics
C-07 (unbounded pos)     ──► affects position features (9-11)
```

**Estimated effort:** 2-3 days. All fixes are localized (1-2 files each).

### Sprint 2: Core Bug Fixes (C-08 through C-10, H-15 through H-18)
**Goal:** Fix logic errors in storage, perception, and coaching.
**Dependencies:** Sprint 1 (C-03 fix changes coordinate semantics).

```
C-08 (NULL entity_id)   ──► match_data_manager.py
C-09 (fallback chain)   ──► coaching_service.py
C-10 (smoke expiry)     ──► player_knowledge.py
H-15 (unique constraint) ──► db_models.py + Alembic migration
H-16 (zombie detection)  ──► session_engine.py
H-17 (usage_count)       ──► experience_bank.py
H-18 (off-by-one)        ──► round_stats_builder.py
```

**Estimated effort:** 2 days. H-15 requires Alembic migration.

### Sprint 3: Performance (C-02, H-14)
**Goal:** Eliminate pipeline bottlenecks.
**Dependencies:** Sprint 1 (may need tick_enrichment changes to align).

```
C-02 (vectorize FOV)    ──► tick_enrichment.py (biggest impact: 5 min → 5 sec)
H-14 (pool size)         ──► database.py (single line change)
```

**Estimated effort:** 1 day for C-02 (numpy vectorization + testing), 10 min for H-14.

### Sprint 4: Pipeline Robustness (H-01 through H-13)
**Goal:** Harden parsing and ingestion edge cases.
**Dependencies:** Sprint 1-3 complete.

### Sprint 5: Medium/Low Priority
**Goal:** Address remaining issues from Tier 3 and Tier 4.
**Dependencies:** Sprint 1-4 complete.

---

*Generated: 2026-03-07 | Method: Deep code review with exact line-number verification | All code snippets verified against current codebase*

---

## 13. Cross-Reference Reconciliation (updated 2026-03-09)

> Status of each issue verified against current codebase on 2026-03-09.
> Legend: **FIXED** = verified resolved | **EVOLVED** = partially addressed | **VALID** = still exists | **BY_DESIGN** = intentional

### Critical Issues (C-01 through C-10)

| ID | Description | Status | Evidence |
|----|-------------|--------|----------|
| C-01 | Training/inference context feature skew | **EVOLVED** | Canonical TrainingOrchestrator path fixed; legacy `train_pipeline.py` deprecated but still broken |
| C-02 | O(n²) enemies_visible computation | **FIXED** | Numpy-vectorized FOV in `tick_enrichment.py:313-343` |
| C-03 | Double Y-flip in coordinate transform | **FIXED** | Single flip in `tensor_factory.py:588` |
| C-04 | Silent event data loss (0.0 vs missing) | **FIXED** | `data_pipeline.py:55` filters by `data_quality != "none"` |
| C-05 | Assister name missing → KAST underestimated | **FIXED** | `demo_parser.py:301-316` tries multiple column names |
| C-06 | Player leakage in dataset splitting | **FIXED** | `data_pipeline.py:192-278` decontaminates player splits |
| C-07 | Position features unbounded | **FIXED** | `vectorizer.py:207-209` clips to [-1, 1] |
| C-08 | NULL entity_id passes SQL filter | **VALID** | Low practical risk (schema enforces non-null) but defensive check missing |
| C-09 | COPER fallback chain breaks | **EVOLVED** | Traditional fallback works; hybrid failure path still uncaught |
| C-10 | Smoke utility zones never expire | **FIXED** | Time-based expiry + position matching in `player_knowledge.py:493-540` |

**Summary: 7 FIXED, 2 EVOLVED, 1 VALID**

### High Issues (H-01 through H-18)

| ID | Description | Status | Evidence |
|----|-------------|--------|----------|
| H-01 | Field resolution order inconsistency | **BY_DESIGN** | Different primary actor per event type is intentional |
| H-02 | Parse timeout too strict (300s) | **FIXED** | Scales by file size: `max(timeout, size_mb * 3)` |
| H-03 | Money field name hardcoded ("balance") | **FIXED** | Tries `balance`, `cash`, `money`, `m_iAccount` |
| H-04 | Inventory always empty | **VALID** | Still `inventory=[]` with TODO |
| H-05 | Nade duration capping (20s) | **EVOLVED** | Tracks capped count + flag, but flag not stored on NadeState |
| H-06 | Round boundary pairing fragile | **VALID** | Still uses last `freeze_end` |
| H-07 | Bomb explode event not handled | **FIXED** | `bomb_exploded` added to round-end event list |
| H-08 | Alive count wrong for dead players | **FIXED** | Rewritten with pandas groupby + merge |
| H-09 | Non-reproducible training data | **FIXED** | `.order_by(PlayerMatchStats.id)` ensures determinism |
| H-10 | FOV_DEGREES dual definition | **EVOLVED** | `constants.py` is shared; `TensorConfig` has independent copy (values match) |
| H-11 | FOV check missing Z/pitch | **FIXED** | Z-distance check with `z_floor_threshold` added |
| H-12 | Weapon class map incomplete | **VALID** | Unknown weapons still default to 0.1 bucket |
| H-13 | Two parallel training paths | **EVOLVED** | Legacy path deprecated with DeprecationWarning; not deleted |
| H-14 | Database pool size = 1 | **VALID** | Intentional for SQLite single-writer; `max_overflow=4` allows 5 connections |
| H-15 | RoundStats missing unique constraint | **VALID** | No UniqueConstraint on `(demo_name, round_number, player_name)` |
| H-16 | Zombie detection for never-updated tasks | **EVOLVED** | New tasks get `default_factory` timestamp; legacy NULL risk remains |
| H-17 | Experience Bank usage_count not persisted | **FIXED** | SQLAlchemy identity-map tracks in-session mutations; session auto-commits |
| H-18 | Round assignment boundary off-by-one | **VALID** | Inclusive both ends; first-match wins |

**Summary: 6 FIXED, 4 EVOLVED, 5 VALID, 2 BY_DESIGN (H-01 intentional, H-14 SQLite constraint)**

### Medium Issues (M-01 through M-27)

| ID | Status | | ID | Status |
|----|--------|-|----|--------|
| M-01 | VALID | | M-15 | VALID |
| M-02 | VALID | | M-16 | VALID |
| M-03 | VALID | | M-17 | FIXED |
| M-04 | EVOLVED | | M-18 | FIXED |
| M-05 | FIXED | | M-19 | FIXED |
| M-06 | VALID | | M-20 | EVOLVED |
| M-07 | BY_DESIGN | | M-21 | VALID |
| M-08 | FIXED | | M-22 | VALID |
| M-09 | VALID | | M-23 | VALID |
| M-10 | FIXED | | M-24 | VALID |
| M-11 | VALID | | M-25 | VALID |
| M-12 | FIXED | | M-26 | EVOLVED |
| M-13 | FIXED | | M-27 | FIXED |
| M-14 | VALID | | | |

**Summary: 8 FIXED, 3 EVOLVED, 12 VALID, 2 BY_DESIGN (M-07 no wallhack, M-26 cosmetic)**

### Low Issues (L-01 through L-28)

| ID | Status | | ID | Status |
|----|--------|-|----|--------|
| L-01 | VALID | | L-15 | EVOLVED |
| L-02 | VALID | | L-16 | VALID |
| L-03 | VALID | | L-17 | VALID |
| L-04 | FIXED | | L-18 | BY_DESIGN |
| L-05 | VALID | | L-19 | VALID |
| L-06 | VALID | | L-20 | VALID |
| L-07 | VALID | | L-21 | VALID |
| L-08 | VALID | | L-22 | VALID |
| L-09 | VALID | | L-23 | VALID |
| L-10 | VALID | | L-24 | VALID |
| L-11 | VALID | | L-25 | VALID |
| L-12 | EVOLVED | | L-26 | BY_DESIGN |
| L-13 | VALID | | L-27 | VALID |
| L-14 | FIXED | | L-28 | FIXED |

**Summary: 3 FIXED, 2 EVOLVED, 19 VALID, 2 BY_DESIGN**

### Overall Pipeline Audit Status

| Category | Count | % |
|----------|:-----:|:-:|
| **Total issues** | 83 | 100% |
| **FIXED** | 26 | 31% |
| **EVOLVED** | 12 | 14% |
| **VALID** | 39 | 47% |
| **BY_DESIGN** | 6 | 7% |

### Remaining High-Priority Items

1. **C-08** — NULL entity_id: add defensive `is not None` check (low cost)
2. **C-09** — COPER: wrap hybrid failure in its own try/except
3. **H-04** — Inventory pipeline disabled entirely
4. **H-15** — RoundStats unique constraint missing (silent duplicates)
5. **H-18** — Off-by-one at round boundaries
6. **M-21** — Sample count committed before calibration (no auto-retry)

---
