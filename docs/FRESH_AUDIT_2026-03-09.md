# Fresh Full-Project Audit — 2026-03-09

> Post-remediation audit after completing all 10 batches (114 issues fixed).
> Performed by 6 parallel deep-audit agents across ~80 source files.

## Executive Summary

| Subsystem | HIGH | MEDIUM | LOW | Total |
|-----------|------|--------|-----|-------|
| Core + Config | 4 | 22 | 2 | 28 |
| Data Sources + Ingestion | 3 | 9 | 2 | 14 |
| Processing + Features | 13 | 28 | 2 | 43 |
| Neural Networks | 2 | 22 | 0 | 24 |
| Analysis + Coaching | 8 | 19 | 6 | 33 |
| Storage + Desktop App | 1 | 31 | 8 | 40 |
| **TOTAL** | **31** | **131** | **20** | **182** |

**Validator status:** 291/293 PASS, 0 failed, 2 non-blocking warnings.

---

## HIGH-Severity Issues (31)

### Core + Config (4)

| ID | File | Issue |
|----|------|-------|
| C-01 | config.py | Global module variables not synchronized; daemon threads read stale credentials |
| C-02 | config.py | STORAGE_ROOT reassigned after SETTINGS_PATH uses it; fragile ordering |
| SE-01 | session_engine.py | Zombie threshold log message hardcoded (300) while logic uses dynamic config |
| AT-01 | app_types.py | Dual Team enums allow silent type mismatches (`app_types.Team.CT != demo_frame.Team.CT`) |

### Data Sources + Ingestion (3)

| ID | File | Issue |
|----|------|-------|
| DS-01 | ingestion/demo_loader.py | Pickle deserialization of cache data — potential RCE with local file access |
| DS-02 | backend/ingestion/watcher.py | TOCTOU race between file size check and accessibility check |
| DS-03 | backend/data_sources/steam_api.py | No max total timeout across retries; potential thread pool starvation |

### Processing + Features (13)

| ID | File | Issue |
|----|------|-------|
| P-TF-02 | tensor_factory.py | Missing upper bounds on grid_radius in _draw_circle |
| P-RSB-01 | round_stats_builder.py | Global FLASH_ASSIST_WINDOW_TICKS mutated — race condition in parallel calls |
| P-RSB-03 | round_stats_builder.py | round_won field is forward-looking — data leakage into training features |
| P-PK-02 | player_knowledge.py | enemy_last_seen dict unbounded — O(n²) per match |
| P-SR-01 | state_reconstructor.py | Training vs inference feature parity not validated |
| P-DP-01 | data_pipeline.py | Outlier removal before temporal split — breaks reproducibility |
| P-DP-04 | data_pipeline.py | Scaler double-application if run_pipeline() called twice |
| P-VEC-01 | vectorizer.py | Z-penalty lazy import: training includes it, inference may skip |
| P-VEC-03 | vectorizer.py | Config thread safety: mid-batch config change possible |
| P-PB-01 | pro_baseline.py | K/D division by zero: dpr=0 → inflated ratio via 0.1 floor |
| P-MD-01 | meta_drift.py | Spatial drift normalization depends on data quality, not map size |
| P-X-01 | (cross-cutting) | No single source of truth for feature extraction across train/infer |
| P-X-02 | (cross-cutting) | No shape assertions on generated tensors before model input |

### Neural Networks (2)

| ID | File | Issue |
|----|------|-------|
| NN-JM-01 | jepa_model.py | Batch=1 edge case in topk() during VL forward |
| NN-RM-02 | rap_coach/model.py | No validation that metadata seq_len >= 1 |

### Analysis + Coaching (8)

