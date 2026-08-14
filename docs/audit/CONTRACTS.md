# Cross-Cutting Contracts & Invariants (Pass 2 evidence)

Filled during pass 2 (L1–L10). One section per lens; tables are the evidence format:
producer → shape/units → consumer; thread ownership; session lifecycle; config keys;
formula → implementation.

## L1 — Tick / coordinate / tensor-dimension contracts
Assembled 2026-08-14 from D-B01..B76 cross-refs; spot verifications noted. Test-net column names the pinning suite.

### Tick-rate SSOT (26-NORM-01, owner decision 2026-07-17)
| Producer/consumer | Contract | Test net |
|---|---|---|
| core/tick_rate.py | THE SSOT: DEFAULT_TICK_RATE=64 ("the one sanctioned literal"), resolve ladder metadata→header→None sentinel, valid [32,256] (DS-07) | test_tick_rate_ssot (AST bare-64 hunter + seeded-violation meta-test) |
| run_ingestion._parse_demo_header_meta | per-demo rate PERSISTED to match_metadata (GAP-01), loud warn out-of-range | test_ingestion_tickrate |
| training_orchestrator._resolve_tick_rate | data-carried provenance, 26-ORCH-02 loud fallback | test_training_orchestrator_logic, test_tick_rate_propagation |
| D2A aggregate + trade_kill_detector | trade windows = seconds × per-demo rate (R4 HIGH 26-TICK); TRADE_WINDOW_TICKS export retired | test_trade_kill_detector, test_tools_regressions |
| movement_quality._seconds_to_ticks | the LONE conversion point; RATE-EQUIVARIANCE property (64 vs 128 identical real-time detection) | test_movement_quality_tickrate |
| deception FLASH_BLIND_WINDOW_SECONDS=2.0 | seconds-based (old TICKS=128 baked 64 t/s) | test_game_theory, test_analysis_gaps |
| tactical_viewer_screen | resolved per demo via header meta; :416 init placeholder = F-0002's ONE offender (W2 one-liner) | RED by design until W2 |
| KNOWN GAP | mine_shard_strategies bare `<=32` HE / `<=128` double-util windows (B51) — UNpinned, unconverted | none (register carries it) |

### Dimension chain (25-dim)
| Link | Contract | Test net |
|---|---|---|
| FeatureExtractor (vectorizer) | 25 features, names==METADATA_DIM, no dupes, batch==individual, thread-local clamp gate 26-VEC-01 | test_feature_extractor_contracts, test_metadata_dim_contract |
| METADATA_DIM == INPUT_DIM == len(TRAINING_FEATURES) == len(MATCH_AGGREGATE_FEATURES) == 25 | quadruple equality; OUTPUT_DIM==10 | test_coach_manager_tensors, test_smoke (==25 pin), ML debugger phase 5, CI cross-module step |
| JEPA windows | contiguous single-player, window_len=11 (10 ctx + 1 tgt, V-1 no-overlap), J-5 skip-not-pad, R4-CRIT | test_jepa_window_fetcher, test_training_orchestrator_flows |
| RAP tensors | view/map/motion (B,3,64,64), metadata (B,5,25), skill_vec (B,10); WR-76 suffix strip | conftest rap_inputs, test_rap_coach, test_rap_window_fetcher |
| OPEN CONTRACT | finetune targets 25-dim vs coaching head OUT=10 — 26-RANGE-01 guard raises NAMED error; NOT resolved (TASKS#64, JEPA-readiness CP0 cluster) | test_jepa_training_pipeline (pins the guard) |

### Radar/world coordinate space
| Element | Contract | Test net |
|---|---|---|
| SPATIAL_REGISTRY + MapMetadata | world→radar via pos_x/pos_y/scale; corners→(0,0)/(1,1); NO Y-inversion doctrine; FoV rotate(90−yaw) | test_spatial_engine, test_tensor_factory (FovConeOrientation), ui_diagnostic §6 |
| Mirage constants | pos_x=-3230, pos_y=1713, scale=5.0 — IDENTICAL in tensor_factory tests + ui_fixtures inverse transform | test_tensor_factory, B50 verify |
| map-SSOT CLUSTER (CP0) | 12 divergent known-map lists (match_utils 11, coach _MAP_RE 9, rebuild_monolith 8, mine_* 8, populate_match_results, d3_recover, seed tools, REQUIRED_MAPS 7, spatial registry, map_config.json, headless EXPECTED, ui fixtures) — single-authority fix is a CP0 decision | none — the cluster IS the finding |

## L2 — Thread & Qt-signal safety
(pending)

## L3 — DB session & transaction lifecycle
(pending)

## L4 — Error-handling & logging consistency
(pending)

## L5 — Resource lifecycle
(pending)

## L6 — Config/settings & path portability
(pending)

## L7 — i18n & user-facing text
(pending)

## L8 — Numerical & ML correctness
(pending)

## L9 — Security & input boundaries
(pending)

## L10 — API-contract drift & dead code
(pending)
