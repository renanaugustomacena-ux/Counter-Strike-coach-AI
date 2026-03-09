# Feature Engineering, Processing Pipeline, and Data Transformation
# Macena CS2 Analyzer — Technical Audit Report 4/8

---

## DOCUMENT CONTROL

| Field | Value |
|-------|-------|
| Report ID | AUDIT-2026-04 |
| Date | 2026-03-08 |
| Version | 1.0 |
| Classification | Internal — Engineering Review |
| Auditor | Engineering Audit Protocol v3 |
| Scope | 38 files across feature engineering, processing pipeline, baselines, validation, and data transformation |
| Total LOC Audited | 6,480 (Python) + ~450 (READMEs/docs) |
| Audit Standard | ISO/IEC 25010 (Software Quality), ISO/IEC 27001 (Security), OWASP Top 10, IEEE 730 (SQA), CLAUDE.md Engineering Constitution |
| Previous Audit | N/A (baseline audit) |

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Audit Methodology](#2-audit-methodology)
3. [Processing Core Pipeline](#3-processing-core-pipeline)
   - 3.1 `processing/__init__.py`
   - 3.2 `tensor_factory.py`
   - 3.3 `data_pipeline.py`
   - 3.4 `state_reconstructor.py`
   - 3.5 `heatmap_engine.py`
   - 3.6 `player_knowledge.py`
   - 3.7 `round_stats_builder.py`
   - 3.8 `skill_assessment.py`
   - 3.9 `tick_enrichment.py`
   - 3.10 `cv_framebuffer.py`
   - 3.11 `connect_map_context.py`
   - 3.12 `external_analytics.py`
4. [Feature Engineering Subsystem](#4-feature-engineering-subsystem)
   - 4.1 `feature_engineering/__init__.py`
   - 4.2 `vectorizer.py`
   - 4.3 `base_features.py`
   - 4.4 `kast.py`
   - 4.5 `rating.py`
   - 4.6 `role_features.py`
5. [Baseline Management](#5-baseline-management)
   - 5.1 `baselines/__init__.py`
   - 5.2 `pro_baseline.py`
   - 5.3 `meta_drift.py`
   - 5.4 `nickname_resolver.py`
   - 5.5 `role_thresholds.py`
6. [Data Validation Pipeline](#6-data-validation-pipeline)
   - 6.1 `validation/__init__.py`
   - 6.2 `dem_validator.py`
   - 6.3 `drift.py`
   - 6.4 `sanity.py`
   - 6.5 `schema.py`
7. [Hopfield Network Layer](#7-hopfield-network-layer)
   - 7.1 `hflayers.py`
8. [Documentation Assessment](#8-documentation-assessment)
9. [Consolidated Findings Matrix](#9-consolidated-findings-matrix)
10. [Recommendations](#10-recommendations)
11. [Appendices](#appendices)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Domain Health Assessment

**Overall Rating: SOUND**

The Feature Engineering and Processing Pipeline domain represents the critical data transformation layer that converts raw demo telemetry (tick-level player positions, events, weapon states) into the 25-dimensional feature vectors consumed by the neural network subsystem. This domain is the mathematical backbone of the entire coaching system — every coaching insight, every skill assessment, every tactical recommendation ultimately traces back to the correctness of these transformations.

The domain demonstrates strong engineering in several areas: the METADATA_DIM=25 dimensional contract is consistently enforced across the vectorizer-to-tensor-factory chain; the NO-WALLHACK sensorial model in PlayerKnowledge correctly prevents information leakage through disciplined FOV-based visibility filtering; the data validation pipeline implements a proper fail-fast hierarchy (schema → sanity → drift → dem_validator); and the baseline management system provides graceful degradation through a three-tier fallback chain (DB → CSV → hardcoded defaults).

However, several systemic weaknesses exist. Magic constants pervade the codebase — tick rates (64 Hz assumed), FOV angles (90 degrees), distance normalization caps (4000 units), spatial drift scales (500 units), sigmoid coefficients (1.702), and memory sizes (512 slots) are hardcoded without documentation of their derivation or sensitivity. The training/inference skew risk in state_reconstructor.py is a HIGH-severity concern: when PlayerKnowledge is None during training but present during inference, the model receives fundamentally different inputs, violating the distributional assumptions of any supervised learning objective. ~~The Hopfield Network implementation in hflayers.py contains an incorrect scaling factor that could cause numerical instability during attention computation.~~ (NOTE: R4-25-01 was INCORRECT — stored_pattern_size IS the per-head dimension; scaling is correct.)

Across the 29 Python source files audited (excluding READMEs and __init__ stubs), we identified 52 findings: 0 CRITICAL, 6 HIGH, 21 MEDIUM, 19 LOW, and 6 INFO. The absence of CRITICAL findings reflects the extensive 12-phase remediation effort (368 issues fixed). **Post-audit update:** HIGH reduced to 3 (R4-04-02, R4-11-01 resolved; R4-25-01 was incorrect); MEDIUM reduced to 19 (R4-03-05, R4-21-01 resolved); R4-20-01 partially fixed.

### 1.2 Critical Findings Summary

| ID | Severity | File | Finding |
|----|----------|------|---------|
| R4-04-01 | HIGH | state_reconstructor.py | Training/inference skew: no fail-fast when knowledge=None but inference uses POV mode |
| R4-04-02 | ~~HIGH~~ | state_reconstructor.py | ~~RESOLVED — METADATA_DIM assertion now in state_reconstructor.py lines 76-81~~ |
| R4-11-01 | ~~HIGH~~ | connect_map_context.py | ~~RESOLVED — Z-penalty constants now imported from core.spatial_data~~ |
| R4-14-01 | HIGH | vectorizer.py | F2-15: Silent (0,0,0) position fallback contaminates training data — position is ambiguous |
| R4-20-01 | HIGH | pro_baseline.py | PARTIALLY FIXED: Memory exhaustion risk in get_pro_positions() — per-match limits added but reservoir sampling not yet implemented |
| R4-25-01 | ~~HIGH~~ | hflayers.py | ~~INCORRECT — stored_pattern_size IS the per-head dimension in this implementation; scaling is correct~~ |

### 1.3 Quantitative Overview

| Metric | Value |
|--------|-------|
| Files Audited | 38 |
| Python Source Files | 29 |
| README/Documentation Files | 9 |
| Total Lines of Code (Python) | 6,480 |
| Classes Analyzed | 18 |
| Functions/Methods Analyzed | ~120 |
| Findings: CRITICAL | 0 |
| Findings: HIGH | 3 (was 6; R4-04-02, R4-11-01 resolved, R4-25-01 incorrect) |
| Findings: MEDIUM | 19 (was 21; R4-03-05, R4-21-01 resolved) |
| Findings: LOW | 19 |
| Findings: INFO | 6 |
| Total Findings | 52 |
| Remediation Items Previously Fixed | 22 (F2-series from Phase 2) |
| Pipeline Audit Items Cross-Referenced | 6 (C-01, C-02, C-04, C-06, C-10, P3-series) |
| Remaining Deferred Items | 1 (G-05: heuristic calibration — requires pro-annotated dataset) |

### 1.4 Risk Heatmap

```
                    IMPACT
              Low    Med    High   Crit
         +--------+--------+--------+--------+
  High   |        | R4-17  | R4-04  |        |
         |        | R4-18  | R4-14  |        |
L        +--------+--------+--------+--------+
I  Med   | R4-07  | R4-05  | R4-11  |        |
K        | R4-08  | R4-06  | R4-20  |        |
E        |        | R4-09  | R4-25  |        |
L        +--------+--------+--------+--------+
I  Low   | R4-03  | R4-12  |        |        |
H        | R4-10  | R4-13  |        |        |
O        | R4-15  |        |        |        |
O        +--------+--------+--------+--------+
D  VLow  | R4-16  |        |        |        |
         +--------+--------+--------+--------+
```

---

## 2. AUDIT METHODOLOGY

### 2.1 Standards Applied

- **ISO/IEC 25010** — Software product quality model (functionality, reliability, usability, efficiency, maintainability, portability, security, compatibility)
- **ISO/IEC 27001** — Information security management
- **OWASP Top 10 2021** — Web/application security risks
- **IEEE 730** — Software quality assurance
- **CLAUDE.md Constitution** — Project-specific engineering rules (Rules 1-7, Dev Rules 1-11)
- **STRIDE** — Threat modeling methodology

### 2.2 Analysis Techniques

- **Static Analysis**: Line-by-line code review, dimensional invariant verification, import graph construction
- **Architectural Analysis**: Component coupling, cohesion metrics, dependency direction verification (processing -> core, never reverse)
- **Data Flow Analysis**: Input-to-output tracing through the full pipeline (raw tick -> feature vector -> tensor -> model input), taint analysis for training data contamination
- **Numerical Analysis**: Floating-point stability, normalization correctness, scaling factor verification, division-by-zero guards
- **Dimensional Analysis**: METADATA_DIM=25 contract verification at every transformation boundary
- **Concurrency Analysis**: Thread safety of shared state (TensorFactory singleton, FeatureExtractor config), lock ordering, ring buffer correctness
- **Performance Analysis**: Big-O complexity for FOV computation (C-02), vectorization effectiveness, memory allocation patterns
- **Training/Inference Parity Analysis**: Feature availability at training vs. inference time, distribution shift detection, silent fallback impact

### 2.3 Severity Classification

| Severity | Definition | SLA |
|----------|------------|-----|
| CRITICAL | System failure, data loss, security breach, or correctness violation affecting core functionality. Production blocking. | Immediate fix required |
| HIGH | Significant functional impact, performance degradation >50%, security weakness exploitable under realistic conditions, or maintainability debt creating cascading risk. | Fix within current sprint |
| MEDIUM | Moderate impact on reliability, performance, or maintainability. Does not block core functionality but degrades system quality. | Fix within next 2 sprints |
| LOW | Minor code quality issues, style inconsistencies, documentation gaps, or optimization opportunities with <10% impact. | Fix during next refactoring cycle |
| INFO | Observations, positive findings, architectural notes, or suggestions for future consideration. No action required. | No SLA — informational |

### 2.4 Cross-Reference Protocol

Findings are cross-referenced to:
- **Remediation Phase Codes**: F2-XX (Phase 2: Processing Pipeline — 42 issues fixed)
- **Pipeline Audit Codes**: C-XX (PIPELINE_AUDIT_REPORT.md — 83 issues cataloged)
- **G-Issue Codes**: G-XX (AIstate.md post-review remediation)
- **CLAUDE.md Rules**: Rule N (Engineering Constitution)
- **Reports 1-3**: R1-XX, R2-XX, R3-XX (prior audit reports in this series)

### 2.5 Domain-Specific Invariants Verified

This audit specifically verified:
1. **METADATA_DIM=25 Contract**: Every function that produces or consumes a feature vector maintains exactly 25 dimensions
2. **NO-WALLHACK Principle**: PlayerKnowledge never exposes information a human player could not perceive (FOV, distance, occlusion)
3. **Tick Fidelity Invariant**: No tick decimation occurs in the processing pipeline (Dev Rule 8)
4. **Training/Inference Parity**: Features computed at training time are identically available at inference time
5. **Coordinate System Consistency**: Y-flip applied exactly once, Z-penalty computed correctly for multi-level maps

---

## 3. PROCESSING CORE PIPELINE

### 3.1 `processing/__init__.py` — Package Initialization and Re-exports

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 28 |
| Classes | 0 |
| Functions/Methods | 0 |
| Cyclomatic Complexity (max) | 1 |
| Import Count | 6 |
| Test Coverage | N/A (package init) |

**Architecture & Design:**
Re-exports core processing classes: `TensorFactory`, `DataPipeline`, `PlayerKnowledgeBuilder`, `HeatmapEngine`, `FeatureExtractor`, and `HeuristicConfig`. Establishes the public API surface for the processing subsystem. All imports are lazy-loaded via try/except blocks to handle optional dependencies (scipy, cv2).

**Correctness Analysis:**
Re-exports are consistent with the actual module exports. No logic — pure namespace management.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-01-01 | INFO | Architecture | Clean public API surface with 6 well-chosen exports | None — exemplary |

**Positive Observations:**
Well-structured package init that clearly defines what the processing subsystem exposes to consumers.

---

### 3.2 `tensor_factory.py` — View and Metadata Tensor Construction

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 319 |
| Classes | 1 (TensorFactory) |
| Functions/Methods | 8 public + 4 private |
| Cyclomatic Complexity (max) | 12 |
| Import Count | 11 |
| Test Coverage | Cross-ref Report 8: test_tensor_factory.py |

**Architecture & Design:**
TensorFactory is the bridge between raw tick data and neural network input tensors. It constructs two tensor types: (1) **view tensors** — 3-channel (RGB) images representing the player's FOV-filtered perspective of the game world, rendered at configurable resolution (64x64 for training, 224x224 for inference); (2) **metadata tensors** — 25-dimensional feature vectors produced by FeatureExtractor.

The factory uses a singleton pattern with double-checked locking for thread-safe access across the Tri-Daemon engine. Configuration is immutable after initialization (resolution, FOV, device).

**Correctness Analysis:**
The METADATA_DIM=25 contract is enforced at the FeatureExtractor level, not at TensorFactory itself. TensorFactory trusts that `extract()` returns a 25-element vector. This is correct design (single source of truth), but lacks a defensive assertion at the tensor creation boundary.

The FOV mask computation uses numpy trigonometry to project enemy positions into the player's field of view. The angular calculation handles yaw wraparound correctly via `atan2()` + modular arithmetic. However, the view resolution difference between training (64x64) and inference (224x224) means the spatial resolution of the FOV mask differs — training sees coarser spatial detail than inference. This is a known tradeoff documented in the ResNet backbone change ([1,2,2,1] for 64x64).

**Concurrency & Thread Safety:**
Singleton access via `get_tensor_factory()` uses double-checked locking with a module-level lock. The factory itself is stateless after initialization (resolution, device are immutable). Thread-safe.

**Performance & Efficiency:**
- View tensor construction: O(n_enemies) for FOV filtering + O(resolution^2) for rasterization — fast
- Metadata tensor construction: O(1) via FeatureExtractor — constant time
- scipy.ndimage.gaussian_filter used for smoothing: O(resolution^2) — separable filter is efficient
- Hard import of scipy could fail if not installed: should use lazy import with graceful fallback

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-02-01 | MEDIUM | Correctness | F2-02: No assertion that metadata tensor shape matches (1, METADATA_DIM). If FeatureExtractor output changes, silent shape mismatch propagates to model | Add `assert metadata.shape[-1] == METADATA_DIM` after extraction |
| R4-02-02 | LOW | Compatibility | F2-03: Training resolution (64x64) vs inference resolution (224x224) creates distribution shift in spatial features. Known limitation | Document resolution sensitivity in model training config |
| R4-02-03 | MEDIUM | Reliability | F2-04: scipy imported at module level — hard failure if not installed. No fallback to numpy-only smoothing | Use lazy import with try/except ImportError |

**Positive Observations:**
- Singleton pattern with double-checked locking is production-grade thread safety
- Clean separation between view tensor (visual) and metadata tensor (statistical) construction
- FOV mask computation is geometrically correct with proper yaw wraparound handling
- Configurable resolution allows training/inference flexibility

---

### 3.3 `data_pipeline.py` — Training Data Preparation and Splitting

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 547 |
| Classes | 1 (DataPipeline) |
| Functions/Methods | 12 public + 6 private |
| Cyclomatic Complexity (max) | 15 |
| Import Count | 14 |
| Test Coverage | Cross-ref Report 8: test_data_pipeline_contracts.py |

**Architecture & Design:**
DataPipeline is responsible for loading raw match data from SQLite, applying quality filters, performing train/val/test splitting with temporal stratification, and outputting DataFrames ready for tensor construction. Key design decisions: (1) temporal splitting ensures no future-leakage (train data always earlier than val/test); (2) player-level decontamination (C-06) ensures no player appears in both train and test; (3) 50,000-row truncation prevents memory exhaustion on large datasets.

**Correctness Analysis:**
The temporal stratification is well-implemented: matches are sorted by date, then split 70/15/15. This prevents the model from training on future matches that it will be tested on — a critical ML correctness requirement.

Player decontamination (C-06 fix) assigns each player entirely to one split. Tie-breaking for players who span the temporal boundary is arbitrary (first-seen split wins). This is acceptable but could bias splits if prolific players cluster temporally.

The 50,000-row truncation is a silent operation — it truncates without warning the user. For datasets with >50K rows, the user receives a subset without knowing data was dropped. This should emit a WARNING-level log.

IQR-based outlier detection uses a 3.0x multiplier (standard practice) but this constant is not documented or configurable.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-03-01 | MEDIUM | Correctness | C-04: data_quality column semantics unclear — used for filtering but meaning undocumented | Add enum or docstring defining quality levels |
| R4-03-02 | LOW | Correctness | C-06: Player decontamination tie-break is arbitrary (first-seen split wins) | Document tie-breaking policy |
| R4-03-03 | LOW | Maintainability | P3-11: IQR outlier multiplier 3.0 is standard but not documented or configurable | Extract to named constant with docstring |
| R4-03-04 | LOW | Reliability | F2-22: Chunk size 500 for SQLite queries is near the 999-variable limit — should be 499 for safety margin | Reduce to 499 |
| R4-03-05 | ~~MEDIUM~~ | ~~Correctness~~ | ~~RESOLVED — 50K truncation now emits logger.warning~~ | ~~Add `logger.warning(f"Truncated dataset from {len(df)} to 50000 rows")`~~ |

**Positive Observations:**
- Temporal stratification prevents future-leakage — critical ML correctness
- Player-level decontamination (C-06) prevents cross-split contamination
- Graceful handling of empty datasets (returns empty DataFrames, no crash)
- IQR-based outlier detection is standard statistical practice

---

### 3.4 `state_reconstructor.py` — Training/Inference Bridge

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 89 |
| Classes | 0 |
| Functions/Methods | 2 |
| Cyclomatic Complexity (max) | 6 |
| Import Count | 5 |
| Test Coverage | Cross-ref Report 8: test_state_reconstructor.py |

**Architecture & Design:**
StateReconstructor bridges the gap between raw tick data (used during training) and the full perception pipeline (used during inference via GhostEngine). During training, it constructs PlayerKnowledge-augmented tensors from tick data. During inference, GhostEngine provides live PlayerKnowledge directly.

The key design question: what happens when `knowledge=None` during training? The reconstructor logs a warning and falls back to "legacy mode" — constructing tensors without FOV filtering. But at inference time, GhostEngine always provides FOV-filtered knowledge. This creates a training/inference distribution mismatch.

**Correctness Analysis:**
This file contains the most significant training/inference skew risk in the entire processing pipeline. When knowledge=None:
- Training: model sees ALL enemy positions (no FOV filter) — equivalent to wallhack
- Inference: model sees only FOV-filtered positions — legitimate visibility

This means the model trains on a superset of information but must predict from a subset. The model may learn to rely on behind-the-back enemy positions that are never available at inference time.

Additionally, there is no assertion that the metadata tensor produced by `extract_batch()` has shape (n, METADATA_DIM). If FeatureExtractor output changes, the error propagates silently through the tensor factory into the neural network, where it manifests as a cryptic dimension mismatch error.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-04-01 | HIGH | Correctness | Training/inference skew: knowledge=None during training creates wallhack-equivalent inputs. Model trains on information unavailable at inference. Should fail-fast or auto-construct PlayerKnowledge from tick data | Require knowledge parameter or auto-build from tick history |
| R4-04-02 | ~~HIGH~~ | ~~Correctness~~ | ~~RESOLVED — METADATA_DIM assertion now in state_reconstructor.py lines 76-81~~ | ~~Add `assert metadata.shape[-1] == 25`~~ |

**Positive Observations:**
- Clean separation of training vs inference code paths
- Warning log when falling back to legacy mode provides observability
- Windowing with 50% overlap is standard temporal batching practice

---

### 3.5 `heatmap_engine.py` — Position Density Visualization

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 295 |
| Classes | 3 (HeatmapData, DifferentialHeatmapData, HeatmapEngine) |
| Functions/Methods | 4 static + 2 data containers |
| Cyclomatic Complexity (max) | 8 |
| Import Count | 7 |
| Test Coverage | Cross-ref Report 8: indirect via test_spatial_and_baseline.py |

**Architecture & Design:**
HeatmapEngine generates density visualizations from player position data. Two modes: (1) standard heatmap — shows where a player spends time; (2) differential heatmap — compares user positions against pro baseline positions, highlighting over/under-coverage.

Key design pattern: data generation (thread-safe, can run in background) is separated from texture creation (must run on Kivy main thread for OpenGL context). This separation enables background processing without blocking the UI.

**Correctness Analysis:**
The coordinate projection uses two sequential Y-inversions that cancel out to a correct result:
1. `ny = (meta.pos_y - pts[:, 1]) * scale_factor` — first inversion
2. `gy = ((1.0 - ny) * resolution)` — second inversion

Net effect: correct world-to-grid projection matching the radar image orientation. While mathematically correct, the double inversion is confusing and should be collapsed into a single transform for clarity.

Hotspot extraction takes the top-N cells by absolute difference, then filters by a 0.05 magnitude threshold. If all top-N cells have magnitude < 0.05, zero hotspots are returned. This is correct behavior (no significant hotspots exist) but could surprise callers expecting exactly N results.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-05-01 | LOW | Maintainability | Double Y-inversion is mathematically correct but confusing. Should collapse into single transform | Refactor to single projection formula |
| R4-05-02 | INFO | Architecture | Well-separated thread safety: data generation (background-safe) vs texture creation (main-thread-only). Excellent pattern | None — exemplary |
| R4-05-03 | LOW | Reliability | No guard on resolution parameter. resolution=1 is useless, resolution=10000 causes memory exhaustion | Clamp resolution to [64, 2048] |

**Positive Observations:**
- Vectorized numpy operations for position projection — O(n) for n points
- Activity masking (d_user > 0.02 OR d_pro > 0.02) prevents noise in dead zones
- Division-by-zero guard on scale_factor
- Immutable HeatmapData dataclass — safe to pass between threads

---

### 3.6 `player_knowledge.py` — NO-WALLHACK Sensorial Model

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 575 |
| Classes | 6 (VisibleEntity, LastKnownEnemy, HeardEvent, UtilityZone, PlayerKnowledge, PlayerKnowledgeBuilder) |
| Functions/Methods | 8 public + 4 private |
| Cyclomatic Complexity (max) | 18 |
| Import Count | 8 |
| Test Coverage | Cross-ref Report 8: test_coach_manager_tensors.py, test_dimension_chain_integration.py |

**Architecture & Design:**
PlayerKnowledge implements the NO-WALLHACK principle — the coach AI sees only what a legitimate human player could perceive. This is the single most important correctness invariant in the entire system. If this module leaks information (showing enemy positions behind walls, through smoke, or outside FOV), the coaching system becomes a cheat tool.

The model constructs a `PlayerKnowledge` state from:
1. **Visible enemies** — within FOV cone and line-of-sight distance, with Z-level filtering for multi-floor maps
2. **Last-known enemies** — enemies previously visible, with exponential memory decay over time
3. **Heard events** — gunfire, footsteps, grenade bounces within audible range
4. **Utility zones** — active smoke, molotov, flash effect areas with lifecycle tracking

**Correctness Analysis:**
The FOV computation is geometrically correct:
- `atan2(dy, dx)` computes bearing angle to enemy
- Yaw wraparound handled via `_angle_diff()` returning [0, 180] — circular distance
- Z-level guard (200-unit threshold) prevents seeing across Nuke/Vertigo floors
- Distance check ensures enemies beyond max_distance are filtered

The entity_id=-1 matching for utility zone end events (C-10) uses position-based matching within a 50-unit radius. This is fragile — 50 units is only 1/4 of a smoke radius (200 units). Spatially close smokes could be mismatched, but this is an acceptable heuristic given the limitation of demoparser2's event correlation.

Memory decay uses an exponential model: confidence decreases from 1.0 to 0.0 over time since last visibility. Pre-indexing by player name (O(1) lookup per enemy) prevents O(n^2) complexity in the memory loop.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-06-01 | LOW | Configuration | Z-level threshold hardcoded at 200 units. Nuke floors are ~256 units apart, Vertigo different. Should be per-map configurable | Import from map-specific config or spatial_data.py |
| R4-06-02 | MEDIUM | Correctness | C-10: Entity_id=-1 utility zone matching within 50-unit radius is fragile. Could mismatch spatially adjacent smokes/molotovs | Increase radius to 100 units or use temporal correlation (closest in time AND space) |
| R4-06-03 | LOW | Compatibility | P3-05: tick_rate=64 default in function signature. 128 Hz demos with tick_rate=64 passed create 0.5-second hearing windows instead of 1-second | Validate tick_rate against demo header or auto-detect |

**Positive Observations:**
- **NO-WALLHACK enforcement is correct** — the most critical invariant in the system is properly maintained
- Defensive programming via `getattr()` with defaults for all player attributes
- Pre-indexed enemy history (O(1) lookup) prevents quadratic complexity
- Utility zone lifecycle tracking handles missing entity_id, max duration enforcement, and start/end event pairing
- Immutable PlayerKnowledge dataclass — safe for cross-thread transfer

---

### 3.7 `round_stats_builder.py` — Event Aggregation Pipeline

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 519 |
| Classes | 0 |
| Functions/Methods | 10 (7 main + 3 helpers) |
| Cyclomatic Complexity (max) | 14 |
| Import Count | 9 |
| Test Coverage | Cross-ref Report 8: test_round_stats_enrichment.py, test_round_utils.py |

**Architecture & Design:**
Converts raw demo events (deaths, hurts, blinds, grenades) into per-round, per-player statistics. This is the primary data aggregation stage — everything downstream (feature vectors, baselines, coaching insights) depends on the correctness of these round-level stats.

Key operations: round boundary detection, team roster inference, per-round stat accumulation (kills, deaths, assists, ADR, HS%, KAST), opening duel detection, flash assist windowing, trade kill integration.

**Correctness Analysis:**
The FLASH_ASSIST_WINDOW_TICKS=128 constant assumes 64 Hz tick rate (128 ticks = 2 seconds). On 128 Hz demos, this becomes a 1-second window. The constant should be derived from the actual tick rate: `FLASH_ASSIST_WINDOW_SECONDS * tick_rate`.

Team mapping (team_num 2 or 3 to CT/T) follows demoparser2 conventions where team 3 = CT in first half, T in second. This assumption is standard but fragile — if demoparser2 changes its convention or a custom server uses non-standard team assignments, all side-based analysis breaks silently.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-07-01 | MEDIUM | Correctness | FLASH_ASSIST_WINDOW_TICKS=128 assumes 64 Hz. On 128 Hz demos, window is 1s instead of 2s. Should derive from tick_rate | Use `int(FLASH_ASSIST_WINDOW_SECONDS * tick_rate)` |
| R4-07-02 | MEDIUM | Reliability | Team mapping assumes demoparser2 convention (team_num 3 = CT first half). Convention change breaks all side analysis silently | Add assertion or validation of team assignment |
| R4-07-03 | LOW | Correctness | F2-10: Warmup ticks before round_start may exist — included in stats. Documented assumption but could contaminate round 1 data | Filter events where tick < first round_start_tick |

**Positive Observations:**
- Unified HLTV 2.0 rating computation via imported `compute_hltv2_rating()` — ensures consistency
- Safe wrapper for demoparser2 calls with graceful degradation on parse errors
- Comprehensive stat initialization (all fields pre-set) prevents None/KeyError downstream
- Trade kill integration with external detector — clean separation of concerns

---

### 3.8 `skill_assessment.py` — 5-Axis Skill Decomposition

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 147 |
| Classes | 2 (SkillAxes, SkillLatentModel) |
| Functions/Methods | 5 static methods |
| Cyclomatic Complexity (max) | 6 |
| Import Count | 4 |
| Test Coverage | Cross-ref Report 8: test_skill_model.py (partial) |

**Architecture & Design:**
Decomposes player performance into 5 skill axes: Mechanics (aim accuracy, headshot%), Positioning (survival, KAST), Utility (flash assists, utility damage), Timing (opening duels, trade participation), Decision (impact rating, ADR). Each axis is computed as a Z-score against pro baseline, then transformed to [0, 1] percentile via a sigmoid function.

**Correctness Analysis:**
The sigmoid coefficient 1.702 (`1.0 / (1.0 + np.exp(-1.702 * z))`) is undocumented. Standard logistic sigmoid uses coefficient 1.0. The value 1.702 appears in the GELU activation function literature (Hendrycks & Gimpel, 2016) as an approximation factor, but its use here for Z-score-to-percentile conversion is not justified. The steeper sigmoid means Z-scores of +/-1.5 already map to ~92%/8% percentile, compressing the tails. For skill assessment, this may be intentional (emphasizing deviation from mean) but should be documented.

The Positioning axis uses outcome-based stats (survival rate, KAST%) as proxies for positioning quality. This is semantically questionable: a passive player who avoids fights but contributes little has high survival and KAST but poor positioning. True positioning quality requires spatial metrics (distance from site, crosshair placement, angle advantage). This is a known limitation.

Curriculum level mapping uses `int(avg_skill * 9) + 1` which truncates, creating uneven buckets.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-08-01 | MEDIUM | Documentation | Sigmoid coefficient 1.702 undocumented. Appears related to GELU approximation but not cited | Add docstring citing source or justification for 1.702 |
| R4-08-02 | MEDIUM | Correctness | Positioning axis uses outcome stats (survival, KAST) as proxy for positioning quality. Passive play != good positioning | Add spatial metrics (distance to site, angle advantage) when available |
| R4-08-03 | LOW | Correctness | Curriculum level rounding uses int() truncation creating uneven buckets | Use `round(avg_skill * 9) + 1` instead |

**Positive Observations:**
- Percentile normalization via sigmoid provides interpretable [0, 1] scale
- Defensive filtering removes None values per-axis before averaging
- Division-by-zero guard: `max(1e-6, b["std"])` prevents crash on zero-variance baselines
- One-hot curriculum tensor output (1, 10) matches RAPPedagogy input contract

---

### 3.9 `tick_enrichment.py` — Per-Tick Feature Enrichment

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 362 |
| Classes | 0 |
| Functions/Methods | 6 (1 main + 5 private) |
| Cyclomatic Complexity (max) | 12 |
| Import Count | 6 |
| Test Coverage | Cross-ref Report 8: test_tactical_features.py |

**Architecture & Design:**
Enriches per-tick data with contextual features: bomb state, alive counts, team economy, round time, and enemies visible. This is the C-02 optimization site — the O(n^2) Python FOV loop was replaced with vectorized numpy operations.

**Correctness Analysis:**
The C-02 optimization replaces nested Python loops with numpy broadcasting for FOV-based visibility computation. The vectorized approach computes pairwise distances and angles for all players simultaneously. Critical correctness point: `np.arccos(dot)` could fail if dot product falls outside [-1, 1] due to floating-point errors. The code clips to [-1, 1] before arccos — **correctly handles this edge case**.

The FOV default of 90 degrees assumes standard widescreen CS2 settings. Players using 4:3 aspect ratio have narrower horizontal FOV (~73 degrees).

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-09-01 | LOW | Configuration | FOV default 90 degrees assumes widescreen. 4:3 aspect ratio users have ~73 degrees horizontal FOV | Make FOV configurable via player settings |
| R4-09-02 | INFO | Performance | C-02 vectorization: O(P^2) numpy replaces O(P^2) Python — ~10x speedup for typical match sizes. ~100-200ms for 100K ticks | None — excellent optimization |

**Positive Observations:**
- Progress logging every 50K ticks provides good UX for long matches
- Defensive column handling with fallbacks for missing data
- `np.clip()` before `np.arccos()` prevents NaN from floating-point errors
- Pure function — no retained state, thread-safe

---

### 3.10 `cv_framebuffer.py` — Thread-Safe Ring Buffer for Video Frames

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 183 |
| Classes | 1 (FrameBuffer) |
| Functions/Methods | 6 (5 public + 1 static) |
| Cyclomatic Complexity (max) | 6 |
| Import Count | 5 |
| Test Coverage | Cross-ref Report 8: indirect |

**Architecture & Design:**
Implements a fixed-size circular (ring) buffer for storing captured video frames. Used by the computer vision pipeline for screen capture analysis. Thread-safe via lock-protected write index and count.

**Correctness Analysis:**
Ring buffer modulo arithmetic is correct. Frame copies are returned (not references) from `get_latest()`, preventing external modifications from corrupting the internal buffer.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-10-01 | MEDIUM | Security | File path in capture_frame() opened directly without validation. If path from user input, path traversal possible | Validate path against expected directory |
| R4-10-02 | LOW | Reliability | No guard against invalid frame sizes (W=0, H=0). Would cause division-by-zero in region scaling | Validate W >= 1 and H >= 1 in constructor |

**Positive Observations:**
- Lock-protected ring buffer is production-grade thread safety
- Frame copy semantics prevent buffer corruption from external modifications
- BGR to RGB conversion correctly handles OpenCV default color space

---

### 3.11 `connect_map_context.py` — Z-Penalty Distance Metric

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 116 |
| Classes | 0 |
| Functions/Methods | 2 |
| Cyclomatic Complexity (max) | 4 |
| Import Count | 3 |
| Test Coverage | Cross-ref Report 8: test_spatial_engine.py (partial) |

**Architecture & Design:**
Implements the Z-penalty distance metric for multi-level maps (Nuke, Vertigo). On single-level maps, distance is standard 2D Euclidean. On multi-level maps, if the Z-difference exceeds a threshold (200 units), an additional penalty is applied: `dist = xy_dist + z_diff * penalty_factor`.

**Correctness Analysis:**
The Z-penalty logic is mathematically sound. On Nuke (lower floor z=-256, upper floor z=+100): z_diff = 356 units, penalty = 356 * 2.0 = 712 units added. Max map distance is approximately 3000 units, so penalty adds ~24% — reasonable.

**CRITICAL DESIGN FLAW (F2-46):** The constants `Z_LEVEL_THRESHOLD=200` and `Z_PENALTY_FACTOR=2.0` are hardcoded locally. They MUST match `core/spatial_data.py` but there is no import — they are manually duplicated. If `spatial_data.py` changes these values, this module drifts silently.

Feature normalization divides all distances by 4000 (assumed max map distance). But map sizes vary: Dust2 is approximately 3000 units, Nuke approximately 3500 units, Vertigo approximately 4000 units. Using fixed 4000 means Dust2 distances never reach 1.0, while Z-penalized Vertigo distances could exceed 1.0.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-11-01 | ~~HIGH~~ | ~~Architecture~~ | ~~RESOLVED — Z-penalty constants now imported from core.spatial_data~~ | ~~Import from core.spatial_data directly~~ |
| R4-11-02 | MEDIUM | Correctness | Fixed 4000-unit distance normalization does not match all maps. Z-penalized distances can exceed 1.0 | Use per-map max_distance from map_config.json |
| R4-11-03 | LOW | Documentation | Z-penalty factor (2.0) and threshold (200) rationale undocumented | Add docstring citing calibration source |

**Positive Observations:**
- Z-penalty design is geometrically sound for multi-level maps
- Graceful 2D fallback when coordinates have fewer than 3 dimensions
- Pure functions — thread-safe, no side effects

---

### 3.12 `external_analytics.py` — External Baseline Comparison

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 166 |
| Classes | 1 (EliteAnalytics) |
| Functions/Methods | 7 public + 5 private |
| Cyclomatic Complexity (max) | 8 |
| Import Count | 6 |
| Test Coverage | Cross-ref Report 8: test_baselines.py (partial) |

**Architecture & Design:**
Loads external CSV datasets (historical stats, tournament baselines) and computes Z-scores comparing user performance to these benchmarks. Implements a health check pattern — `is_healthy()` reports whether sufficient data is loaded.

**Correctness Analysis:**
Inconsistent health semantics: `is_healthy()` returns True if at least one dataset loaded, but `analyze_user_vs_elite()` can return an empty dict even when healthy (if required columns are missing). Callers checking only `is_healthy()` may proceed with empty results.

NaN propagation: if historical_stats contains NaN (from empty columns), Z-scores become NaN silently. The division guard (`max(1e-6, std)`) only protects against zero-std, not NaN-std.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-12-01 | MEDIUM | Correctness | is_healthy() can return True while analyze_user_vs_elite() returns empty dict. Inconsistent semantics mislead callers | Verify required columns exist in is_healthy() |
| R4-12-02 | MEDIUM | Correctness | NaN propagation from empty columns. Z-scores become NaN silently | Add np.isnan() check after mean/std computation |
| R4-12-03 | LOW | Maintainability | Fixed Z-score features hardcoded. Not configurable | Extract to class constant or config |

**Positive Observations:**
- Graceful degradation: missing CSVs produce empty DataFrames, not crashes
- is_healthy() pattern allows callers to check data availability before analysis
- Division-by-zero guard prevents crash on zero-variance features

---

## 4. FEATURE ENGINEERING SUBSYSTEM

### 4.1 `feature_engineering/__init__.py` — Lazy Import and Re-export

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 58 |
| Classes | 0 |
| Functions/Methods | 1 |
| Cyclomatic Complexity (max) | 3 |
| Import Count | 4 (lazy) |
| Test Coverage | N/A (package init) |

**Architecture & Design:**
Provides lazy imports for the feature engineering subsystem components. Uses try/except blocks around imports to handle cases where optional dependencies (scipy, sklearn) are not installed.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-13-01 | INFO | Architecture | Lazy import pattern provides graceful degradation when optional dependencies missing | None — good practice |

---

### 4.2 `vectorizer.py` — The 25-Dimensional Feature Vector (METADATA_DIM Contract)

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 379 |
| Classes | 1 (FeatureExtractor) |
| Functions/Methods | 4 public + 2 private |
| Cyclomatic Complexity (max) | 14 |
| Import Count | 7 |
| Test Coverage | Cross-ref Report 8: test_feature_extractor_contracts.py, test_features.py |

**Architecture & Design:**
FeatureExtractor is THE single source of truth for the 25-dimensional feature vector consumed by all neural networks. This is arguably the most critical file in the entire processing pipeline — any change to its output dimensions breaks every model.

The 25-dimensional feature vector is structured as:

```
METADATA_DIM = 25
+-- Vitals (0-4):      health, armor, helmet, defuser, equipment_value
+-- Stance (5-7):      crouch, scope, blind
+-- Awareness (8):     enemies_visible
+-- Position (9-11):   x, y, z (world coordinates, normalized)
+-- View (12-14):      yaw_sin, yaw_cos, pitch
+-- Environment (15):  z_penalty (map-aware distance factor)
+-- Engagement (16):   kast_estimate
+-- Context (17-24):   map_id, round_phase, weapon_class, time_in_round,
                       bomb_planted, teammates_alive, enemies_alive, economy_ratio
```

Key design patterns:
- Static factory methods for batch processing
- Dual-input polymorphism (accepts dict OR object with attributes)
- Fallback chain for missing fields (pos_x -> x -> X)
- Cyclic encoding for yaw (sin/cos to avoid +/-180 degree discontinuity)
- Thread-safe config via RLock

**Correctness Analysis:**
**F2-15 (HIGH): Silent (0,0,0) Position Fallback.** When pos_x, pos_y, pos_z are all 0, the code logs at DEBUG level and continues. However, (0,0,0) is a VALID world position on some maps (near bomb site boundaries). The code cannot distinguish between "position data missing" and "player is at world origin." This contaminates training data with ambiguous position values.

**F2-16 (MEDIUM): NaN/Inf Warning AFTER Clamp.** Non-finite values are warned about then immediately clamped. The warning is diagnostic but useless — the damage has already occurred. The clamp masks the upstream bug. Should propagate the error to the caller or raise immediately.

**Thread Safety Gap:** `extract_batch()` iterates over contexts without holding the config lock for the entire batch. If `configure()` is called mid-batch by another thread, different ticks within the same batch could use different normalization configs.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-14-01 | HIGH | Correctness | F2-15: Silent (0,0,0) position fallback. Position (0,0,0) is valid on some maps but treated as "data missing." Training data contaminated with ambiguous values | Validate positions against map bounds |
| R4-14-02 | MEDIUM | Error Handling | F2-16: NaN/Inf warning logged after silent clamp. Masks upstream bugs | Raise ValueError on non-finite values, or count and warn at batch end |
| R4-14-03 | MEDIUM | Concurrency | Thread safety gap in extract_batch(): config could change mid-batch if configure() called concurrently | Acquire lock for entire batch or snapshot config at batch start |

**Positive Observations:**
- **METADATA_DIM=25 contract is the architectural cornerstone** — enforced consistently
- Cyclic yaw encoding (sin/cos) correctly avoids +/-180 degree discontinuity
- Fallback chain for field names handles different input formats gracefully
- KAST ratio/percentage detection (auto-converts ratio to percentage) — excellent safety check

---

### 4.3 `base_features.py` — Match-Level Feature Aggregation

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 189 |
| Classes | 1 (HeuristicConfig) |
| Functions/Methods | 3 |
| Cyclomatic Complexity (max) | 6 |
| Import Count | 5 |
| Test Coverage | Cross-ref Report 8: test_features.py |

**Architecture & Design:**
Provides HeuristicConfig dataclass for feature normalization bounds, with JSON serialization. `extract_match_stats()` aggregates per-round DataFrames into match-level features using means, stds, and the unified HLTV 2.0 rating.

**Correctness Analysis:**
F2-28 (econ rating formula) is FIXED: previously summed ADR (already averages), now correctly uses mean ADR. JSON load failure handling catches all exceptions and silently returns defaults. This makes "file not found" (expected on first run) and "file corrupted" (unexpected) indistinguishable.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-15-01 | LOW | Error Handling | JSON load failure silently returns defaults for all error types. Cannot distinguish "first run" from "file corrupted" | Catch FileNotFoundError separately |
| R4-15-02 | INFO | Correctness | F2-28 econ rating formula FIXED — uses mean ADR correctly | None — fix confirmed |

**Positive Observations:**
- `np.nan_to_num()` handles NaN from single-row `.std()` — defensive
- HLTV 2.0 rating integration via imported function — single source of truth

---

### 4.4 `kast.py` — Kill/Assist/Survive/Trade Calculation

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 162 |
| Classes | 0 |
| Functions/Methods | 3 |
| Cyclomatic Complexity (max) | 10 |
| Import Count | 3 |
| Test Coverage | Cross-ref Report 8: test_feature_kast_roles.py |

**Architecture & Design:**
Three functions for KAST: per-round calculation (from death events), percentage aggregation (across rounds), and heuristic estimation (from aggregate stats only).

**Correctness Analysis:**
F2-35: The `estimate_kast_from_stats()` function uses a 0.8 weighting on assists to reduce double-counting. This heuristic is acknowledged as empirically derived with no formal statistical source. The O(deaths^2) trade detection is acceptable for typical round sizes (max ~25 deaths/round).

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-16-01 | LOW | Documentation | F2-35: Assist-weighting heuristic (0.8) acknowledged as unvalidated empirical observation | Make configurable via HeuristicConfig |

**Positive Observations:**
- Clear separation of per-round, percentage, and estimation functions
- Trade detection within KAST aligns with HLTV methodology

---

### 4.5 `rating.py` — Unified HLTV 2.0 Rating

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 178 |
| Classes | 0 |
| Functions/Methods | 5 |
| Cyclomatic Complexity (max) | 6 |
| Import Count | 3 |
| Test Coverage | Cross-ref Report 8: test_features.py, test_round_stats_enrichment.py |

**Architecture & Design:**
Implements the reverse-engineered HLTV 2.0 rating formula (R^2=0.995 vs HLTV published ratings).

Formula: `0.0073*KAST + 0.3591*KPR - 0.5329*DPR + 0.2372*Impact + 0.0032*ADR + 0.1587`

**Correctness Analysis:**
The KAST ratio/percentage guard is EXCELLENT: it detects at runtime whether the caller passed KAST as a ratio (0-1) or percentage (0-100), and auto-converts with a warning. This prevents a silent 100x error. F2-39: `compute_hltv2_rating_regression()` is dead code kept for reference.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-17-01 | LOW | Maintainability | F2-39: compute_hltv2_rating_regression() is dead code kept "for reference" | Mark with @deprecated or move to tests/ |
| R4-17-02 | INFO | Correctness | KAST ratio/percentage auto-detection guard is exemplary safety engineering | None — best practice |

**Positive Observations:**
- R^2=0.995 regression accuracy against HLTV published ratings — exceptional
- Runtime KAST format detection prevents silent 100x error
- Component-based rating allows per-factor coaching analysis

---

### 4.6 `role_features.py` — Role Classification and Feature Extraction

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 222 |
| Classes | 0 |
| Functions/Methods | 4 |
| Cyclomatic Complexity (max) | 8 |
| Import Count | 5 |
| Test Coverage | Cross-ref Report 8: test_feature_kast_roles.py |

**Architecture & Design:**
Classifies players into 5 roles (Entry, AWPer, Support, Lurker, IGL) using a learned RoleClassifier with a heuristic centroid-distance fallback. Static ROLE_SIGNATURES define centroid positions in 5D feature space.

**Correctness Analysis:**
F2-20: ROLE_SIGNATURES are hardcoded based on "top 20 HLTV players in each role." These centroids do not adapt to meta shifts. The `meta_drift.py` module exists independently but is not integrated with role classification. P3-09: Near-zero normalization range returns 0.5 (arbitrary midpoint).

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-18-01 | MEDIUM | Correctness | F2-20: Static ROLE_SIGNATURES don't adapt to meta shifts. Detected by meta_drift.py but not integrated | Wire meta_drift detection into role signature updates |
| R4-18-02 | LOW | Correctness | P3-09: Near-zero normalization range returns 0.5 (arbitrary). Acceptable for degenerate cases | Log warning when normalization range collapses |

**Positive Observations:**
- Dual classification strategy: learned model (preferred) with heuristic fallback
- Per-role coaching focus areas provide actionable recommendations

---

## 5. BASELINE MANAGEMENT

### 5.1 `baselines/__init__.py` — Empty Package Placeholder

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 1 |

Empty placeholder. No findings.

---

### 5.2 `pro_baseline.py` — Pro Player Baseline Statistics

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 485 |
| Classes | 1 (TemporalBaselineDecay) |
| Functions/Methods | 7 + 4 nested |
| Cyclomatic Complexity (max) | 12 |
| Import Count | 9 |
| Test Coverage | Cross-ref Report 8: test_baselines.py, test_temporal_baseline.py |

**Architecture & Design:**
Provides pro player baseline statistics (Gaussian distributions with mean/std) for comparison against user performance. Three-tier data source hierarchy: (1) DB — per-match ProPlayerStatCard aggregation; (2) CSV fallback — static CSV file; (3) hardcoded defaults — last resort.

The TemporalBaselineDecay class implements exponential decay with a 90-day half-life: `weight = e^(-0.693 * age_days / 90)`. This ensures recent pro stats (reflecting current meta) are weighted more heavily than historical stats.

**Correctness Analysis:**
F2-45: Division-by-zero guard in meta drift detection uses `max(hist_avg, 1e-6)`. In the degenerate case where all pro ratings are 0.0, the guard computes `0/1e-6 = 0`, which appears stable. But the underlying issue (all ratings are zero) indicates a data quality problem that should trigger an alarm, not a silent recovery.

**Memory Exhaustion Risk (HIGH):** `get_pro_positions()` loads ALL pro player positions into memory before downsampling. For large pro databases (millions of ticks across hundreds of matches), this could exceed available RAM. Should use reservoir sampling (Knuth's Algorithm R) for bounded memory.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-20-01 | HIGH | Performance | PARTIALLY FIXED: Memory exhaustion risk in get_pro_positions(). Per-match limits added but reservoir sampling not yet implemented | Use reservoir sampling (Algorithm R) for bounded memory |
| R4-20-02 | MEDIUM | Correctness | F2-45: Division-by-zero guard masks data quality issues. Zero ratings appear "stable" but indicate missing data | Add explicit check: if all ratings zero, return baseline_quality="degraded" |
| R4-20-03 | LOW | Correctness | K/D ratio floor max(0.1, dpr) artificially clamps extreme performers | Reduce DPR floor to 0.01 and document |

**Positive Observations:**
- Three-tier fallback (DB -> CSV -> defaults) ensures coaching always has baseline data
- Temporal decay (90-day half-life) adapts to meta shifts
- Map-specific baselines supported
- `detect_meta_shift()` flags significant changes (>5% drift)

---

### 5.3 `meta_drift.py` — Meta Shift Detection

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 126 |
| Classes | 1 (MetaDriftEngine) |
| Functions/Methods | 3 static |
| Cyclomatic Complexity (max) | 6 |
| Import Count | 4 |
| Test Coverage | Cross-ref Report 8: test_drift_and_heuristics.py |

**Architecture & Design:**
Detects CS2 meta shifts through two complementary signals: (1) statistical drift (40% weight); (2) spatial drift via centroid distance (60% weight). Combined into a single drift coefficient (0.0 = stable, 1.0 = chaos).

**Correctness Analysis:**
F2-44: Tuple handling for spatial positions filters None and checks len(p) == 2, but does not validate that individual tuple elements are non-None. A tuple like (None, 123.5) passes the length check but fails during computation.

Spatial drift normalization uses a fixed 500-unit threshold (dist / 500.0). This is arbitrary and does not scale with map size. Centroid drift assumes 2D positions are normally distributed; in practice, pro positions cluster around sites (bimodal distribution).

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-21-01 | ~~MEDIUM~~ | ~~Correctness~~ | ~~RESOLVED — tuple validation now checks individual elements for None~~ | ~~Add p[0] is not None and p[1] is not None guard~~ |
| R4-21-02 | MEDIUM | Correctness | Spatial drift normalization arbitrary (500 units = 1.0). Not scaled to map dimensions | Use map_extent from config |

**Positive Observations:**
- Dual-signal approach (40% stat + 60% spatial) provides robust drift detection
- Confidence adjustment multiplier (1.0 - drift*0.5) gracefully reduces coaching certainty during meta shifts
- Static methods — thread-safe

---

### 5.4 `nickname_resolver.py` — Pro Player Name Matching

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 129 |
| Classes | 1 (NicknameResolver) |
| Functions/Methods | 3 static |
| Cyclomatic Complexity (max) | 6 |
| Import Count | 4 |
| Test Coverage | Cross-ref Report 8: test_baselines.py (partial) |

**Architecture & Design:**
Resolves demo nicknames to HLTV Pro Player IDs via three-tier matching: exact (O(1) DB lookup) -> substring (loads all pros) -> fuzzy (SequenceMatcher with 0.8 threshold).

**Correctness Analysis:**
F2-41: For substring and fuzzy matching, the entire ProPlayer table is loaded into memory for each resolution call. In batch processing, this creates O(n^2) database access. The fuzzy matcher uses SequenceMatcher.ratio() (Gestalt Pattern Matching), NOT Levenshtein distance.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-22-01 | LOW | Performance | F2-41: O(n^2) complexity for batch resolution — loads all pros per call | Build one-time in-memory index |

**Positive Observations:**
- Three-tier matching chain provides good coverage
- `_clean()` strips team tags and special characters
- 0.8 fuzzy threshold prevents false positives

---

### 5.5 `role_thresholds.py` — Anti-Mock Threshold Learning

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 279 |
| Classes | 2 (LearnedThreshold, RoleThresholdStore) + factory |
| Functions/Methods | 8 |
| Cyclomatic Complexity (max) | 8 |
| Import Count | 7 |
| Test Coverage | Cross-ref Report 8: test_baselines.py |

**Architecture & Design:**
Implements the "anti-mock principle" — all role classification thresholds start as None (unknown) and must be learned from real data. Cold-start detection requires 10+ samples AND 3+ valid thresholds. Thread-safe singleton via double-checked locking.

**Correctness Analysis:**
F2-19: `validate_consistency()` is a placeholder — returns True unconditionally despite docstring promising partition consistency checks. The learning logic uses percentiles (70th for Entry, 75th for AWP) without justification.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-23-01 | MEDIUM | Correctness | F2-19: validate_consistency() returns True unconditionally. Partition consistency check not implemented | Implement overlap/gap detection for role boundaries |

**Positive Observations:**
- Anti-mock principle is excellent design philosophy
- Cold-start detection prevents premature classification
- Thread-safe singleton with double-checked locking
- Persistence to/from database ensures thresholds survive restarts

---

## 6. DATA VALIDATION PIPELINE

### 6.1 `validation/__init__.py` — Simple Re-export Module

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 3 |

Simple re-export module. No findings.

---

### 6.2 `dem_validator.py` — Demo File Validation (6-Layer Hierarchy)

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 201 |
| Classes | 1 (DEMValidator) |
| Functions/Methods | 7 (1 public + 6 private) |
| Cyclomatic Complexity (max) | 8 |
| Import Count | 5 |
| Test Coverage | Cross-ref Report 8: test_dem_validator.py |

**Architecture & Design:**
Validates CS2/CSGO demo files before ingestion using a 6-layer validation hierarchy:
1. Filename integrity (security: no command injection characters)
2. File existence (readable, not symlink)
3. File size (100 KB - 800 MB range)
4. Magic number (CS2: PBDEMS2\0, CSGO: HL2DEMO\0)
5. Header completeness (16+ bytes for CSGO, 512+ for CS2)
6. Estimated processing time (~1s per 10MB heuristic)

**Correctness Analysis:**
Excellent security awareness: forbids symlinks, command injection characters, double extensions. Each check is independent and fails fast. Clear error messages with context.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-24-01 | INFO | Security | Excellent 6-layer fail-fast validation hierarchy with security-first design | None — exemplary |

**Positive Observations:**
- Security-first design prevents command injection via crafted filenames
- Clear error messages with context (file size in KB vs MB)
- Magic number detection correctly identifies CS2 vs CSGO demos
- Processing time estimation helps UX (progress prediction)

---

### 6.3 `drift.py` — Statistical Drift Detection

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 176 |
| Classes | 2 (DriftReport, DriftMonitor) |
| Functions/Methods | 5 |
| Cyclomatic Complexity (max) | 8 |
| Import Count | 5 |
| Test Coverage | Cross-ref Report 8: test_drift_and_heuristics.py |

**Architecture & Design:**
Statistical drift detection using rolling Z-scores. Two parallel implementations: functional (`detect_feature_drift()`) and OOP (`DriftMonitor` class). Retraining trigger requires 3+ of last 5 reports showing drift (prevents spurious triggers).

**Correctness Analysis:**
Epsilon handling for zero-std (past_std=0 uses epsilon=0.01) prevents division-by-zero but masks data quality issues (all past values identical). The parallel functional + OOP implementations create maintenance burden — should unify. Retraining threshold (60% of recent windows) is hardcoded.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-24-02 | LOW | Maintainability | Two parallel implementations (functional + OOP) create maintenance burden | Unify into single approach |
| R4-24-03 | LOW | Configuration | Retraining threshold (3 of 5 = 60%) hardcoded | Make configurable |

**Positive Observations:**
- Rolling Z-score approach is standard statistical practice
- Retraining trigger requires sustained drift (3 of 5), preventing spurious triggers
- DriftReport dataclass provides structured output

---

### 6.4 `sanity.py` — Statistical Plausibility Validation

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 116 |
| Classes | 0 |
| Functions/Methods | 4 |
| Cyclomatic Complexity (max) | 6 |
| Import Count | 3 |
| Test Coverage | Cross-ref Report 8: test_dem_validator.py (partial) |

**Architecture & Design:**
Validates statistical plausibility of demo stats with per-round limits: kills (0-10), deaths (0-10), assists (0-10), ADR (0-200), headshot_pct (0-100), KAST (0-100). Two modes: strict (raise error) vs trim (clamp outliers).

**Correctness Analysis:**
KAST limit is (0.0, 100.0) — but the column semantics are ambiguous. Is KAST stored as ratio (0-1) or percentage (0-100)? The vectorizer's `extract()` computes KAST as ratio, but the sanity check expects percentage range. This discrepancy could allow invalid values to pass validation or incorrectly reject valid values.

Trim mode uses `.clip()` which modifies values in-place, destroying information. Clamping 15 kills to 10 silently — should flag these rows for review.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-24-04 | MEDIUM | Correctness | KAST limits (0-100) semantics ambiguous — ratio vs percentage interpretation inconsistent across modules | Document explicitly as percentage (0-100) and validate consistently |
| R4-24-05 | LOW | Data Integrity | Trim mode silently clamps outliers, destroying information | Log which rows were trimmed for audit trail |

**Positive Observations:**
- Per-round limits are reasonable for CS2 gameplay mechanics
- Dual-mode (strict/trim) provides flexibility for different contexts

---

### 6.5 `schema.py` — Versioned Schema Registry

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 95 |
| Classes | 0 |
| Functions/Methods | 3 |
| Cyclomatic Complexity (max) | 5 |
| Import Count | 3 |
| Test Coverage | Cross-ref Report 8: test_dem_validator.py (partial) |

**Architecture & Design:**
Versioned schema for demo parser output (V1: core stats, V2: HLTV 2.0 extensions with accuracy). Validates both column existence and type correctness.

**Correctness Analysis:**
F2-48: Fractional integer detection checks `.mod(1) != 0` after `.dropna()` — code is actually CORRECT. The verbose type checking (numeric dtype check then fractional check) is sound but could be simplified. No deprecation policy for old schema versions.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-24-06 | LOW | Maintainability | F2-48: Type checking is correct but verbose. No deprecation policy for V1 | Document minimum supported version |

**Positive Observations:**
- Schema versioning allows parser evolution without breaking validators
- Both column existence and type correctness are validated
- Forward-compatible design

---

## 7. HOPFIELD NETWORK LAYER

### 7.1 `hflayers.py` — Modern Hopfield Network Implementation

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 117 |
| Classes | 1 (Hopfield) |
| Functions/Methods | 2 (__init__, forward) |
| Cyclomatic Complexity (max) | 4 |
| Import Count | 3 |
| Test Coverage | Cross-ref Report 8: test_nn_extensions.py (partial) |

**Architecture & Design:**
First-principles implementation of the Modern Hopfield Network (Ramsauer et al., 2020), replacing the missing `hflayers` library. Uses scaled dot-product attention with a learnable memory bank of 512 stored patterns. Used in the RAP Coach memory layer (LTC -> Hopfield).

Architecture:
```
Hopfield(input_size, output_size, num_heads, stored_pattern_size)
+-- Memory: fixed bank of 512 learned patterns (keys/values)
+-- Forward Pass:
    1. Project input -> queries (linear projection)
    2. Compute attention scores (Q @ K.T * scaling)
    3. Apply softmax
    4. Aggregate values (Attn @ V)
    5. Project output (linear projection)
```

**Correctness Analysis:**

~~**Scaling Factor Error (HIGH):** Line 37 uses `scaling = 1.0 / math.sqrt(stored_pattern_size)`, but the standard Transformer scaling (Vaswani et al., 2017) uses `1.0 / sqrt(head_dim)` where `head_dim = stored_pattern_size / num_heads`.~~ **NOTE (R4-25-01 INCORRECT):** Upon re-examination, `stored_pattern_size` in this implementation IS the per-head dimension, not the total dimension across heads. The scaling factor `1.0 / math.sqrt(stored_pattern_size)` is therefore correct and matches the standard Transformer scaling convention. The original analysis incorrectly assumed stored_pattern_size represented the full multi-head dimension.

**Fixed Memory Size:** 512 memory slots are hardcoded. This is not configurable and may be a bottleneck for large sequence lengths or complex tactical patterns.

**Static Memory:** Memory keys/values are learned parameters but are NOT updated during training in any special way — they are standard `nn.Parameter` objects trained via backpropagation. The documentation suggests "store prototype rounds" but the learning mechanism is just gradient descent on fixed-size embeddings. No mechanism for explicit pattern injection or context-dependent memory.

**Findings for this file:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-25-01 | ~~HIGH~~ | ~~Correctness~~ | ~~INCORRECT — stored_pattern_size IS the per-head dimension in this implementation; scaling is correct~~ | ~~Use `math.sqrt(stored_pattern_size / num_heads)`~~ |
| R4-25-02 | MEDIUM | Architecture | Fixed memory size (512 patterns) hardcoded. Not configurable for different use cases | Make memory_slots a constructor parameter |
| R4-25-03 | LOW | Documentation | No unit tests or usage examples. Integration with RAP Coach memory layer not validated independently | Add standalone test with known attention patterns |

**Positive Observations:**
- First-principles implementation avoids dependency on unmaintained library
- Multi-head attention support via view reshaping
- Standard PyTorch nn.Module — compatible with training infrastructure

---

## 8. DOCUMENTATION ASSESSMENT

### 8.1 README Files (9 files)

The processing, feature_engineering, and baselines directories each have README files in three languages (EN, IT, PT). These provide:
- Module purpose and architecture overview
- Key class/function descriptions
- Usage examples
- Cross-references to related modules

**Quality Assessment:**
- READMEs are well-maintained and reflect current architecture
- Three-language support (English, Italian, Portuguese) is consistent
- Code examples are present but not always runnable (missing import context)
- No automated freshness checks — READMEs could drift from code

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R4-26-01 | LOW | Documentation | README code examples lack import context — not directly runnable | Add complete import blocks to examples |

---

## 9. CONSOLIDATED FINDINGS MATRIX

### Findings by Severity

#### HIGH Findings

| ID | File | Category | Finding | Impact | Recommendation | Cross-Ref |
|----|------|----------|---------|--------|----------------|-----------|
| R4-04-01 | state_reconstructor.py | Correctness | Training/inference skew: knowledge=None creates wallhack-equivalent training inputs | Model trains on information unavailable at inference, degrading real-world performance | Require knowledge parameter or auto-build from tick history | C-01 |
| R4-04-02 | state_reconstructor.py | ~~Correctness~~ | ~~RESOLVED — METADATA_DIM assertion now in state_reconstructor.py lines 76-81~~ | ~~Silent dimension mismatch propagates to model, causing cryptic errors~~ | ~~Add shape assertion~~ | C-01 |
| R4-11-01 | connect_map_context.py | ~~Architecture~~ | ~~RESOLVED — Z-penalty constants now imported from core.spatial_data~~ | ~~Constants drift silently if spatial_data changes~~ | ~~Import from core.spatial_data~~ | F2-46 |
| R4-14-01 | vectorizer.py | Correctness | Silent (0,0,0) position fallback contaminates training data | Ambiguous position values corrupt model learning | Validate against map bounds | F2-15 |
| R4-20-01 | pro_baseline.py | Performance | PARTIALLY FIXED: get_pro_positions() per-match limits added but reservoir sampling not yet implemented | OOM risk reduced but not eliminated on very large datasets | Use reservoir sampling | — |
| R4-25-01 | hflayers.py | ~~Correctness~~ | ~~INCORRECT — stored_pattern_size IS the per-head dimension in this implementation; scaling is correct~~ | ~~Attention distribution too uniform, reducing memory retrieval precision~~ | ~~Use sqrt(stored_pattern_size / num_heads)~~ | — |

#### MEDIUM Findings

| ID | File | Category | Finding | Impact | Recommendation | Cross-Ref |
|----|------|----------|---------|--------|----------------|-----------|
| R4-02-01 | tensor_factory.py | Correctness | No metadata shape assertion | Silent shape errors | Add assertion | F2-02 |
| R4-02-03 | tensor_factory.py | Reliability | scipy hard import fails if not installed | Crash on minimal installs | Lazy import | F2-04 |
| R4-03-01 | data_pipeline.py | Correctness | data_quality column semantics unclear | Ambiguous filtering | Add enum/docstring | C-04 |
| R4-03-05 | data_pipeline.py | ~~Correctness~~ | ~~RESOLVED — 50K truncation now emits logger.warning~~ | ~~Data loss undetected~~ | ~~Log warning~~ | — |
| R4-06-02 | player_knowledge.py | Correctness | Entity_id=-1 matching within 50-unit radius fragile | Utility zone mismatches | Increase radius or add temporal correlation | C-10 |
| R4-07-01 | round_stats_builder.py | Correctness | Flash assist window assumes 64 Hz | Incorrect window on 128 Hz demos | Derive from tick_rate | — |
| R4-07-02 | round_stats_builder.py | Reliability | Team mapping assumes demoparser2 convention | Silent breakage if convention changes | Add validation | — |
| R4-08-01 | skill_assessment.py | Documentation | Sigmoid coefficient 1.702 undocumented | Unverifiable design decision | Cite source | — |
| R4-08-02 | skill_assessment.py | Correctness | Positioning axis uses outcome stats as proxy | Passive play scores high | Add spatial metrics | — |
| R4-10-01 | cv_framebuffer.py | Security | File path opened without validation | Path traversal possible | Validate path | — |
| R4-11-02 | connect_map_context.py | Correctness | Fixed 4000-unit normalization cap | Distances exceed 1.0 on some maps | Use per-map max_distance | — |
| R4-12-01 | external_analytics.py | Correctness | is_healthy() inconsistent with result dict | Silent coaching failures | Verify columns in is_healthy() | — |
| R4-12-02 | external_analytics.py | Correctness | NaN propagation from empty columns | Silent NaN in Z-scores | Add isnan() check | — |
| R4-14-02 | vectorizer.py | Error Handling | NaN/Inf warning after clamp masks upstream bugs | Hidden upstream errors | Raise or count errors | F2-16 |
| R4-14-03 | vectorizer.py | Concurrency | Config could change mid-batch | Training skew within batch | Snapshot config at batch start | — |
| R4-18-01 | role_features.py | Correctness | Static role signatures don't adapt to meta | Outdated coaching during meta shifts | Wire meta_drift integration | F2-20 |
| R4-20-02 | pro_baseline.py | Correctness | Div-by-zero guard masks data quality issues | Missing data appears stable | Add explicit quality check | F2-45 |
| R4-21-01 | meta_drift.py | ~~Correctness~~ | ~~RESOLVED — tuple validation now checks individual elements for None~~ | ~~Crash on (None, value) tuples~~ | ~~Add element-level None check~~ | F2-44 |
| R4-21-02 | meta_drift.py | Correctness | Spatial drift scale arbitrary (500 units) | Inconsistent drift detection across maps | Scale by map extent | — |
| R4-23-01 | role_thresholds.py | Correctness | validate_consistency() always returns True | Overlapping role boundaries undetected | Implement partition check | F2-19 |
| R4-24-04 | sanity.py | Correctness | KAST limits ambiguous (ratio vs percentage) | Incorrect validation | Document as percentage | — |
| R4-25-02 | hflayers.py | Architecture | Fixed 512 memory slots hardcoded | May limit representation capacity | Make configurable | — |

#### LOW Findings

| ID | File | Category | Finding | Cross-Ref |
|----|------|----------|---------|-----------|
| R4-02-02 | tensor_factory.py | Compatibility | Training/inference resolution distribution shift | F2-03 |
| R4-03-02 | data_pipeline.py | Correctness | Player decontamination tie-break arbitrary | C-06 |
| R4-03-03 | data_pipeline.py | Maintainability | IQR multiplier 3.0 undocumented | P3-11 |
| R4-03-04 | data_pipeline.py | Reliability | Chunk size 500 near SQLite limit | F2-22 |
| R4-05-01 | heatmap_engine.py | Maintainability | Double Y-inversion confusing | — |
| R4-05-03 | heatmap_engine.py | Reliability | No resolution range guard | — |
| R4-06-01 | player_knowledge.py | Configuration | Z-level threshold hardcoded | — |
| R4-06-03 | player_knowledge.py | Compatibility | tick_rate default inconsistency | P3-05 |
| R4-07-03 | round_stats_builder.py | Correctness | Warmup ticks may contaminate round 1 | F2-10 |
| R4-08-03 | skill_assessment.py | Correctness | Curriculum level truncation bias | — |
| R4-09-01 | tick_enrichment.py | Configuration | FOV default 90 degrees assumes widescreen | — |
| R4-10-02 | cv_framebuffer.py | Reliability | No frame size validation | — |
| R4-11-03 | connect_map_context.py | Documentation | Z-penalty rationale undocumented | — |
| R4-12-03 | external_analytics.py | Maintainability | Fixed Z-score features | — |
| R4-15-01 | base_features.py | Error Handling | JSON load failure undifferentiated | — |
| R4-16-01 | kast.py | Documentation | Assist-weighting heuristic unvalidated | F2-35 |
| R4-17-01 | rating.py | Maintainability | Dead code kept for reference | F2-39 |
| R4-18-02 | role_features.py | Correctness | Near-zero normalization range | P3-09 |
| R4-20-03 | pro_baseline.py | Correctness | K/D ratio floor too aggressive | — |
| R4-22-01 | nickname_resolver.py | Performance | O(n^2) batch resolution | F2-41 |
| R4-24-02 | drift.py | Maintainability | Parallel functional+OOP implementations | — |
| R4-24-03 | drift.py | Configuration | Retraining threshold hardcoded | — |
| R4-24-05 | sanity.py | Data Integrity | Trim mode destroys information silently | — |
| R4-24-06 | schema.py | Maintainability | No V1 deprecation policy | F2-48 |
| R4-25-03 | hflayers.py | Documentation | No standalone tests or usage examples | — |
| R4-26-01 | READMEs | Documentation | Code examples lack import context | — |

#### INFO Findings

| ID | File | Category | Finding |
|----|------|----------|---------|
| R4-01-01 | processing/__init__.py | Architecture | Clean public API surface |
| R4-05-02 | heatmap_engine.py | Architecture | Well-separated thread safety pattern |
| R4-09-02 | tick_enrichment.py | Performance | C-02 vectorization — excellent 10x speedup |
| R4-13-01 | feature_engineering/__init__.py | Architecture | Lazy import pattern for optional dependencies |
| R4-15-02 | base_features.py | Correctness | F2-28 econ rating formula FIXED |
| R4-17-02 | rating.py | Correctness | KAST ratio/percentage guard — exemplary |
| R4-24-01 | dem_validator.py | Security | Excellent 6-layer fail-fast validation |

### Findings by Category

| Category | CRIT | HIGH | MED | LOW | INFO | Total |
|----------|------|------|-----|-----|------|-------|
| Correctness | 0 | 4 | 13 | 6 | 3 | 26 |
| Architecture | 0 | 1 | 1 | 0 | 3 | 5 |
| Performance | 0 | 1 | 0 | 1 | 1 | 3 |
| Concurrency | 0 | 0 | 1 | 0 | 0 | 1 |
| Security | 0 | 0 | 1 | 0 | 1 | 2 |
| Reliability | 0 | 0 | 2 | 3 | 0 | 5 |
| Maintainability | 0 | 0 | 0 | 6 | 0 | 6 |
| Documentation | 0 | 0 | 1 | 3 | 0 | 4 |
| Error Handling | 0 | 0 | 1 | 1 | 0 | 2 |
| Configuration | 0 | 0 | 0 | 3 | 0 | 3 |
| Compatibility | 0 | 0 | 0 | 2 | 0 | 2 |
| Data Integrity | 0 | 0 | 1 | 1 | 0 | 2 |
| **Total** | **0** | **6** | **21** | **26** | **8** | **61** |

### Findings Trend (vs Prior Remediation)

| Phase | Issues Fixed | Issues Remaining in This Audit |
|-------|-------------|-------------------------------|
| Phase 2 (Processing Pipeline) | 42 fixed | 22 findings reference F2-codes |
| Pipeline Audit (C-codes) | 14 fixed, 67 new | 6 C-codes cross-referenced |
| G-Issues (post-review) | G-02 (danger zone), G-05 (calibration) | G-05 deferred (requires pro data) |

---

## 10. RECOMMENDATIONS

### Immediate Actions (HIGH — Fix Within Current Sprint)

1. ~~**Fix Hopfield scaling factor** (R4-25-01): INCORRECT — stored_pattern_size IS the per-head dimension in this implementation; scaling is correct. No action needed.~~

2. **Resolve (0,0,0) position ambiguity** (R4-14-01): In vectorizer.py, validate positions against map bounds instead of treating (0,0,0) as missing. Use `map_bounds.contains(pos)` from spatial_data or flag as unknown.

3. **Fix training/inference skew** (R4-04-01): In state_reconstructor.py, either require knowledge parameter (fail-fast) or auto-construct PlayerKnowledge from tick history. The current silent fallback to legacy mode creates distributional mismatch.

4. ~~**Add METADATA_DIM assertion** (R4-04-02): RESOLVED — assertion now in state_reconstructor.py lines 76-81.~~

5. ~~**Import Z-penalty constants** (R4-11-01): RESOLVED — Z-penalty constants now imported from core.spatial_data.~~

6. **Bound pro position loading** (R4-20-01): PARTIALLY FIXED — per-match limits added to get_pro_positions(), but reservoir sampling not yet implemented. Remaining risk reduced but not eliminated on very large datasets.

### Short-Term Actions (MEDIUM — Fix Within Next 2 Sprints)

7. **Parameterize tick rate constants**: Flash assist window (R4-07-01), hearing range (R4-06-03), FOV (R4-09-01) should all derive from demo header tick rate.

8. **Integrate meta_drift into role_features** (R4-18-01): Wire MetaDriftEngine detection into ROLE_SIGNATURES updates so role centroids evolve with the meta.

9. **Fix is_healthy() semantics** (R4-12-01): Verify required columns exist in is_healthy(), not just dataset count.

10. **Add NaN propagation guards** (R4-12-02, R4-14-02): Check for NaN after computation, not just zero-division.

11. **Implement validate_consistency()** (R4-23-01): In role_thresholds.py, verify learned thresholds form a valid partition (no gaps, no overlaps).

12. **Resolve KAST semantics** (R4-24-04): Document explicitly across all modules whether KAST is ratio (0-1) or percentage (0-100), and validate consistently.

13. **Make Hopfield memory configurable** (R4-25-02): Add memory_slots constructor parameter to hflayers.py.

### Long-Term Actions (LOW + Strategic)

14. **Add spatial positioning metrics** (R4-08-02): Supplement outcome-based positioning axis with actual spatial metrics (distance to site, angle advantage, crosshair placement).

15. **Cache NicknameResolver roster** (R4-22-01): Build one-time in-memory index at startup to avoid O(n^2) batch resolution.

16. **Unify drift detection API** (R4-24-02): Consolidate functional and OOP implementations into single interface.

17. **Use per-map distance normalization** (R4-11-02): Replace fixed 4000-unit cap with map-specific extents from map_config.json.

18. **Document all magic constants**: Sigmoid coefficient 1.702 (R4-08-01), Z-penalty 2.0/200 (R4-11-03), IQR 3.0 (R4-03-03), assist weight 0.8 (R4-16-01).

### Architectural Recommendations

19. **Establish Dimensional Contract Tests**: Create automated tests that verify METADATA_DIM=25 is maintained at every boundary (vectorizer output, tensor_factory input, model input layer). A single parameterized test that traces a dummy tick through the entire pipeline would catch dimension drift.

20. **Centralize Tick Rate Configuration**: Create a `TickRateConfig` dataclass that auto-detects from demo headers and propagates to all tick-rate-dependent computations. Eliminates the scattered 64 Hz assumptions.

21. **Implement Feature Registry**: Create a registry that maps feature index (0-24) to feature name, normalization range, and source function. This would enable automated feature drift detection and self-documenting feature vectors.

---

## APPENDIX A: COMPLETE FILE INVENTORY

| # | File Path | LOC | Classes | Functions | Findings |
|---|-----------|-----|---------|-----------|----------|
| 1 | processing/__init__.py | 28 | 0 | 0 | 1 (I) |
| 2 | processing/tensor_factory.py | 319 | 1 | 12 | 3 (M/L/M) |
| 3 | processing/data_pipeline.py | 547 | 1 | 18 | 5 (M/L/L/L/M) |
| 4 | processing/state_reconstructor.py | 89 | 0 | 2 | 2 (H/H) |
| 5 | processing/heatmap_engine.py | 295 | 3 | 6 | 3 (L/I/L) |
| 6 | processing/player_knowledge.py | 575 | 6 | 12 | 3 (L/M/L) |
| 7 | processing/round_stats_builder.py | 519 | 0 | 10 | 3 (M/M/L) |
| 8 | processing/skill_assessment.py | 147 | 2 | 5 | 3 (M/M/L) |
| 9 | processing/tick_enrichment.py | 362 | 0 | 6 | 2 (L/I) |
| 10 | processing/cv_framebuffer.py | 183 | 1 | 6 | 2 (M/L) |
| 11 | processing/connect_map_context.py | 116 | 0 | 2 | 3 (H/M/L) |
| 12 | processing/external_analytics.py | 166 | 1 | 12 | 3 (M/M/L) |
| 13 | feature_engineering/__init__.py | 58 | 0 | 1 | 1 (I) |
| 14 | feature_engineering/vectorizer.py | 379 | 1 | 6 | 3 (H/M/M) |
| 15 | feature_engineering/base_features.py | 189 | 1 | 3 | 2 (L/I) |
| 16 | feature_engineering/kast.py | 162 | 0 | 3 | 1 (L) |
| 17 | feature_engineering/rating.py | 178 | 0 | 5 | 2 (L/I) |
| 18 | feature_engineering/role_features.py | 222 | 0 | 4 | 2 (M/L) |
| 19 | baselines/__init__.py | 1 | 0 | 0 | 0 |
| 20 | baselines/pro_baseline.py | 485 | 1 | 11 | 3 (H/M/L) |
| 21 | baselines/meta_drift.py | 126 | 1 | 3 | 2 (M/M) |
| 22 | baselines/nickname_resolver.py | 129 | 1 | 3 | 1 (L) |
| 23 | baselines/role_thresholds.py | 279 | 2 | 8 | 1 (M) |
| 24 | validation/__init__.py | 3 | 0 | 0 | 0 |
| 25 | validation/dem_validator.py | 201 | 1 | 7 | 1 (I) |
| 26 | validation/drift.py | 176 | 2 | 5 | 2 (L/L) |
| 27 | validation/sanity.py | 116 | 0 | 4 | 2 (M/L) |
| 28 | validation/schema.py | 95 | 0 | 3 | 1 (L) |
| 29 | hflayers.py | 117 | 1 | 2 | 3 (H/M/L) |
| 30-38 | READMEs (9 files) | ~450 | 0 | 0 | 1 (L) |

---

## APPENDIX B: GLOSSARY

| Term | Definition |
|------|-----------|
| METADATA_DIM | The 25-dimensional feature vector contract. Every feature vector in the system has exactly 25 elements |
| FOV | Field of View — the angular extent of the player's visible area (default: 90 degrees horizontal) |
| KAST | Kill, Assist, Survive, or Trade — per-round binary metric indicating player contribution |
| HLTV 2.0 Rating | Reverse-engineered rating formula matching HLTV.org's published player ratings (R^2=0.995) |
| Z-Penalty | Distance penalty applied on multi-level maps (Nuke, Vertigo) when players are on different floors |
| NO-WALLHACK | Principle that the coaching AI must never see information a legitimate player could not perceive |
| PlayerKnowledge | The perception state representing what a player can see, hear, and remember at a given tick |
| TensorFactory | Singleton that converts tick data into view tensors (visual) and metadata tensors (statistical) |
| FeatureExtractor | The vectorizer that produces the 25-dimensional feature vector from raw tick data |
| Pro Baseline | Statistical distributions (mean/std) of pro player performance, used for comparison |
| Meta Drift | Changes in the CS2 competitive meta that affect baseline relevance and coaching accuracy |
| Temporal Decay | Exponential decay with 90-day half-life applied to pro baseline weights |
| IQR | Interquartile Range — used for outlier detection in data pipeline (Q3-Q1, multiplier 3.0) |
| Reservoir Sampling | Algorithm for randomly sampling k items from a stream of unknown length in O(k) memory |
| Hopfield Network | Modern associative memory network using scaled dot-product attention (Ramsauer et al., 2020) |
| COPER | Coaching paradigm: Correction + Observation + Practice + Experience + Reflection |

---

## APPENDIX C: CROSS-REFERENCE INDEX

| Finding ID | Remediation Code | Status |
|------------|-----------------|--------|
| R4-02-01 | F2-02 | Open — no assertion added |
| R4-02-02 | F2-03 | Known limitation — documented |
| R4-02-03 | F2-04 | Open — scipy hard import |
| R4-03-01 | C-04 | Open — semantics undocumented |
| R4-03-02 | C-06 | Fixed — decontamination works, tie-break arbitrary |
| R4-03-03 | P3-11 | Open — constant undocumented |
| R4-03-04 | F2-22 | Open — chunk size 500 |
| R4-06-02 | C-10 | Partial — 50-unit radius heuristic |
| R4-06-03 | P3-05 | Open — tick rate inconsistency |
| R4-07-03 | F2-10 | Open — warmup ticks |
| R4-11-01 | F2-46 | ~~Resolved — Z-penalty constants now imported from core.spatial_data~~ |
| R4-14-01 | F2-15 | Open — (0,0,0) ambiguity |
| R4-14-02 | F2-16 | Open — NaN clamp |
| R4-16-01 | F2-35 | Open — assist weight |
| R4-17-01 | F2-39 | Open — dead code |
| R4-18-01 | F2-20 | Open — static signatures |
| R4-18-02 | P3-09 | Open — near-zero range |
| R4-20-02 | F2-45 | Open — div-by-zero mask |
| R4-21-01 | F2-44 | ~~Resolved — tuple validation now checks individual elements for None~~ |
| R4-22-01 | F2-41 | Open — O(n^2) |
| R4-23-01 | F2-19 | Open — consistency placeholder |
| R4-24-04 | — | New finding |
| R4-24-06 | F2-48 | Open — verbose type check |

---

## APPENDIX D: DEPENDENCY GRAPH

```
                    +------------------+
                    |  core/config.py  |
                    |  core/constants  |
                    +--------+---------+
                             |
               +-------------+-------------+
               |                           |
    +----------v-----------+    +----------v-----------+
    | processing/          |    | core/spatial_data.py |
    |   tensor_factory.py  |    | core/map_manager.py  |
    +----------+-----------+    +----------+-----------+
               |                           |
    +----------v-----------+    +----------v-----------+
    | feature_engineering/  |    | processing/          |
    |   vectorizer.py      |    |  connect_map_context  |
    |   (METADATA_DIM=25)  |    |  (Z-penalty)         |
    +----------+-----------+    +----------------------+
               |
    +----------v-----------+
    |   base_features.py   |
    |   kast.py             |
    |   rating.py           |
    |   role_features.py    |
    +----------+-----------+
               |
    +----------v-----------+
    | baselines/            |
    |   pro_baseline.py     |
    |   meta_drift.py       |
    |   nickname_resolver   |
    |   role_thresholds     |
    +----------+-----------+
               |
    +----------v-----------+
    | validation/           |
    |   dem_validator.py    |
    |   schema.py           |
    |   sanity.py           |
    |   drift.py            |
    +----------------------+

    +----------------------+
    | processing/          |
    |  player_knowledge.py |----> NO-WALLHACK invariant
    |  state_reconstructor |----> Training/Inference bridge
    |  round_stats_builder |----> Event aggregation
    |  tick_enrichment.py  |----> C-02 vectorized FOV
    |  heatmap_engine.py   |----> Visualization
    |  skill_assessment.py |----> 5-axis decomposition
    |  data_pipeline.py    |----> Train/val/test splitting
    |  cv_framebuffer.py   |----> Video ring buffer
    |  external_analytics  |----> Z-score comparison
    +----------------------+

    +----------------------+
    | hflayers.py          |----> Hopfield memory (used by RAP Coach)
    +----------------------+
```

---

## APPENDIX E: DATA FLOW DIAGRAMS

### E.1 Feature Vector Construction Pipeline

```
Raw Demo (.dem file)
        |
        v
+------------------+
| demoparser2      |  tick-level data: pos_x, pos_y, pos_z, yaw, pitch,
| (demo_parser.py) |  health, armor, weapon, team, ...
+--------+---------+
         |
         v
+------------------+
| round_stats_     |  Per-round aggregation: kills, deaths, assists,
| builder.py       |  ADR, HS%, KAST, opening duels, trade kills
+--------+---------+
         |
         v
+------------------+     +------------------+
| tick_enrichment  |     | player_knowledge |
| .py              |     | .py              |
| (bomb state,     |     | (FOV filtering,  |
|  alive counts,   |     |  memory decay,   |
|  team economy,   |     |  sound events,   |
|  enemies visible)|     |  utility zones)  |
+--------+---------+     +--------+---------+
         |                         |
         +------------+------------+
                      |
                      v
         +------------------+
         | vectorizer.py    |  25-dimensional feature vector
         | (FeatureExtractor)|  [health, armor, ..., economy_ratio]
         +--------+---------+
                  |
                  v
         +------------------+
         | tensor_factory   |  view tensor: (1, 3, 64, 64) or (1, 3, 224, 224)
         | .py              |  metadata tensor: (1, 25)
         +--------+---------+
                  |
                  v
         +------------------+
         | Neural Networks  |  (Report 5)
         | (model.py,       |
         |  rap_coach/,     |
         |  jepa_model.py)  |
         +------------------+
```

### E.2 Baseline Comparison Flow

```
+------------------+     +------------------+     +------------------+
| DB: ProPlayer    |     | CSV: pro_baseline|     | Hardcoded        |
| StatCard table   |     | .csv             |     | defaults         |
+--------+---------+     +--------+---------+     +--------+---------+
         |                         |                         |
         +--------> Tier 1 --------+-------> Tier 2 ---------+---> Tier 3
                      |
                      v
         +------------------+
         | pro_baseline.py  |  Gaussian(mean, std) per metric
         | TemporalDecay    |  90-day half-life weighting
         +--------+---------+
                  |
         +--------+--------+
         |                  |
         v                  v
+------------------+  +------------------+
| skill_assessment |  | meta_drift.py    |
| .py              |  | (40% stat +      |
| (Z-score to      |  |  60% spatial)    |
|  percentile)     |  +------------------+
+------------------+
```

### E.3 Data Validation Pipeline

```
Input: .dem file path
        |
        v
+------------------+
| dem_validator.py |  Fail-fast: filename -> exists -> size -> magic ->
|                  |  header -> time estimate
+--------+---------+
         | PASS
         v
+------------------+
| schema.py        |  Column existence + type validation (V1/V2)
+--------+---------+
         | PASS
         v
+------------------+
| sanity.py        |  Statistical plausibility (kills 0-10, ADR 0-200, etc.)
|                  |  Modes: strict (raise) or trim (clamp)
+--------+---------+
         | PASS
         v
+------------------+
| drift.py         |  Rolling Z-score drift detection
|                  |  Retraining trigger: 3/5 windows drifted
+--------+---------+
         | PASS or DRIFT_DETECTED
         v
+------------------+
| Data Pipeline    |  Temporal split, player decontamination, outlier removal
+------------------+
```

---

*End of Report 4/8 — Feature Engineering, Processing Pipeline, and Data Transformation*
