# Audit Report 07 — Data Ingestion & Sources

**Scope:** `backend/data_sources/`, `ingestion/`, `backend/ingestion/` — 30 files, ~4,684 lines | **Date:** 2026-03-10
**Open findings:** 0 HIGH | 14 MEDIUM | 11 LOW

---

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| D-01 | demo_parser.py | ThreadPoolExecutor with single worker provides no parallelism (timeout enforcement only) |
| D-04 | demo_parser.py | `parse_demo()` returns empty dict on failure — no structured error category |
| D-08 | event_registry.py | Coverage report ignores severity weighting |
| D-10 | faceit_api.py | No rate limiting or retry (vs faceit_integration.py which has full hardening) |
| D-11 | faceit_api.py | API key in query parameter instead of Authorization header |
| D-13 | faceit_integration.py | `download_demo()` no total size limit on streaming response |
| D-16 | steam_demo_finder.py | Duplicate Steam path discovery (same as steam_locator.py) |
| D-18 | trade_kill_detector.py | `TRADE_WINDOW_TICKS = 192` hardcoded for 64-tick — breaks on other tick rates |
| D-19 | docker_manager.py | Italian log messages (rest of codebase uses English) |
| D-21 | flaresolverr_client.py | No retry logic for session creation/destruction |
| D-24 | stat_fetcher.py | `_safe_float()` returns 0.0 for unknowns — misleading for stats like rating |
| D-25 | stat_fetcher.py | Partial scrape data saved without completeness flag |
| D-27 | demo_loader.py | `_SafeUnpickler` allowlist could still construct memory-consuming objects |
| D-30 | json_tournament_ingestor.py | Derived metrics stored at ingestion time — stale if formula changes |
| D-31 | user_ingest.py | Only PlayerMatchStats stored — no RoundStats for user demos |
| D-33 | csv_migrator.py | Per-row idempotency SELECT for every row on large CSVs |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| D-02 | demo_parser.py | Approximate HLTV 2.0 rating — coefficients may drift |
| D-03 | demo_parser.py | `data_quality="partial"` flag not checked by downstream consumers |
| D-05 | demo_format_adapter.py | MIN_DEMO_SIZE 10MB vs watcher 5MB — two different thresholds |
| D-06 | demo_format_adapter.py | PROTO_CHANGELOG dict never programmatically consumed |
| D-09 | event_registry.py | `handler_path` field never validated at runtime |
| D-12 | faceit_integration.py | Duplicates ~60% of faceit_api.py intent |
| D-14 | round_context.py | `merge_asof` relies on pre-sorted `round_df` — no assertion |
| D-17 | steam_demo_finder.py | Hardcoded drive letters may miss non-standard installations |
| D-28 | demo_loader.py | HMAC key rotation silently invalidates all caches (not documented) |
| D-29 | steam_locator.py | Duplicate of steam_demo_finder.py (F6-11) |
| D-32 | lifecycle.py | `purge_old_demos()` deletes files but not DB records — orphans |
| D-34 | watcher.py | MIN_DEMO_SIZE inconsistency with demo_format_adapter.py |

## Cross-Cutting

1. **Duplicate Clients** — steam_locator.py vs steam_demo_finder.py (~150 lines duplication); faceit_api.py vs faceit_integration.py (vastly different quality).
2. **Italian Log Messages** — docker_manager.py breaks English-only logging convention.
3. **Derived Metric Storage** — Both json_tournament_ingestor.py and csv_migrator.py compute/store derived metrics at ingestion time.
