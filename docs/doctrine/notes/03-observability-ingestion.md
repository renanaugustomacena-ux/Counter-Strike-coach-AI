# Cluster 03 — `observability/` + `ingestion/` + `backend/ingestion/`

Files read (all): observability/{logger_setup, error_codes, exceptions, label_source_monitor,
rasp, sentry_setup}; ingestion/{demo_loader, integrity, steam_locator,
pipelines/json_tournament_ingestor, pipelines/user_ingest, registry/{lifecycle, registry}};
backend/ingestion/{csv_migrator, resource_manager, watcher, match_date_resolver}.

## observability/

- `logger_setup.py`: single JSON RotatingFileHandler on the `cs2analyzer` parent logger (F-0011 — previously 187 loggers each had a handler on the same file). Per-process files via `CS2_LOG_ROLE` env. Thread-local correlation IDs (OBS-07). Lazy `app_logger` proxy (WR-26) so no handler exists before config wires LOG_DIR.
- `error_codes.py`: formal registry of the inline codes (LS/RP/DA/P/F/SE/IM/NN/G/H/CO/R1) with severity+remediation — the codebase's issue-ID convention is institutionalized.
- `label_source_monitor.py`: **G-01 telemetry** — every concept-alignment batch reports `round_stats` vs `skipped_no_round_stats`; sliding 5-min window alarms at >1% skipped (min 50 samples). "The concept-alignment path is degrading toward InfoNCE-only" is treated as a monitored failure mode of the AI. Passive: never blocks training. References CS2_Coach_Modernization_Report.pdf §9 + N=260 supplement.
- `rasp.py`: HMAC-signed integrity manifest; frozen builds REFUSE to start without CS2_MANIFEST_KEY (fail-closed, R4); dev warns and uses public key.
- `sentry_setup.py`: double opt-in (enabled + DSN), pytest-gated, PII scrubbing of home paths before events leave the process.
- `exceptions.py`: typed hierarchy (Configuration/Database/Ingestion/Training/Integration/UI errors) with optional error_code.

## ingestion/ (viewer-oriented) vs backend/ingestion/ (pipeline-oriented)

- `demo_loader.py`: the TACTICAL VIEWER's parser (frames for playback), separate from run_ingestion's DB path. 3-pass design: positions → grenade linking (throw↔detonate via steamid + ≤10s window; trajectory 2 points) → full tick frames (vectorized, searchsorted round index). Bomb state via sorted-pointer scan (WR-40). Cache: pickled result **HMAC-signed with a random persisted 0600 key** (BE-12/FE-02) and loaded through a **restricted unpickler allowlisting only demo_frame classes** (DS-01). Nade durations capped at heuristic ceiling carry `is_duration_estimated=True` (H-05/DS-14) — estimated data is FLAGGED, never silently mixed. `_quality_flags` propagated when pass 1 fails. NOTE: header tick_rate here defaults to 64.0 inline (demo_loader.py:719) — predates/bypasses `core.tick_rate.resolve_tick_rate`; viewer-only impact.
- `integrity.py`: thin wrapper over demo_format_adapter validation; legacy CS:GO demos rejected explicitly.
- `steam_locator.py`: registry → known paths → psutil drive sweep; queues found demos as user tasks. Duplicate authority acknowledged in-code (F6-11: steam_demo_finder.py is "supplementary"; this is primary).
- `registry/registry.py`: JSON processed-demos registry with threading.Lock + FileLock, backup + atomic replace, backup-recovery ladder, loud "Registry reset — all demo history lost!" as last resort.
- `pipelines/user_ingest.py`: user-demo path: stats + RoundStats/enrichment (F6-19: "leaving them at 0.0 fabricated coaching signal"), archive ONLY after full pipeline success (R3-H03).
- `pipelines/json_tournament_ingestor.py`: external tournament JSON → flat CSV with structure validation (R3-M17) and safe coercion (DS-04).

## backend/ingestion/

- `watcher.py`: watchdog FS events with size-stability debounce (2 stable checks @1s, max 120 attempts F6-16), min-size from the canonical demo_format_adapter constant (R3-M20), lock-probe before queueing, final TOCTOU existence check (IM-01), then event-driven `signal_work_available()` to wake the Digester.
- `resource_manager.py`: CPU throttling with 10s moving average + hysteresis (85%/70%), RAM>90% immediate, HP_MODE bypass; worker count: high-priority = cores-1, background = cores/4, throttled = 1. Windows priority classes.
- `match_date_resolver.py` (OI-2): **chronology honesty** — resolution ladder filename_date → filename_year → file_mtime → ingested_at, each with a provenance marker; `CHRONOLOGICAL_SOURCES` frozenset tells the split logic which rows carry REAL chronology. Reason: match_date used to default to now(), so "the chronological anti-leak split actually ordered by ingestion order".
- `csv_migrator.py`: external CSVs → Ext_ tables with idempotency checks; singleton DB accessor enforced (R4: direct DatabaseManager() forbidden — bypasses WAL/pooling config).

## Invariants observed (doctrine candidates)

- **Provenance over plausibility**: every derived value that could be wrong carries a source/quality marker (match_date_source, is_duration_estimated, _quality_flags, label_source). The system is designed so downstream consumers can distinguish measured from estimated from fabricated.
- **The chronological split is sacred**: OI-2 exists because ingestion-order masquerading as chronology silently invalidates the anti-leakage 70/15/15 split.
- **Concept labels have a monitored degradation path** (G-01): losing RoundStats coverage is an alarmed condition, not a silent fallback.
- **Security posture on caches**: anything pickled is HMAC-signed and allowlist-unpickled; keys are random, persisted 0600, and cache invalidates on key loss by design.
- **demoparser2 is a hostile boundary**: PyO3 can raise bare Exception/BaseException; every call site catches at the boundary with `is_parse_error` filtering (F-0006, #28.3) — narrowing there would "re-open the exact hole".
- **Event-driven over polling**: watcher signals the digester; daemons wait on events with timeout safety nets (IM-03 wait-then-clear ordering).

## Risks / open questions carried forward

- demo_loader.py:719 inline `tick_rate = header.get("tick_rate", 64.0) or 64.0` — does not use resolve_tick_rate; check whether test_tick_rate_ssot exempts it (viewer path).
- watcher.py:644 pro_path default is `os.path.expanduser("~")` and `os.makedirs(pro_path)` — tension with the F-0008 never-$HOME rule (watching $HOME non-recursively is benign but inconsistent).
- Two Steam-path authorities still coexist (steam_locator vs steam_demo_finder, F6-11 acknowledged).
- config.py ZOMBIE default 300 vs P4-B 1800 (carried from cluster 02).
