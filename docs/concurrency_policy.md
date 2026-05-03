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
| `d_track_running` | D1, D2A, D2B, D2C, D3, D4, M1 tools | Main DB write in progress; HLTV daemon must pause; ad-hoc ingestion must refuse |
| `rollback` | `tools/rollback_to_baseline.py` | Restore in progress; nothing else may read or write either DB |
| `m2_demo_fetch` | `tools/fetch_hltv_demos.py` | Pulling .dem files from HLTV; rate-limited; do not start a second fetcher |
| `h3_player_sweep` | each `tools/hltv_full_backfill.py` sub-agent | One per agent slice; M3 must wait for all five to finish |

Locks reclaim automatically when the holder PID is dead
(`os.kill(pid, 0)` raises `ProcessLookupError`). Crashes do not
strand the lock file.

## Per-tool obligations

### D-track tools (D1, D2A, D2B, D2C, D3, M1)

```python
from Programma_CS2_RENAN.core import lock_files
lock_files.install_signal_handlers()
with lock_files.lock('d_track_running'):
    ...  # do migration work
```

Override flag for emergencies: `--i-stopped-the-daemon` skips the
lock check. Do not use unless the user has manually `pkill`ed the
HLTV daemon and confirmed via `ps aux | grep hltv_sync_service`
that nothing is running.

### HLTV daemon (`Programma_CS2_RENAN/hltv_sync_service.py`)

Inside `run_sync_loop`, before the per-cycle scrape:

```python
if lock_files.is_held('d_track_running'):
    logger.info('d_track_running held; pausing HLTV sync for 60s')
    time.sleep(60)
    continue   # skip this cycle, retry next iteration
```

Daemon does NOT exit when the lock is held. It pauses cycles. When
the lock is released, the next cycle proceeds normally.

### Ad-hoc demo ingestion (`run_ingestion._ingest_single_demo`)

Hard refusal:

```python
if lock_files.is_held('d_track_running'):
    raise RuntimeError(
        'D-track migration in progress (lock=d_track_running, '
        f'pid={lock_files.holder_pid("d_track_running")}). '
        'Re-run ingestion after the migration completes.'
    )
```

This propagates to the Qt app's "Analyze" button — the user sees
the error in the UI and knows to wait.

### Qt app launch

Read-only screens (dashboard, match history, performance) are
safe to use while D-track runs. Each query goes through
`db_manager.get_session()` which uses SQLite's deferred-transaction
read lock — does not block on the writer. The "Analyze" button
fails as above; the rest of the UI is unaffected.

### H-track tools (H2 fixture capture, H3 player sweep, M3 team/event)

Safe to run while D-track is running. Different DB
(`hltv_metadata.db`). The shared resource is FlareSolverr — H3
sub-agents stagger 30s on launch and FlareSolverr serves one
concurrent request at a time, so combined load stays bounded.

H3's per-agent lock (`h3_player_sweep_<n>`) prevents a second
invocation of the same slice from racing.

### M2 demo fetcher

Holds `m2_demo_fetch` lock. Does NOT acquire `d_track_running`
because it does not write to main DB until D2B re-runs against the
fetched files. M2 ↔ D-track ordering is enforced by phase
sequencing in the plan, not by locks.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `LockConflict` on D-track tool startup | Prior run crashed mid-flight, or HLTV daemon raced | Inspect `<repo_root>/.locks/d_track_running.lock`; if PID is dead, re-run (auto-reclaim); if PID is live, kill it deliberately |
| HLTV daemon pauses for hours during D1 | Expected — D1 takes 12-18h; daemon waits | Nothing to do; daemon resumes when D1 finishes |
| Qt app shows "D-track migration in progress" on Analyze click | Expected | User waits; lock releases when migration completes |
| WAL file grows unbounded during D1 | `PRAGMA wal_checkpoint(TRUNCATE)` not called between batches | D1 tool calls it every 10 demos per plan §4 |
| `database.db-shm` orphaned after crash | WAL not cleanly closed | `sqlite3 database.db "PRAGMA wal_checkpoint(TRUNCATE);"` reabsorbs the WAL into the main file |

## Verification

A short unit test under `tests/test_lock_files.py` covers the
locking primitives. Each D-track tool's CLI tests (under
`tests/tools/test_*.py`, added in V phase) verify the tool
acquires the lock at startup and releases it on `--dry-run` exit.
