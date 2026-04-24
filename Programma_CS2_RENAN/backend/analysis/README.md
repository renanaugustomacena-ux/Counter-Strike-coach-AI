> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Analysis — Game Theory & Statistical Engines

**Authority:** Phase 6 Game Theory implementation + Phase 1B foundation modules.
**Skill Level:** Advanced — Bayesian inference, information theory, adversarial search, neural classification.

---

## Overview

This directory contains 11 analytical engines that form the tactical intelligence layer of the CS2 coaching system. They transform raw demo data (tick positions, kill events, economy snapshots, utility throws) into actionable coaching insights through game theory, probabilistic modeling, and statistical analysis.

Every module follows the factory function pattern for thread-safe singleton access. All engines are orchestrated by `backend/services/coaching_service.py` and exposed to the UI through the analysis orchestrator.

---

## File Inventory

| File | Primary Classes | Factory Function | Purpose |
|------|----------------|------------------|---------|
| `belief_model.py` | `DeathProbabilityEstimator`, `BeliefState`, `AdaptiveBeliefCalibrator` | `get_death_estimator()` | Bayesian death probability with online calibration |
| `win_probability.py` | `WinProbabilityPredictor`, `WinProbabilityNN`, `GameState` | `get_win_predictor()` | Neural round win prediction from game state |
| `blind_spots.py` | `BlindSpotDetector`, `BlindSpot` | `get_blind_spot_detector()` | Recurring suboptimal decisions vs. game tree |
| `engagement_range.py` | `EngagementRangeAnalyzer`, `NamedPositionRegistry`, `EngagementProfile` | `get_engagement_range_analyzer()` | Kill distance profiling and callout annotation |
| `entropy_analysis.py` | `EntropyAnalyzer`, `UtilityImpact` | `get_entropy_analyzer()` | Shannon entropy for utility effectiveness |
| `deception_index.py` | `DeceptionAnalyzer`, `DeceptionMetrics` | `get_deception_analyzer()` | Tactical deception quantification |
| `game_tree.py` | `ExpectiminimaxSearch`, `OpponentModel`, `GameNode` | `get_game_tree_search()` | Adversarial decision tree with chance nodes |
| `role_classifier.py` | `RoleClassifier`, `RoleProfile` | `get_role_classifier()` | 5-role neural + heuristic classification |
| `utility_economy.py` | `UtilityAnalyzer`, `EconomyOptimizer`, `EconomyDecision` | `get_utility_analyzer()`, `get_economy_optimizer()` | Grenade efficiency and buy-round optimization |
| `momentum.py` | `MomentumTracker`, `MomentumState` | `get_momentum_tracker()` | Round momentum with tilt detection |
| `movement_quality.py` | `MovementQualityAnalyzer` | `get_movement_quality_analyzer()` | Positioning-mistake detector (MLMove paper, 4 patterns) |
| `__init__.py` | _(re-exports all public symbols)_ | _(all factory functions)_ | Package API surface |

---

## Module Descriptions

### 1. Probabilistic Models

#### belief_model.py — Bayesian Death Assessment

Estimates `P(death | belief, HP, armor, weapon_class)` using a logistic Bayesian update. The `BeliefState` dataclass captures information asymmetry: visible enemies, inferred enemy count, information age, and positional exposure. Threat decays exponentially via `THREAT_DECAY_LAMBDA` (default 0.1, calibratable).

The `AdaptiveBeliefCalibrator` extends calibration with three pipelines:
- **HP bracket priors** from historical round death rates (grouped into full/damaged/critical).
- **Weapon lethality multipliers** from per-weapon-class kill ratios, normalized to rifle = 1.0.
- **Threat decay lambda** fitted via log-linearized least squares on information-age bins.

All calibrated values are bounded by safety limits and persisted as `CalibrationSnapshot` rows for observability. The helper `extract_death_events_from_db()` pulls calibration data from `RoundStats` with a `MAX_CALIBRATION_SAMPLES = 5000` cap.