| ID | File | Issue |
|----|------|-------|
| W-01 | win_probability.py | Heuristic adjustments produce prob > 1.0 before clamp |
| O-02 | analysis_orchestrator.py | tick_data 'team' column accessed without existence check |
| C-01 | coaching_service.py | COPER fallback chain incomplete — Traditional without deviations produces nothing |
| P-03 | profile_service.py | Both API fetches fail → creates empty profile with NULL stats |
| H-03 | hybrid_engine.py | Hardcoded fallback baseline is stale — no version/date annotation |
| E-02 | experience_bank.py | ValueError from base64 decode not caught in retrieve_similar() |
| R-02 | rag_knowledge.py | Seed-based fallback embedding is random, not semantic |
| E-02-alt | entropy_analysis.py | If all probs < 1e-38, entropy silently returns 0 |

### Storage + Desktop App (1)

| ID | File | Issue |
|----|------|-------|
| DG-02 | db_governor.py | PRAGMA quick_check can block indefinitely — no timeout in sync mode |

---

## MEDIUM-Severity Issues (131)

### Core + Config (22)

- C-03: get_secret() silently falls back when keyring unavailable
- C-04: Corrupted settings file silently overwritten on next save
- C-05: Secret handling inconsistency between keyring and in-memory
- C-06: Dead commented-out code in config.py
- SE-02: Daemon threads not joined on shutdown — potential data corruption
- SE-04: No validation that ZOMBIE_TASK_THRESHOLD is positive integer
- SE-05: Backup failure doesn't warn user in UI
- SE-06: Training lock wait blocks all daemons during shutdown
- SE-07: TOCTOU race between refresh_settings() and folder operations
- AT-02: team_from_demo_frame() lacks type hints for input
- REG-01: Registry._mapping has no thread lock
- LOC-01: Home dir hardcoded at import time
- LOC-02: JSON translation fallback priority inversion
- LOC-03: Missing translation key returns raw key name in UI
- PU-01: Drive detection fallback doesn't validate path exists
- PU-02: Platform detection only handles "win" vs non-win
- MM-01: load_map_async() returns None on fallback without warning
- SD-01: Double-checked locking anti-pattern in SpatialConfigLoader
- SD-02: Map config JSON values not validated for numeric types
- SD-03: Ambiguous partial-match in multi-level map lookup
- DF-01: No validation for NaN/Inf player coordinates in PlayerState
- (1 additional misc)

### Data Sources + Ingestion (9)

- DS-04: JSON tournament ingestor doesn't validate field types before arithmetic
- DS-05: Docker manager subprocess path not validated
- DS-06: Dead code patterns in demo_loader.py
- DS-07: HLTV stat_fetcher swallows exceptions at DEBUG level
- DS-08: Registry lock ordering violation (thread lock vs file lock)
- DS-09: Missing null checks on demo parser outputs
- DS-12: MIN_DEMO_SIZE gap (1MB threshold vs real 50MB+ demos)
- DS-14: Nade duration capping has no transparency flag
- (1 additional misc)

### Processing + Features (28)

