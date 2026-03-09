# Deep Audit Report — Phase 2: Processing Pipeline

> **STATUS: HISTORICAL — All FIXED items removed (2026-03-08)**
> Cross-referenced against DEFERRALS.md. Only ACCEPTED design decisions and MONITORING items retained.

**Date:** 2026-02-27
**Files Audited:** 25 / 25
**Original Issues:** 42 (4 CRITICAL, 5 HIGH, 18 MEDIUM, 15 LOW)
**Remaining:** 13 (12 ACCEPTED + 1 MONITORING)

---

## Accepted Design Decisions (12)

| F-Code | File | Severity | Description |
|--------|------|----------|-------------|
| F2-02 | `tensor_factory.py:73` | MEDIUM | 128-dim output contract depends on RAPPerception's `input_dim`; change requires coordinated update across model and feature pipeline |
| F2-03 | `tensor_factory.py:54` | MEDIUM | `MAX_SPEED_UNITS_PER_TICK=4.0` calibrated for 64 tick/s; 128-tick demos (FACEIT/ESEA) may need adjustment |
| F2-04 | `tensor_factory.py:22` | LOW | scipy is a required dependency; import fails at module level if missing (intentional, listed in requirements) |
| F2-08 | `player_knowledge.py:514` | MEDIUM | Using SMOKE_RADIUS (200 units) as proxy for flash effective radius — no official CS2 source for flash radius |
| F2-10 | `round_stats_builder.py:65` | LOW | First round (i==0) start_tick=0 may include warmup ticks; not critical since demoparser2 typically excludes warmup |
| F2-15 | `vectorizer.py:191` | LOW | (0,0,0) could be valid position on some maps; sentinel check is heuristic |
| F2-20 | `role_features.py` | LOW | Role signatures (aggression, entry, support) are static heuristic approximations; drift captured by meta_drift.py |
| F2-35 | `kast.py:131` | LOW | KAST threshold is empirical observation at pro level; no formal statistical source |
| F2-40 | `rating.py:89` | LOW | Per-component average deliberately diverges from official HLTV 2.0 formula (two different computational paths by design) |
| F2-41 | `nickname_resolver.py` | MEDIUM | Substring + fuzzy lookup is O(n) per query, O(n^2) total — acceptable for <1000 players |
| F2-45 | `meta_drift.py:86` | LOW | 0/1e-6 = 0 keeps stat_drift at 0.0 in degenerate case — correct behavior |
| F2-46 | `connect_map_context.py` | LOW | Distance normalization constants are fixed per-map values |

## Monitoring Items (1)

| F-Code | File | Severity | Description |
|--------|------|----------|-------------|
| F2-19 | `role_thresholds.py:105` | MEDIUM | `validate_consistency()` is a stub returning `True` unconditionally; threshold validation checks individual values but not inter-threshold consistency (no gaps/overlaps between role boundaries) |
