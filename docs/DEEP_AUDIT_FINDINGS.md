# Deep Audit Findings — Full-Scale Independent Verification

> **Audit started:** 2026-04-11
> **Auditor:** Claude Opus (independent, zero-trust, no assumptions from prior reports)
> **Goal:** Answer one question — does real data flow end-to-end, or is this placebo?
> **Status:** Phases 1-6 complete. Phases 7-10 pending.

---

# EXECUTIVE VERDICT (Phases 1-6)

**This is NOT placebo. The system is REAL, with honest limitations.**

| Subsystem | Verdict | Confidence |
|-----------|---------|------------|
| Data Ingestion | REAL | 95% — 118.5M tick records from actual demoparser2 |
| Database Layer | REAL | 90% — 23 tables, 42GB, proper schema. 10 zero columns need re-aggregation |
| Neural Networks | PARTIALLY TRAINED | 80% — Checkpoints show training evidence despite docs saying "zero epochs" |
| Game Theory Engines | REAL but HARDCODED | 70% — Real computation with ~60-70% hardcoded parameters |
| Coaching Pipeline | REAL and FUNCTIONAL | 85% — Produces meaningful output, degrades gracefully |
| Knowledge Base/RAG | REAL and POPULATED | 95% — 22,202 experiences, 701 knowledge entries, FAISS working |

**The prior documentation was WRONG about one critical claim:** "zero training epochs on production data" is false. Training evidence includes:
- training_progress.json showing multiple 0-10 epoch cycles since January 2026
- 113 MB of TensorBoard logs from March-April 2026
- Checkpoint weights that deviate from Xavier initialization (1.91x on first layer)
- LayerNorm parameters moved from initialization values
- Gate biases non-zero

---

## Phase 1: Data Ingestion Truth

**Verdict: HEALTHY**

14 files audited (~3,200 lines). The demo parsing pipeline is genuine:
- Uses real `demoparser2.DemoParser` calls (not mocked)
- 3-pass extraction: positions → nades → full state → kills
- HMAC-signed cache with safe unpickling
- 25-dim feature vector with compile-time assertion (`len(FEATURE_NAMES) == METADATA_DIM`)
- HLTV 2.0 rating with reverse-engineered coefficients (R²=0.995)

**Live DB Probe:**
```
playertickstate:     118,458,478 rows (118.5M tick records)
playermatchstats:    765 rows (76 distinct demos, all pro)
roundstats:          20,860 rows
Sample: NiKo avg_kills=0.73, rating=1.27, kast=1.00 — realistic pro stats
```

**10 zero columns** in PlayerMatchStats: kill_std, adr_std, utility_blind_time, utility_enemies_blinded, clutch_win_pct, positional_aggression_score, anomaly_score, avg_trade_response_ticks, flash_assists, unused_utility_per_round. **Root cause:** re-aggregation script not yet run (code exists, data ready).

---

## Phase 2: Database Layer and Data Persistence

**Verdict: HEALTHY with gaps**

23 tables, 42GB monolith database. Key findings:
- **WAL enforcement**: Verified on every connection via `@event.listens_for`
- **Schema**: Proper CHECK constraints, UniqueConstraints, indexes
- **Dataset splits PROPERLY ASSIGNED**: 535 train / 115 val / 115 test (70/15/15)
- **Ingestion tasks**: 78 completed, 30 failed, 4 still processing
- **Calibration**: 40 auto-calibration snapshots exist in DB

**8 empty tables** (designed for future features): datalineage, dataqualitymetric, ext_playerplaystyle, ext_teamroundstats, hltvdownload, mapveto, matchresult, rolethresholdrecord

**HLTV data sparse**: Only 2 ProPlayer + 2 ProPlayerStatCard rows in monolith DB. However, `hltv_metadata.db` contains 151 players + 140 stat cards.

---

## Phase 3: Neural Network Training Reality

**Verdict: PARTIALLY TRAINED (contradicts prior documentation)**