#### win_probability.py — Neural Win Prediction

A 12-feature feedforward network (64 -> 32 -> 1 with sigmoid) predicts real-time round win probability. The `GameState` dataclass captures economy, player counts, utility, map control, time, bomb state, and side. Feature normalization: economy / 16000, players / 5, time / 115, utility / 5.

Heuristic post-processing overrides neural output for deterministic boundary cases (0 alive = 0%, 0 enemies = 100%) and applies player-advantage clamps and bomb-planted adjustments. Checkpoint validation (rule A-12) prevents cross-loading the 9-dim trainer model into the 12-dim predictor.

---

### 2. Tactical Analysis

#### blind_spots.py — Strategic Weakness Detection

Compares player actions against `ExpectiminimaxSearch` optimal recommendations across historical rounds. Classifies game states into human-readable situations (e.g., "1v3 clutch", "post-plant advantage", "eco round") and aggregates mismatches by frequency and win-probability impact.

The `generate_training_plan()` method produces a natural-language coaching plan targeting the top-N most impactful blind spots, with specific practice recommendations per action type (push, hold, rotate, use_utility).

#### engagement_range.py — Kill Distance Profiling

Computes Euclidean kill distances from 3D positions and classifies them into four bands: close (<500u), medium (500-1500u), long (1500-3000u), extreme (>3000u). The `EngagementProfile` is compared against role-specific pro baselines (AWPer, Entry, Support, Lurker, IGL, Flex) with a 15% deviation threshold.

Includes `NamedPositionRegistry` with 60+ hardcoded callout positions across 9 competitive maps (Mirage, Inferno, Dust2, Anubis, Nuke, Ancient, Overpass, Vertigo, Train). Supports JSON extension for community-contributed callouts. Kill events are annotated with the nearest named position for human-readable output.

#### entropy_analysis.py — Information-Theoretic Utility Evaluation

Measures the Shannon entropy `H = -sum(p * log2(p))` of enemy position distributions before and after utility throws. Positions are discretized onto a 32x32 grid (configurable). Entropy delta quantifies each throw's information gain, normalized against theoretical maximums per utility type (smoke: 2.5 bits, molotov: 2.0, flash: 1.8, HE: 1.5).

Thread safety is maintained via `_buffer_lock` protecting the pre-allocated grid buffer. The `rank_utility_usage()` method sorts throws by effectiveness for coaching output.

#### deception_index.py — Tactical Deception Quantification

Computes a composite deception index from three sub-metrics:
- **Fake flash rate** (weight 0.25): fraction of flashbangs that fail to blind enemies within 128 ticks (~2s). Detected via vectorized `searchsorted` over blind event ticks.
- **Rotation feint rate** (weight 0.40): significant direction reversals (>108 degrees) in sampled movement paths, normalized by map extent.
- **Sound deception score** (weight 0.35): inverse crouch ratio as a proxy for deliberate noise generation vs. silent movement.

The `compare_to_baseline()` method produces natural-language coaching output comparing player metrics against pro baselines.

---

### 3. Decision Optimization

#### game_tree.py — Expectiminimax Search

Models CS2 round strategy as an alternating max/min/chance tree with four tactical actions: push, hold, rotate, use_utility. Leaf nodes are evaluated by `WinProbabilityPredictor` (lazy-loaded to avoid circular imports).

The `OpponentModel` adapts action distributions using:
- Economy-tier priors (eco/force/full_buy).
- Side adjustments (T push more, CT hold more).
- Player advantage and time pressure modifiers.
- EMA blending with learned profiles once 10+ rounds of data are available.

Performance features: transposition table (`_TT_MAX_SIZE = 10000`), deterministic state hashing, configurable node budget (`DEFAULT_NODE_BUDGET = 1000`). The `suggest_strategy()` method returns natural-language recommendations with win probability and confidence level.

