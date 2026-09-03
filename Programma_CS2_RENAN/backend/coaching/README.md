> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Coaching -- Multi-Mode Coaching Pipeline

> **Authority:** `backend/coaching/`
> **Skill:** `/ml-check`, `/api-contract-review`
> **Owner module:** `backend/services/coaching_service.py`

## Overview

The coaching package is the intelligence layer that transforms raw analysis data into
actionable player feedback. It implements a **four-mode coaching pipeline** where each
mode offers a different trade-off between knowledge-driven advice and neural-network
predictions. The default mode is **COPER** ("Context Optimized with Prompt, Experience,
and Replay"), which combines an Experience Bank, RAG knowledge retrieval, and professional
player reference data to produce coaching output grounded in real match evidence.

All coaching modes are consumed by a single entry point --
`backend/services/coaching_service.py` -- which selects the active mode based on the
feature flags `USE_COPER_COACHING`, `USE_HYBRID_COACHING`, and `USE_RAG_COACHING`
(the separate `USE_JEPA_MODEL` flag gates the JEPA insight adapter, not mode selection).

## The Four Coaching Modes

| # | Mode | Flag | Description |
|---|------|------|-------------|
| 1 | **COPER** | `USE_COPER_COACHING=True` (default) | Experience Bank semantic retrieval + RAG knowledge + Pro References. Requires map name + tick data. |
| 2 | **Hybrid** | `USE_HYBRID_COACHING=True` (default False) | Baseline-deviation Z-scores synthesized with RAG context. ML predictions are computed but currently not consumed by the synthesis (F-0028). Requires player stats. |
| 3 | **Traditional + RAG** | `USE_RAG_COACHING=True` (default False) | Correction engine enhanced with tactical knowledge retrieval. No ML inference. |
| 4 | **Traditional** | _(none — always available)_ | Pure deviation-based correction engine. Zero external dependencies; ultimate fallback. |

### Coaching Fallback Flow

When a higher-fidelity mode is unavailable (missing model, empty knowledge base, etc.),
the pipeline degrades gracefully through the following chain:

```
COPER (Experience Bank + RAG + Pro)
   |  [failure/timeout, or map/tick data missing]
   v
Hybrid (baseline Z + RAG)
   |  [disabled, player stats missing, or failure]
   v
Traditional + RAG (correction engine + knowledge retrieval)
   |  [USE_RAG_COACHING disabled]
   v
Traditional heuristic corrections (correction_engine.py — terminal)
```

Each transition is logged at WARNING level with a structured JSON message containing
the reason for degradation, so the operator always knows which mode is active.

Note: the chain above is a *priority ladder*. At failure time, COPER
failure/timeout falls to Hybrid only when `USE_HYBRID_COACHING` is enabled and
player stats are available — otherwise it lands on plain Traditional; a Hybrid
failure always lands on plain Traditional. The Traditional + RAG level is chosen
only at dispatch time when neither COPER nor Hybrid is selected and
`USE_RAG_COACHING` is enabled.

## File Inventory

| File | Primary Export | Purpose |
|------|---------------|---------|
| `__init__.py` | Package API | Re-exports `HybridCoachingEngine`, `generate_corrections`, `ExplanationGenerator`, `PlayerCardAssimilator`, `get_pro_baseline_for_coach` |
| `hybrid_engine.py` | `HybridCoachingEngine` | Hybrid-mode orchestrator: baseline Z-score deviations + RAG knowledge retrieval; ML predictions computed but not yet consumed by the synthesis (F-0028) |
| `correction_engine.py` | `generate_corrections()` | Ranks precomputed Z-score deviations into the top-3 weighted corrections (confidence and importance scaling) |
| `nn_refinement.py` | `apply_nn_refinement()` | Correction weight scaling — multiplies Z-score deviations by feature-specific weights. Does NOT perform NN inference (historical name) |
| `longitudinal_engine.py` | `generate_longitudinal_coaching()` | Turns precomputed performance trends into regression/improvement insights for long-term advice |
| `explainability.py` | `ExplanationGenerator` | Template-based narrative generation per skill axis, plus insight severity classification |
| `pro_bridge.py` | `PlayerCardAssimilator` | Assimilates professional player stat cards into coach-format baselines and archetypes |
| `token_resolver.py` | `PlayerTokenResolver` | Retrieves static pro "Player Tokens" (stat cards) from `hltv_metadata.db` and compares match stats against them |
| `jepa_insight_adapter.py` | `generate_jepa_insights()` | Converts JEPA coaching-head sigmoid outputs to `InsightCandidate` objects. Maps the first 10 of the 25-dim feature contract to 5 tactical axes. Maturity-gated; activated by `USE_JEPA_MODEL` flag (default `False`). NO-WALLHACK compliant — consumes only player-POV data. Open finding F-0029: it arms on any sidecar-verified checkpoint, including pretrain-only ones whose coaching head is untrained. |

## Module Descriptions

### hybrid_engine.py -- HybridCoachingEngine

The `HybridCoachingEngine` is the primary orchestrator for the Hybrid coaching mode.
Its pipeline: compute Z-score deviations of `player_stats` against the pro baseline
(optionally a contextual baseline from a specific pro's stat card), run ML inference
through the legacy AdvancedCoachNN when a trained checkpoint loads (26-HYB-01;
skipped entirely when `USE_JEPA_MODEL` is on — that path is RAG-only), retrieve
relevant knowledge from the RAG index, and synthesize insights from the deviations
and knowledge. Open finding F-0028 (see `docs/OPEN_ISSUES.md`): the ML predictions
are computed but currently not consumed by the synthesis step — output is grounded
in baseline Z-scores + RAG only. Insight confidence combines |Z| with knowledge
usage counts; stale fallback baselines tag every insight with a degraded-baseline
warning (F4-02).

### correction_engine.py -- generate_corrections()

Stateless function that takes *precomputed* Z-score deviations (baseline comparison
happens upstream) plus `rounds_played`. Each deviation is scaled by a confidence
factor (`rounds_played / 300`, capped at 1.0) and a per-feature importance weight
(overridable via the `COACH_WEIGHT_OVERRIDES` setting); the top-3 corrections
sorted by `|weighted_z| * importance` are returned as dicts (`feature`,
`weighted_z`, `importance`). Severity and human-readable narratives are attached
downstream by `coaching_service.py` using `ExplanationGenerator`. This module is
the final fallback when all higher-fidelity coaching modes are unavailable.

### nn_refinement.py -- apply_nn_refinement()

Correction weight scaling step (DA-03: historical name is misleading). Takes heuristic
corrections from `correction_engine.py` and multiplies each `weighted_z` by
`(1 + feature_weight)` from a provided adjustments dict. This is pure arithmetic — no
neural network is loaded, no model inference occurs, no confidence scoring is performed.
The adjustments dict *may* originate from an NN model's output upstream, but this module
itself is a scalar multiplication. Called conditionally by `correction_engine.py` only
when `nn_adjustments` is non-empty — the current service path never passes adjustments,
so this step is dormant in production.

### longitudinal_engine.py -- generate_longitudinal_coaching()

Generates coaching advice from *precomputed* per-feature trend objects (slope +
confidence, produced by `compute_trend()` in `backend/progress/trend_analysis.py`
and passed in by `coaching_service.py`). Trends with confidence >= 0.6 yield up to
3 insights: negative slopes become regression insights (severity escalated to High
when the NN signals a `stability_warning`), positive slopes become improvement
insights.

### explainability.py -- ExplanationGenerator

Template-based narrative generation: `generate_narrative()` renders per-axis
templates (`SkillAxes` MECHANICS / POSITIONING / UTILITY / TIMING / DECISION) with
dynamic context (location, weapon, delta magnitude). Deltas below the silence
threshold (|delta| < 0.2) produce no feedback — "silence is a valid action" — and a
skill-level filter simplifies output for beginners. `classify_insight_severity()`
maps |delta| to High / Medium / Low. Used by `coaching_service.py` to turn
correction Z-scores into readable coaching messages.

### pro_bridge.py -- PlayerCardAssimilator

Bridges the gap between professional player statistics (from `hltv_metadata.db`) and
the coaching pipeline. The `PlayerCardAssimilator` translates a `ProPlayerStatCard`
into the coach's baseline format on per-round scales (KPR/DPR — P3-02), with
defensive normalization of legacy percent-form values (V-2), and classifies the
pro's archetype via `get_player_archetype()` (Star Fragger / Support Anchor /
Sniper Specialist / All-Rounder). The `get_pro_baseline_for_coach()` helper
provides a ready-to-use contextual baseline dictionary, used by `hybrid_engine.py`
when a pro reference is selected.

### token_resolver.py -- PlayerTokenResolver

Retrieves static pro "Player Tokens" for the AI Coach: `get_player_token()` looks
up a professional by exact nickname in `hltv_metadata.db` (`ProPlayer` + latest
`ProPlayerStatCard`) and assembles a structured token dict (identity, core metrics,
tactical baselines, granular detailed stats, metadata).
`compare_performance_to_token()` returns a "Correction Delta" (rating / ADR / KAST /
HS deltas plus an underperformance flag) for expert assessment against the token.
Fuzzy name matching lives elsewhere (`nickname_resolver.py`, used by
`backend/services/player_lookup.py`), not in this module.

## Integration with Services Layer

```
coaching_service.py
    |
    +-- selects coaching mode (COPER / Hybrid / Traditional+RAG / Traditional)
    |
    +-- calls hybrid_engine.py (Hybrid mode)
    |       |-- baseline Z-score deviations (pro_bridge.py contextual baselines)
    |       |-- ML inference (legacy AdvancedCoachNN -- output unused, F-0028)
    |       +-- RAG retrieval (knowledge/)
    |
    +-- calls correction_engine.py (Traditional modes and failure fallbacks)
    |       +-- nn_refinement.py (only if nn_adjustments passed -- dormant today)
    |
    +-- calls longitudinal_engine.py (trends from compute_trend())
    |
    +-- calls explainability.py (narratives + severity for corrections)
    |
    +-- saves CoachingInsight rows to the database (consumed by the UI)
```

The `coaching_service.py` orchestrator also injects temporal baseline context from
`backend/processing/baselines/pro_baseline.py` (`TemporalBaselineDecay`), ensuring that coaching advice accounts
for how the player's skill level has evolved over recent sessions.

## Development Notes

- **Feature flag discipline:** Never bypass feature flags. The coaching mode is selected
  exclusively through `core/config.py` flags. Hard-coding a mode causes test failures.
- **25-dim contract:** Any module that touches the feature vector must respect
  `METADATA_DIM=25`. See the Dimensional Contract table in the project root `CLAUDE.md`.
- **Structured logging:** All modules use `get_logger("cs2analyzer.coaching.<module>")`.
  Fallback transitions log at WARNING level with correlation IDs.
- **Thread safety:** The coaching pipeline may be invoked from the Quad-Daemon's Teacher
  thread. All shared state must be accessed through thread-safe accessors, never module-level
  globals.
- **Testing:** Tests live in `Programma_CS2_RENAN/tests/`. Use the `mock_db_manager` and
  `torch_no_grad` fixtures for coaching tests.

## Dependencies

- **PyTorch** -- ML model loading and inference in `hybrid_engine.py` and `jepa_insight_adapter.py`
- **sentence-transformers** -- Embedding generation for RAG and Experience Bank retrieval
- **SQLModel** -- Database access (tactical knowledge, coaching insights, pro stat cards)