- P-TF-01: Normalization inverted when max_val < threshold
- P-TF-03: Velocity channel sharp discontinuity at 0.01 threshold
- P-TF-04: FOV mask always uses sigma=1.5, ignoring config.sigma
- P-RSB-02: Invalid team_num players fall through without exclusion
- P-RSB-04: Opening duel detection counts first death in demo, not per-round
- P-RSB-05: FLASH_ASSIST_WINDOW_TICKS fallback not validated
- P-PK-01: Z-level threshold inconsistency between methods
- P-PK-03: Z-coordinate fallback logic incorrect when only z is missing
- P-PK-04: FOV/visibility count mismatch not warned
- P-SR-02: Vision tensor config ignored — uses default instead of model config
- P-DP-02: Player decontamination violates temporal split chronology
- P-DP-03: IQR outlier threshold (3.0) hardcoded without rationale
- P-DP-05: Sklearn scaler compatibility check only at major version
- P-SA-01: GELU comment is misleading (actually sigmoid CDF approximation)
- P-SA-01-2: Zero baseline std produces garbage Z-score
- P-SA-02: Curriculum level edge case at skill=0.0
- P-CVF-01: Ring buffer crashes if buffer_size=0
- P-CVF-02: get_latest() wraps and returns duplicate frames
- P-EA-01: Division by zero in t_z_scores with std=0
- P-EA-02: Missing column check doesn't warn about degraded analysis
- P-EA-03: Regex number extraction fails on scientific notation
- P-VEC-02: NaN/Inf conversion masks upstream bugs
- P-VEC-04: Unknown weapon logging spam
- P-RF-01: Adaptive signatures scaling is inverted (reduces instead of widens)
- P-RF-02: Role classification delegation hides fallback without logging
- P-PB-02: rating_survival assumes linear relationship (incorrect)
- P-PB-03: CSV fallback drops unique columns silently
- P-PB-04: Temporal baseline requires only 10 samples (too few)
- P-MD-02: Division by zero edge case in stat_drift
- P-MD-03: Weighted drift coefficient (40/60) is arbitrary
- P-RT-01: Percentile thresholds inconsistent across roles (75 vs 70)
- P-RT-02: Sample count conflates samples with unique players
- P-RT-03: Thresholds persisted without validation
- P-SAN-01: KAST ratio vs percentage confusion unresolved

### Neural Networks (22)

- NN-JM-02: Dropout active during inference when is_pretrained=False
- NN-JM-03: Heuristic label_tick() path still active — label leakage risk
- NN-JM-04: EMA in-place modification risk if target_encoder unfrozen
- NN-JM-05: Inconsistent device handling in vl_jepa_concept_loss()
- NN-JT-01: Negative sampling permutation OOB risk
- NN-JT-02: Misleading fallback log messages (np.tile reference)
- NN-JT-03: Implicit device placement in load_user_match_sequences()
- NN-TR-01: O(B²) fallback in "vectorized" negative sampling
- NN-TR-02: Empty dataloader silently skips training
- NN-EV-01: SHAP zero-vector baseline bias (F3-18 still live)
- NN-RM-01: Missing skill_vec validation in RAPCoachModel
- NN-RM-03: Gate weights thread safety between forward/loss
- NN-MEM-01: Hopfield early inference returns random prototypes
- NN-MEM-02: NCP wiring uses global np.random seed
- NN-TR-02b: Hardcoded z_axis_penalty_weight=2.0
- NN-TR-03: Target tensor shapes not validated in train_step
- NN-COM-01: Scalar array indexing in generate_advice()
- NN-CV-01: Vague error context on model load failure
- NN-CV-02: Silent tick truncation at 50K without user warning
- NN-CV-03: Peak tick OOB risk in chronovisor scanner
- NN-CTRL-01: Lock release without acquisition in _run_wrapper
- NN-CTRL-02: Race condition on _is_running flag

### Analysis + Coaching (19)

- A-01: Unbound log variable in calibrate_threat_decay()
- A-02: Thread safety in death estimator singleton
- B-01: Missing error handling in blind spot detect()
- D-01: Index bounds edge case in _detect_flash_baits()
- E-01: _grid_buffer not thread-safe
- W-02: Model always starts untrained (checkpoint may fail silently)
- W-03: utility_remaining normalized to /10 (max is 5 items)
- O-01: Module failure counter never resets per match
- O-03: Engagement analysis missing map metadata
- R-01: Role consensus threshold (0.1) is arbitrary
- R-03: _neural_classify() doesn't validate model output shape
- C-02: Type mismatch — tick_data can be dict or DataFrame
- C-03: Unused import — infer_round_phase imported but reimplemented
- P-01: profile_service fetch_steam_stats has no retry
- P-02: Missing length check on players[0] in Steam response
- H-01: Lazy retriever load failure not clearly logged
- H-02: Feature dimension validation missing
- E-01-alt: experience_bank effectiveness_score not capped
- R-01-alt: rag_knowledge version mismatch detection missing

### Storage + Desktop App (31)