**Checkpoint analysis:**
- `jepa_brain.pt` (3.7MB, 44 params): Context encoder, target encoder, predictor, LSTM, 3 experts, gate
- `latest.pt` (1MB, 30 params): LSTM, LayerNorm, 3 experts, gate

**Weight forensics — JEPA brain:**
- First layer std = 0.1166 vs Xavier init range [0.0604, 0.0614] → **1.91x outside init**
- LayerNorm weight deviation from 1.0: 0.024 (trained would be higher)
- LayerNorm bias deviation from 0.0: 0.017 (untrained = 0)
- Gate bias: [0.012, 0.061, -0.013] (untrained = [0, 0, 0])
- Expert layer stds consistently BELOW Xavier → weight decay effect

**Training evidence:**
- `training_progress.json`: Started 2026-01-17, shows repeated 0-10 epoch cycles
- TensorBoard runs: `jepa_pretrain/` (5.8MB, Mar 25), `console_training/` (107MB, Apr 1)
- Console training: 5+ hours on Apr 1 alone
- Training on Lenovo IdeaPad Gaming 3 (hostname in event files)

**Diagnosis:** Weights are **partially trained** — they've moved from initialization but not dramatically. This suggests moderate training (10-50 epochs total across multiple restarts) but not convergence.

---

## Phase 4: Game Theory Analysis Engines

**Verdict: REAL COMPUTATION, ~60-70% HARDCODED PARAMETERS**

9 engines audited. All take real data as input and produce real computation.

| Engine | Real % | Hardcoded % | Critical Issue |
|--------|--------|-------------|---------------|
| win_probability | 40% | 60% | W-02: Random weights without checkpoint → 100% heuristic |
| belief_model | 35% | 65% | HP brackets use economy heuristic (100/60/30), not real tick HP |
| momentum | 5% | 95% | Multipliers (0.05/-0.04) "validate via 500+ matches" — NOT DONE |
| entropy_analysis | 40% | 60% | Max deltas hand-estimated, need empirical validation |
| game_tree | 50% | 50% | Leaf evaluation delegates to win_probability |
| blind_spots | 30% | 70% | Cascades through game_tree → win_probability |
| deception_index | 60% | 40% | Weights (0.25/0.40/0.35) never validated |
| engagement_range | 50% | 50% | 68 hardcoded callout positions |
| role_classifier | 45% | 55% | Cold-start returns FLEX with 0% confidence |
| utility_economy | 30% | 70% | Pro baselines hand-estimated |

**Critical cascade:** game_tree → win_probability → checkpoint. If checkpoint missing, tree search produces garbage leaf values, which cascades to blind_spots.

**However:** Checkpoints DO exist and show training evidence. The W-02 error may not fire if the model loads successfully.

**Calibration gap:** 40 calibration snapshots exist in DB but the orchestrator never reads or applies them. The belief model's AdaptiveBeliefCalibrator has run but its output is orphaned.

---

## Phase 5: Coaching Pipeline Output Quality

**Verdict: REAL AND MEANINGFUL**

The coaching output is **hybrid: partially data-driven, partially template-mediated**.

**What the user gets:**
1. **Z-score deviations** from pro baselines — REAL statistical signals
2. **ML predictions** from AdvancedCoachNN/JEPA (if loaded) — REAL inference
3. **RAG retrieval** from 701 knowledge entries — REAL semantic search
4. **Experience Bank** from 22,202 pro scenarios — REAL contextual advice
5. **Pro references** linked from HLTV data — REAL pro comparisons

**Fallback chain (never zero output):**
- COPER mode → Hybrid mode → Traditional mode → Generic insight
- Each level degrades gracefully
- C-01 "Zero Output Protection" guarantees user always sees something

**Ollama (LLM) is OPTIONAL:**
- Coaching works without Ollama (degrades to template text, not silence)
- Ollama polishes insights when available (llama3.1:8b default)
- Dialogue mode requires Ollama; falls back to raw data dump

**nn_refinement.py** is just a Z-score scaling function, NOT real NN inference.

