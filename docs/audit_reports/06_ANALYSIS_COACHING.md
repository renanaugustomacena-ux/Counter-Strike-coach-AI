# Analysis Engines, Coaching Intelligence, and Knowledge Systems
# Macena CS2 Analyzer — Technical Audit Report 6/8

---

## DOCUMENT CONTROL

| Field | Value |
|-------|-------|
| Report ID | AUDIT-2026-06 |
| Date | 2026-03-08 |
| Version | 1.0 |
| Classification | Internal — Engineering Review |
| Auditor | Engineering Audit Protocol v3 |
| Scope | 39 Python files across analysis, coaching, services, knowledge, and progress modules |
| Total LOC Audited | ~8,900 |
| Audit Standard | ISO/IEC 25010, ISO/IEC 27001, OWASP Top 10, IEEE 730, CLAUDE.md Constitution |
| Previous Audit | N/A (baseline audit) |

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Audit Methodology](#2-audit-methodology)
3. [Analysis Engines](#3-analysis-engines)
4. [Coaching Module](#4-coaching-module)
5. [Services Layer](#5-services-layer)
6. [Knowledge Module](#6-knowledge-module)
7. [Progress Module](#7-progress-module)
8. [Consolidated Findings Matrix](#8-consolidated-findings-matrix)
9. [Recommendations](#9-recommendations)
10. [Appendix A: File Inventory](#appendix-a-complete-file-inventory)
11. [Appendix B: Glossary](#appendix-b-glossary)
12. [Appendix C: Cross-Reference Index](#appendix-c-cross-reference-index)
13. [Appendix D: Dependency Graph](#appendix-d-dependency-graph)
14. [Appendix E: Data Flow Diagrams](#appendix-e-data-flow-diagrams)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Domain Health Assessment

**Overall Rating: SOUND**

The analysis and coaching subsystem represents the intellectual core of the CS2 Coach AI — the layer that transforms raw game data into actionable coaching insights. It comprises 10 analysis engines, 7 coaching modules, 10 service files, 7 knowledge management components, and 2 progress tracking modules.

The architecture demonstrates mature design patterns: a well-defined coaching fallback chain (COPER → Hybrid → Traditional+RAG → Traditional), clean separation between analysis engines and coaching pipeline, and a sophisticated RAG-augmented knowledge retrieval system. The COPER workflow — integrating Experience Bank, RAG Knowledge, and Pro References — is architecturally sound and represents a genuine innovation in game coaching.

However, the subsystem exhibits several recurring patterns that prevent an "EXEMPLARY" rating: thread-unsafe singletons across 3 modules (down from 5 — `game_tree.py` singleton removed, `coaching_service.py` engine caching fixed), heavy constructor initialization (SBERT model loading on instantiation), and inconsistent factory patterns (some return singletons, others create new instances). The in-memory vector search scalability bottleneck has been **RESOLVED** via FAISS indexing (`vector_index.py`). The KAST display bug in `pro_demo_miner.py` has also been **RESOLVED** (now correctly multiplies by 100 with a guard).

All previously identified remediation items (G-02, G-07, G-08, G-09, F5-03, F5-04, F5-20, F5-23, F5-27) have been verified as correctly resolved.

### 1.2 Critical Findings Summary

| ID | Severity | Finding |
|----|----------|---------|
| ~~AC-35-02~~ | ~~MEDIUM~~ | ~~`pro_demo_miner.py` formats KAST as `card.kast:.1f%` producing "0.7%" instead of "74.0%", generating incorrect knowledge entries~~ **OBSOLETE — fixed: multiplies by 100 with guard for already-percentage values** |
| AC-15-01 | MEDIUM | `hybrid_engine.py` constructor loads SBERT model, DB manager, and ML model eagerly — slow startup, potential failures during import |
| ~~AC-23-03~~ | ~~MEDIUM~~ | ~~`coaching_service.py` creates new `HybridCoachingEngine()` on every call, triggering repeated SBERT model loading~~ **OBSOLETE — fixed: lazy-cached as `self._hybrid_engine`** |
| ~~AC-32-03~~ | ~~MEDIUM~~ | ~~`experience_bank.py` demo extraction uses O(E×T) linear scan instead of tick-indexed lookup~~ **OBSOLETE — fixed: uses `tick_data_by_tick` dict for O(1) lookup** |
| AC-07-01 | MEDIUM | `game_tree.py` transposition table depth semantics may cause suboptimal pruning |
| ~~AC-36-02~~ | ~~MEDIUM~~ | ~~`rag_knowledge.py` loads 500 entries for in-memory similarity — no vector DB index~~ **OBSOLETE — fixed: FAISS vector index implemented in `vector_index.py`** |

### 1.3 Quantitative Overview

| Metric | Value |
|--------|-------|
| Files Audited | 39 |
| Total Lines of Code | ~8,900 |
| Classes Analyzed | 42 |
| Functions/Methods Analyzed | ~280 |
| Findings: CRITICAL | 0 |
| Findings: HIGH | 0 |
| Findings: MEDIUM | 18 (originally 26; 8 resolved post-audit) |
| Findings: LOW | 76 (originally 77; AC-07-05 resolved post-audit) |
| Findings: INFO/GOOD | 15 |
| Remediation Items Previously Fixed | 9 (G-02, G-07, G-08, G-09, F5-03, F5-04, F5-20, F5-23, F5-27) |
| Findings Resolved Post-Audit | 9 (AC-35-02, AC-23-03, AC-32-03, AC-36-02, AC-07-02, AC-07-05, AC-39-01, AC-28-02, AC-23-03) |
| Remaining Deferred Items | 1 (G-05: Heuristic calibration — requires pro-annotated dataset) |

### 1.4 Risk Heatmap

```
              Impact
         Low    Med    High
    ┌────────┬────────┬────────┐
Hi  │        │        │        │
    ├────────┼────────┼────────┤
Lk  │  LOW   │ AC-15  │ AC-23  │
Med │ issues │ AC-21  │ (01,02)│
    ├────────┼────────┼────────┤
Lo  │        │ AC-07  │        │
    └────────┴────────┴────────┘
         Likelihood

(AC-35, AC-36, AC-32-03, AC-23-03: RESOLVED — removed from heatmap)
```

---

## 2. AUDIT METHODOLOGY

### 2.1 Standards Applied

- **ISO/IEC 25010** — Software product quality model
- **ISO/IEC 27001** — Information security management
- **OWASP Top 10 2021** — Application security risks
- **IEEE 730** — Software quality assurance
- **CLAUDE.md Constitution** — Project engineering rules (Rules 1–7)
- **STRIDE** — Threat modeling methodology

### 2.2 Analysis Techniques

- Static line-by-line code review of all 39 files
- Data flow analysis through the COPER coaching pipeline
- Concurrency analysis for singleton patterns and shared state
- Performance profiling of RAG retrieval and game tree search
- Cross-reference verification against prior remediation phases

### 2.3 Severity Classification

| Severity | Definition | SLA |
|----------|------------|-----|
| CRITICAL | System failure, data loss, security breach, or correctness violation affecting core functionality | Immediate fix required |
| HIGH | Significant functional impact, performance degradation >50%, exploitable security weakness | Fix within current sprint |
| MEDIUM | Moderate impact on reliability, performance, or maintainability | Fix within next 2 sprints |
| LOW | Minor code quality issues, style inconsistencies, documentation gaps | Next refactoring cycle |
| INFO | Observations, positive findings, architectural notes | No SLA |

---

## 3. ANALYSIS ENGINES

### 3.1 `backend/analysis/__init__.py` — Barrel Re-export

**File Metrics:** 95 LOC | 0 classes | 5 factory functions re-exported

Clean barrel module that re-exports `get_*()` factory functions from all 10 analysis submodules. Provides a unified import surface for consumers. No issues found.

---

### 3.2 `backend/analysis/win_probability.py` — Real-time Win Probability Estimation

**File Metrics:** 290 LOC | 2 classes (`WinProbabilityModel`, `WinProbabilityEstimator`) | 12 functions

**Architecture:** Dual-approach model combining a lightweight PyTorch neural network with heuristic adjustments. Feature extraction from game state → NN inference → heuristic post-processing → clamped probability output.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-11-01 | MEDIUM | The NN model weights are initialized via Xavier but never trained — the model produces essentially random predictions unless a checkpoint is loaded. The heuristic fallbacks (lines 182–213) compensate. | Document this design intent explicitly; consider a warning log when no checkpoint is loaded |
| AC-11-02 | LOW | `prob *= 1.2` for bomb-planted adjustment can push probability above 1.0, but the final `clamp(0.0, 1.0)` at line 214 corrects this | No action needed |
| AC-11-03 | LOW | `torch.load(model_path, weights_only=True)` correctly uses the secure option preventing arbitrary code execution | Positive observation |

**Performance:** O(F) feature extraction + O(H²) forward pass where H = hidden_dim (64). Negligible for inference.

**Positive Observations:** `weights_only=True` is the correct security practice for model loading.

---

### 3.3 `backend/analysis/role_classifier.py` — Player Role Classification

**File Metrics:** 544 LOC | 2 classes | 15 functions

**Architecture:** K-Means clustering (k=5) with heuristic label mapping. Supports both single-match and multi-match role inference. `PlayerRole` enum provides type-safe role identifiers.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-09-01 | MEDIUM | Cluster-to-role label assignment uses hardcoded centroid comparison. If K-Means produces different cluster orderings across runs (non-deterministic seed), the role labels could swap between runs | Set `random_state=GLOBAL_SEED` in KMeans constructor |
| AC-09-02 | LOW | `if len(feature_matrix) < 5` falls back to heuristic classification. The threshold 5 is a magic number | Extract to named constant `MIN_CLUSTER_SAMPLES` |
| AC-09-03 | LOW | Feature vector normalization uses `StandardScaler` fit per-call — no persistent scaler means role boundaries shift with each match set | Consider persistent scaler or fixed normalization bounds |
| AC-09-04 | LOW | `_classify_role_heuristic` uses hardcoded thresholds (ADR > 80, HS% > 55, etc.) without governance annotation | Add P8-XX calibration comments |

---

### 3.4 `backend/analysis/game_tree.py` — Strategic Game Tree Search

**File Metrics:** 515 LOC | 3 classes (`GameState`, `StrategyNode`, `GameTreeAnalyzer`) | 18 functions

**Architecture:** The most architecturally sophisticated analysis module. Implements expectiminimax search with adaptive opponent modeling, transposition tables, and contextual probability adaptation. Simplified state transitions model symmetric push casualties.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-07-01 | MEDIUM | Transposition table stores `(value, depth)` tuples. The depth check at line 370-373 uses `stored_depth >= current_depth`, but "depth" semantics are inverted — stored values from deeper searches (higher depth) should be preferred, but "higher depth" could mean "further from leaf" (less accurate) or "more explored" depending on the implementation | Verify depth direction matches the expectiminimax convention; add comment |
| ~~AC-07-02~~ | ~~MEDIUM~~ | ~~Module-level singleton without thread safety~~ | ~~Add threading.Lock~~ **RESOLVED — singleton removed; `get_game_tree_search()` returns new stateless instance per call** |
| AC-07-03 | LOW | `_compute_action_probability` uses hardcoded probabilities (push=0.4, hold=0.35, rotate=0.25). These are not calibrated against pro play data | Document as P8-XX heuristic |
| AC-07-04 | LOW | Simplified state transitions assume symmetric casualties — both teams lose the same fraction of players per engagement. Real CS2 has asymmetric engagement outcomes based on position advantage | Document simplification explicitly |
| ~~AC-07-05~~ | ~~LOW~~ | ~~Transposition table grows unboundedly during analysis~~ | ~~Add max size with LRU eviction~~ **RESOLVED — `_TT_MAX_SIZE = 10_000` with eviction implemented** |

**Performance:** O(B^D) where B = branching factor (~3 actions) and D = depth (configurable, default 3). With alpha-beta pruning, effective complexity is O(B^(D/2)). Transposition table provides significant speedup for repeated states.

---

### 3.5 `backend/analysis/belief_model.py` — Bayesian Belief State Estimation

**File Metrics:** 463 LOC | 3 classes | 16 functions

**Architecture:** Bayesian inference model for estimating hidden opponent states. Maintains probability distributions over opponent positions and intentions. Supports auto-calibration from death events (G-07 fix).

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-05-01 | MEDIUM | `auto_calibrate()` updates priors from death events. If death events are sparse (pistol-only demos), the posterior could be dominated by the uniform prior, giving uninformative beliefs | Log a warning when calibration sample size < 20 |
| AC-05-02 | LOW | Bayesian update uses `log_posterior = log_prior + log_likelihood`. Numerical underflow possible for very low probabilities. The `np.logaddexp` utility is not used | Consider using scipy's log-sum-exp for numerical stability |
| AC-05-03 | LOW | `_discretize_position` uses 10x10 grid for position quantization. This resolution may be too coarse for detailed position inference on larger maps | Make grid resolution configurable |
| AC-05-04 | LOW | Thread-safe singleton with double-checked locking (lines 174-188) — correct pattern, good | Positive observation |
| AC-05-05 | LOW | Death position extraction from DB correctly uses `extract_death_events_from_db()` (G-07 fix verified) | Verified remediation |

---

### 3.6 `backend/analysis/blind_spots.py` — Danger Zone & FOV Analysis

**File Metrics:** 213 LOC | 1 class | 8 functions

**Architecture:** Identifies map areas where the player is frequently killed without returning fire. Uses accumulated FOV analysis with POV mode (G-02 fix).

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-03-01 | MEDIUM | `_compute_danger_zones` uses 50x50 grid with Gaussian blur. The grid is allocated per-call (50×50×8 bytes ≈ 20KB) — fine for single calls but could accumulate if called in a loop | Pool grid allocation for batch analysis |
| AC-03-02 | LOW | Death positions are filtered by `death.get("victim_id") == player_id`. If `player_id` format changes (Steam ID vs display name), no matches would be found | Validate player_id format before filtering |
| AC-03-03 | LOW | G-02 FOV+POV mode verified as correctly implemented | Verified remediation |
| AC-03-04 | LOW | Danger zone severity thresholds (0.3, 0.6, 0.9) are hardcoded without governance annotations | Add P8-XX calibration comments |

---

### 3.7 `backend/analysis/deception_index.py` — Deception Detection

**File Metrics:** 235 LOC | 1 class | 10 functions

**Architecture:** Detects deceptive play patterns (fakes, lurks, bait plays) by comparing stated team strategy with actual player movement.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-04-01 | MEDIUM | Fake detection uses velocity magnitude threshold without accounting for map scale. A "fast movement" on Nuke (compact) is different from "fast movement" on Overpass (spread out) | Normalize velocity by map bounding box |
| AC-04-02 | LOW | `_compute_team_centroid` excludes dead players but doesn't account for spectating players who may have valid position data | Filter on `is_alive` explicitly |
| AC-04-03 | LOW | Deception confidence decay over rounds (older rounds weighted less) uses a linear decay. Exponential decay would better model recency | Consider exponential decay |
| AC-04-04 | LOW | Factory function returns new instance each call. Consistent with stateless-per-analysis pattern | No action needed |

---

### 3.8 `backend/analysis/entropy_analysis.py` — Information-Theoretic Analysis

**File Metrics:** 159 LOC | 1 class | 7 functions

**Architecture:** Measures strategic unpredictability via Shannon entropy on player movement and utility usage patterns.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-06-01 | MEDIUM | `np.log2(prob)` for entropy computation can produce `-inf` if prob is exactly 0. The `prob > 0` filter at line 89 prevents this, but floating-point representation of "exactly 0" vs "very small" can be unreliable | Use `scipy.stats.entropy` or add `+ 1e-12` epsilon |
| AC-06-02 | LOW | Position discretization to 8×8 grid is very coarse (each cell covers ~500×500 game units on Mirage). Many positions map to the same cell | Increase to at least 16×16 |
| AC-06-03 | LOW | Entropy values are not normalized to [0,1] range. Raw entropy depends on number of bins, making cross-map comparisons invalid | Normalize by `log2(num_bins)` |

---

### 3.9 `backend/analysis/momentum.py` — Round Momentum Tracking

**File Metrics:** 218 LOC | 1 class | 8 functions

**Architecture:** Tracks momentum swings across rounds using an exponential moving average of round outcomes. Identifies tilt zones and streak patterns.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-08-01 | LOW | EMA alpha hardcoded at 0.3. Higher alpha = more responsive but noisier momentum signal | Make configurable or document rationale |
| AC-08-02 | LOW | "Tilt zone" detection triggers when momentum drops below -0.5 for 3+ consecutive rounds. The threshold is reasonable but not calibrated against pro play | Document as P8-XX heuristic |
| AC-08-03 | LOW | `round_outcomes` list grows unboundedly for very long matches (overtime). In practice, CS2 matches rarely exceed 30 rounds | Cap at reasonable maximum |

---

### 3.10 `backend/analysis/engagement_range.py` — Kill Distance Analysis

**File Metrics:** 437 LOC | 1 class | 14 functions

**Architecture:** Analyzes kill distances to identify optimal and suboptimal engagement ranges per weapon class.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-10-01 | LOW | Distance calculation uses 2D Euclidean (`sqrt(dx² + dy²)`) ignoring Z-axis. On multi-level maps (Nuke, Vertigo), this underestimates vertical engagement distances | Consider 3D distance or document limitation |
| AC-10-02 | LOW | Weapon classification uses hardcoded weapon-to-category mapping. New weapons added in CS2 updates would be unclassified | Load from configuration file |
| AC-10-03 | LOW | Statistical outlier detection uses 2σ threshold. For small sample sizes (<10 kills), this is unreliable | Require minimum sample size before analysis |

---

### 3.11 `backend/analysis/utility_economy.py` — Utility Usage Economics

**File Metrics:** 405 LOC | 1 class | 12 functions

**Architecture:** Evaluates grenade usage efficiency by correlating utility expenditure with round outcomes and damage dealt.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-12-01 | LOW | Utility cost values are hardcoded ($200 flash, $300 smoke, $400 HE, $400 molotov). CS2 economy changes would silently invalidate these | Load from configuration or document as constants |
| AC-12-02 | LOW | "Wasted utility" detection counts grenades thrown in the last 5 seconds of a round as potentially wasted. Late-round utility (e.g., retake smokes) may be optimal | Exclude retake scenarios |
| AC-12-03 | LOW | Damage efficiency ratio divides total utility damage by utility cost. If no utility is bought (eco round), the denominator is 0 — guarded by `if total_cost > 0` check | Correctly handled |
| AC-12-04 | LOW | Economy state tracking across rounds uses simple accumulation. Side switches at halftime are not explicitly handled | Add half-time reset logic |

---

## 4. COACHING MODULE

### 4.1 `backend/coaching/__init__.py` — Barrel Re-export

**File Metrics:** 25 LOC | Exports 5 symbols from 4 submodules

Clean barrel module. No issues.

---

### 4.2 `backend/coaching/correction_engine.py` — Deviation-Based Corrections

**File Metrics:** 64 LOC | 1 class | 4 functions

**Architecture:** Generates top-3 weighted corrections from Z-score deviations. Supports user-configurable importance weights and NN refinement.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-13-01 | LOW | Confidence formula `min(1.0, rounds_played / 300)` saturates at 300 rounds. For single-match analysis (24 rounds), confidence = 0.08, heavily penalizing corrections. Intentional design — more matches = more confidence | Document rationale |
| AC-13-02 | LOW | `z = val[0] if isinstance(val, (tuple, list)) else val` handles legacy float vs new (z, raw_dev) tuple format. Shows schema evolution debt | Standardize to single format |

---

### 4.3 `backend/coaching/explainability.py` — Narrative Generation

**File Metrics:** 94 LOC | 1 class (`ExplainabilityEngine`) | 5 functions

**Architecture:** Template-based narrative generation with 5 skill axes, severity classification, and skill-level-dependent verbosity filtering.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-14-01 | LOW | `abs(int(delta * 100))` truncates to integer percentage. A delta of 0.005 becomes 0% | Use `round()` instead of `int()` |
| AC-14-02 | LOW | `score=max(0, int(100 - abs(delta * 100)))` — for large deltas (>1.0), score becomes 0. Produces "0% stability" messages for extreme deviations | Cap delta at ±1.0 before scoring |
| AC-14-03 | LOW | `context: Dict = None` — mutable default argument anti-pattern. The `ctx = context or {}` guard prevents issues | Change to `Optional[Dict] = None` |

---

### 4.4 `backend/coaching/hybrid_engine.py` — ML + RAG + Pro Baseline Fusion

**File Metrics:** 641 LOC | 1 class (`HybridCoachingEngine`) | 22 functions

**Architecture:** The most complex coaching module. Combines ML predictions, RAG knowledge retrieval, pro baselines, meta-drift adjustment, and Reference Clip indexing. Well-layered pipeline: deviation → ML prediction → RAG retrieval → synthesis → priority scoring.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-15-01 | MEDIUM | Constructor calls `get_db_manager()` and `KnowledgeRetriever()` (which loads SBERT model). Heavy initialization should be lazy-loaded | Defer SBERT and DB init to first use |
| AC-15-02 | MEDIUM | `MATCH_AGGREGATE_FEATURES` import from `nn.coach_manager` has circular import risk. The try/except masks legitimate errors | Restructure import or use lazy import pattern |
| AC-15-03 | LOW | `knowledge_effectiveness` calculation normalizes usage_count by dividing by 100. If usage_count >> 100, effectiveness saturates | Use logarithmic scaling |
| AC-15-04 | LOW | `MetaDriftEngine.get_meta_confidence_adjustment()` called per-confidence calculation. Should be cached per session | Cache per-analysis-session |
| AC-15-05 | LOW | Mutates `HybridInsight` in-place after creation (line 243). Could cause issues if insights are cached | Return new instance instead of mutating |

**Concurrency:** NOT thread-safe. Mutable `self.model`, `self.pro_baseline`, `self._using_fallback_baseline`.

---

### 4.5 `backend/coaching/longitudinal_engine.py` — Trend-Based Insights

**File Metrics:** 49 LOC | 1 function

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-16-01 | LOW | `if t.confidence >= 0.6` — hardcoded threshold | Extract to named constant |
| AC-16-02 | LOW | `return insights[:3]` truncates to 3 insights, possibly dropping important regression warnings | Return all insights; let consumer decide |
| AC-16-03 | LOW | Two if-statements (not elif) for slope check look like both could trigger. They cannot (slope can't be both < 0 and > 0), but code clarity suffers | Use if/elif for clarity |

---

### 4.6 `backend/coaching/nn_refinement.py` — NN Weight Adjustments

**File Metrics:** 30 LOC | 1 function

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-17-01 | LOW | `refined_z = c["weighted_z"] * (1 + adjustment)` — if adjustment ≤ -1.0, the sign flips or becomes 0. No bounds checking | Clamp adjustment to [-0.9, +1.0] |

---

### 4.7 `backend/coaching/pro_bridge.py` — HLTV Pro Baseline Translation

**File Metrics:** 117 LOC | 1 class | 6 functions

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-18-01 | MEDIUM | `float(opening) / ASSUMED_ROUNDS_SAMPLE` where `ASSUMED_ROUNDS_SAMPLE = 100.0` is arbitrary. May not match actual rounds played for the pro player | Calculate from actual match count when available |
| AC-18-02 | LOW | HS ratio fallback default 0.45 is a reasonable CS2 pro average but is a magic number | Extract to named constant with comment |
| AC-18-03 | LOW | DPR division guarded by `if self.card.dpr > 0` — correct edge case handling | Positive observation |

---

### 4.8 `backend/coaching/token_resolver.py` — Pro Player Token Resolution

**File Metrics:** 108 LOC | 1 class | 4 functions

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-19-01 | LOW | Two sequential DB queries (ProPlayer then ProPlayerStatCard) could be combined into a single JOIN | Optimize to single query |
| AC-19-02 | LOW | `card.last_updated.isoformat()` raises AttributeError if `last_updated` is None | Add defensive None check |
| AC-19-03 | LOW | `compare_performance_to_token` computes simple deltas without normalization. ADR (range 0-150) and KAST (range 0-1) are not comparable | Z-score normalize before comparison |

---

## 5. SERVICES LAYER

### 5.1 `backend/services/__init__.py` — Empty Package

**File Metrics:** 1 LOC

Empty `__init__.py`. No exports defined.

---

### 5.2 `backend/services/analysis_orchestrator.py` — Analysis Engine Coordination

**File Metrics:** 537 LOC | 1 class | 16 functions

**Architecture:** Bridge between analysis engines and coaching pipeline. Coordinates 7 analysis modules and produces `CoachingInsight` objects. Module-level singleton with per-module failure counting.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-21-01 | MEDIUM | Module-level singleton without thread safety. Race condition on concurrent first access | Add threading.Lock |
| AC-21-02 | LOW | Utility entropy analysis uses `tick + 128` hardcoded post-utility tick offset. Incorrect for 128-tick servers | Use constant or derive from tick rate metadata |
| AC-21-03 | LOW | Engagement range builds kill event dicts with triple-nested fallbacks (`row.get("attacker_pos_x", row.get("pos_x", 0))`), masking data quality issues | Log a warning when falling back to secondary keys |

**Positive Observations:** Good observability pattern with `_module_failure_counts` dict tracking consecutive failures per module.

---

### 5.3 `backend/services/analysis_service.py` — DB-Backed Analysis

**File Metrics:** 91 LOC | 1 class | 3 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-22-01 | LOW | `get_pro_comparison` assumes pro stats are in the same `PlayerMatchStats` table as user stats. If no pro record exists, both queries fail silently | Return explicit "no pro data" indicator |
| AC-22-02 | LOW | `limit(100)` for drift detection loads 100 match dicts into memory for DataFrame conversion | Stream results or use DB-side aggregation |

---

### 5.4 `backend/services/coaching_service.py` — Central Coaching Orchestrator

**File Metrics:** 713 LOC | 1 class | 24 functions

**Architecture:** Implements the COPER → Hybrid → Traditional+RAG → Traditional fallback chain. Well-documented priority system. Singleton pattern.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-23-01 | MEDIUM | Module-level singleton without thread safety | Add threading.Lock |
| AC-23-02 | MEDIUM | Z-score threshold check `deviations.get("avg_adr", 0) < -10` — Z-scores are typically [-3, +3]. A Z-score of -10 is virtually impossible. This RAG enhancement check would never trigger | Change threshold to -1.5 or -2.0 |
| ~~AC-23-03~~ | ~~MEDIUM~~ | ~~`_generate_hybrid_insights` creates new `HybridCoachingEngine()` on every call~~ | ~~Cache engine instance~~ **RESOLVED — `self._hybrid_engine` lazy-cached in constructor** |
| AC-23-04 | LOW | COPER tick_data type check silently returns without coaching. Correctly logs at WARNING (line 181) | Adequate |
| AC-23-05 | LOW | f-string in logger.warning — should use lazy `%s` formatting | Convert to lazy format |
| AC-23-06 | LOW | Deviations/rounds_played correctly propagated to COPER handler (G-08 fix verified) | Verified remediation |

---

### 5.5 `backend/services/coaching_dialogue.py` — Multi-Turn Coaching Chat

**File Metrics:** 373 LOC | 1 class | 14 functions

**Architecture:** Multi-turn dialogue with RAG augmentation and Ollama chat. Intent classification, context retrieval, and sliding-window conversation history.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-24-01 | MEDIUM | Experience Bank retrieval uses hardcoded context: `round_phase="full_buy"`, `side="T"` instead of actual game context | Use player_context data when available |
| AC-24-02 | LOW | Sliding window `self._history[:-1]` correctly removes last assistant message for context window | Correct behavior |
| AC-24-03 | LOW | User messages passed to Ollama without sanitization. LOW severity since Ollama runs locally | Add basic input sanitization |
| AC-24-04 | LOW | Intent classification returns "general" when all scores are 0 — correct via `if scores[best] > 0` check | Correct behavior |

---

### 5.6 `backend/services/lesson_generator.py` — Structured Lesson Generation

**File Metrics:** 382 LOC | 1 class | 12 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-25-01 | LOW | Map name extraction from demo name uses string matching — could false-match on player names containing map substrings | Use regex with word boundaries |
| AC-25-02 | LOW | Pro tips are hardcoded per map referencing 2024 teams/players. Will become stale | Move to data file or periodic refresh |
| AC-25-03 | LOW | Death ratio warning triggers for any death when kills=0 (`deaths > kills * threshold` ≡ `deaths > 0`). The `_MIN_DEATHS_FOR_WARNING` guard prevents false positives for short matches | Adequate |

---

### 5.7 `backend/services/llm_service.py` — Ollama REST Client

**File Metrics:** 253 LOC | 1 class | 8 functions

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-26-01 | MEDIUM | Model auto-selection uses `model_names[0]` — could select a 70B model causing OOM. Should prefer smaller models | Sort by model size or use a whitelist |
| AC-26-02 | LOW | 60-second timeout may be insufficient for complex prompts but increasing risks blocking | Make configurable |
| AC-26-03 | LOW | Connection error sets `self._available = False` without updating `_available_checked_at`. Allows quick recovery — correct design | Adequate |

**Security:** `OLLAMA_URL` configurable via env var. If set to an external server, coaching prompts containing player stats would be sent externally. MEDIUM severity in production.

---

### 5.8 `backend/services/ollama_writer.py` — Coaching Message Polish

**File Metrics:** 110 LOC | 1 class | 4 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-27-01 | LOW | Error detection via `result.startswith("[LLM")` is fragile — legitimate Ollama output starting with "[LLM" would be treated as error | Use structured error responses |

---

### 5.9 `backend/services/profile_service.py` — External API Integration

**File Metrics:** 119 LOC | 3 functions

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-28-01 | MEDIUM | `sync_all_external_data` creates a `PlayerProfile` but doesn't write fetched Steam/FaceIT data to it. Profile is saved essentially empty | Wire API data to profile fields |
| ~~AC-28-02~~ | ~~MEDIUM~~ | ~~FaceIT API URL includes nickname without URL encoding~~ | ~~Use `urllib.parse.quote()`~~ **RESOLVED — `quote(nickname)` applied in URL construction** |
| AC-28-03 | LOW | App ID 730 is correct for CS2 (formerly CS:GO). `timeout=10` on requests is appropriate | Correct |

---

### 5.10 `backend/services/visualization_service.py` — Radar Charts

**File Metrics:** 119 LOC | 1 class | 3 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-29-01 | LOW | `list(user_stats.keys())` relies on dict insertion order. If `user_stats` and `pro_stats` have different key orders, chart compares wrong metrics | Use fixed feature order list |
| AC-29-02 | LOW | No directory existence check before `plt.savefig(output_path)` | Add `os.makedirs(parent, exist_ok=True)` |

---

### 5.11 `backend/services/telemetry_client.py` — HTTP Telemetry

**File Metrics:** 59 LOC | 1 class | 3 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-30-01 | LOW | `httpx.Client()` created and closed per call. Should use persistent client with connection pooling | Use singleton client |
| AC-30-02 | LOW | `time.time()` correct for absolute timestamps (not `time.monotonic()`) | Correct |

**Security:** Telemetry URL defaults to localhost. Player IDs and stats sent without TLS enforcement.

---

### 5.12 `backend/server.py` — Backend API Server

Not included in this report scope — covered in Report 3 (Data Acquisition).

---

## 6. KNOWLEDGE MODULE

### 6.1 `backend/knowledge/__init__.py` — Package Init

**File Metrics:** 1 LOC

Single re-export from graph module. No issues.

---

### 6.2 `backend/knowledge/experience_bank.py` — COPER Experience Bank

**File Metrics:** 748 LOC | 4 classes | 28 functions

**Architecture:** The most substantial knowledge module. Implements semantic search via SBERT embeddings, context hashing, pro reference linking, narrative synthesis, and a feedback loop for coaching effectiveness tracking. The feedback loop implements a complete learning cycle: coaching advice → player action → outcome measurement → experience confidence adjustment via EMA.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-32-01 | MEDIUM | Embedding stored as JSON (`json.dumps(embedding_vec.tolist())`) — ~3KB per 384-dim SBERT vector. Binary BLOB storage would be 6x more efficient | Consider binary encoding for embeddings |
| AC-32-02 | MEDIUM | `retrieve_similar` loads 100 candidates, computes cosine similarity, then updates `usage_count` in the same session. Usage update on read violates command-query separation | Separate retrieval from usage tracking |
| ~~AC-32-03~~ | ~~MEDIUM~~ | ~~Demo extraction uses O(E×T) linear scan~~ | ~~Create `{tick: data}` dict~~ **RESOLVED — `tick_data_by_tick = {td.get("tick"): td for td in tick_data}` with O(1) dict lookup** |
| AC-32-04 | LOW | Action matching uses exact string comparison (`player_action.lower() == experience.action_taken.lower()`). "pushed" vs "push" would not match | Use fuzzy matching or normalized action vocabulary |
| AC-32-05 | LOW | Singleton via `get_experience_bank()` correctly avoids re-loading SBERT model (F5-04 fix verified) | Verified remediation |

**Positive Observations:** The feedback loop (lines 513-633) implementing continuous coaching quality improvement is a mature and well-designed pattern.

---

### 6.3 `backend/knowledge/graph.py` — Knowledge Graph

**File Metrics:** 199 LOC | 1 class | 8 functions

**Architecture:** SQLite-backed knowledge graph with entities and relations. Uses direct `sqlite3` (not SQLModel). WAL mode enabled.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-33-01 | MEDIUM | `query_subgraph` with depth > 1 logs a warning but only returns 1-hop neighbors. The `depth` parameter is accepted but ignored — could mislead callers | Either implement multi-hop or remove the parameter |
| AC-33-02 | LOW | `add_entity` uses `ON CONFLICT(name) DO UPDATE` which overwrites observations entirely. Append/merge strategy would preserve history | Consider observation append mode |
| AC-33-03 | LOW | DB initialization runs `PRAGMA journal_mode=WAL` on every instantiation. Idempotent but unnecessary after first call | Check and skip if already WAL |

---

### 6.4 `backend/knowledge/init_knowledge_base.py` — KB Initialization Script

**File Metrics:** 111 LOC | 2 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-34-01 | MEDIUM | `sys.path.insert(0, str(PROJECT_ROOT))` modifies sys.path at module level. Can cause import issues if imported as library rather than run as `__main__` | Guard with `if __name__ == "__main__"` |
| AC-34-02 | LOW | Emoji in logger output (`"✓ Loaded manual knowledge"`) — should use ASCII-only per project convention | Replace with ASCII marker |

---

### 6.5 `backend/knowledge/pro_demo_miner.py` — Pro Knowledge Extraction

**File Metrics:** 189 LOC | 1 class | 6 functions

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-35-01 | LOW | N+1 query pattern: fetches stat cards, then queries ProPlayer in loop for each card | Use JOIN query |
| ~~AC-35-02~~ | ~~MEDIUM~~ | ~~`card.kast:.1f%` formats KAST as "0.7%" instead of "74.0%"~~ | ~~Fix formatting: multiply by 100~~ **RESOLVED — now reads `(card.kast * 100 if card.kast <= 1.0 else card.kast):.1f%` with guard for already-percentage values** |

**Impact:** ~~This is the most impactful correctness issue in the entire subsystem.~~ **RESOLVED.** The KAST formatting now correctly handles both decimal (0.74) and percentage (74.0) formats.

---

### 6.6 `backend/knowledge/rag_knowledge.py` — RAG Implementation

**File Metrics:** 477 LOC | 3 classes | 14 functions

**Architecture:** RAG with SBERT embeddings, cosine similarity search, knowledge population, and unified coaching insight generation.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| AC-36-01 | LOW | Fallback embedding produces 100-dim vectors vs SBERT's 384-dim. If mixed, cosine similarity is undefined. The `check_embedding_compatibility` method addresses this | Correctly handled |
| ~~AC-36-02~~ | ~~MEDIUM~~ | ~~`stmt = stmt.limit(500)` loads up to 500 entries for in-memory similarity. No vector DB.~~ | ~~Implement FAISS~~ **RESOLVED — FAISS `vector_index.py` with IndexFlatIP + lazy rebuild + disk persistence. Brute-force kept as fallback when FAISS not installed.** |
| AC-36-03 | LOW | JSON embedding parsing in retrieval loop (`json.loads(entry.embedding)`) could be cached | Cache parsed embeddings |
| AC-36-04 | LOW | Cosine similarity epsilon (1e-8) differs from ExperienceBank's explicit zero-norm check. Inconsistent approaches | Standardize to one approach |

---

### 6.7 `backend/knowledge/round_utils.py` — Shared Round Phase Utility

**File Metrics:** 35 LOC | 1 function | 3 named constants

**Architecture:** Shared utility extracted from 3 modules (F5-20). Single function with named thresholds.

**Correctness Analysis:** No issues. Clean, minimal, correct. O(1) performance.

**Positive Observations:** Exemplary DRY extraction. Named constants for thresholds. Defensive `isinstance(tick_data, dict)` check.

---

## 7. PROGRESS MODULE

### 7.1 `backend/progress/longitudinal.py` — Feature Trend Dataclass

**File Metrics:** 10 LOC | 1 dataclass

Minimal dataclass with 4 fields: `feature`, `slope`, `volatility`, `confidence`. No issues.

---

### 7.2 `backend/progress/trend_analysis.py` — Linear Regression Trend Detection

**File Metrics:** 14 LOC | 1 function

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| ~~AC-39-01~~ | ~~MEDIUM~~ | ~~`np.polyfit(x, y, 1)[0]` crashes if `len(values) < 2`~~ | ~~Add guard~~ **RESOLVED — `if len(values) < 2: return 0.0, 0.0, 0.0` guard added** |
| AC-39-02 | LOW | `confidence = min(1.0, len(values) / 30)` — 30 data points = full confidence. For typical usage (10 matches), confidence = 0.33. May be too conservative | Document rationale or lower threshold |

---

## 8. CONSOLIDATED FINDINGS MATRIX

### Findings by Severity

#### CRITICAL Findings

None.

#### HIGH Findings

None.

#### MEDIUM Findings

| ID | File | Category | Finding | Recommendation | Cross-Ref |
|----|------|----------|---------|----------------|-----------|
| ~~AC-35-02~~ | ~~pro_demo_miner.py~~ | ~~Correctness~~ | ~~KAST formatted as 0.7% instead of 74.0%~~ | ~~Multiply by 100~~ | **RESOLVED** |
| AC-15-01 | hybrid_engine.py | Performance | Constructor eagerly loads SBERT, DB, ML model | Defer to first use | — |
| AC-15-02 | hybrid_engine.py | Architecture | Circular import risk on `MATCH_AGGREGATE_FEATURES` | Restructure import | — |
| AC-23-01 | coaching_service.py | Concurrency | Thread-unsafe singleton | Add Lock | — |
| AC-23-02 | coaching_service.py | Correctness | Z-score threshold -10 never triggers RAG enhancement | Change to -1.5 | — |
| ~~AC-23-03~~ | ~~coaching_service.py~~ | ~~Performance~~ | ~~New HybridCoachingEngine per call loads SBERT repeatedly~~ | ~~Cache engine instance~~ | **RESOLVED** |
| AC-24-01 | coaching_dialogue.py | Correctness | Hardcoded game context (full_buy, T) in Experience Bank query | Use player_context | — |
| AC-21-01 | analysis_orchestrator.py | Concurrency | Thread-unsafe singleton | Add Lock | — |
| AC-07-01 | game_tree.py | Correctness | Transposition table depth semantics may cause suboptimal pruning | Verify depth convention | — |
| ~~AC-07-02~~ | ~~game_tree.py~~ | ~~Concurrency~~ | ~~Thread-unsafe singleton~~ | ~~Add Lock~~ | **RESOLVED** — singleton removed; stateless factory |
| AC-32-01 | experience_bank.py | Performance | JSON embedding storage (~3KB per vector) vs binary BLOB | Consider binary encoding | — |
| AC-32-02 | experience_bank.py | Architecture | Usage count update on read violates CQS | Separate retrieval from tracking | — |
| ~~AC-32-03~~ | ~~experience_bank.py~~ | ~~Performance~~ | ~~O(E×T) linear scan for tick lookup~~ | ~~Build tick-indexed dict~~ | **RESOLVED** |
| ~~AC-36-02~~ | ~~rag_knowledge.py~~ | ~~Scalability~~ | ~~In-memory similarity search limited to 500 entries~~ | ~~Implement FAISS index~~ | **RESOLVED** — FAISS `vector_index.py` implemented |
| AC-33-01 | graph.py | Correctness | depth parameter accepted but ignored in subgraph query | Implement or remove parameter | — |
| AC-34-01 | init_knowledge_base.py | Architecture | sys.path modification at module level | Guard with __main__ check | — |
| ~~AC-39-01~~ | ~~trend_analysis.py~~ | ~~Correctness~~ | ~~np.polyfit crashes if len(values) < 2~~ | ~~Add input validation~~ | **RESOLVED** |
| AC-05-01 | belief_model.py | Correctness | Auto-calibration unreliable with sparse death events | Log warning on small samples | — |
| AC-03-01 | blind_spots.py | Performance | Grid allocation per-call in danger zone computation | Pool allocation | — |
| AC-04-01 | deception_index.py | Correctness | Velocity threshold not map-scale-normalized | Normalize by map bounds | — |
| AC-06-01 | entropy_analysis.py | Correctness | np.log2(0) risk despite filter — floating point edge case | Add epsilon or use scipy.stats.entropy | — |
| AC-09-01 | role_classifier.py | Correctness | K-Means non-determinism could swap role labels | Set random_state=GLOBAL_SEED | — |
| AC-11-01 | win_probability.py | Correctness | NN model produces random predictions without checkpoint | Document or add warning log | — |
| AC-26-01 | llm_service.py | Performance | Model auto-selection may choose oversized model | Sort by size or whitelist | — |
| AC-28-01 | profile_service.py | Correctness | sync_all_external_data saves empty profile | Wire API data to profile | — |
| ~~AC-28-02~~ | ~~profile_service.py~~ | ~~Security~~ | ~~FaceIT URL lacks URL encoding for nickname~~ | ~~Use urllib.parse.quote()~~ | **RESOLVED** |

#### LOW Findings

77 LOW findings across all files (see per-file analysis above for complete listing).

### Findings by Category

| Category | CRIT | HIGH | MED | LOW | INFO | Total | Resolved |
|----------|------|------|-----|-----|------|-------|----------|
| Correctness | 0 | 0 | 9 | 28 | 0 | 37 | 2 (AC-35-02, AC-39-01) |
| Performance | 0 | 0 | 3 | 4 | 0 | 7 | 4 (AC-23-03, AC-32-03, AC-36-02→Scalability, AC-07-05→LOW) |
| Concurrency | 0 | 0 | 2 | 0 | 0 | 2 | 2 (AC-07-02, AC-07-05→LOW resolved) |
| Architecture | 0 | 0 | 3 | 8 | 0 | 11 | 0 |
| Security | 0 | 0 | 0 | 3 | 0 | 3 | 1 (AC-28-02) |
| Scalability | 0 | 0 | 0 | 0 | 0 | 0 | 1 (AC-36-02) |
| Data Integrity | 0 | 0 | 0 | 6 | 0 | 6 | 0 |
| Maintainability | 0 | 0 | 0 | 27 | 0 | 27 | 0 |
| **Total** | **0** | **0** | **18** | **76** | **15** | **109** | **8 MEDIUM + 1 LOW resolved** |

### Findings Trend (vs Prior Audits)

| Phase | Items Fixed | Items Still Open |
|-------|-----------|------------------|
| Phase 4 (Analysis+Coaching) | 24 | 0 |
| Phase 5 (Services+Knowledge) | 38 | 0 |
| G-02 (Danger zone) | 1 | 0 (verified) |
| G-07 (Belief calibrator) | 1 | 0 (verified) |
| G-08 (Coaching fallback) | 1 | 0 (verified) |
| G-05 (Heuristic calibration) | 0 | 1 (permanently deferred) |
| Post-audit fixes | 8 MEDIUM + 1 LOW | 0 |
| **Remaining open findings** | — | **18 MEDIUM, 76 LOW** |

---

## 9. RECOMMENDATIONS

### Immediate Actions (MEDIUM severity)

1. ~~**Fix KAST formatting in `pro_demo_miner.py`**~~ — **RESOLVED.** Now multiplies by 100 with guard for already-percentage values.

2. ~~**Cache HybridCoachingEngine in `coaching_service.py`**~~ — **RESOLVED.** Lazy-cached as `self._hybrid_engine`.

3. **Fix Z-score threshold in `coaching_service.py`** — Change `-10` to `-1.5` for RAG enhancement trigger. (Complexity: LOW)

4. ~~**Add input validation in `trend_analysis.py`**~~ — **RESOLVED.** `len(values) < 2` guard added.

5. **Add threading.Lock to 2 remaining singleton patterns** — `coaching_service.py`, `analysis_orchestrator.py`. (Complexity: LOW) ~~`game_tree.py`~~ resolved (singleton removed). `coaching_dialogue.py` still open.

6. **Set `random_state=GLOBAL_SEED` in role_classifier.py K-Means** — Ensures deterministic clustering. (Complexity: LOW)

### Short-Term Actions (Architectural)

7. **Lazy-load SBERT model in `hybrid_engine.py`** — Defer to first retrieval call. (Complexity: MEDIUM)

8. ~~**Build tick-indexed lookup in `experience_bank.py`**~~ — **RESOLVED.** Uses `tick_data_by_tick` O(1) dict.

9. ~~**Fix `profile_service.py` FaceIT URL encoding**~~ — **RESOLVED.** Uses `urllib.parse.quote()`.

10. **Implement depth parameter or remove it in `graph.py`** — Currently misleads callers. (Complexity: MEDIUM)

### Long-Term Actions (Strategic)

11. ~~**Implement FAISS vector index**~~ — **RESOLVED.** `vector_index.py` implements FAISS IndexFlatIP with disk persistence, lazy rebuild, and brute-force fallback.

12. **Binary embedding storage** — Replace JSON-encoded SBERT vectors with BLOB columns. 6x storage reduction. (Complexity: MEDIUM)

13. **Standardize factory function behavior** — All analysis engine factories should consistently return either singletons or new instances, not mix both patterns. (Complexity: MEDIUM)

---

## APPENDIX A: COMPLETE FILE INVENTORY

| # | File Path | LOC | Classes | Functions | Findings (M/L) |
|---|-----------|-----|---------|-----------|-----------------|
| 1 | backend/analysis/__init__.py | 95 | 0 | 5 | 0/0 |
| 2 | backend/analysis/win_probability.py | 290 | 2 | 12 | 1/2 |
| 3 | backend/analysis/role_classifier.py | 544 | 2 | 15 | 1/3 |
| 4 | backend/analysis/game_tree.py | 515 | 3 | 18 | 1/2 (was 2/3; AC-07-02, AC-07-05 resolved) |
| 5 | backend/analysis/belief_model.py | 463 | 3 | 16 | 1/4 |
| 6 | backend/analysis/blind_spots.py | 213 | 1 | 8 | 1/3 |
| 7 | backend/analysis/deception_index.py | 235 | 1 | 10 | 1/3 |
| 8 | backend/analysis/entropy_analysis.py | 159 | 1 | 7 | 1/2 |
| 9 | backend/analysis/momentum.py | 218 | 1 | 8 | 0/3 |
| 10 | backend/analysis/engagement_range.py | 437 | 1 | 14 | 0/3 |
| 11 | backend/analysis/utility_economy.py | 405 | 1 | 12 | 0/4 |
| 12 | backend/coaching/__init__.py | 25 | 0 | 5 | 0/0 |
| 13 | backend/coaching/correction_engine.py | 64 | 1 | 4 | 0/2 |
| 14 | backend/coaching/explainability.py | 94 | 1 | 5 | 0/3 |
| 15 | backend/coaching/hybrid_engine.py | 641 | 1 | 22 | 2/3 |
| 16 | backend/coaching/longitudinal_engine.py | 49 | 0 | 1 | 0/3 |
| 17 | backend/coaching/nn_refinement.py | 30 | 0 | 1 | 0/1 |
| 18 | backend/coaching/pro_bridge.py | 117 | 1 | 6 | 1/2 |
| 19 | backend/coaching/token_resolver.py | 108 | 1 | 4 | 0/3 |
| 20 | backend/services/__init__.py | 1 | 0 | 0 | 0/0 |
| 21 | backend/services/analysis_orchestrator.py | 537 | 1 | 16 | 1/2 |
| 22 | backend/services/analysis_service.py | 91 | 1 | 3 | 0/2 |
| 23 | backend/services/coaching_service.py | 713 | 1 | 24 | 2/3 (was 3/3; AC-23-03 resolved) |
| 24 | backend/services/coaching_dialogue.py | 373 | 1 | 14 | 1/3 |
| 25 | backend/services/lesson_generator.py | 382 | 1 | 12 | 0/3 |
| 26 | backend/services/llm_service.py | 253 | 1 | 8 | 1/2 |
| 27 | backend/services/ollama_writer.py | 110 | 1 | 4 | 0/1 |
| 28 | backend/services/profile_service.py | 119 | 0 | 3 | 1/1 (was 2/1; AC-28-02 resolved) |
| 29 | backend/services/visualization_service.py | 119 | 1 | 3 | 0/2 |
| 30 | backend/services/telemetry_client.py | 59 | 1 | 3 | 0/2 |
| 31 | backend/knowledge/__init__.py | 1 | 0 | 0 | 0/0 |
| 32 | backend/knowledge/experience_bank.py | 748 | 4 | 28 | 2/2 (was 3/2; AC-32-03 resolved) |
| 33 | backend/knowledge/graph.py | 199 | 1 | 8 | 1/2 |
| 34 | backend/knowledge/init_knowledge_base.py | 111 | 0 | 2 | 1/1 |
| 35 | backend/knowledge/pro_demo_miner.py | 189 | 1 | 6 | 0/1 (was 1/1; AC-35-02 resolved) |
| 36 | backend/knowledge/rag_knowledge.py | 477 | 3 | 14 | 0/3 (was 1/3; AC-36-02 resolved) |
| 37 | backend/knowledge/round_utils.py | 35 | 0 | 1 | 0/0 |
| 38 | backend/progress/longitudinal.py | 10 | 1 | 0 | 0/0 |
| 39 | backend/progress/trend_analysis.py | 14 | 0 | 1 | 0/1 (was 1/1; AC-39-01 resolved) |
| | **TOTALS** | **~8,900** | **42** | **~280** | **18/76** (originally 26/77; 8M+1L resolved) |

---

## APPENDIX B: GLOSSARY

| Term | Definition |
|------|-----------|
| COPER | Coaching Orchestration via Pro-Enhanced References — the primary coaching mode |
| RAG | Retrieval-Augmented Generation — semantic search over tactical knowledge base |
| SBERT | Sentence-BERT (all-MiniLM-L6-v2) — embedding model for semantic similarity |
| Expectiminimax | Game tree search algorithm combining minimax with probability-weighted chance nodes |
| CQS | Command-Query Separation — principle that methods should either modify state or return data, not both |
| Z-score | Standard deviation from mean — measures how far a player's stat deviates from baseline |
| KAST | Kills, Assists, Survived, Traded — composite CS2 performance metric (0.0–1.0 range) |
| ADR | Average Damage per Round — key CS2 performance indicator |
| EMA | Exponential Moving Average — used for momentum tracking and feedback confidence |
| FOV | Field of View — used in blind spot analysis |
| POV | Point of View — player camera direction |

---

## APPENDIX C: CROSS-REFERENCE INDEX

| Finding ID | Prior Code | Status |
|------------|-----------|--------|
| — | G-02 (Danger zone) | VERIFIED FIXED in blind_spots.py |
| — | G-07 (Belief calibrator) | VERIFIED FIXED in belief_model.py |
| — | G-08 (Coaching fallback) | VERIFIED FIXED in coaching_service.py |
| — | G-09 (Test failures) | VERIFIED FIXED — imports resolved |
| — | F5-03 (OOM knowledge base) | VERIFIED FIXED — MAX_REEMBED_BATCH limit |
| — | F5-04 (SBERT re-loading) | VERIFIED FIXED — singleton get_experience_bank() |
| — | F5-20 (Round phase DRY) | VERIFIED FIXED — round_utils.py shared utility |
| — | F5-23 (init_database in constructor) | VERIFIED FIXED — removed from constructors |
| — | F5-27 (Synthetic data disclosure) | VERIFIED FIXED — __main__ block annotated |
| — | G-05 (Heuristic calibration) | PERMANENTLY DEFERRED — requires pro dataset |
| AC-35-02 | KAST formatting | RESOLVED POST-AUDIT — multiplies by 100 with guard |
| AC-23-03 | SBERT reload per call | RESOLVED POST-AUDIT — lazy-cached `_hybrid_engine` |
| AC-32-03 | O(E×T) tick scan | RESOLVED POST-AUDIT — `tick_data_by_tick` O(1) dict |
| AC-36-02 | In-memory similarity | RESOLVED POST-AUDIT — FAISS `vector_index.py` added |
| AC-07-02 | Game tree singleton | RESOLVED POST-AUDIT — singleton removed; stateless factory |
| AC-07-05 | Unbounded TT | RESOLVED POST-AUDIT — `_TT_MAX_SIZE` + LRU eviction |
| AC-39-01 | polyfit crash | RESOLVED POST-AUDIT — `len(values) < 2` guard added |
| AC-28-02 | FaceIT URL encoding | RESOLVED POST-AUDIT — `urllib.parse.quote()` applied |

---

## APPENDIX D: DEPENDENCY GRAPH

```
                     ┌──────────────────────┐
                     │   coaching_service    │ (orchestrator)
                     └──────────┬───────────┘
                        ┌───────┴───────────────────┐
                        │                           │
              ┌─────────▼──────────┐     ┌──────────▼──────────┐
              │  hybrid_engine     │     │  analysis_orchestrator│
              └─────────┬──────────┘     └──────────┬──────────┘
         ┌──────────────┼──────────────┐    ┌───────┴───────────────┐
         │              │              │    │                       │
   ┌─────▼─────┐ ┌──────▼────┐ ┌──────▼┐   │  10 analysis engines  │
   │rag_knowledge│ │pro_bridge│ │nn_model│   │  (win_prob, game_tree,│
   └─────┬─────┘ └──────┬────┘ └───────┘   │   belief, momentum,   │
         │              │                   │   deception, entropy,  │
   ┌─────▼─────┐ ┌──────▼────────┐         │   blind_spots, engage, │
   │experience  │ │token_resolver│          │   role_class, utility) │
   │  _bank     │ └──────────────┘          └───────────────────────┘
   └────────────┘
         │
   ┌─────▼─────┐
   │round_utils │ (shared utility)
   └────────────┘
```

---

## APPENDIX E: DATA FLOW DIAGRAMS

### Coaching Pipeline (COPER Mode)

```
Demo Parse → Feature Engineering → Analysis Engines ─┐
                                                      │
                                                      ▼
                                              coaching_service.py
                                                      │
                                    ┌─────────────────┼─────────────────┐
                                    ▼                 ▼                 ▼
                              COPER Mode       Hybrid Mode       Traditional
                                    │                 │                 │
                              ┌─────┴─────┐     ┌────┴────┐      ┌────┴────┐
                              │Experience │     │ RAG +   │      │Z-score  │
                              │  Bank     │     │ ML Pred │      │Deviations│
                              │+ RAG      │     │+ Pro    │      └─────────┘
                              │+ Pro Refs │     │Baseline │
                              │+ Ollama   │     └─────────┘
                              └───────────┘
                                    │
                                    ▼
                            User-Facing Coaching Insight
```

### Knowledge Retrieval Pipeline

```
User Query / Player Stats
        │
        ▼
  KnowledgeEmbedder (SBERT / fallback hash)
        │
        ▼
  384-dim embedding vector
        │
        ▼
  KnowledgeRetriever.retrieve()
        │
   ┌────┴────┐
   │ SQL     │ SELECT * FROM TacticalKnowledge
   │ Fetch   │ WHERE category=? AND map=?
   │ (≤500)  │ LIMIT 500
   └────┬────┘
        │
        ▼
  Cosine Similarity (in-memory, O(N×D))
        │
        ▼
  Top-K Results + Usage Count Update
        │
        ▼
  generate_unified_coaching_insight()
        │
   ┌────┴────┐
   │ RAG     │ tactical knowledge entries
   │ +       │
   │ ExpBank │ experience-based advice
   │ +       │
   │ Pro Ref │ pro player references
   └────┬────┘
        │
        ▼
  Unified Coaching Insight String
```

---

*End of Report 6/8*
