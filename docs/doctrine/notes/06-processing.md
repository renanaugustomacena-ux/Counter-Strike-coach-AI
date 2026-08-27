# Cluster 06 — `backend/processing/` (+ `core/team_codes.py`)

Files read (all 28): tensor_factory, player_knowledge, feature_engineering/{vectorizer, kast,
rating, base_features, role_features, __init__}, round_stats_builder, state_reconstructor,
tick_enrichment, connect_map_context, skill_assessment, rating (processing-level),
round_reconstructor, data_pipeline, heatmap_engine, external_analytics,
baselines/{pro_baseline, role_thresholds, meta_drift, nickname_resolver, pro_player_linker},
validation/{dem_validator, drift, sanity, schema}, core/team_codes.py.

## The perception system (the project's "eyes")

- **`player_knowledge.py` — NO-WALLHACK sensorial model**: what a player legitimately KNOWS per tick. Own state full access; teammates always known (radar/comms); enemies visible ONLY when `enemies_visible>0` AND in FOV cone AND not blinded; last-known enemies via exponential memory decay (tau=2.5s, cutoff 7.5s, in per-demo ticks — C1); sound inference (gunfire ≤2000u, 1s tick-rate-aware window); utility zones with tick-rate-aware expiry. The memory path applies the same H-11 Z-floor guard as the live path — without it "last-known enemies could be populated through floors... a wallhack leak into the NO-WALLHACK sensorial model" (R4 MED). `_tick_yaw` shared accessor pins the view_x=yaw contract (reading `yaw` on DB rows silently gave 0.0 — east-facing FOV for every sample, R4 CRIT class).
- **`tensor_factory.py` — the visual encoding**: three 3-channel image tensors — map (teammates / decayed-enemy-memory / utility+bomb), view (FOV cone / distance-weighted visible entities / utility), motion (trajectory trail / velocity radial gradient / crosshair-flick blob). POV mode is canonical; legacy mode warns loudly (tick rows carry no team → enemy channel structurally empty). C-03 single-Y-flip grid convention shared with heatmap_engine. R4 HIGH: FOV cone was mirrored vertically until the row-delta negation fix. `_normalize` divides by max(max_val, 1.0) so sparse noise is never amplified to 1.0. Shape assertions (P-X-02) on every output. Known limitation F2-03: velocity normalization calibrated for 64-tick.
- **`state_reconstructor.py`**: training-side bridge — same FeatureExtractor + TensorFactory as inference; `require_pov=True` RAISES if knowledge is missing (R4-04-01 anti-skew); explicit context dicts close the 20-24 feature skew; 32-tick windows with 50% overlap.
- **`tick_enrichment.py`**: cross-player context at ingest (round ctx, bomb state with BETWEEN-rows event transition semantics, alive counts, team economy, geometric FOV `enemies_visible` — vectorized pairwise, no occlusion by documented design).

## The 25-dim metadata contract (`vectorizer.py`)

