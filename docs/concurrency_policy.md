# Concurrency policy — Data Restoration Plan v3

`database.db` is single-writer under SQLite WAL. The v3 plan runs
long-lived migrations (D1 ≈ 12-18h tick imports; D2A ≈ 4-6h SQL
re-aggregations; D3 ≈ 3-5h corrupted-match recovery; M1 ≈ 1-2h
match-level aggregations) that hold a write transaction across
many demos. Concurrent writers — `hltv_sync_service`, ad-hoc
`run_ingestion`, the Qt app's "Analyze" button — must pause for
the duration to prevent WAL contention and corruption.

## Lock semantics

`Programma_CS2_RENAN/core/lock_files.py` provides named lock files
under `<repo_root>/.locks/<name>.lock`. Format: `<pid> <iso_timestamp>`.

| Lock name | Held by | Means |
|---|---|---|
| `d_track_running` | `tools/rebuild_monolith.py` (D1) and `Programma_CS2_RENAN/tools/aggregate_match_stats_sql.py` (D2A, `--commit` mode) | Main DB write in progress; do not run the HLTV daemon, ad-hoc ingestion, or the Qt "Analyze" button |
| `rollback` | The manual rollback procedure (`docs/rollback_procedure.md`) — acquired via `lock_files.acquire('rollback')`; there is no dedicated rollback tool | Restore in progress; nothing else may read or write either DB |
| `hltv_schema_migration` | `Programma_CS2_RENAN/tools/migrate_hltv_schema_2026_05.py` | HLTV metadata schema migration in progress (touches `hltv_metadata.db`, not the main DB) |

The plan also defined `m2_demo_fetch` (HLTV demo fetcher) and
`h3_player_sweep` (per-agent HLTV backfill slices), but those tools
were never shipped — no code acquires these locks today.

Locks reclaim automatically when the holder PID is dead (liveness is
checked cross-platform: `OpenProcess` on Windows, `os.kill(pid, 0)`
on POSIX). Crashes do not strand the lock file.

## Per-tool obligations

### D-track tools (`rebuild_monolith.py`, `aggregate_match_stats_sql.py`)

```python
from Programma_CS2_RENAN.core import lock_files
lock_files.install_signal_handlers()
with lock_files.lock('d_track_running'):
    ...  # do migration work
```

Both tools accept a `--no-lock` escape hatch that skips the lock
check. Do not use it unless you have manually stopped the HLTV
daemon and confirmed via `ps aux | grep hltv_sync_service` (or Task
Manager on Windows) that nothing else is running.

### HLTV daemon (`Programma_CS2_RENAN/hltv_sync_service.py`)

The daemon does **not** check `d_track_running` — the pause-on-lock
behavior described in earlier drafts of this policy was never
implemented. Before starting a D-track migration, stop the daemon
manually: create its stop-signal file
(`Programma_CS2_RENAN/hltv_sync.stop`) or kill the PID recorded in
`Programma_CS2_RENAN/hltv_sync.pid`, and restart it after the
migration completes.

### Ad-hoc demo ingestion (`run_ingestion` / `run_worker`)

Ingestion does **not** check `d_track_running` either. Do not start
`Programma_CS2_RENAN/run_ingestion.py`, `run_worker.py`,
`batch_ingest.py`, or the Qt app's "Analyze" button while a D-track
migration is running — operator discipline is the only guard.

### Qt app launch

Read-only screens (dashboard, match history, performance) are
generally safe to use while D-track runs. Each query goes through
`db_manager.get_session()` and SQLite's WAL read path — reads do not
block on the writer. Avoid the "Analyze" button (see above); the rest
of the UI is unaffected.

### HLTV-side tools

Tools that only touch `hltv_metadata.db` (`tools/seed_hltv_top_n.py`,
`tools/rescrape_placeholder_pros.py`,
`Programma_CS2_RENAN/tools/migrate_hltv_schema_2026_05.py`, …) are
safe to run while D-track is running — different DB. (Note:
`tools/sync_pro_players.py` writes to the MAIN DB — treat it like a
D-track writer, not an HLTV-side tool.) The shared
resource is FlareSolverr, which serves one request at a time, so
combined scraping load stays bounded; don't run two scrapers at once.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `LockConflict` on D-track tool startup | Prior run crashed mid-flight, or another migration is live | Inspect `<repo_root>/.locks/d_track_running.lock`; if PID is dead, re-run (auto-reclaim); if PID is live, kill it deliberately |
| HLTV daemon writes during D1 | Daemon was not stopped before the migration | Stop it (stop-signal file or kill PID) and check the run's output for contention errors |
| WAL file grows unbounded during D1 | Periodic checkpointing disabled | Run `rebuild_monolith.py` with `--wal-checkpoint-every 10` to `PRAGMA wal_checkpoint(TRUNCATE)` every 10 demos |
| `database.db-shm` orphaned after crash | WAL not cleanly closed | `sqlite3 database.db "PRAGMA wal_checkpoint(TRUNCATE);"` reabsorbs the WAL into the main file |

## Verification

A unit test under `tests/test_lock_files.py` covers the locking
primitives (acquire/release/conflict, dead-PID reclaim, context
manager, signal handlers).