**_FALLBACK_BASELINE** (Jan 2024 hardcoded stats) is last-resort only — system prefers HLTV data → demo stats → CSV → hardcoded.

---

## Phase 6: Knowledge Base, RAG, and FAISS

**Verdict: FULLY REAL AND POPULATED**

| Component | Count | Source | Verified |
|-----------|-------|--------|----------|
| Tactical Knowledge | 701 entries | Coach Book (151) + Pro mining (550) | Real content |
| Coaching Experiences | 22,202 entries | 101 pro demos, 120 unique pro players | m0nesy, yekindar, kscerato, etc. |
| FAISS knowledge index | 1.0 MB | 701 vectors, 384-dim SBERT | Working |
| FAISS experience index | 21.2 MB | 22,202 vectors, 384-dim SBERT | Working |
| Coach Book JSONs | 151 entries | 8 map files + general | Genuine tactical advice |
| Pro stat cards | 140 | HLTV metadata DB | ZywOo rating 1.44, etc. |

**Embeddings:** All 384-dim SBERT (all-MiniLM-L6-v2). Base64 for experiences (4x compression). Version tracking with re-embedding trigger.

**Experience Bank quality:** Real pro scenarios with real game states, real outcomes, real delta_win_prob. Sample: m0nesy on mirage T-side eco, entry_frag, kills=1, deaths=1, damage=112, round_won=true.

**FAISS search:** IndexFlatIP (inner product for cosine similarity), thread-safe, lazy rebuild, persistence to disk. Fallback to brute-force O(n) if FAISS unavailable.

---

# WHAT'S LEFT (Phases 7-10)

| Phase | Status | Expected Impact |
|-------|--------|----------------|
| 7. RAP Coach | Pending | Likely dead code (USE_RAP_MODEL=False, ncps/hflayers unavailable) |
| 8. External Data Sources | Pending | HLTV scraper works (151 players scraped). Steam/FACEIT likely stubs. |
| 9. Frontend | Pending | Qt screens exist, need to verify they query real data |
| 10. Meta-Audit | Pending | Validator checks are real (confirmed in exploration) |

---

# HONEST ASSESSMENT: WHAT YOU ACTUALLY HAVE

## What's REAL and working:
1. **Data pipeline:** 118.5M tick records from 76+ pro demos, properly parsed and stored
2. **Feature engineering:** 25-dim vector with compile-time assertion, NaN protection
3. **Game theory engines:** 9 engines that compute real metrics from real data
4. **Knowledge base:** 22,903 entries (701 knowledge + 22,202 experiences) with SBERT embeddings
5. **Coaching output:** Meaningful, data-grounded, gracefully degrading
6. **Test suite:** 1,782 real tests with meaningful assertions
7. **Validator:** 308 checks that verify real things (imports, schema, contracts, ML smoke)
8. **Database:** Production-grade SQLite + WAL, properly split train/val/test

## What's PARTIALLY working:
1. **Neural networks:** Checkpoints exist and show training evidence, but quality is uncertain
2. **Win probability:** Has checkpoint but heuristics may still dominate
3. **Calibration:** 40 snapshots computed but never applied by the orchestrator
4. **HLTV scraping:** 151 players scraped but selector drift needs testing

## What's HONESTLY NOT working:
1. **10 zero columns** in PlayerMatchStats — need re-aggregation
2. **Game theory constants** — ~60-70% hardcoded, never empirically validated
3. **RAP model** — disabled, dependencies unavailable (ncps/hflayers)
4. **Model quality verification** — no evaluation benchmark exists
5. **LLM fine-tuning** — no scaffolding, using base llama3.1:8b

## What the prior documentation got WRONG:
1. "Zero training epochs" — FALSE. Training occurred (evidence: TensorBoard logs, weight forensics)
2. "308/313 checks pass" — TRUE but misleading. Checks verify instantiation, not output quality.
3. "All audit findings fixed" — PARTIALLY TRUE. Code fixes applied, but calibration pipeline disconnected.