#### role_classifier.py — Neural 5-Role Classification

Dual-classifier architecture combining weighted heuristic scoring with a neural secondary opinion:
- **Heuristic**: computes per-role affinity scores from stats (AWP kill ratio, entry rate, assist rate, survival rate, solo kills) against learned thresholds from `RoleThresholdStore`.
- **Neural**: 5-class softmax head loaded from checkpoint (`load_role_head()`), with feature normalization using training statistics.
- **Consensus**: agreement boosts confidence (+0.1), neural overrides heuristic only with sufficient margin (+0.1).

Cold-start guard returns FLEX with 0% confidence when thresholds are not yet learned. Team-level classification (`classify_team()`) enforces composition constraints (max 1 AWPer). The `audit_team_balance()` method detects structural weaknesses (missing Entry, duplicate Lurkers, etc.).

Role-specific coaching tips are retrieved via RAG (`KnowledgeRetriever`) with fallback to static `_FALLBACK_TIPS`.

---

### 4. Economy & Resources

#### utility_economy.py — Grenade Efficiency & Buy Decisions

`UtilityAnalyzer` scores each utility type against pro baselines: molotov (35 dmg/throw), HE (25 dmg/throw), flash (1.2 enemies/flash), smoke (0.9 usage rate). Generates per-type recommendations when effectiveness < 50% and computes dollar-value economy impact.

`EconomyOptimizer` recommends buy decisions (full-buy, force-buy, half-buy, eco, pistol) based on current money, round number, side, score differential, and loss bonus. Supports MR12 (CS2 default) and MR13 (legacy) formats via configurable `HALF_ROUND` mapping. Special-cases pistol rounds and half-switch critical rounds.

#### momentum.py — Psychological Momentum Tracking

Models momentum as a time-decaying multiplier (bounded [0.7, 1.4]) driven by win/loss streaks. Win streaks add +0.05 per streak round; loss streaks subtract -0.04 (asymmetric to reflect CS2 economy advantage). Momentum decays exponentially across skipped rounds (`decay_rate = 0.15`) and resets at half-switch (round 13 MR12, round 16 MR13).

Tilt detection triggers at multiplier < 0.85 (~3-round loss streak). The `predict_performance_adjustment()` helper scales base player ratings by the momentum multiplier. The `from_round_stats()` function builds a full momentum timeline from `RoundStats` records.

---

## Integration Flow

```
Demo Parser (demoparser2)
    |
    v
Feature Engineering (vectorizer.py, 25-dim)
    |
    +--> WinProbabilityPredictor ----+
    |                                |
    +--> DeathProbabilityEstimator --+--> BlindSpotDetector
    |                                |        |
    +--> EntropyAnalyzer ------------+        v
    |                                |   Training Plan
    +--> DeceptionAnalyzer ----------+
    |                                |
    +--> EngagementRangeAnalyzer ----+--> Coaching Service
    |                                |    (coaching_service.py)
    +--> RoleClassifier -------------+        |
    |                                |        v
    +--> MomentumTracker -----------+    Analysis Orchestrator
    |                                |    (analysis_orchestrator.py)
    +--> UtilityAnalyzer -----------+        |
    |                                |        v
    +--> EconomyOptimizer ----------+    UI / Reports
    |                                |
    +--> ExpectiminimaxSearch ------+
              |
              v
         OpponentModel
```

---

## Factory Function Exports

All factory functions are re-exported from `__init__.py`:

```python
from Programma_CS2_RENAN.backend.analysis import (
    get_death_estimator,        # -> DeathProbabilityEstimator
    get_win_predictor,          # -> WinProbabilityPredictor
    get_blind_spot_detector,    # -> BlindSpotDetector
    get_engagement_range_analyzer,  # -> EngagementRangeAnalyzer
    get_entropy_analyzer,       # -> EntropyAnalyzer
    get_deception_analyzer,     # -> DeceptionAnalyzer
    get_game_tree_search,       # -> ExpectiminimaxSearch
    get_role_classifier,        # -> RoleClassifier
    get_utility_analyzer,       # -> UtilityAnalyzer
    get_economy_optimizer,      # -> EconomyOptimizer
    get_momentum_tracker,       # -> MomentumTracker
)
```