- METADATA_DIM=25 with FEATURE_NAMES tuple asserted at import (P-X-01); `validate_feature_parity` called at both train and inference boundaries (P-SR-01). Slots: vitals/movement 0-7, awareness/position/view 8-14 (yaw sin/cos), z_penalty 15, kast/map_id/round_phase 16-18, weapon_class 19, context 20-24.
- **Quality gates**: batch path P3-A — >5% NaN/Inf contamination raises `DataQualityError` ("fix upstream before training"); single-sample (live inference) path D1 — sliding 1000-window, >5% ⇒ CRITICAL + user notification but NEVER raises ("Law 3": degrade loudly, don't kill live coaching); hysteresis re-arm. D2 log-emission throttling — counters stay exact, only emission is throttled.
- map_id via hashlib.md5 (built-in hash() is non-deterministic across sessions); KAST slot uses REAL data or 0.0 (the old estimate wrote 0.91 vs real 0.71 — retired); (0,0,0) positions logged as R4-14-01 with throttling; unknown weapons warn once and get 0.5 sentinel.

## Round statistics (`round_stats_builder.py` + `team_codes.py`)

- Round numbers are ORDINAL over sorted round_end ticks — the raw 'round' column is UNTRUSTED (CS2 patch 14160 shifted it +1); uniform offsets logged, non-uniform ⇒ event-loss warning (H-06).
- `core/team_codes.normalize_team` SSOT: 'TERRORIST'/int 2/'T' vocabularies — `== "CT"` comparisons silently misclassified (F-0016 round_won always-False; F-0025 RAP labeled TERRORIST as CT).
- MR12 side resolution incl. overtime 3-round alternating blocks (R4 MED: old formula inverted side for half of every OT).
- **CS2 blind events are SYNTHESIZED** from per-tick flash_duration upward jumps (>0.05s epsilon), attributed to the temporally closest flashbang_detonate; "when no detonation matches, the transition is skipped (no attribution is fabricated)". Modern demos emit zero player_blind events — before this, flash metrics were 0.0 and coach_manager compared them against pro baselines.
- 14 enrichment fields flow through the `ENRICHMENT_TO_PLAYERMATCHSTATS` SSOT map; `persist_round_stats_and_enrichment` is idempotent, case-insensitive on names, filters non-finite values, and NEVER raises (enrichment is additive to ingestion).

## Rating SSOT (`feature_engineering/rating.py`)

- Reverse-engineered HLTV 2.0 (R²=0.995 documented); contract: **rating_\* columns are RAW components; baseline normalization happens ONLY inside the aggregate `rating`** — "writing normalized ratios into these columns silently corrupts every downstream Z-score". kast is RATIO-only; the percentage-variant function was DELETED (F2-39) because differing semantics "invited silently wrong ×100 ratings". F2-40: the per-component average deliberately diverges from the regression formula — "Do NOT reconcile; the divergence is by design" (per-component interpretability for deviation analysis).
- kast.py: canonical per-round K/A/S/T with tick-rate-required trade window; the closed-form estimate documents its heuristic status (F2-35: "no formal statistical source exists").
- base_features.HeuristicConfig: every normalization bound/threshold is a named, documented-range, JSON-persistable parameter — magic numbers institutionalized as tunables.

## Anti-leakage training data discipline (`data_pipeline.py`)

- Temporal split FIRST; outlier thresholds computed from TRAIN only, applied to all splits (P-DP-01); scaler fit on train only, persisted with sklearn version check (major.minor); **player-level decontamination**: a player spanning splits is assigned to their EARLIEST split and later rows are DROPPED — "dropping later-split rows is preferred over moving them backward in time" (P-DP-02); growing-window CV boundaries (Counter_Strike_ML.pdf §5.1.4); pros and users split separately for balance; deterministic ordering + row cap with loud truncation warning.

## Baselines (the "pro reference frame")

- `pro_baseline.get_pro_baseline` — **fusion layering** (hard defaults → external CSV → ingested pro demos → HLTV cards), later layers override, `_provenance` string records the mix; each empirical layer returns ONLY empirical keys (F-0018: merging defaults inside a layer poisons the contract). Per-player averaging before mean/std (match-count bias); min 30 demo rows (OI-7: "10 rows = one 5v5 match — stds collapse and z-scores inflate"); std=0 metrics excluded/skipped; CSV percent-vs-ratio detection by column max (F-0019). `TemporalBaselineDecay`: 90-day half-life weights, naive-UTC normalization fix, meta-shift detection at 5%.
- `role_thresholds.py` — **"Anti-Mock Principle": thresholds start None, are learned from ≥30 unique players (75th percentile), and in cold start the classifier returns UNKNOWN with 0% confidence — "Coach never learns from fake/mock data"**; consistency validated before persistence.
- `meta_drift.py`: spatial drift = centroid shift of recent (30d) vs historical pro positions per map (R4 HIGH fixed a join across unrelated ID spaces + missing map filter); combined 0.4·stat + 0.6·spatial → `get_meta_confidence_adjustment` multiplies coach confidence down under meta chaos. role_features widens tolerance bands when drift >0.3 (conservative over wrong).
- nickname_resolver: exact → cleaned-exact → substring → fuzzy (SequenceMatcher ≥0.8); pro_player_linker: idempotent backfill of pro_player_id.

## Validation & grounding

- dem_validator: format pre-screen with security checks (forbidden chars, double extensions, symlinks) — deliberately looser than the ingestion 10MB floor ("intentional layering, do not 'fix'").
- drift.py: match-aggregate DriftMonitor + **TickFeatureDriftMonitor over the actual 25-dim model-input space** (DRIFT-01); `should_retrain` requires 3-of-5 drifted reports (anti-spurious).
- sanity.py: plausibility limits (ratio convention enforced, percent self-heal in trim mode); schema.py: versioned parser-output schema, int columns reject fractional floats (silent truncation masks parser bugs, F2-48).
- `round_reconstructor.py`: tick data → human-readable timeline for the LLM with callouts, engagements, health deltas — and an explicit **`_DATA_LIMITATIONS` list injected into LLM context** ("voice comms not captured...") so the narrator knows what it cannot claim; team-wide eliminations labeled as such (self-contradicting grounding was "a hallucination source").
- heatmap_engine: user-vs-pro positional KDE differential → top-5 hotspots in world coords for coaching; external_analytics: elite CSV z-scores, per-component degradation, health checks.

## Invariants observed (doctrine candidates)

- **The coach perceives as a player, never as a spectator** — the no-wallhack model is enforced structurally (FOV, visibility gating, memory decay, Z-floor, blind gating) and its leaks are treated as critical bugs.
- **One extraction path for train and serve** — FeatureExtractor/TensorFactory shared; parity validated at both boundaries; skew opportunities either raise (require_pov) or warn loudly.
- **Quality gates fail training loudly and degrade inference loudly** — never silently, never fabricating.
- **Semantics contracts are singular and pinned**: team codes, rating component scale, impact_rounds share, enrichment field map, ratio convention, ordinal round numbers.
- **Baselines are fused with provenance, learned not mocked, time-decayed, and drift-aware** — and coach confidence explicitly shrinks when the meta moves.
- **The LLM gets grounded facts plus an honest list of unknowables.**

## Risks / open questions carried forward

- tick_enrichment `enemies_visible` (geometric, no occlusion) both feeds feature 8 AND gates PlayerKnowledge visibility — approximation compounds; documented but worth doctrine attention.
- estimate_kast_from_stats still referenced as fallback in demo_parser (loud) — retired in vectorizer; consistent direction, two stages of removal.
- data_pipeline splits at match granularity via PlayerMatchStats only; tick-level JEPA windows derive splits elsewhere (check coach_manager assign_dataset_splits in cluster 07).
- round_reconstructor samples positions at fixed 256-tick stride (26-TICK-02 documents why it's OK — display only).
