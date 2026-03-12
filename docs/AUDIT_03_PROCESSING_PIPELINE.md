# Audit Report 03 — Processing Pipeline

**Scope:** `backend/processing/` — 28 files, ~6,679 lines | **Date:** 2026-03-10
**Open findings:** 0 HIGH | 18 MEDIUM | 12 LOW

---

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| P3-01 | data_pipeline.py | `joblib.load()` deserialization risk — no HMAC integrity check on scaler file |
| P3-04 | tensor_factory.py | Training 64x64 vs inference 224x224 — no spatial dimension assertion in model forward |
| P3-06 | tick_enrichment.py | FOV hardcoded at 90° — scoped weapons reduce to 10-55° |
| P3-07 | player_knowledge.py | Utility zones use time-based expiry, not destruction events |
| P3-09 | base_features.py | `load_learned_heuristics()` no schema validation on JSON |
| P3-10 | kast.py | Linear KAST heuristic diverges at edge cases, can exceed [0,1] before clamping |
| P3-11 | rating.py | Dead code `compute_hltv2_rating_regression()` still importable |
| P3-13 | role_features.py | ROLE_SIGNATURES centroids never updated by `meta_drift` |
| P3-14 | heatmap_engine.py | No max resolution cap — memory scales quadratically |
| P3-15 | cv_framebuffer.py | HUD coordinates hardcoded for specific CS2 UI layout |
| P3-16 | round_stats_builder.py | Flash assist uses fixed 2s window instead of actual flash duration |
| P3-17 | skill_assessment.py | Sigmoid CDF approximation deviates ~2% at tails |
| P3-22 | drift.py | `should_retrain()` threshold 3/5 has no hysteresis |
| P3-28 | pro_baseline.py | Survival rate approximation using `1 - dpr` is crude |
| P3-31 | meta_drift.py | Queries monolith tick data but detailed ticks live in per-match DBs |
| P3-32 | role_thresholds.py | Only 5 of 9 threshold types computed — 4 always None |
| P3-33 | role_thresholds.py | `persist_to_db()` no explicit transaction boundary |
| P3-35 | nickname_resolver.py | Case-sensitive SQL exact match forces O(n) fallback |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| P3-02 | data_pipeline.py | `_MAX_PIPELINE_ROWS = 50_000` not configurable |
| P3-03 | vectorizer.py | Unknown weapons silently default to "unknown" — no logging |
| P3-05 | tensor_factory.py | Lazy scipy import adds ~200-500ms on first heatmap |
| P3-08 | player_knowledge.py | Memory decay tau values not empirically validated |
| P3-12 | rating.py | KAST ratio vs percentage contract not enforced at function boundary |
| P3-19 | external_analytics.py | NaN skip count not reported |
| P3-20 | connect_map_context.py | Z-penalty factor same for all maps |
| P3-21 | dem_validator.py | 2GB max file size may be tight for 40+ round matches |
| P3-23 | drift.py | Z-score drift threshold 2.0 same for all features |
| P3-24 | schema.py | Schema validates 8 of 25 features |
| P3-25 | schema.py | Unknown schema version silently falls back to latest |
| P3-29 | pro_baseline.py | Mid-file imports (PEP 8 violation) |
| P3-34 | role_thresholds.py | `datetime.now()` without `timezone.utc` |

## Cross-Cutting

1. **Hardcoded CS2 Constants** — FOV, flash duration, HUD coordinates, trade window, kill max should be centralized in `cs2_constants.py`.
2. **Baseline Provenance Gap** — Consumers don't know which tier (DB/CSV/hardcoded) produced baseline data.
3. **Timezone Inconsistency** — Most pipeline uses UTC; `role_thresholds.py` uses naive datetime.