---

## Key Algorithms

| Algorithm | Module | Description |
|-----------|--------|-------------|
| Bayesian logistic update | `belief_model.py` | Log-odds prior + weighted likelihood terms -> sigmoid posterior |
| Exponential threat decay | `belief_model.py` | `P(threat) = visible + inferred * exp(-lambda * age) * 0.5` |
| Least-squares lambda fit | `belief_model.py` | Log-linearize death rate vs. info age, `polyfit` degree 1 |
| Xavier-initialized MLP | `win_probability.py` | 12 -> 64 -> 32 -> 1 sigmoid, ReLU + Dropout |
| Shannon entropy on grid | `entropy_analysis.py` | `H = -sum(p * log2(p))` over 32x32 spatial discretization |
| Vectorized flash detection | `deception_index.py` | `searchsorted` on sorted blind ticks for O(F log B) matching |
| Expectiminimax + TT | `game_tree.py` | Max/min/chance tree with transposition table memoization |
| EMA opponent blending | `game_tree.py` | `(1 - alpha) * base + alpha * learned`, alpha capped at 0.7 |
| Dual-classifier consensus | `role_classifier.py` | Heuristic + neural with boost/margin fusion rules |
| Exponential momentum decay | `momentum.py` | `multiplier = 1.0 +/- streak_delta * exp(-decay * gap)` |

---

## Development Notes

1. **Thread safety.** `DeathProbabilityEstimator` uses double-checked locking for its singleton. `EntropyAnalyzer` protects its shared grid buffer with `_buffer_lock`. Other modules are instantiated per-request via factory functions.

2. **Lazy imports.** `ExpectiminimaxSearch` lazy-loads `WinProbabilityPredictor` to break circular import chains. `BlindSpotDetector` imports `ExpectiminimaxSearch` at `__init__` time (function-level).

3. **Calibration pipeline.** `AdaptiveBeliefCalibrator.auto_calibrate()` is called by the Teacher daemon periodically. Calibration snapshots are persisted as `CalibrationSnapshot` DB rows for rollback and observability.

4. **Cold-start behavior.** `RoleClassifier` returns FLEX/0% confidence when `RoleThresholdStore` has no learned data. `OpponentModel` falls back to `_DEFAULT_OPPONENT_PROBS` until 10+ rounds are observed.

5. **Checkpoint isolation.** `WinProbabilityNN` (12-dim predictor) and `WinProbabilityTrainerNN` (9-dim trainer) are separate architectures. Rule A-12 validates input dimension before `load_state_dict` to prevent silent corruption.

6. **Named positions.** The `NamedPositionRegistry` ships with 60+ callouts across 9 maps. Additional positions can be loaded from JSON without code changes via `load_from_json()`.

7. **Safety bounds.** All calibrated parameters are clamped: priors [0.05, 0.95], weapon lethality [0.1, 3.0], decay lambda [0.01, 1.0], momentum [0.7, 1.4]. This prevents pathological values from corrupting downstream analysis.

8. **Structured logging.** Every module uses `get_logger("cs2analyzer.analysis.<module>")` with correlation ID support for tracing analysis calls through the coaching pipeline.

---

## Dependencies

- **PyTorch** — `WinProbabilityNN`, neural role head, tensor operations.
- **NumPy** — Grid entropy computation, vectorized flash detection, statistical analysis.
- **pandas** — Calibration data frames, round data for deception analysis.
- **SQLModel** — `CalibrationSnapshot` persistence, `RoundStats` queries.
- **Standard library** — `math`, `threading`, `dataclasses`, `json`, `pathlib`, `enum`, `collections`.
