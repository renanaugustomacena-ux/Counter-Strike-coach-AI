# Deep Audit Report — Phase 6: Core Engine + Data Sources + Ingestion

> **STATUS: HISTORICAL — All FIXED items removed (2026-03-08)**
> Cross-referenced against DEFERRALS.md. Only ACCEPTED design decisions and MONITORING items retained.

**Date:** 2026-02-27
**Files Audited:** 38 / 38
**Original Issues:** 34 (4 CRITICAL, 6 HIGH, 16 MEDIUM, 8 LOW)
**Remaining:** 9 (8 ACCEPTED + 1 MONITORING)

---

## Accepted Design Decisions (8)

| F-Code | File | Severity | Description |
|--------|------|----------|-------------|
| F6-02 | `browser/manager.py:44` | HIGH | Requires explicit ToS compliance sign-off before production HLTV scraping. Anti-bot evasion + spoofed UAs may violate HLTV Terms of Service |
| F6-06 | `session_engine.py:7` | LOW | `sys.path` bootstrap required when daemon executed directly as script. Acceptable for CLI entry points |
| F6-11 | `steam_locator.py:13` | MEDIUM | Steam path discovery duplicated with `steam_demo_finder.py` (different consumers, different fallback strategies) |
| F6-13 | `run_ingestion.py:327` | MEDIUM | Objects fetched in one session; do not access lazy-loaded attrs after close. Risk of `DetachedInstanceError` |
| F6-19 | `user_ingest.py:16` | MEDIUM | Legacy pipeline stores basic PlayerMatchStats only; RoundStats added separately via enrichment pipeline |
| F6-25 | `rate_limit.py:17` | LOW | Randomness intentionally unseeded — deterministic jitter would synchronize scrapers |
| F6-26 | `spatial_engine.py:16` | MEDIUM | Z coordinate ignored; multi-level maps (Nuke, Vertigo) place all players on same plane |
| F6-32 | `asset_manager.py:93` | LOW | Class-level mutable cache shared across all AssetAuthority instances; works because AssetAuthority is a singleton |

## Monitoring Items (1)

| F-Code | File | Severity | Description |
|--------|------|----------|-------------|
| F6-33 | `event_registry.py:32` | MEDIUM | Handler path references not validated at registration time. If handlers are moved or renamed, the registry becomes stale. No runtime validation of handler existence |