- DB-02: Session context manager dirty state on commit failure
- DM-01: JSON field validator doesn't check structure
- DM-02: Ext_PlayerPlaystyle conflates profile with playstyle
- DM-04: Unbounded JSON fields for social_links, pc_specs, etc.
- SM-01: Race condition in CoachState singleton get_state()
- SM-02: Silent telemetry failures with no retry
- SM-03: Unbounded ServiceNotification growth
- DG-01: Backup restore doesn't verify backup integrity
- DG-03: Path traversal risk in fallback DB check
- IM-01: Race between file disappearance and enqueue
- IM-02: Stale task recovery doesn't check last_updated timestamp
- IM-03: Event clear-after-wait race condition
- WZ-01: Path traversal via manual text input in wizard
- WZ-02: MDFileManager exception not caught
- WZ-03: Synchronous makedirs can freeze UI on slow storage
- WZ-04: Error message suggests fallback path that may also be locked
- DV-01: Background thread has no cancellation mechanism
- DV-02: DB session potential leak before with block
- DV-03: demo_name not validated for empty string
- TM-01: LRU cache uses plain dict, not OrderedDict
- TM-02: Ghost widget potential leak on recreate
- TM-03: Heatmap generation thread has no timeout
- TM-04: Apex marker init value should be float('-inf')
- WG-01: Matplotlib figure retained after plt.close()
- WG-02: BytesIO buffer not in context manager
- VZ-01: savefig exception propagates despite finally close
- VZ-02: Map image path traversal via map_tensors.json
- RG-01: Report output path not validated for write permission
- RG-02: Absolute filesystem path embedded in Markdown
- RP-01: HMAC key fallback not suitable for production
- LS-01: RotatingFileHandler fallback has no size limit

---

## Comparison with Pre-Remediation State

| Metric | Before (10 audits) | After (fresh audit) |
|--------|--------------------|--------------------|
| HIGH issues | ~114 identified | 31 remaining |
| Issues fixed | — | 114 across 10 batches |
| Validator | 291/293 | 291/293 (stable) |
| Audit documents | 27 files, 16K lines | 1 consolidated report |

**Key improvements:**
- All data contamination issues (Batch 1) resolved
- All concurrency crashes (Batch 2) resolved
- All database migration issues (Batch 3) resolved
- All critical pipeline integrity issues (Batch 4) resolved
- HMAC manifest signing added
- Bandit HIGH findings now CI-blocking
- Docker image pinned to specific version

**Remaining risk areas (by priority):**
1. **Processing pipeline** (13 HIGH) — feature parity, data leakage, temporal split ordering
2. **Analysis + Coaching** (8 HIGH) — probability bounds, fallback chains, stale baselines
3. **Core config** (4 HIGH) — thread safety on global variables
4. **Data ingestion** (3 HIGH) — pickle RCE, TOCTOU race, timeout gaps
5. **Neural networks** (2 HIGH) — shape validation edge cases
6. **Storage** (1 HIGH) — PRAGMA quick_check blocking

---

## Recommendations for Next Remediation Cycle

### Priority 1 (Critical — data correctness)
1. Fix `round_won` data leakage in round_stats_builder (P-RSB-03)
2. Fix temporal split ordering in data_pipeline (P-DP-01)
3. Add feature parity assertions between training and inference (P-SR-01, P-X-01)
4. Replace pickle cache with JSON serialization (DS-01)

### Priority 2 (High — stability)
5. Add shape assertions on tensor factory outputs (P-X-02)
6. Fix config.py global variable synchronization (C-01)
7. Fix COPER fallback chain to always produce output (C-01 coaching)
8. Add max total timeout to steam_api retries (DS-03)

### Priority 3 (Medium — quality)
9. Fix adaptive role signature scaling direction (P-RF-01)
10. Cap enemy_last_seen dict growth in player_knowledge (P-PK-02)
11. Fix probability bounds in win_probability heuristics (W-01)
12. Use real TF-IDF fallback instead of random embeddings (R-02)
